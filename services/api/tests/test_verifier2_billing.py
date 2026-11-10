"""Independent verifier (AT-12): double-charge paths, credit races, invoice immutability, period handling."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import psycopg
from conftest import APP_DSN, OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv import billing
from vv.admin import add_member

PERIOD = datetime.now(UTC).strftime("%Y-%m")


def _owner(app, t):
    c = TestClient(app)
    c.__enter__()
    csrf = c.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject}).json()
    c.headers.update({"X-CSRF-Token": csrf["csrf_token"]})
    return c


def _charges(owner, sid):
    return owner.execute("SELECT charge_type, amount_minor FROM usage_events WHERE session_id = %s "
                         "AND charge_type IN ('completed_verification','credit') ORDER BY created_at", (sid,)).fetchall()


def test_review_then_appeal_then_replay_charges_once(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t, ref="v2-bill-appeal")
    applicant_ready(client, c["hosted_url"], settings)
    att = run_capture(client, "liveness_fail")
    drain(worker)
    sid = c["session"]["id"]
    view = client.get(f"/v1/verifications/{sid}", headers=t.headers).json()
    assert _charges(owner, sid) == []  # review_required: not yet chargeable
    body = {"expected_revision": view["revision"], "outcome": "declined", "reason": "Evidence does not match",
            "method": "evidence_review", "evidence_ids": [view["checks"][0]["id"]]}
    # Concurrent API decisions (same body, different idempotency keys): one wins, one charge.
    results = []

    def go():
        with TestClient(client.app) as b:
            results.append(b.post(f"/v1/verifications/{sid}/decisions", json=body,
                                  headers={**t.headers, **idem()}).status_code)
    ths = [threading.Thread(target=go) for _ in range(4)]
    [x.start() for x in ths]
    [x.join() for x in ths]
    assert sorted(results).count(200) == 1, results
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        add_member(conn, t.id, f"v2-rev-{t.id}@synthetic.example", "reviewer")
    o = _owner(client.app, t)
    ap = o.post(f"/console/verifications/{sid}/appeals", json={"summary": "Applicant disputes decline"}).json()
    o.post(f"/console/appeals/{ap['id']}/claim")
    s = client.get(f"/v1/verifications/{sid}", headers=t.headers).json()
    r = o.post(f"/console/appeals/{ap['id']}/resolve",
               json={"expected_revision": s["revision"], "outcome": "approved", "method": "alternative_method",
                     "reason": "In-person check passed", "evidence_ids": [view["checks"][0]["id"]]})
    assert r.status_code == 200, r.text
    # Duplicate provider callback / replay
    ref = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att["attempt_id"],)).fetchone()
    dummy = client.app.state.vv.providers["dummy"]
    raw, headers = dummy.build_callback(ref["provider_reference"])
    from vv import events
    events.ingest_callback(client.app.state.vv.db, dummy, settings.data_key, raw, headers)
    drain(worker)
    assert [x["charge_type"] for x in _charges(owner, sid)] == ["completed_verification"]
    o.__exit__(None, None, None)


def test_concurrent_credits_capped(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t, ref="v2-credit")
    applicant_ready(client, c["hosted_url"], settings)
    run_capture(client, "all_pass")
    drain(worker)
    sid = c["session"]["id"]
    key = f"complete:{sid}"
    ok, bad = [], []
    barrier = threading.Barrier(6)

    def go():
        with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (t.id,))
            barrier.wait()
            try:
                billing.add_credit(conn, t.id, key, 100, "goodwill credit", "pytest")
                conn.commit()
                ok.append(1)
            except Exception:  # noqa: BLE001
                conn.rollback()
                bad.append(1)
    ths = [threading.Thread(target=go) for _ in range(6)]
    [x.start() for x in ths]
    [x.join() for x in ths]
    total = owner.execute("SELECT -sum(amount_minor) AS c FROM usage_events WHERE credit_for = %s", (key,)).fetchone()
    assert total["c"] <= 250 and len(ok) == 2, (len(ok), total)
    # credit against a credit/reservation key is refused
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (t.id,))
        for k in (f"reserve:{sid}", f"credit:{key}:1"):
            try:
                billing.add_credit(conn, t.id, k, 1, "bad credit", "pytest")
                raise AssertionError(f"credit accepted for {k}")
            except billing.ApiError:
                conn.rollback()
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (t.id,))
    # other tenant cannot credit this charge
    other = make_tenant()
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (other.id,))
        try:
            billing.add_credit(conn, other.id, key, 1, "cross tenant", "pytest")
            raise AssertionError("cross-tenant credit")
        except billing.ApiError as e:
            assert e.status == 404


def test_invoice_period_rules_and_immutability(client, make_tenant, owner):
    t = make_tenant()
    o = _owner(client.app, t)
    for bad in ("2026-13", "2026-1", "26-11", "2026-11-01", "../x"):
        assert o.post(f"/console/invoices/{bad}/issue").status_code in (400, 404), bad
    assert o.post(f"/console/invoices/{PERIOD}/issue").json()["code"] == "period_open"
    assert o.post("/console/invoices/2999-01/issue").json()["code"] == "period_open"
    r = o.post("/console/invoices/2020-01/issue")
    assert r.status_code == 201
    assert o.post("/console/invoices/2020-01/issue").status_code == 409
    with psycopg.connect(APP_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        for sql in ("UPDATE invoices SET total_minor = 0", "DELETE FROM invoices"):
            try:
                conn.execute(sql)
                raise AssertionError(sql)
            except psycopg.Error:
                conn.rollback()
                conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
    # reviewer cannot see billing
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        add_member(conn, t.id, f"v2-r-{t.id}@synthetic.example", "reviewer")
    with TestClient(client.app) as rv:
        rv.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": f"v2-r-{t.id}@synthetic.example"})
        assert rv.get("/console/usage", params={"period": PERIOD}).status_code == 403
    o.__exit__(None, None, None)
