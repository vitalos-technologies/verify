"""Independent verifier (M02-T02): OIDC negative paths. test_DEFECT_* assert spec behaviour (expected FAIL)."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import psycopg
import pytest
from conftest import OWNER_DSN, fake_resolver
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from test_oidc import CLIENT, ISS, FakeIdP

from vv import oidc
from vv.admin import add_member
from vv.api.app import create_app


class RawIdP(FakeIdP):
    """Can return an attacker-chosen raw id_token from the token endpoint."""

    def __init__(self):
        super().__init__()
        self.raw: dict[str, str] = {}

    def handler(self, request):
        if request.url.path == "/token":
            form = parse_qs(request.content.decode())
            if form["code"][0] in self.raw:
                return httpx.Response(200, json={"id_token": self.raw.pop(form["code"][0])})
        return super().handler(request)


@pytest.fixture()
def idp():
    return RawIdP()


def _app(settings, idp):
    client = oidc.OidcClient(oidc.OidcConfig(ISS, CLIENT, "secret", "http://testserver/console/oidc/callback"),
                             http=httpx.Client(transport=httpx.MockTransport(idp.handler)))
    return create_app(settings, resolver=fake_resolver, oidc_client=client)


@pytest.fixture()
def oidc_app(settings, idp):
    return _app(settings, idp)


def _member(t, sub, role="owner"):
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        return add_member(conn, t.id, f"{ISS}|{sub}", role)


def _start(c, tenant=None):
    r = c.get("/console/oidc/start", params={"tenant": tenant} if tenant else None, follow_redirects=False)
    assert r.status_code == 302
    return parse_qs(urlsplit(r.headers["location"]).query)


def _claims(q, sub, **over):
    now = int(time.time())
    c = {"iss": ISS, "aud": CLIENT, "sub": sub, "iat": now, "exp": now + 300, "nonce": q["nonce"][0],
         "amr": ["pwd", "otp"], "auth_time": now, "_challenge": q["code_challenge"][0]}
    c.update(over)
    return c


def _b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")


def test_fixed_login_csrf_state_not_bound_to_browser(oidc_app, idp, make_tenant):
    """Attacker starts a login in their own browser, authenticates as themselves, and makes the victim's
    browser open the callback URL. The callback succeeds in a browser that never started the flow."""
    t = make_tenant()
    _member(t, "attacker")
    with TestClient(oidc_app) as attacker_browser:
        q = _start(attacker_browser)
    idp.issue("code-csrf", _claims(q, "attacker"))
    with TestClient(oidc_app) as victim_browser:  # no cookies at all
        r = victim_browser.get("/console/oidc/callback", params={"code": "code-csrf", "state": q["state"][0]},
                               follow_redirects=False)
        print("victim callback:", r.status_code, r.headers.get("set-cookie", "")[:60])
        assert r.status_code != 302, "callback accepted in a browser that did not start the login (login CSRF)"


@pytest.mark.parametrize("amr", [["otp"], ["pwd", "kba"], ["pwd", "rba"], ["swk"], ["face"]])
def test_fixed_single_factor_amr_accepted_as_mfa(amr):
    assert not oidc.has_mfa({"amr": amr}), f"{amr} treated as multi-factor"


def test_fixed_step_up_satisfied_without_reauthentication(oidc_app, idp, make_tenant, owner):
    """Authorize request carries no max_age/prompt=login, and when auth_time is absent the session's auth time
    is taken from iat. A silent SSO re-login therefore satisfies step-up without the user re-authenticating."""
    t = make_tenant()
    _member(t, "sso-user")
    with TestClient(oidc_app) as c:
        q = _start(c)
        print("authorize params:", sorted(q))
        long_ago = int(time.time()) - 3600
        claims = _claims(q, "sso-user")
        claims.pop("auth_time")  # IdP not asked for auth_time (no max_age) -> may omit it
        idp.issue("code-sso", claims)
        r = c.get("/console/oidc/callback", params={"code": "code-sso", "state": q["state"][0]},
                  follow_redirects=False)
        assert r.status_code == 302
        s = owner.execute("SELECT extract(epoch FROM now() - auth_time) AS age FROM console_sessions WHERE "
                          "tenant_id = %s", (t.id,)).fetchone()
        print("session auth age (s):", s["age"], "real authentication was at", long_ago)
        assert "max_age" in q or q.get("prompt") == ["login"], "step-up cannot force re-authentication at the IdP"


def test_ok_alg_none_and_hs256_with_public_key_rejected(oidc_app, idp, make_tenant):
    t = make_tenant()
    _member(t, "alg")
    pub_pem = idp.key.public_key().public_bytes(serialization.Encoding.PEM,
                                                serialization.PublicFormat.SubjectPublicKeyInfo)
    with TestClient(oidc_app) as c:
        for i, mk in enumerate(("none", "hs256", "nokid", "jwk_header")):
            q = _start(c)
            claims = _claims(q, "alg")
            claims.pop("_challenge")
            if mk == "none":
                tok = f"{_b64({'alg': 'none', 'kid': 'k1'})}.{_b64(claims)}."
            elif mk == "hs256":
                import hashlib
                import hmac
                h = _b64({"alg": "HS256", "kid": "k1", "typ": "JWT"})
                p = _b64(claims)
                sig = base64.urlsafe_b64encode(hmac.new(pub_pem, f"{h}.{p}".encode(), hashlib.sha256).digest()
                                               ).decode().rstrip("=")
                tok = f"{h}.{p}.{sig}"
            elif mk == "nokid":
                tok = jwt.encode(claims, idp.key, algorithm="RS256")
            else:  # attacker-supplied embedded jwk, signed with attacker key
                pubjwk = jwt.algorithms.RSAAlgorithm.to_jwk(idp.other.public_key(), as_dict=True)
                tok = jwt.encode(claims, idp.other, algorithm="RS256", headers={"kid": "k1", "jwk": pubjwk})
            idp.raw[f"raw-{i}"] = tok
            r = c.get("/console/oidc/callback", params={"code": f"raw-{i}", "state": q["state"][0]},
                      follow_redirects=False)
            assert r.status_code == 401, (mk, r.status_code)
        assert c.get("/console/me").status_code == 401


def test_ok_revoked_member_and_suspended_tenant_cannot_sign_in(oidc_app, idp, make_tenant, owner):
    t = make_tenant()
    mid = _member(t, "gone")
    owner.execute("UPDATE memberships SET active = false WHERE id = %s", (mid,))
    with TestClient(oidc_app) as c:
        q = _start(c)
        idp.issue("code-gone", _claims(q, "gone"))
        r = c.get("/console/oidc/callback", params={"code": "code-gone", "state": q["state"][0]},
                  follow_redirects=False)
        assert r.status_code == 403
    u = make_tenant()
    _member(u, "susp")
    owner.execute("UPDATE tenants SET status = 'suspended' WHERE id = %s", (u.id,))
    with TestClient(oidc_app) as c:
        q = _start(c)
        idp.issue("code-susp", _claims(q, "susp"))
        r = c.get("/console/oidc/callback", params={"code": "code-susp", "state": q["state"][0]},
                  follow_redirects=False)
        assert r.status_code == 403


def test_ok_production_cookie_flags_and_fixed_redirect(settings, idp, make_tenant, monkeypatch):
    monkeypatch.setenv("VV_EVIDENCE_BUCKET", "vv-prod-evidence-test")
    monkeypatch.setenv("VV_EVIDENCE_KMS_KEY_ID", "alias/test")
    prod = replace(settings, environment="production", hosted_base_url="https://verify.synthetic.example",
                   console_base_url="https://console.synthetic.example")
    app = _app(prod, idp)
    t = make_tenant()
    _member(t, "prod")
    with TestClient(app, base_url="https://testserver") as c:
        assert c.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": "x"}).status_code in (404, 405)
        r = c.get("/console/oidc/start", params={"tenant": t.id, "return_to": "https://evil.example",
                                                  "next": "//evil.example"}, follow_redirects=False)
        q = parse_qs(urlsplit(r.headers["location"]).query)
        idp.issue("code-prod", _claims(q, "prod"))
        r = c.get("/console/oidc/callback", params={"code": "code-prod", "state": q["state"][0],
                                                    "return_to": "https://evil.example"}, follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "https://console.synthetic.example/app"
        cookies = r.headers.get_list("set-cookie")
        print(cookies)
        console = next(x for x in cookies if x.startswith("vv_console="))
        csrf = next(x for x in cookies if x.startswith("vv_csrf="))
        for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/console"):
            assert flag.lower() in console.lower(), flag
        assert "secure" in csrf.lower() and "samesite=strict" in csrf.lower()
