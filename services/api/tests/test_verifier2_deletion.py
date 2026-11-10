"""Independent verifier (AT-09): deletion lifecycle negative paths.

Tests named test_DEFECT_* assert the CORRECT (spec) behaviour and are expected to FAIL on HEAD a3be6ec.
Tests named test_ok_* are positive checks expected to pass.
"""

from __future__ import annotations

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv import deletion
from vv.deletion import replay_tombstones


def _delete(client, t, subject):
    return client.post("/v1/deletions", headers={**t.headers, **idem()},
                       json={"subject_id": subject, "reason": "Applicant erasure request",
                             "controller_authorisation_reference": "CTRL-REQ-V2"})


def _hold(app, t, subject):
    with TestClient(app) as c:
        csrf = c.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject}).json()
        r = c.post("/console/legal-holds", headers={"X-CSRF-Token": csrf["csrf_token"]},
                   json={"subject_id": subject, "owner": "privacy@synthetic.example",
                         "reason": "Pending employment tribunal claim", "days": 30})
        assert r.status_code == 201, r.text


def _complete(client, worker, t, settings, ref):
    with TestClient(client.app) as b:
        c = create_session(b, t, ref=ref)
        applicant_ready(b, c["hosted_url"], settings, email=f"{ref}@synthetic.example")
        run_capture(b, "all_pass")
    drain(worker)
    return c["session"]["id"]


def test_d_b_no_new_session_for_subject_with_pending_deletion(client, worker, make_tenant, settings, owner):
    """D-B fixed: a new session cannot attach to a subject being erased; redaction also works by subject."""
    t = make_tenant()
    ref = "v2-escape-subject"
    _complete(client, worker, t, settings, ref)
    _hold(client.app, t, ref)
    r = _delete(client, t, ref)
    assert r.status_code == 202 and r.json()["state"] == "on_hold"
    late = client.post("/v1/verifications", headers={**t.headers, **idem()},
                       json={"external_reference": ref, "policy_id": "workforce_identity", "policy_version": 1,
                             "country": "ZZ", "document_type": "passport"})
    assert late.status_code == 409 and late.json()["code"] == "subject_deletion_pending"


def test_ok_processing_session_late_event_ignored_after_deletion(
        client, worker, make_tenant, settings, owner):
    """Deletion requested while the session is 'processing' (submitted, awaiting supplier). If the deletion
    worker runs before the provider event, the late result is still evaluated: checks + evidence stored,
    completion webhook emitted, and the new evidence objects survive primary deletion."""
    t = make_tenant()
    ref = "v2-processing-subject"
    with TestClient(client.app) as b:
        c = create_session(b, t, ref=ref)
        applicant_ready(b, c["hosted_url"], settings, email="proc@synthetic.example")
        run_capture(b, "all_pass")  # session -> processing, provider event pending
    sid = c["session"]["id"]
    assert owner.execute("SELECT state FROM sessions WHERE id = %s", (sid,)).fetchone()["state"] == "processing"
    r = _delete(client, t, ref)
    assert r.status_code == 202
    # Deletion worker step happens to run first (provider events can be delayed by retry/backoff).
    deletion.advance_deletions(worker.db, worker.providers, store=worker.store)
    assert owner.execute("SELECT primary_state FROM deletion_jobs WHERE id = %s",
                         (r.json()["id"],)).fetchone()["primary_state"] == "done"
    from vv import events
    events.process_due_events(worker.db, worker.providers, store=worker.store)
    s = owner.execute("SELECT state FROM sessions WHERE id = %s", (sid,)).fetchone()
    live = owner.execute("SELECT storage_key FROM evidence WHERE session_id = %s AND deleted_at IS NULL",
                         (sid,)).fetchall()
    on_disk = [x for x in live if worker.store.exists(x["storage_key"])]
    completed = owner.execute("SELECT count(*) AS n FROM outbox WHERE resource_id = %s AND "
                              "event_type = 'verification.completed'", (sid,)).fetchone()["n"]
    print("state after late event:", s, "live evidence rows:", len(live), "objects on disk:", len(on_disk),
          "completed events:", completed)
    assert len(on_disk) == 0, "evidence objects written after primary deletion and never erased"
    assert s["state"] != "approved", "session decided after the subject's deletion was requested"


def test_d_c_replay_respects_legal_hold(client, worker, make_tenant, settings, owner):
    """`vv-admin replay-tombstones` passes the evidence store; replay redacts and deletes evidence for a subject
    whose deletion is ON HOLD (legal hold active)."""
    t = make_tenant()
    ref = "v2-held-replay"
    sid = _complete(client, worker, t, settings, ref)
    _hold(client.app, t, ref)
    r = _delete(client, t, ref)
    assert r.json()["state"] == "on_hold"
    drain(worker, 2)
    assert owner.execute("SELECT state FROM deletion_jobs WHERE id = %s", (r.json()["id"],)).fetchone()[
        "state"] == "on_hold"
    before = owner.execute("SELECT count(*) AS n FROM evidence WHERE session_id = %s AND deleted_at IS NULL",
                           (sid,)).fetchone()["n"]
    assert before == 2
    replay_tombstones(OWNER_DSN, worker.store)  # as vv-admin replay-tombstones does (admin.py:95)
    after = owner.execute("SELECT count(*) AS n FROM evidence WHERE session_id = %s AND deleted_at IS NULL",
                          (sid,)).fetchone()["n"]
    subj = owner.execute("SELECT s.external_reference FROM subjects s JOIN sessions x ON x.subject_id = s.id "
                         "WHERE x.id = %s", (sid,)).fetchone()
    print("evidence before/after replay:", before, after, "subject ref:", subj)
    assert after == before, "legal-held evidence destroyed by tombstone replay"
    blocked = owner.execute("SELECT evidence_access_blocked_at FROM sessions WHERE id = %s", (sid,)).fetchone()
    assert blocked["evidence_access_blocked_at"] is not None
    assert subj["external_reference"] == ref, "legal-held subject redacted by tombstone replay"


def test_d_a_restore_of_pre_deletion_backup_replays_from_external_log(client, worker, make_tenant, settings, owner):
    """AT-09 procedure: restore a backup *containing old evidence* (i.e. taken before the deletion).
    replay_tombstones reads tombstones from the restored database itself (recovery.py:96 passes restore_dsn),
    and such a backup has no tombstone row. Simulated in place: put the rows back as they were in the backup
    (subject/session identifiable, no tombstone, no job)."""
    t = make_tenant()
    ref = "v2-old-backup"
    sid = create_session(client, t, ref=ref)["session"]["id"]
    r = _delete(client, t, ref)
    did = r.json()["id"]
    drain(worker, 2)
    with psycopg.connect(OWNER_DSN, row_factory=dict_row, autocommit=True) as conn:
        # == state of a backup taken before POST /v1/deletions ==
        conn.execute("ALTER TABLE deletion_tombstones DISABLE TRIGGER tombstones_append_only")
        try:
            conn.execute("DELETE FROM deletion_tombstones WHERE deletion_id = %s", (did,))
        finally:
            conn.execute("ALTER TABLE deletion_tombstones ENABLE TRIGGER tombstones_append_only")
        conn.execute("DELETE FROM deletion_supplier_targets WHERE deletion_id = %s", (did,))
        conn.execute("UPDATE subjects SET external_reference = %s, deleted_at = NULL WHERE tenant_id = %s",
                     (ref, t.id))
        conn.execute("UPDATE sessions SET external_reference = %s, evidence_access_blocked_at = NULL WHERE id = %s",
                     (ref, sid))
        conn.execute("DELETE FROM outbox WHERE resource_id = %s", (did,))
        conn.execute("DELETE FROM deletion_jobs WHERE id = %s", (did,))
    out = replay_tombstones(OWNER_DSN, log=worker.tombstone_log)
    assert out["redacted"] >= 1
    s = owner.execute("SELECT external_reference, evidence_access_blocked_at FROM sessions WHERE id = %s",
                      (sid,)).fetchone()
    print("after replay on pre-deletion backup:", s)
    assert s["external_reference"] == "deleted", "deletion not re-applied: tombstones live inside the backup"
    assert s["evidence_access_blocked_at"] is not None
    assert owner.execute("SELECT state FROM deletion_jobs WHERE id = %s", (did,)).fetchone()["state"] == "in_progress"


def test_ok_reveal_and_download_blocked_after_deletion_request(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    ref = "v2-reveal-after-del"
    sid = _complete(client, worker, t, settings, ref)
    with TestClient(client.app) as o:
        csrf = o.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject}).json()
        o.headers.update({"X-CSRF-Token": csrf["csrf_token"]})
        ev = o.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
        path = o.post(f"/console/evidence/{ev}/reveal", json={"reason": "Checking before erasure"}).json()[
            "download_path"]
        _hold(client.app, t, ref)  # hold delays erasure, so objects still exist
        assert _delete(client, t, ref).status_code == 202
        assert o.get(path).status_code == 410  # previously issued link dies at request time
        assert o.post(f"/console/evidence/{ev}/reveal", json={"reason": "Checking after request"}).status_code == 410
        items = o.get(f"/console/verifications/{sid}/evidence").json()["items"]
        assert all(not i["available"] for i in items)
        # Appeals refused for a deleted subject
        assert o.post(f"/console/verifications/{sid}/appeals",
                      json={"summary": "Applicant appeal after erasure"}).status_code == 409


def test_ok_supplier_never_confirming_is_not_complete(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    ref = "v2-supplier-slow"
    _complete(client, worker, t, settings, ref)
    dummy = worker.providers["dummy"]
    dummy.deletion_confirm_delay_seconds = 10 ** 6
    try:
        did = _delete(client, t, ref).json()["id"]
        for _ in range(6):
            drain(worker, 1)
        owner.execute("UPDATE deletion_jobs SET backup_expires_at = now() - interval '1 day' WHERE id = %s", (did,))
        drain(worker, 2)
        st = client.get(f"/v1/deletions/{did}", headers=t.headers).json()
        assert st["state"] == "primary_deleted" and "supplier:dummy" in st["pending_targets"]
    finally:
        dummy.deletion_confirm_delay_seconds = 0
