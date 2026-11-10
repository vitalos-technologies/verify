"""Verifier: cross-tenant attacks on console, applicant and worker paths."""
from __future__ import annotations

import psycopg
import pytest
from conftest import APP_DSN, WORKER_DSN, applicant_ready, create_session, drain, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv.admin import DEV_POLICY


def _login(c, tid, subj):
    r = c.post("/console/dev-login", json={"tenant_id": tid, "user_subject": subj})
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def test_console_of_b_cannot_touch_a(client, make_tenant, owner):
    a, b = make_tenant("A"), make_tenant("B")
    sid = create_session(client, a, ref="a-ref-secret")["session"]["id"]
    # A-side objects
    with TestClient(client.app) as ca:
        csrf_a = _login(ca, a.id, a.owner_subject)
        key_a = ca.post("/console/api-keys", json={"scopes": ["sessions:read"]}, headers={"X-CSRF-Token": csrf_a}).json()
        r = ca.post("/console/policies", json=dict(DEV_POLICY, id="a_only", version=1), headers={"X-CSRF-Token": csrf_a})
        assert r.status_code == 201, r.text
    with TestClient(client.app) as cb:
        csrf_b = _login(cb, b.id, b.owner_subject)
        h = {"X-CSRF-Token": csrf_b}
        r = cb.get(f"/console/verifications/{sid}")
        assert r.status_code == 404 and "a-ref-secret" not in r.text
        assert cb.post(f"/console/api-keys/{key_a['id']}/revoke", json={"reason": "xtenant"}, headers=h).status_code == 404
        assert cb.post(f"/console/memberships/{a.owner_membership}/revoke", json={"reason": "xtenant"},
                       headers=h).status_code == 404
        assert cb.post("/console/policies/a_only/1/publish", headers=h).status_code == 404
        # dev-login with B's subject against A's tenant
        assert cb.post("/console/dev-login", json={"tenant_id": a.id, "user_subject": b.owner_subject}).status_code == 401
    # A's key still works
    assert client.get("/v1/verifications", headers={"Authorization": f"Bearer {key_a['key']}"}).status_code == 200


def test_applicant_cookie_a_cannot_touch_b(client, worker, make_tenant, settings):
    a, b = make_tenant("A"), make_tenant("B")
    ca_created = create_session(client, a)
    cb_created = create_session(client, b)
    with TestClient(client.app) as bb:
        applicant_ready(bb, cb_created["hosted_url"], settings)
        att_b = bb.post("/applicant/attempts").json()
    with TestClient(client.app) as aa:
        applicant_ready(aa, ca_created["hosted_url"], settings)
        r = aa.post(f"/applicant/attempts/{att_b['attempt_id']}/submitted")
        assert r.status_code == 404
        # also same-tenant other session
    b_view = client.get(f"/v1/verifications/{cb_created['session']['id']}", headers=b.headers).json()
    assert b_view["state"] == "in_progress"


def test_worker_role_in_tenant_context_sees_only_that_tenant(client, make_tenant):
    """D5: worker_scan policies apply only without tenant context."""
    a, b = make_tenant("A"), make_tenant("B")
    create_session(client, b, ref="b-ref")
    with psycopg.connect(WORKER_DSN, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (a.id,))
        n = conn.execute("SELECT count(*) AS n FROM outbox WHERE tenant_id = %s", (b.id,)).fetchone()["n"]
    assert n == 0


def test_app_role_cannot_read_provider_events(client, worker, make_tenant, settings):
    a = make_tenant("A")
    created = create_session(client, a)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "all_pass")
    drain(worker)
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT tenant_id, session_id FROM provider_events WHERE tenant_id = %s", (a.id,))


def test_suspended_tenant_console_refused(client, make_tenant, owner):
    t = make_tenant()
    csrf = _login(client, t.id, t.owner_subject)
    owner.execute("UPDATE tenants SET status = 'suspended' WHERE id = %s", (t.id,))
    assert client.get("/v1/verifications", headers=t.headers).status_code == 403
    r = client.post("/console/api-keys", json={"scopes": ["sessions:create"]}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 403  # D6
