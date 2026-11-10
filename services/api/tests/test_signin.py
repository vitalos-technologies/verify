"""Owner-chosen console sign-in: Google or email magic link, then an authenticator code (TOTP)."""

from __future__ import annotations

import time
from urllib.parse import parse_qs, urlsplit

import psycopg
from conftest import OWNER_DSN
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from test_oidc import _sign_in, idp, oidc_app  # noqa: F401 (pytest fixtures)

from vv import signin
from vv.admin import add_member

EMAIL = "reviewer.signin@synthetic.example"


def _member(t, subject, role="owner"):
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        return add_member(conn, t.id, subject, role)


def _magic(c, email=EMAIL):
    r = c.post("/console/magic/start", json={"email": email})
    assert r.status_code == 200 and r.json() == {"status": "sent_if_valid"}
    return c.app.state.vv.messenger.last_link


def _code(secret, offset=0):
    return signin.totp(secret, int(time.time() // 30) + offset)


def test_totp_matches_rfc6238_vector():
    # RFC 6238 Appendix B, SHA-1, T=59 s -> 94287082 (8 digits); our 6-digit code is the last 6.
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32("12345678901234567890")
    assert signin.totp(secret, 59 // 30) == "287082"
    assert signin.match_step(secret, "287082", now=59) == 1


def test_magic_link_enrol_and_sign_in(client, make_tenant, owner):
    t = make_tenant()
    _member(t, f"email|{EMAIL}")
    with TestClient(client.app) as c:
        link = _magic(c)
        assert link and "/console/magic/callback?token=ml_" in link
        token = parse_qs(urlsplit(link).query)["token"][0]
        r = c.get("/console/magic/callback", params={"token": token}, follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/app/mfa")
        assert c.get("/console/me").status_code == 401
        st = c.get("/console/mfa/status").json()
        assert st == {"enrolled": False, "first_factor": "email", "account": EMAIL}
        enrol = c.post("/console/mfa/enroll").json()
        assert enrol["otpauth_uri"].startswith("otpauth://totp/Vitalos%20Verify:")
        assert c.post("/console/mfa/verify", json={"code": "000000"}).status_code == 400
        r = c.post("/console/mfa/verify", json={"code": _code(enrol["secret"])})
        assert r.status_code == 200 and r.json()["redirect"] == "/app"
        me = c.get("/console/me")
        assert me.status_code == 200 and me.json()["role"] == "owner"
        # Link and pending login are single-use.
        assert c.get("/console/magic/callback", params={"token": token}, follow_redirects=False).status_code == 401
        assert c.get("/console/mfa/status").status_code == 401
    sess = owner.execute("SELECT auth_method, amr FROM console_sessions WHERE tenant_id = %s", (t.id,)).fetchone()
    assert sess == {"auth_method": "email+totp", "amr": ["email", "otp"]}
    # Stored secret is sealed.
    row = owner.execute("SELECT secret_sealed FROM user_mfa WHERE subject = %s", (f"email|{EMAIL}",)).fetchone()
    assert enrol["secret"].encode() not in bytes(row["secret_sealed"])


def test_magic_link_bound_to_browser_and_no_enumeration(client, make_tenant):
    t = make_tenant()
    _member(t, "email|bound@synthetic.example")
    with TestClient(client.app) as requester:
        link = _magic(requester, "bound@synthetic.example")
    token = parse_qs(urlsplit(link).query)["token"][0]
    with TestClient(client.app) as other:
        r = other.get("/console/magic/callback", params={"token": token}, follow_redirects=False)
        assert r.status_code == 401  # opened in a browser that did not ask for it (login CSRF / forwarded link)
    before = client.app.state.vv.messenger.last_link
    with TestClient(client.app) as c:
        r = c.post("/console/magic/start", json={"email": "nobody@synthetic.example"})
        assert r.json() == {"status": "sent_if_valid"}  # identical answer
    assert client.app.state.vv.messenger.last_link == before  # nothing sent


def test_code_replay_and_lockout(client, make_tenant):
    t = make_tenant()
    _member(t, "email|replay@synthetic.example")
    with TestClient(client.app) as c:
        token = parse_qs(urlsplit(_magic(c, "replay@synthetic.example")).query)["token"][0]
        c.get("/console/magic/callback", params={"token": token}, follow_redirects=False)
        secret = c.post("/console/mfa/enroll").json()["secret"]
        code = _code(secret)
        assert c.post("/console/mfa/verify", json={"code": code}).status_code == 200
        h = {"X-CSRF-Token": c.cookies["vv_csrf"]}
        # Step-up with the same (already used) code is refused; the next step's code works.
        assert c.post("/console/mfa/step-up", json={"code": code}, headers=h).status_code == 400
        assert c.post("/console/mfa/step-up", json={"code": _code(secret, 1)}, headers=h).status_code == 200
    with TestClient(client.app) as c:  # second sign-in: five wrong codes end the pending login
        token = parse_qs(urlsplit(_magic(c, "replay@synthetic.example")).query)["token"][0]
        c.get("/console/magic/callback", params={"token": token}, follow_redirects=False)
        assert c.get("/console/mfa/status").json()["enrolled"] is True
        for _ in range(5):
            assert c.post("/console/mfa/verify", json={"code": "123456"}).status_code in (400, 401)
        assert c.post("/console/mfa/verify", json={"code": _code(secret, 1)}).status_code == 401


def test_step_up_by_code_unlocks_sensitive_action(client, make_tenant, owner):
    t = make_tenant()
    _member(t, "email|stepup@synthetic.example")
    with TestClient(client.app) as c:
        token = parse_qs(urlsplit(_magic(c, "stepup@synthetic.example")).query)["token"][0]
        c.get("/console/magic/callback", params={"token": token}, follow_redirects=False)
        secret = c.post("/console/mfa/enroll").json()["secret"]
        c.post("/console/mfa/verify", json={"code": _code(secret, -1)})
        owner.execute("UPDATE console_sessions SET auth_time = now() - interval '1 hour' WHERE tenant_id = %s",
                      (t.id,))
        h = {"X-CSRF-Token": c.cookies["vv_csrf"]}
        r = c.post("/console/api-keys", json={"scopes": ["sessions:read"]}, headers=h)
        assert r.status_code == 401 and r.json()["code"] == "step_up_required"
        assert c.post("/console/mfa/step-up", json={"code": _code(secret)}, headers=h).status_code == 200
        assert c.post("/console/api-keys", json={"scopes": ["sessions:read"]}, headers=h).status_code == 201


def test_google_verified_email_reaches_email_membership(oidc_app, idp, make_tenant):  # noqa: F811
    t = make_tenant()
    _member(t, "email|g.user@synthetic.example")
    with TestClient(oidc_app) as c:
        r, _ = _sign_in(c, idp, "google-sub-1", amr=(),
                        mutate=lambda cl: cl.update(email="G.User@synthetic.example", email_verified=True))
        assert r.status_code == 302 and r.headers["location"].endswith("/app/mfa")
        assert c.get("/console/mfa/status").json()["account"] == "g.user@synthetic.example"
        r2, _ = _sign_in(c, idp, "google-sub-2", amr=(),
                         mutate=lambda cl: cl.update(email="g.user@synthetic.example", email_verified=False))
        assert r2.status_code == 403  # unverified email never maps to a membership


def test_ses_messenger_sends_without_logging_secrets():
    from vv.applicant import SesMessenger

    class Stub:
        sent: list = []

        def send_email(self, **kw):
            self.sent.append(kw)

    stub = Stub()
    m = SesMessenger("no-reply@verify.example", client=stub)
    m.send_link(None, "hash", "https://console.example/console/magic/callback?token=ml_x", "a@b.example")
    m.send_code(None, "email", "hash", "123456", "a@b.example")
    assert stub.sent[0]["Destination"] == {"ToAddresses": ["a@b.example"]}
    assert "ml_x" in stub.sent[0]["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "123456" in stub.sent[1]["Content"]["Simple"]["Body"]["Text"]["Data"]
