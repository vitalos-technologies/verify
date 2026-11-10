"""AT-14 recovery exercise on synthetic data: isolated restore, tombstone replay, no outbound work, measured RTO."""

from __future__ import annotations

from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture

from vv.recovery import run_exercise


def test_isolated_restore_replays_deletions_and_disables_outbound(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    client.post("/v1/webhook-endpoints", headers=t.headers,
                json={"url": "https://hooks.customer-a.example/vv", "events": ["verification.completed"]})
    c = create_session(client, t, ref="restore-subject")
    applicant_ready(client, c["hosted_url"], settings)
    run_capture(client, "all_pass")
    drain(worker)
    client.post("/v1/deletions", headers={**t.headers, **idem()},
                json={"subject_id": "restore-subject", "reason": "Erasure", "controller_authorisation_reference": "C"})
    drain(worker, 2)
    create_session(client, t, ref="pending-webhook")  # leaves undelivered outbox/delivery work behind
    report = run_exercise(OWNER_DSN, worker.store)
    assert report["passed"], report
    assert report["counts_match"] and report["tombstone_leaks_after_replay"] == 0
    assert report["outbound_work_remaining"] == 0 and report["tables_with_rls"] >= 20
    assert report["measured_rto_seconds"] < 4 * 3600
    # The exercise copy is destroyed.
    dbs = owner.execute("SELECT datname FROM pg_database WHERE datname LIKE 'vv_restore_%'").fetchall()
    assert dbs == []
    # Report carries counts only, no identifiers or references.
    assert "restore-subject" not in str(report) and "@" not in str(report)
