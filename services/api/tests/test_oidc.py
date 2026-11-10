"""M02-T02 / AT-02: OIDC sign-in with PKCE, nonce and MFA enforcement; step-up for sensitive actions."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import psycopg
import pytest
from conftest import OWNER_DSN, fake_resolver
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv import oidc
from vv.admin import add_member
from vv.api.app import create_app

ISS = "https://idp.synthetic.example"
CLIENT = "vv-console-test"


class FakeIdP:
    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.codes: dict[str, dict] = {}
        pub = jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
        self.jwks = {"keys": [{**pub, "kid": "k1", "use": "sig", "alg": "RS256"}]}

    def issue(self, code: str, claims: dict, sign_with=None, kid="k1") -> None:
        self.codes[code] = {"claims": claims, "key": sign_with or self.key, "kid": kid}

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(200, json={"issuer": ISS, "authorization_endpoint": f"{ISS}/authorize",
                                             "token_endpoint": f"{ISS}/token", "jwks_uri": f"{ISS}/jwks"})
        if path == "/jwks":
            return httpx.Response(200, json=self.jwks)
        if path == "/token":
            form = parse_qs(request.content.decode())
            entry = self.codes.pop(form["code"][0], None)
            if entry is None:
                return httpx.Response(400, json={"error": "invalid_grant"})
            verifier = form["code_verifier"][0]
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
            if challenge != entry["claims"].pop("_challenge"):
                return httpx.Response(400, json={"error": "invalid_grant"})
            token = jwt.encode(entry["claims"], entry["key"], algorithm="RS256", headers={"kid": entry["kid"]})
            return httpx.Response(200, json={"id_token": token, "token_type": "Bearer"})
        return httpx.Response(404)


@pytest.fixture()
def idp():
    return FakeIdP()


@pytest.fixture()
def oidc_app(settings, idp):
    client = oidc.OidcClient(oidc.OidcConfig(ISS, CLIENT, "secret", "http://testserver/console/oidc/callback"),
                             http=httpx.Client(transport=httpx.MockTransport(idp.handler)))
    return create_app(settings, resolver=fake_resolver, oidc_client=client)


def _member(t, sub, role="owner"):
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        return add_member(conn, t.id, f"{ISS}|{sub}", role)


def _sign_in(c, idp, sub, *, amr=("pwd", "otp"), tenant=None, mutate=None, sign_with=None, kid="k1"):
    r = c.get("/console/oidc/start", params={"tenant": tenant} if tenant else None, follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert q["code_challenge_method"] == ["S256"]
    now = int(time.time())
    claims = {"iss": ISS, "aud": CLIENT, "sub": sub, "iat": now, "exp": now + 300, "nonce": q["nonce"][0],
              "amr": list(amr), "auth_time": now, "_challenge": q["code_challenge"][0]}
    if mutate:
        mutate(claims)
    code = f"code-{sub}-{now}-{len(idp.codes)}"
    idp.issue(code, claims, sign_with=sign_with, kid=kid)
    return c.get("/console/oidc/callback", params={"code": code, "state": q["state"][0]}, follow_redirects=False), q


def test_sign_in_with_mfa_creates_session(oidc_app, idp, make_tenant, owner):
    t = make_tenant()
    _member(t, "alice")
    with TestClient(oidc_app) as c:
        r, _ = _sign_in(c, idp, "alice")
        assert r.status_code == 302 and r.headers["location"].endswith("/app")
        assert "vv_console" in r.headers.get("set-cookie", "") and "vv_csrf" in r.cookies
        me = c.get("/console/me")
        assert me.status_code == 200 and me.json()["role"] == "owner"
        key = c.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                     headers={"X-CSRF-Token": c.cookies["vv_csrf"]})
        assert key.status_code == 201
    s = owner.execute("SELECT auth_method, amr FROM console_sessions WHERE tenant_id = %s", (t.id,)).fetchone()
    assert s == {"auth_method": "oidc", "amr": ["pwd", "otp"]}


@pytest.mark.parametrize("case", ["no_mfa", "wrong_nonce", "wrong_aud", "wrong_iss", "expired", "bad_key",
                                  "unknown_kid"])
def test_rejected_tokens(oidc_app, idp, make_tenant, case):
    t = make_tenant()
    _member(t, f"bob-{case}")
    kwargs: dict = {}
    if case == "no_mfa":
        kwargs["amr"] = ("pwd",)
    elif case == "wrong_nonce":
        kwargs["mutate"] = lambda c: c.update(nonce="attacker")
    elif case == "wrong_aud":
        kwargs["mutate"] = lambda c: c.update(aud="other-client")
    elif case == "wrong_iss":
        kwargs["mutate"] = lambda c: c.update(iss="https://evil.example")
    elif case == "expired":
        kwargs["mutate"] = lambda c: c.update(exp=int(time.time()) - 600, iat=int(time.time()) - 900)
    elif case == "bad_key":
        kwargs["sign_with"] = idp.other
    elif case == "unknown_kid":
        kwargs["kid"] = "nope"
    with TestClient(oidc_app) as c:
        r, _ = _sign_in(c, idp, f"bob-{case}", **kwargs)
        assert r.status_code in (401, 403), (case, r.status_code)
        assert c.get("/console/me").status_code == 401


def test_state_is_one_use_and_non_member_refused(oidc_app, idp, make_tenant):
    t = make_tenant()
    _member(t, "carol")
    with TestClient(oidc_app) as c:
        r, q = _sign_in(c, idp, "carol")
        assert r.status_code == 302
        replay = c.get("/console/oidc/callback", params={"code": "x", "state": q["state"][0]}, follow_redirects=False)
        assert replay.status_code == 401
        r2, _ = _sign_in(c, idp, "mallory")  # valid MFA token, but no membership
        assert r2.status_code == 403 and r2.json()["code"] == "no_membership"


def test_multiple_organisations_need_a_choice(oidc_app, idp, make_tenant):
    a, b = make_tenant(), make_tenant()
    _member(a, "dave")
    _member(b, "dave", "reviewer")
    with TestClient(oidc_app) as c:
        r, _ = _sign_in(c, idp, "dave")
        assert r.status_code == 403 and r.json()["code"] == "choose_organisation"
        r, _ = _sign_in(c, idp, "dave", tenant=b.id)
        assert r.status_code == 302 and c.get("/console/me").json()["role"] == "reviewer"


def test_step_up_required_for_sensitive_actions(oidc_app, idp, make_tenant, owner):
    t = make_tenant()
    _member(t, "erin")
    with TestClient(oidc_app) as c:
        _sign_in(c, idp, "erin")
        owner.execute("UPDATE console_sessions SET auth_time = now() - interval '20 minutes' WHERE tenant_id = %s",
                      (t.id,))
        h = {"X-CSRF-Token": c.cookies["vv_csrf"]}
        r = c.post("/console/api-keys", json={"scopes": ["sessions:read"]}, headers=h)
        assert r.status_code == 401 and r.json()["code"] == "step_up_required"
        assert c.get("/console/me").status_code == 200  # ordinary reads continue
        _sign_in(c, idp, "erin")  # re-authenticate
        assert c.post("/console/api-keys", json={"scopes": ["sessions:read"]},
                      headers={"X-CSRF-Token": c.cookies["vv_csrf"]}).status_code == 201


def test_oidc_routes_absent_without_configuration(client):
    assert client.get("/console/oidc/start", follow_redirects=False).status_code == 404


def test_amr_rules():
    assert oidc.has_mfa({"amr": ["mfa"]}) and oidc.has_mfa({"amr": ["pwd", "otp"]}) and oidc.has_mfa({"amr": ["hwk"]})
    assert not oidc.has_mfa({"amr": ["pwd"]}) and not oidc.has_mfa({}) and not oidc.has_mfa({"amr": "mfa"})
    json.dumps(oidc.describe({"iss": ISS, "amr": ["mfa"]}))
