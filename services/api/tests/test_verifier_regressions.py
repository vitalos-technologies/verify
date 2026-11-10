"""Regression tests for defects D1-D3 and D9 found by independent verification of 81686a7."""

from __future__ import annotations

import threading

from conftest import applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient

from vv import events


def _view(client, t, sid):
    return client.get(f"/v1/verifications/{sid}", headers=t.headers).json()


def test_d1_unexpected_provider_exception_does_not_stall_worker(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c1 = create_session(client, t, ref="poison-1")
    with TestClient(client.app) as b1:
        applicant_ready(b1, c1["hosted_url"], settings)
        run_capture(b1, "all_pass")
    dummy = worker.providers["dummy"]

    def boom(ref, *, correlation_id):
        raise TimeoutError("transport timeout")

    worker.providers["dummy"] = type("P", (), {"name": "dummy", "fetch_result": staticmethod(boom)})()
    c2 = create_session(client, t, ref="victim-2")
    owner.execute("UPDATE sessions SET expires_at = now() - interval '1 second' WHERE id = %s", (c2["session"]["id"],))
    try:
        for _ in range(2):
            worker.run_once()  # must not raise
    finally:
        worker.providers["dummy"] = dummy
    assert _view(client, t, c2["session"]["id"])["state"] == "expired"
    ev = owner.execute("SELECT processing_state FROM provider_events WHERE session_id = %s OR (session_id IS NULL "
                       "AND provider_reference IN (SELECT provider_reference FROM attempts WHERE session_id = %s))",
                       (c1["session"]["id"], c1["session"]["id"])).fetchone()
    assert ev["processing_state"] == "retry"
    # Once the provider recovers, the same event is processed normally.
    owner.execute("UPDATE provider_events SET next_attempt_at = now()")
    drain(worker)
    assert _view(client, t, c1["session"]["id"])["state"] == "approved"


def test_d2_submitted_requires_capture_and_stuck_sessions_expire(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    att = client.post("/applicant/attempts").json()
    owner.execute("UPDATE attempts SET state = 'creating' WHERE id = %s", (att["attempt_id"],))
    assert client.post(f"/applicant/attempts/{att['attempt_id']}/submitted").status_code == 409
    owner.execute("UPDATE attempts SET state = 'capturing' WHERE id = %s", (att["attempt_id"],))
    assert client.post(f"/applicant/attempts/{att['attempt_id']}/submitted").status_code == 200
    assert _view(client, t, sid)["state"] == "processing"  # client hint only; never captured
    owner.execute("UPDATE sessions SET expires_at = now() - interval '1 second' WHERE id = %s", (sid,))
    drain(worker, 1)
    assert _view(client, t, sid)["state"] == "expired"
    assert owner.execute("SELECT count(*) AS n FROM usage_events WHERE session_id = %s AND charge_type = "
                         "'reservation_release'", (sid,)).fetchone()["n"] == 1


def test_d2_error_session_expires_after_deadline(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    run_capture(client, "provider_error")
    drain(worker)
    assert _view(client, t, sid)["state"] == "error"
    owner.execute("UPDATE sessions SET expires_at = now() - interval '1 second' WHERE id = %s", (sid,))
    drain(worker, 1)
    assert _view(client, t, sid)["state"] == "expired"


def test_d3_concurrent_workers_process_an_event_once(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    applicant_ready(client, c["hosted_url"], settings)
    att = client.post("/applicant/attempts").json()
    client.post("/dummy-provider/capture", json={"capture_token": att["capture_token"], "scenario": "all_pass"})
    ev = owner.execute("SELECT event_id FROM provider_events WHERE provider_reference = (SELECT provider_reference "
                       "FROM attempts WHERE id = %s)", (att["attempt_id"],)).fetchone()["event_id"]
    results: list[str] = []

    def go():
        results.append(events.process_event(worker.db, worker.providers, "dummy", ev))

    threads = [threading.Thread(target=go) for _ in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(results).count("processed") == 1 and results.count("skipped") == 5
    row = owner.execute("SELECT processing_state FROM provider_events WHERE event_id = %s", (ev,)).fetchone()
    assert row["processing_state"] == "processed"


def test_d9_alternative_method_is_distinguished_in_result(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    c = create_session(client, t)
    sid = c["session"]["id"]
    applicant_ready(client, c["hosted_url"], settings)
    run_capture(client, "liveness_attack")
    drain(worker)
    v = _view(client, t, sid)
    assert v["decision"]["method"] == "automated" and v["decision"]["outcome"] == "review_required"
    r = client.post(f"/v1/verifications/{sid}/decisions", headers={**t.headers, **idem()},
                    json={"expected_revision": v["revision"], "outcome": "approved", "reason": "In-person ID check",
                          "method": "alternative_method", "reviewer_reference": "reviewer-7",
                          "evidence_ids": [x["id"] for x in v["checks"] if x["type"] == "email"]})
    assert r.status_code == 200
    out = r.json()
    assert out["state"] == "approved"
    assert out["decision"]["method"] == "alternative_method"
    assert "review.alternative_method" in out["decision"]["reason_codes"]
    assert {c["type"]: c["result"] for c in out["checks"]}["liveness"] == "fail"
    trace = owner.execute("SELECT trace FROM decisions WHERE session_id = %s AND actor_type = 'reviewer'",
                          (sid,)).fetchone()["trace"]
    assert trace["review"]["reviewer_reference"] == "reviewer-7"
