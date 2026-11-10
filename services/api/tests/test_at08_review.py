"""Reviewer decisions (VV-008 groundwork; leases/appeals are M05): revisions, immutability, alternative method."""

from __future__ import annotations

import psycopg
import pytest
from conftest import APP_DSN, applicant_ready, create_session, drain, idem, run_capture


def _review_case(client, worker, t, settings, scenario="liveness_fail"):
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, scenario)
    drain(worker)
    view = client.get(f"/v1/verifications/{created['session']['id']}", headers=t.headers).json()
    assert view["state"] == "review_required"
    return view


def _decide(client, t, view, **over):
    body = {"expected_revision": view["revision"], "outcome": "approved", "reason": "Checked alternative evidence",
            "method": "alternative_method", "evidence_ids": [c["id"] for c in view["checks"]
                                                              if not c["id"].startswith("chk_pending")]}
    body.update(over)
    return client.post(f"/v1/verifications/{view['id']}/decisions", json=body, headers={**t.headers, **idem()})


def test_cannot_assert_biometric_pass_contrary_to_evidence(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    r = _decide(client, t, view, method="evidence_review")
    assert r.status_code == 422 and r.json()["code"] == "review.alternative_method_required"
    r = _decide(client, t, view)
    assert r.status_code == 200
    out = r.json()
    assert out["state"] == "approved"
    live = {c["type"]: c for c in out["checks"]}["liveness"]
    assert live["result"] == "fail"  # original check unchanged


def test_stale_revision_conflicts_and_only_one_reviewer_wins(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    view = _review_case(client, worker, t, settings, "liveness_inconclusive")
    first = _decide(client, t, view, outcome="declined", method="evidence_review", reason="Reviewer A declines case")
    second = _decide(client, t, view, reason="Reviewer B approves stale case")
    assert first.status_code == 200 and second.status_code == 409
    assert second.json()["code"] == "revision.stale"
    decisions = owner.execute("SELECT revision, actor_type, outcome, method FROM decisions WHERE session_id = %s "
                              "ORDER BY revision", (view["id"],)).fetchall()
    assert [(d["actor_type"], d["outcome"]) for d in decisions] == [("policy_engine", "review_required"),
                                                                     ("reviewer", "declined")]


def test_unknown_evidence_rejected_and_idempotent_replay(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    r = _decide(client, t, view, evidence_ids=["chk_from_elsewhere"])
    assert r.status_code == 422
    body = {"expected_revision": view["revision"], "outcome": "action_required", "reason": "Please retake selfie",
            "method": "evidence_review", "evidence_ids": [view["checks"][0]["id"]]}
    h = {**t.headers, "Idempotency-Key": f"review-{view['id']}"}
    a = client.post(f"/v1/verifications/{view['id']}/decisions", json=body, headers=h)
    b = client.post(f"/v1/verifications/{view['id']}/decisions", json=body, headers=h)
    assert a.status_code == b.status_code == 200 and a.json() == b.json()


def test_checks_and_decisions_are_append_only(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    with psycopg.connect(APP_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE checks SET result = 'pass' WHERE session_id = %s", (view["id"],))
        conn.rollback()
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE decisions SET outcome = 'approved' WHERE session_id = %s", (view["id"],))
        conn.rollback()
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE policies SET definition = '{}'::jsonb WHERE status = 'published'")
