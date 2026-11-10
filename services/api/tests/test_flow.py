"""End-to-end decision pipeline with the dummy provider (AT-05, AT-06, AT-07)."""

from __future__ import annotations

import time

import psycopg
from conftest import APP_DSN, applicant_ready, create_session, drain, idem, run_capture
from psycopg.rows import dict_row

from vv.admin import DEV_POLICY


def _get(client, tenant, sid):
    r = client.get(f"/v1/verifications/{sid}", headers=tenant.headers)
    assert r.status_code == 200, r.text
    return r.json()


def _checks(view):
    return {c["type"]: c for c in view["checks"]}


def test_happy_path_approves_only_after_authoritative_fetch(client, worker, make_tenant, settings):
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    assert created["session"]["state"] == "created"
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "all_pass")
    # Client said "submitted" and a valid callback arrived, but nothing is approved until the worker fetches.
    assert _get(client, t, sid)["state"] == "processing"
    drain(worker)
    view = _get(client, t, sid)
    assert view["state"] == "approved"
    checks = _checks(view)
    assert {k: v["result"] for k, v in checks.items()} == {
        "government_id": "pass", "face_match": "pass", "liveness": "pass", "email": "pass"}
    assert checks["liveness"]["provider_version"] == "dummy-1.0.0"


def test_missing_liveness_never_approves_and_stays_visible(client, worker, make_tenant, settings):  # AT-05
    t = make_tenant()
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "liveness_missing")
    drain(worker)
    view = _get(client, t, created["session"]["id"])
    assert view["state"] == "review_required"
    live = _checks(view)["liveness"]
    assert live["result"] == "not_run" and "evidence.missing" in live["reasons"]


def test_inconclusive_liveness_routes_to_review(client, worker, make_tenant, settings):  # AT-05
    t = make_tenant()
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "liveness_inconclusive")
    drain(worker)
    view = _get(client, t, created["session"]["id"])
    assert view["state"] == "review_required"
    assert _checks(view)["liveness"]["result"] == "inconclusive"


def test_suspected_attack_routes_to_review_not_decline(client, worker, make_tenant, settings):
    t = make_tenant()
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "liveness_attack")
    drain(worker)
    assert _get(client, t, created["session"]["id"])["state"] == "review_required"


def test_provider_error_check_is_error_not_fail(client, worker, make_tenant, settings):
    t = make_tenant()
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "provider_error")
    drain(worker)
    view = _get(client, t, created["session"]["id"])
    assert view["state"] == "error"
    assert _checks(view)["government_id"]["result"] == "error"


def test_provider_outage_retries_then_errors_without_decline(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "provider_outage")
    for _ in range(6):
        drain(worker, 1)
        owner.execute("UPDATE provider_events SET next_attempt_at = now() WHERE session_id = %s OR session_id IS NULL",
                      (sid,))
    view = _get(client, t, sid)
    assert view["state"] == "error"
    assert owner.execute("SELECT count(*) AS n FROM decisions WHERE session_id = %s", (sid,)).fetchone()["n"] == 0


def test_forged_and_stale_callbacks_rejected(client, worker, make_tenant, settings, owner):  # AT-06
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    applicant_ready(client, created["hosted_url"], settings)
    att = client.post("/applicant/attempts").json()
    ref = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att["attempt_id"],)).fetchone()[
        "provider_reference"]
    dummy = client.app.state.vv.providers["dummy"]
    body, headers = dummy.build_callback(ref)
    bad = dict(headers, **{"X-Dummy-Signature": "v1=" + "0" * 64})
    assert client.post("/callbacks/dummy", content=body, headers=bad).status_code == 401
    body2, stale = dummy.build_callback(ref, timestamp=int(time.time()) - 3600)
    assert client.post("/callbacks/dummy", content=body2, headers=stale).status_code == 401
    tampered = body.replace(ref.encode(), b"dmyref_other")
    assert client.post("/callbacks/dummy", content=tampered, headers=headers).status_code == 401
    assert owner.execute("SELECT count(*) AS n FROM provider_events WHERE provider_reference = %s",
                         (ref,)).fetchone()["n"] == 0
    # A correctly signed callback before capture completes cannot approve: authoritative result is still pending.
    assert client.post("/callbacks/dummy", content=body, headers=headers).status_code == 202
    client.post(f"/applicant/attempts/{att['attempt_id']}/submitted")  # client SDK "success" hint
    drain(worker)
    assert _get(client, t, sid)["state"] == "processing"


def test_callback_for_unknown_reference_is_quarantined(client, worker, owner):
    dummy = client.app.state.vv.providers["dummy"]
    body, headers = dummy.build_callback("dmyref_does_not_exist", event_id="dmyevt_unknown_ref")
    assert client.post("/callbacks/dummy", content=body, headers=headers).status_code == 202
    drain(worker, 1)
    row = owner.execute("SELECT processing_state FROM provider_events WHERE event_id = 'dmyevt_unknown_ref'").fetchone()
    assert row["processing_state"] == "quarantined"


def test_duplicate_and_late_callbacks_do_not_change_decision(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    applicant_ready(client, created["hosted_url"], settings)
    att = run_capture(client, "all_pass")
    drain(worker)
    before = _get(client, t, sid)
    ref = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att["attempt_id"],)).fetchone()[
        "provider_reference"]
    dummy = client.app.state.vv.providers["dummy"]
    body, headers = dummy.build_callback(ref, event_id="dmyevt_late_1")
    assert client.post("/callbacks/dummy", content=body, headers=headers).status_code == 202
    assert client.post("/callbacks/dummy", content=body, headers=headers).status_code == 202  # duplicate
    drain(worker)
    after = _get(client, t, sid)
    assert after == before
    st = owner.execute("SELECT processing_state FROM provider_events WHERE event_id = 'dmyevt_late_1'").fetchone()
    assert st["processing_state"] == "ignored"
    assert owner.execute("SELECT count(*) AS n FROM decisions WHERE session_id = %s", (sid,)).fetchone()["n"] == 1


def test_frozen_policy_version_and_reproducible_trace(client, worker, make_tenant, settings, owner):  # AT-07
    t = make_tenant()
    created = create_session(client, t)  # bound to v1 (quality_retries=2)
    sid = created["session"]["id"]
    # Publish v2 (no quality retries) while v1 session is in flight.
    v2 = dict(DEV_POLICY, version=2, quality_retries=0)
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        from vv import service
        from vv.domain.coverage import CoverageRegistry
        service.create_policy_draft(conn, t.id, v2)
        service.publish_policy(conn, t.id, "workforce_identity", 2, CoverageRegistry.load(settings.coverage_path), 250)
        conn.commit()
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "low_quality")
    drain(worker)
    view = _get(client, t, sid)
    assert view["policy_version"] == 1
    assert view["state"] == "action_required"  # v1 allows retries; v2 would have routed to review
    dec = owner.execute("SELECT * FROM decisions WHERE session_id = %s", (sid,)).fetchone()
    assert dec["policy_version"] == 1 and dec["trace"]["engine"] == "policy-engine/1"
    # Replay v1 evidence through the engine: identical outcome and trace.
    from vv.domain.policy import CheckView, evaluate
    pol = owner.execute("SELECT definition FROM policies WHERE id = %s", (dec["policy_row_id"],)).fetchone()
    rows = owner.execute("SELECT * FROM checks WHERE id = ANY(%s) OR (session_id = %s AND attempt_id IS NULL) "
                         "ORDER BY created_at, id", (dec["evidence_check_ids"], sid)).fetchall()
    replay = evaluate(pol["definition"], [CheckView(r["id"], r["type"], r["result"], tuple(r["reasons"]))
                                          for r in rows], quality_retries_used=0)
    assert replay.outcome == dec["outcome"]
    assert replay.trace == dec["trace"]["steps"]
    # New sessions with v2 use v2.
    r = client.post("/v1/verifications", json={"external_reference": "w-v2", "policy_id": "workforce_identity",
                                               "policy_version": 2, "country": "ZZ", "document_type": "passport"},
                    headers={**t.headers, **idem()})
    assert r.status_code == 201 and r.json()["session"]["policy_version"] == 2


def test_quality_retry_then_success(client, worker, make_tenant, settings):
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "low_quality")
    drain(worker)
    assert _get(client, t, sid)["state"] == "action_required"
    run_capture(client, "all_pass")
    drain(worker)
    view = _get(client, t, sid)
    assert view["state"] == "approved"
    assert _checks(view)["government_id"]["result"] == "pass"
