"""AT-12 invoice integrity (VV-012): one charge per completed verification, append-only credits, reconciliation."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import psycopg
import pytest
from conftest import APP_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient

PERIOD = datetime.now(UTC).strftime("%Y-%m")


def _owner_browser(client, t):
    csrf = client.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject}).json()
    client.headers.update({"X-CSRF-Token": csrf["csrf_token"]})
    return client


def _complete(client, worker, t, settings, scenario="all_pass", ref="bill"):
    with TestClient(client.app) as b:
        c = create_session(b, t, ref=ref)
        applicant_ready(b, c["hosted_url"], settings)
        att = run_capture(b, scenario)
    drain(worker)
    return c["session"]["id"], att


def test_charges_only_completed_and_never_twice(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    approved, att = _complete(client, worker, t, settings, ref="b1")
    _complete(client, worker, t, settings, "provider_error", ref="b2")  # technical failure: no charge
    expired = create_session(client, t, ref="b3")["session"]["id"]
    owner.execute("UPDATE sessions SET expires_at = now() - interval '1 second' WHERE id = %s", (expired,))
    review, _ = _complete(client, worker, t, settings, "liveness_inconclusive", ref="b4")
    drain(worker, 1)
    # Duplicate/late callback for the approved session does not re-charge.
    ref = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att["attempt_id"],)).fetchone()
    dummy = client.app.state.vv.providers["dummy"]
    body, headers = dummy.build_callback(ref["provider_reference"])
    client.post("/callbacks/dummy", content=body, headers=headers)
    drain(worker)
    # Review decision completes the 4th session: charged once at that point.
    v = client.get(f"/v1/verifications/{review}", headers=t.headers).json()
    client.post(f"/v1/verifications/{review}/decisions", headers={**t.headers, **idem()},
                json={"expected_revision": v["revision"], "outcome": "declined", "method": "evidence_review",
                      "reason": "Could not confirm liveness", "evidence_ids": [v["checks"][0]["id"]]})
    charges = owner.execute("SELECT session_id FROM usage_events WHERE tenant_id = %s AND charge_type = "
                            "'completed_verification' ORDER BY session_id", (t.id,)).fetchall()
    assert sorted(c["session_id"] for c in charges) == sorted([approved, review])
    s = _owner_browser(client, t).get("/console/usage", params={"period": PERIOD}).json()
    line = next(x for x in s["lines"] if x["charge_type"] == "completed_verification")
    assert line == {"charge_type": "completed_verification", "quantity": 2, "amount_minor": 500}
    assert s["pricing_status"] == "hypothesis_not_approved_price"


def test_credits_append_and_cannot_exceed_charge(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid, _ = _complete(client, worker, t, settings, ref="c1")
    b = _owner_browser(client, t)
    key = f"complete:{sid}"
    r = b.post("/console/usage/credits", json={"ledger_key": key, "amount_minor": 100, "reason": "Support goodwill"})
    assert r.status_code == 201
    results = []

    def go():
        with TestClient(client.app) as c:
            c.cookies.update(b.cookies)
            c.headers.update(b.headers)
            results.append(c.post("/console/usage/credits",
                                  json={"ledger_key": key, "amount_minor": 100, "reason": "Concurrent credit"}))

    threads = [threading.Thread(target=go) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(r.status_code for r in results) == [201, 409, 409, 409]  # 250 max: 100 + 100 then refused
    total = owner.execute("SELECT sum(amount_minor) AS s FROM usage_events WHERE tenant_id = %s AND "
                          "charge_type IN ('completed_verification','credit')", (t.id,)).fetchone()["s"]
    assert total == 50
    with psycopg.connect(APP_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE usage_events SET amount_minor = 0 WHERE tenant_id = %s", (t.id,))
    assert b.post("/console/usage/credits", json={"ledger_key": "complete:nope", "amount_minor": 1,
                                                  "reason": "Unknown"}).status_code == 404


def test_invoice_issued_once_after_period_and_immutable(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    _complete(client, worker, t, settings, ref="i1")
    b = _owner_browser(client, t)
    assert b.post(f"/console/invoices/{PERIOD}/issue").status_code == 409  # period still open
    past = "2026-01"  # move this ledger into a closed period (test-only owner bypass of the append-only trigger)
    owner.execute("ALTER TABLE usage_events DISABLE TRIGGER usage_append_only")
    try:
        owner.execute("UPDATE usage_events SET created_at = '2026-01-15' WHERE tenant_id = %s", (t.id,))
    finally:
        owner.execute("ALTER TABLE usage_events ENABLE TRIGGER usage_append_only")
    inv = b.post(f"/console/invoices/{past}/issue")
    assert inv.status_code == 201 and inv.json()["total_minor"] == 255  # 250 verification + 5 message
    assert b.post(f"/console/invoices/{past}/issue").status_code == 409
    with psycopg.connect(APP_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE invoices SET total_minor = 0")
    assert b.get("/console/usage", params={"period": "2026-13"}).status_code == 400


def test_supplier_reconciliation(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid, att = _complete(client, worker, t, settings, ref="r1")
    with TestClient(client.app) as br:  # second attempt never completed (abandoned) but billed by supplier
        c = create_session(br, t, ref="r2")
        applicant_ready(br, c["hosted_url"], settings)
        att2 = br.post("/applicant/attempts").json()
    refs = {r["id"]: r["provider_reference"] for r in owner.execute(
        "SELECT id, provider_reference FROM attempts WHERE tenant_id = %s", (t.id,)).fetchall()}
    lines = [{"provider_reference": refs[att["attempt_id"]]}, {"provider_reference": refs[att["attempt_id"]]},
             {"provider_reference": refs[att2["attempt_id"]]}, {"provider_reference": "dmyref_foreign"}]
    rep = _owner_browser(client, t).post("/console/usage/reconcile", json={"period": PERIOD, "lines": lines}).json()
    assert rep["supplier_duplicates"] == [refs[att["attempt_id"]]]
    assert rep["unknown_to_us"] == ["dmyref_foreign"]
    assert rep["billed_attempt_not_charged"] == [refs[att2["attempt_id"]]]
    assert rep["not_billed_by_supplier"] == []
