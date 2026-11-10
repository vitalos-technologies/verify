"""AT-08 complete (VV-008): claim leases, stale clients, second review for overrides, appeals."""

from __future__ import annotations

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv.admin import add_member


def _review_case(client, worker, t, settings, scenario="liveness_fail"):
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, scenario)
    drain(worker)
    return client.get(f"/v1/verifications/{created['session']['id']}", headers=t.headers).json()


def _browser(app, tenant_id, subject):
    c = TestClient(app)
    c.__enter__()
    csrf = c.post("/console/dev-login", json={"tenant_id": tenant_id, "user_subject": subject}).json()["csrf_token"]
    c.headers.update({"X-CSRF-Token": csrf})
    return c


def _reviewers(app, t, n=2):
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        subs = [f"rev{i}-{t.id}@synthetic.example" for i in range(n)]
        for s in subs:
            add_member(conn, t.id, s, "reviewer")
    return [_browser(app, t.id, s) for s in subs]


def _body(view, **over):
    b = {"expected_revision": view["revision"], "outcome": "declined", "reason": "Evidence does not match",
         "method": "evidence_review", "evidence_ids": [view["checks"][0]["id"]]}
    b.update(over)
    return b


def test_queue_claim_lease_and_stale_lock(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    r1, r2 = _reviewers(client.app, t)
    queue = r1.get("/console/reviews").json()["items"]
    rev = next(i for i in queue if i["session_id"] == view["id"])
    claimed = r1.post(f"/console/reviews/{rev['id']}/claim").json()
    assert claimed["status"] == "claimed"
    assert r2.post(f"/console/reviews/{rev['id']}/claim").status_code == 409
    # API-key decision is blocked while a reviewer holds the lease.
    r = client.post(f"/v1/verifications/{view['id']}/decisions", json=_body(view), headers={**t.headers, **idem()})
    assert r.status_code == 409 and r.json()["code"] == "review_claimed"
    # Without a lease, deciding fails; with a stale lock_version, deciding fails.
    assert r2.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": claimed["lock_version"]}).status_code == 409
    assert r1.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": claimed["lock_version"] - 1}).status_code == 409
    # Lease expiry lets another reviewer take over; the first reviewer's stale client cannot act.
    owner.execute("UPDATE reviews SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (rev["id"],))
    taken = r2.post(f"/console/reviews/{rev['id']}/claim").json()
    assert taken["assignee"] != claimed["assignee"]
    assert r1.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": claimed["lock_version"]}).status_code == 409
    out = r2.post(f"/console/reviews/{rev['id']}/decision", json={**_body(view), "lock_version": taken["lock_version"]})
    assert out.status_code == 200 and out.json()["session"]["state"] == "declined"
    assert out.json()["session"]["decision"]["actor_type"] == "reviewer"
    for c in (r1, r2):
        c.__exit__(None, None, None)


def test_override_requires_a_second_different_reviewer(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings, "liveness_attack")
    r1, r2 = _reviewers(client.app, t)
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    body = {**_body(view, outcome="approved", method="alternative_method", reason="Verified in person at branch"),
            "lock_version": lock}
    proposed = r1.post(f"/console/reviews/{rev['id']}/decision", json=body).json()
    assert proposed["review"]["status"] == "awaiting_second_review" and proposed["session"] is None
    assert client.get(f"/v1/verifications/{view['id']}", headers=t.headers).json()["state"] == "review_required"
    assert r1.post(f"/console/reviews/{rev['id']}/second-review", json={"confirm": True}).status_code == 403
    out = r2.post(f"/console/reviews/{rev['id']}/second-review", json={"confirm": True}).json()
    assert out["session"]["state"] == "approved"
    assert out["session"]["decision"]["method"] == "alternative_method"
    assert {c["type"]: c["result"] for c in out["session"]["checks"]}["liveness"] == "fail"  # evidence untouched
    for c in (r1, r2):
        c.__exit__(None, None, None)


def test_rejected_override_returns_case_to_queue(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    r1, r2 = _reviewers(client.app, t)
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    r1.post(f"/console/reviews/{rev['id']}/decision",
            json={**_body(view, outcome="approved", method="alternative_method", reason="Phone call verification"),
                  "lock_version": lock})
    out = r2.post(f"/console/reviews/{rev['id']}/second-review", json={"confirm": False}).json()
    assert out["review"]["status"] == "open"
    for c in (r1, r2):
        c.__exit__(None, None, None)


def test_appeal_goes_to_different_reviewer_and_appends_revision(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    r1, r2, r3 = _reviewers(client.app, t, 3)
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    decided = r1.post(f"/console/reviews/{rev['id']}/decision", json={**_body(view), "lock_version": lock}).json()
    session = decided["session"]
    assert session["state"] == "declined"
    # Appeal only on completed sessions; one open appeal at a time.
    appeal = r1.post(f"/console/verifications/{view['id']}/appeals",
                     json={"summary": "Applicant says the selfie was blurred by poor lighting"})
    assert appeal.status_code == 201
    appeal = appeal.json()
    assert r1.post(f"/console/verifications/{view['id']}/appeals",
                   json={"summary": "Duplicate appeal for the same case"}).status_code == 409
    # Original reviewer cannot take the appeal while another reviewer exists.
    assert r1.post(f"/console/appeals/{appeal['id']}/claim").json()["code"] == "conflict_of_interest"
    assert r2.post(f"/console/appeals/{appeal['id']}/claim").status_code == 200
    bad = r2.post(f"/console/appeals/{appeal['id']}/resolve",
                  json={"expected_revision": session["revision"], "outcome": "approved", "method": "evidence_review",
                        "reason": "Looks fine on review", "evidence_ids": [view["checks"][0]["id"]]})
    assert bad.status_code == 422  # cannot assert a pass the evidence contradicts
    proposed = r2.post(f"/console/appeals/{appeal['id']}/resolve",
                       json={"expected_revision": session["revision"], "outcome": "approved",
                             "method": "alternative_method", "reason": "Second ID checked in person",
                             "evidence_ids": [view["checks"][0]["id"]]}).json()
    assert proposed["appeal"]["status"] == "awaiting_second_review" and proposed["session"] is None
    assert r2.post(f"/console/appeals/{appeal['id']}/second-review", json={"confirm": True}).status_code == 403
    ok = r3.post(f"/console/appeals/{appeal['id']}/second-review", json={"confirm": True}).json()
    assert ok["appeal"]["status"] == "resolved"
    assert ok["session"]["state"] == "approved" and ok["session"]["revision"] == session["revision"] + 1
    revs = owner.execute("SELECT revision, outcome, supersedes_revision FROM decisions WHERE session_id = %s "
                         "ORDER BY revision", (view["id"],)).fetchall()
    assert [(r["outcome"], r["supersedes_revision"]) for r in revs][-2:] == [("declined", 1), ("approved", 2)]
    events = owner.execute("SELECT payload FROM outbox WHERE resource_id = %s AND "
                           "event_type = 'verification.completed' ORDER BY created_at", (view["id"],)).fetchall()
    assert [e["payload"]["state"] for e in events] == ["declined", "approved"]
    hold = owner.execute("SELECT appeal_hold_until FROM sessions WHERE id = %s", (view["id"],)).fetchone()
    assert hold["appeal_hold_until"] is not None
    for c in (r1, r2, r3):
        c.__exit__(None, None, None)


def test_console_list_me_and_timeline(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings)
    (r1,) = _reviewers(client.app, t, 1)
    me = r1.get("/console/me").json()
    assert me["role"] == "reviewer" and "decisions:write" in me["permissions"]
    items = r1.get("/console/verifications", params={"state": "review_required"}).json()["items"]
    assert [i["id"] for i in items] == [view["id"]]
    tl = r1.get(f"/console/verifications/{view['id']}/timeline").json()
    assert tl["review"]["status"] == "open"
    assert [i["type"] for i in tl["items"] if i["kind"] == "event"][:1] == ["verification.created"]
    assert any(i["kind"] == "decision" and i["outcome"] == "review_required" for i in tl["items"])
    other = make_tenant()
    with TestClient(client.app) as ob:
        csrf = ob.post("/console/dev-login", json={"tenant_id": other.id, "user_subject": other.owner_subject}).json()
        assert csrf
        assert ob.get(f"/console/verifications/{view['id']}/timeline").status_code == 404
    r1.__exit__(None, None, None)
