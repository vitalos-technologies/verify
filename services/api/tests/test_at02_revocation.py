"""AT-02 credential and membership revocation (VV-002)."""

from __future__ import annotations

import psycopg
from conftest import OWNER_DSN, create_body, idem
from psycopg.rows import dict_row

from vv.admin import add_member


def _login(client, tenant_id, subject):
    r = client.post("/console/dev-login", json={"tenant_id": tenant_id, "user_subject": subject})
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def test_revoked_api_key_is_denied_and_audited(client, make_tenant, owner):
    t = make_tenant()
    csrf = _login(client, t.id, t.owner_subject)
    r = client.post("/console/api-keys", json={"label": "ci", "scopes": ["sessions:read"]},
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201
    key_id, raw = r.json()["id"], r.json()["key"]
    hdr = {"Authorization": f"Bearer {raw}"}
    assert client.get("/v1/verifications", headers=hdr).status_code == 200
    # Scope enforcement: read-only key cannot create.
    assert client.post("/v1/verifications", json=create_body(), headers={**hdr, **idem()}).status_code == 403
    r = client.post(f"/console/api-keys/{key_id}/revoke", json={"reason": "rotation test"},
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert client.get("/v1/verifications", headers=hdr).status_code == 401
    audit = owner.execute("SELECT action, reason FROM audit_events WHERE object_id = %s ORDER BY created_at",
                          (key_id,)).fetchall()
    assert [a["action"] for a in audit] == ["api_key.create", "api_key.revoke"]
    assert audit[1]["reason"] == "rotation test"
    # The stored key is a hash; the raw secret never appears in the table.
    row = owner.execute("SELECT * FROM api_keys WHERE id = %s", (key_id,)).fetchone()
    assert raw.split("_", 3)[3] not in str(row)


def test_expired_and_malformed_keys_denied(client, make_tenant, owner):
    t = make_tenant()
    owner.execute("UPDATE api_keys SET expires_at = now() - interval '1 minute' WHERE tenant_id = %s", (t.id,))
    assert client.get("/v1/verifications", headers=t.headers).status_code == 401
    for bad in ["", "Bearer", "Bearer vvk_test_nope", "Basic abc", f"Bearer {t.api_key}x"]:
        assert client.get("/v1/verifications", headers={"Authorization": bad}).status_code == 401


def test_revoked_membership_ends_existing_browser_session(client, make_tenant, owner):
    t = make_tenant()
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        mid = add_member(conn, t.id, "dev@synthetic.example", "developer")
    owner_csrf = _login(client, t.id, t.owner_subject)
    owner_cookie = client.cookies.get("vv_console")
    # Developer signs in on a separate browser.
    from fastapi.testclient import TestClient
    with TestClient(client.app) as dev_browser:
        r = dev_browser.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": "dev@synthetic.example"})
        dev_csrf = r.json()["csrf_token"]
        assert dev_browser.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                                headers={"X-CSRF-Token": dev_csrf}).status_code == 201
        client.cookies.set("vv_console", owner_cookie, path="/console")
        r = client.post(f"/console/memberships/{mid}/revoke", json={"reason": "left company"},
                        headers={"X-CSRF-Token": owner_csrf})
        assert r.status_code == 200, r.text
        # Existing developer session is now denied.
        assert dev_browser.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                                headers={"X-CSRF-Token": dev_csrf}).status_code == 401
        assert dev_browser.post("/console/dev-login", json={"tenant_id": t.id,
                                "user_subject": "dev@synthetic.example"}).status_code == 401
    row = owner.execute("SELECT reason FROM audit_events WHERE object_id = %s AND action = 'membership.revoke'",
                        (mid,)).fetchone()
    assert row["reason"] == "left company"


def test_last_owner_protected_and_role_permissions(client, make_tenant):
    t = make_tenant()
    csrf = _login(client, t.id, t.owner_subject)
    r = client.post(f"/console/memberships/{t.owner_membership}/revoke", json={"reason": "oops"},
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 409 and r.json()["code"] == "last_owner"
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        add_member(conn, t.id, "reviewer@synthetic.example", "reviewer")
    csrf = _login(client, t.id, "reviewer@synthetic.example")
    r = client.post("/console/api-keys", json={"scopes": ["sessions:read"]}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 403


def test_console_commands_require_csrf_and_idle_timeout(client, make_tenant, owner):
    t = make_tenant()
    csrf = _login(client, t.id, t.owner_subject)
    assert client.post("/console/api-keys", json={"scopes": ["sessions:read"]}).status_code == 403
    assert client.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                       headers={"X-CSRF-Token": "wrong"}).status_code == 403
    owner.execute("UPDATE console_sessions SET last_seen_at = now() - interval '2 hours' WHERE tenant_id = %s",
                  (t.id,))
    assert client.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                       headers={"X-CSRF-Token": csrf}).status_code == 401
