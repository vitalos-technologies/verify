"""Verifier: behaviours whose guards survive mutation of the implementer's suite."""
from __future__ import annotations

from conftest import applicant_ready, create_session, drain, idem, run_capture


def _view(client, t, sid):
    return client.get(f"/v1/verifications/{sid}", headers=t.headers).json()


def test_late_event_for_superseded_attempt_is_ignored(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    att1 = run_capture(client, "low_quality")
    drain(worker)
    assert _view(client, t, sid)["state"] == "action_required"
    att2 = client.post("/applicant/attempts").json()
    assert att2["attempt_id"] != att1["attempt_id"]
    ref1 = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att1["attempt_id"],)).fetchone()[
        "provider_reference"]
    dummy = client.app.state.vv.providers["dummy"]
    body, h = dummy.build_callback(ref1, event_id=f"dmyevt_late_super_{sid}")
    assert client.post("/callbacks/dummy", content=body, headers=h).status_code == 202
    drain(worker)
    assert _view(client, t, sid)["state"] == "in_progress"
    st = owner.execute("SELECT processing_state FROM provider_events WHERE event_id = %s",
                       (f"dmyevt_late_super_{sid}",)).fetchone()
    assert st["processing_state"] == "ignored"


def test_late_event_for_review_required_session(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    att = run_capture(client, "liveness_inconclusive")
    drain(worker)
    ref = owner.execute("SELECT provider_reference FROM attempts WHERE id = %s", (att["attempt_id"],)).fetchone()[
        "provider_reference"]
    dummy = client.app.state.vv.providers["dummy"]
    body, h = dummy.build_callback(ref, event_id=f"dmyevt_late_rr_{sid}")
    client.post("/callbacks/dummy", content=body, headers=h)
    drain(worker)
    assert _view(client, t, sid)["state"] == "review_required"


def test_attempt_requires_notice_and_contact(client, make_tenant):
    t = make_tenant()
    c = create_session(client, t)
    tok = c["hosted_url"].rsplit("/", 1)[1]
    assert client.post("/applicant/exchange", json={"token": tok}).status_code == 200
    r = client.post("/applicant/attempts")
    assert r.status_code == 409 and r.json()["code"] == "notice_required"
    assert client.post("/applicant/notice", json={"notice_version": "notice-synthetic-1"}).status_code == 200
    assert client.post("/applicant/notice", json={"notice_version": "old"}).status_code == 409
    r = client.post("/applicant/attempts")
    assert r.status_code == 409 and r.json()["code"] == "contact_required"


def test_suspended_key_and_billing_hold(client, make_tenant, owner):
    t = make_tenant()
    owner.execute("UPDATE tenants SET status = 'billing_hold' WHERE id = %s", (t.id,))
    r = client.post("/v1/verifications", json={"external_reference": "bh", "policy_id": "workforce_identity",
                    "policy_version": 1, "country": "ZZ", "document_type": "passport"}, headers={**t.headers, **idem()})
    assert r.status_code == 403 and r.json()["code"] == "billing_hold"
    owner.execute("UPDATE tenants SET status = 'suspended' WHERE id = %s", (t.id,))
    assert client.get("/v1/verifications", headers=t.headers).status_code == 403


def test_console_absolute_timeout(client, make_tenant, owner):
    t = make_tenant()
    csrf = client.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject}).json()[
        "csrf_token"]
    owner.execute("UPDATE console_sessions SET absolute_expires_at = now() - interval '1 second' WHERE tenant_id = %s",
                  (t.id,))
    assert client.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                       headers={"X-CSRF-Token": csrf}).status_code == 401


def test_reviewer_action_required_then_retry_limit(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    owner.execute("UPDATE sessions SET quality_retries_used = 2 WHERE id = %s", (sid,))
    run_capture(client, "liveness_inconclusive")
    drain(worker)
    v = _view(client, t, sid)
    r = client.post(f"/v1/verifications/{sid}/decisions", headers={**t.headers, **idem()},
                    json={"expected_revision": v["revision"], "outcome": "action_required", "reason": "retake please",
                          "method": "evidence_review", "evidence_ids": [v["checks"][0]["id"]]})
    assert r.status_code == 200
    r = client.post("/applicant/attempts")
    print("attempt after retry budget exhausted:", r.status_code, r.json().get("code"))
    assert r.status_code == 409 and r.json()["code"] == "retry_limit_reached"
