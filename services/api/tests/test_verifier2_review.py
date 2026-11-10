"""Independent verifier (AT-08): review/appeal bypass paths. test_DEFECT_* assert spec behaviour (expected FAIL)."""

from __future__ import annotations

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv.admin import add_member


def _review_case(client, worker, t, settings, scenario="liveness_fail", ref="v2-rev"):
    created = create_session(client, t, ref=ref)
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


def _members(app, t, roles):
    out = []
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        for i, role in enumerate(roles):
            s = f"v2-{role}{i}-{t.id}@synthetic.example"
            add_member(conn, t.id, s, role)
            out.append(s)
    return [_browser(app, t.id, s) for s in out]


def _body(view, **over):
    b = {"expected_revision": view["revision"], "outcome": "declined", "reason": "Evidence does not match",
         "method": "evidence_review", "evidence_ids": [view["checks"][0]["id"]]}
    b.update(over)
    return b


def _decline_via_console(r, view):
    rev = next(i for i in r.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    out = r.post(f"/console/reviews/{rev['id']}/decision", json={**_body(view), "lock_version": lock})
    assert out.status_code == 200, out.text
    return out.json()["session"]


def test_fixed_appeal_resolution_overrides_without_second_review(client, worker, make_tenant, settings, owner):
    """High-impact override (approve by alternative method despite failed liveness) needs a second, different
    reviewer in the review path, but a single reviewer can do exactly that through an appeal."""
    t = make_tenant()
    view = _review_case(client, worker, t, settings, ref="v2-appeal-bypass")
    r1, r2 = _members(client.app, t, ["reviewer", "reviewer"])
    session = _decline_via_console(r1, view)
    appeal = r2.post(f"/console/verifications/{view['id']}/appeals",
                     json={"summary": "Applicant disputes the decline"}).json()  # r2 records the appeal
    assert r2.post(f"/console/appeals/{appeal['id']}/claim").status_code == 200  # ...claims it
    res = r2.post(f"/console/appeals/{appeal['id']}/resolve",  # ...and approves alone
                  json={"expected_revision": session["revision"], "outcome": "approved",
                        "method": "alternative_method", "reason": "Phoned the applicant, seems fine",
                        "evidence_ids": [view["checks"][0]["id"]]})
    trace = owner.execute("SELECT trace FROM decisions WHERE session_id = %s ORDER BY revision DESC LIMIT 1",
                          (view["id"],)).fetchone()["trace"]
    print("trace:", trace)
    assert res.status_code == 200 and res.json()["session"] is None
    assert res.json()["appeal"]["status"] == "awaiting_second_review", \
        "alternative-method approval recorded by one person without second review"
    assert r2.post(f"/console/appeals/{appeal['id']}/second-review", json={"confirm": True}).status_code == 403
    for c in (r1, r2):
        c.__exit__(None, None, None)


def test_fixed_developer_mints_decision_key_and_approves_without_second_review(client, worker, make_tenant, settings):
    """Developer role has no decisions:write, but can create an API key with any scope (incl. decisions:write)
    and then record an alternative-method approval via the API, which never requires a second reviewer."""
    t = make_tenant()
    view = _review_case(client, worker, t, settings, ref="v2-dev-escalation")
    (dev,) = _members(client.app, t, ["developer"])
    assert "decisions:write" not in dev.get("/console/me").json()["permissions"]
    k = dev.post("/console/api-keys", json={"scopes": ["decisions:write", "sessions:read", "deletions:create"]})
    assert k.status_code in (400, 403), "role without decisions:write minted a decisions:write key"
    ok = dev.post("/console/api-keys", json={"scopes": ["sessions:read", "webhooks:manage"]})
    assert ok.status_code == 201  # within the role's ceiling
    dev.__exit__(None, None, None)


def test_fixed_second_reviewer_can_take_appeal_against_decision_they_confirmed(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings, ref="v2-coi")
    r1, r2, r3 = _members(client.app, t, ["reviewer", "reviewer", "reviewer"])
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    p = r1.post(f"/console/reviews/{rev['id']}/decision",
                json={**_body(view, outcome="approved", method="alternative_method",
                              reason="In-person document inspection"), "lock_version": lock})
    assert p.status_code == 200
    c = r2.post(f"/console/reviews/{rev['id']}/second-review", json={"confirm": True})
    assert c.status_code == 200 and c.json()["session"]["state"] == "approved"
    appeal = r3.post(f"/console/verifications/{view['id']}/appeals",
                     json={"summary": "Fraud team disputes approval"}).json()
    claim = r2.post(f"/console/appeals/{appeal['id']}/claim")
    print("second reviewer claims appeal:", claim.status_code, claim.json().get("code"))
    assert claim.status_code == 409, "co-signer of the appealed decision may handle the appeal"
    for x in (r1, r2, r3):
        x.__exit__(None, None, None)


def test_ok_same_person_cannot_second_review_and_api_blocked_while_awaiting(client, worker, make_tenant, settings):
    t = make_tenant()
    view = _review_case(client, worker, t, settings, ref="v2-same")
    (r1,) = _members(client.app, t, ["reviewer"])
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    r1.post(f"/console/reviews/{rev['id']}/decision",
            json={**_body(view, outcome="approved", method="alternative_method", reason="Phone verification ok"),
                  "lock_version": lock})
    assert r1.post(f"/console/reviews/{rev['id']}/second-review", json={"confirm": True}).status_code == 403
    assert r1.post(f"/console/reviews/{rev['id']}/claim").status_code == 409
    api = client.post(f"/v1/verifications/{view['id']}/decisions", json=_body(view),
                      headers={**t.headers, **idem()})
    assert api.status_code == 409 and api.json()["code"] == "review_claimed"
    r1.__exit__(None, None, None)


def test_ok_expired_lease_holder_cannot_decide_after_reclaim(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    view = _review_case(client, worker, t, settings, ref="v2-lease")
    r1, r2 = _members(client.app, t, ["reviewer", "reviewer"])
    rev = next(i for i in r1.get("/console/reviews").json()["items"] if i["session_id"] == view["id"])
    lock1 = r1.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    owner.execute("UPDATE reviews SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (rev["id"],))
    # Expired lease: holder cannot decide even with the right lock_version
    assert r1.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": lock1}).status_code == 409
    lock2 = r2.post(f"/console/reviews/{rev['id']}/claim").json()["lock_version"]
    assert lock2 > lock1
    assert r1.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": lock2}).status_code == 409
    assert r2.post(f"/console/reviews/{rev['id']}/decision",
                   json={**_body(view), "lock_version": lock2}).status_code == 200
    # Decision rows immutable even for the app role
    with psycopg.connect(OWNER_DSN.replace("vv_owner:vv_owner_local", "vv_app:vv_app_local")) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (t.id,))
        try:
            conn.execute("UPDATE decisions SET outcome = 'approved' WHERE session_id = %s", (view["id"],))
            raise AssertionError("decision update allowed")
        except psycopg.Error:
            pass
    for c in (r1, r2):
        c.__exit__(None, None, None)
