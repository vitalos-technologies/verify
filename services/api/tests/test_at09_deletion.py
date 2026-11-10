"""AT-09 deletion lifecycle (VV-009): access blocked, not complete prematurely, tombstone replay after restore."""

from __future__ import annotations

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from psycopg.rows import dict_row
from test_contract import check

from vv.deletion import replay_tombstones

REF = "subject-del-canary-001"


def _completed_subject(client, worker, t, settings):
    created = create_session(client, t, ref=REF)
    applicant_ready(client, created["hosted_url"], settings, email="del.canary@synthetic.example")
    run_capture(client, "all_pass")
    drain(worker)
    return created["session"]["id"]


def _delete(client, t, subject=REF):
    return client.post("/v1/deletions", headers={**t.headers, **idem()},
                       json={"subject_id": subject, "reason": "Applicant erasure request",
                             "controller_authorisation_reference": "CTRL-REQ-42"})


def _state(client, t, did):
    r = client.get(f"/v1/deletions/{did}", headers=t.headers)
    check(r.json(), "Deletion")
    return r.json()


def test_full_lifecycle_with_delayed_supplier_and_backup_expiry(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid = _completed_subject(client, worker, t, settings)
    dummy = worker.providers["dummy"]
    dummy.deletion_confirm_delay_seconds = 3600  # supplier slow to confirm
    try:
        r = _delete(client, t)
        assert r.status_code == 202, r.text
        did = r.json()["id"]
        assert r.json()["state"] == "requested"
        drain(worker, 2)
        st = _state(client, t, did)
        assert st["state"] == "primary_deleted"
        assert st["pending_targets"] == ["backups", "supplier:dummy"]
        view = client.get(f"/v1/verifications/{sid}", headers=t.headers).json()
        assert view["external_reference"] == "deleted" and view["state"] == "approved"  # outcome kept, PII redacted
        assert owner.execute("SELECT count(*) AS n FROM subjects WHERE external_reference = %s",
                             (REF,)).fetchone()["n"] == 0
        # Supplier received the request but has not confirmed: not complete.
        tgt = owner.execute("SELECT state, receipt FROM deletion_supplier_targets WHERE deletion_id = %s",
                            (did,)).fetchone()
        assert tgt["state"] == "requested" and tgt["receipt"].startswith("dmydel_")
        dummy.deletion_confirm_delay_seconds = 0
        drain(worker, 1)
        st = _state(client, t, did)
        assert st == {"id": did, "state": "awaiting_backup_expiry", "pending_targets": ["backups"]}
        drain(worker, 1)
        assert _state(client, t, did)["state"] == "awaiting_backup_expiry"  # backups still within retention
        owner.execute("UPDATE deletion_jobs SET backup_expires_at = now() - interval '1 second' WHERE id = %s", (did,))
        drain(worker, 1)
        assert _state(client, t, did) == {"id": did, "state": "complete", "pending_targets": []}
    finally:
        dummy.deletion_confirm_delay_seconds = 0
    events = owner.execute("SELECT payload->>'state' AS s FROM outbox WHERE resource_id = %s ORDER BY created_at",
                           (did,)).fetchall()
    assert [e["s"] for e in events] == ["requested", "in_progress", "primary_deleted", "awaiting_backup_expiry",
                                        "complete"]


def test_request_blocks_access_and_cancels_open_session(client, worker, make_tenant, owner):
    t = make_tenant()
    created = create_session(client, t, ref="open-subject-1")
    token = created["hosted_url"].rsplit("/", 1)[1]
    assert client.post("/applicant/exchange", json={"token": token}).status_code == 200
    r = _delete(client, t, "open-subject-1")
    assert r.status_code == 202
    assert client.get("/applicant/session").status_code == 401  # applicant session ended
    view = client.get(f"/v1/verifications/{created['session']['id']}", headers=t.headers).json()
    assert view["state"] == "cancelled"
    # A second deletion while one is open conflicts; unknown subject is 404; other tenants cannot see it.
    assert _delete(client, t, "open-subject-1").status_code == 409
    assert _delete(client, t, "no-such-subject").status_code == 404
    other = make_tenant()
    assert client.get(f"/v1/deletions/{r.json()['id']}", headers=other.headers).status_code == 404


def test_late_provider_event_after_deletion_is_not_stored(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    created = create_session(client, t, ref="late-subject")
    applicant_ready(client, created["hosted_url"], settings, email="late.canary@synthetic.example")
    att = client.post("/applicant/attempts").json()
    client.post("/dummy-provider/capture", json={"capture_token": att["capture_token"], "scenario": "all_pass"})
    assert _delete(client, t, "late-subject").status_code == 202
    drain(worker, 2)
    assert owner.execute("SELECT count(*) AS n FROM checks WHERE session_id = %s AND attempt_id IS NOT NULL",
                         (created["session"]["id"],)).fetchone()["n"] == 0
    ev = owner.execute("SELECT processing_state, outcome_note FROM provider_events WHERE session_id = %s",
                       (created["session"]["id"],)).fetchone()
    assert ev["processing_state"] == "ignored"


def test_legal_hold_delays_erasure_but_blocks_access(client, worker, make_tenant, owner):
    t = make_tenant()
    created = create_session(client, t, ref="held-subject")
    r = client.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject})
    csrf = r.json()["csrf_token"]
    r = client.post("/console/legal-holds", headers={"X-CSRF-Token": csrf},
                    json={"subject_id": "held-subject", "owner": "privacy@synthetic.example",
                          "reason": "Pending employment tribunal claim", "days": 30})
    assert r.status_code == 201
    r = _delete(client, t, "held-subject")
    assert r.json()["state"] == "on_hold"
    drain(worker, 2)
    did = r.json()["id"]
    assert _state(client, t, did)["state"] == "on_hold"
    blocked = owner.execute("SELECT evidence_access_blocked_at FROM sessions WHERE id = %s",
                            (created["session"]["id"],)).fetchone()
    assert blocked["evidence_access_blocked_at"] is not None
    owner.execute("UPDATE legal_holds SET released_at = now() WHERE tenant_id = %s", (t.id,))
    drain(worker, 2)
    assert _state(client, t, did)["state"] == "awaiting_backup_expiry"  # no supplier targets (no capture made)


def test_tombstone_replay_after_restore(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid = create_session(client, t, ref="restore-me")["session"]["id"]
    _delete(client, t, "restore-me")
    drain(worker, 2)
    # Simulate restoring a backup taken before the deletion.
    owner.execute("UPDATE subjects SET external_reference = 'restore-me', deleted_at = NULL WHERE tenant_id = %s",
                  (t.id,))
    owner.execute("UPDATE sessions SET external_reference = 'restore-me', evidence_access_blocked_at = NULL "
                  "WHERE id = %s", (sid,))
    assert replay_tombstones(OWNER_DSN)["redacted"] >= 1
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        s = conn.execute("SELECT external_reference, evidence_access_blocked_at FROM sessions WHERE id = %s",
                         (sid,)).fetchone()
        assert s["external_reference"] == "deleted" and s["evidence_access_blocked_at"] is not None
        assert conn.execute("SELECT count(*) AS n FROM subjects WHERE external_reference = 'restore-me'"
                            ).fetchone()["n"] == 0


def test_tombstones_are_append_only(make_tenant, client, owner):
    t = make_tenant()
    create_session(client, t, ref="tomb-1")
    _delete(client, t, "tomb-1")
    import pytest
    from conftest import APP_DSN
    with psycopg.connect(APP_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM deletion_tombstones")
