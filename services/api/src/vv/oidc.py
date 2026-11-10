"""OIDC sign-in for the customer console (M02-T02, VV-002, 11_security §Secrets and authentication).

Authorization code flow with PKCE (S256), state and nonce. ID tokens are verified against the
issuer's JWKS (signature, iss, aud, exp, iat, nonce). Every console role handles identity data,
so sign-in requires multi-factor evidence in the `amr` claim (RFC 8176). Sensitive actions
(evidence reveal, API key creation, membership changes) need a recent authentication (step-up).
Provider-agnostic: works with Cognito, Entra ID, Okta, Keycloak once the IdP is chosen (M01).
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt

from vv import crypto
from vv.errors import ApiError

# RFC 8176 methods grouped into factor categories; MFA needs two different categories, or an explicit "mfa".
KNOWLEDGE = {"pwd", "pin", "kba"}
POSSESSION = {"otp", "sms", "tel", "hwk", "swk", "sc", "pop"}
INHERENCE = {"fpt", "face", "iris", "retina", "vbm"}
LOGIN_TTL_SECONDS = 600
STEP_UP_SECONDS = 15 * 60


@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    client_id: str
    client_secret: str | None
    redirect_uri: str


class OidcClient:
    def __init__(self, cfg: OidcConfig, http: httpx.Client | None = None) -> None:
        self.cfg = cfg
        self.http = http or httpx.Client(timeout=10, follow_redirects=False)
        self._meta: dict | None = None
        self._jwks: tuple[float, jwt.PyJWKSet] | None = None

    def meta(self) -> dict:
        if self._meta is None:
            r = self.http.get(self.cfg.issuer.rstrip("/") + "/.well-known/openid-configuration")
            r.raise_for_status()
            meta = r.json()
            if meta.get("issuer") != self.cfg.issuer:
                raise ApiError(502, "idp_misconfigured", "Identity provider metadata is invalid.")
            self._meta = meta
        return self._meta

    def jwks(self, force: bool = False) -> jwt.PyJWKSet:
        if force or self._jwks is None or time.time() - self._jwks[0] > 3600:
            r = self.http.get(self.meta()["jwks_uri"])
            r.raise_for_status()
            self._jwks = (time.time(), jwt.PyJWKSet.from_dict(r.json()))
        return self._jwks[1]

    def authorize_url(self, state: str, nonce: str, verifier: str, max_age: int) -> str:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        q = {"response_type": "code", "client_id": self.cfg.client_id, "redirect_uri": self.cfg.redirect_uri,
             "scope": "openid email", "state": state, "nonce": nonce, "code_challenge": challenge,
             "code_challenge_method": "S256", "max_age": str(max_age)}
        if max_age == 0:
            q["prompt"] = "login"
        return self.meta()["authorization_endpoint"] + "?" + urlencode(q)

    def exchange(self, code: str, verifier: str) -> str:
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.cfg.redirect_uri,
                "client_id": self.cfg.client_id, "code_verifier": verifier}
        auth = (self.cfg.client_id, self.cfg.client_secret) if self.cfg.client_secret else None
        r = self.http.post(self.meta()["token_endpoint"], data=data, auth=auth)
        if r.status_code != 200 or "id_token" not in r.json():
            raise ApiError(401, "sign_in_failed", "Sign-in failed.")
        return r.json()["id_token"]

    def verify(self, id_token: str, nonce: str) -> dict:
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
            keys = self.jwks()
            try:
                key = keys[kid]
            except KeyError:
                key = self.jwks(force=True)[kid]  # key rotation
            claims = jwt.decode(id_token, key.key, algorithms=["RS256", "ES256", "PS256"], audience=self.cfg.client_id,
                                issuer=self.cfg.issuer, options={"require": ["exp", "iat", "sub", "nonce"]},
                                leeway=60)
        except (jwt.PyJWTError, KeyError):
            raise ApiError(401, "sign_in_failed", "Sign-in failed.") from None
        if not crypto.constant_time_equal(str(claims.get("nonce")), nonce):
            raise ApiError(401, "sign_in_failed", "Sign-in failed.")
        return claims


def has_mfa(claims: dict) -> bool:
    amr = claims.get("amr") or []
    if not isinstance(amr, list):
        return False
    methods = {str(a) for a in amr}
    if "mfa" in methods:
        return True
    categories = sum(1 for group in (KNOWLEDGE, POSSESSION, INHERENCE) if methods & group)
    return categories >= 2


def start(conn, client: OidcClient, data_key: bytes, tenant_hint: str | None, *,
          reauth: bool = False) -> tuple[str, str]:
    """Returns (authorize_url, browser_binding). The binding goes in an HttpOnly cookie (login CSRF, D-G)."""
    state, nonce, verifier = crypto.random_token(24), crypto.random_token(24), crypto.random_token(48)
    binding = crypto.random_token(24)
    max_age = 0 if reauth else STEP_UP_SECONDS
    conn.execute("INSERT INTO oidc_logins (state_hash, nonce, verifier_sealed, tenant_hint, expires_at, "
                 "browser_binding_hash, max_age) VALUES (%s,%s,%s,%s, now() + make_interval(secs => %s), %s, %s)",
                 (crypto.token_hash(state), nonce, crypto.seal(data_key, verifier.encode(), b"oidc"), tenant_hint,
                  LOGIN_TTL_SECONDS, crypto.token_hash(binding), max_age))
    return client.authorize_url(state, nonce, verifier, max_age), binding


def finish(db, client: OidcClient, data_key: bytes, code: str, state: str, binding: str | None) -> dict:
    """Returns {'subject', 'claims', 'tenant_hint'} after full verification. One-use state bound to the browser."""
    with db.system_tx() as conn:
        row = conn.execute("UPDATE oidc_logins SET used_at = now() WHERE state_hash = %s AND used_at IS NULL "
                           "AND expires_at > now() AND browser_binding_hash = %s RETURNING *, "
                           "extract(epoch FROM created_at)::bigint AS started",
                           (crypto.token_hash(state or ""), crypto.token_hash(binding or ""))).fetchone()
    if row is None:
        raise ApiError(401, "sign_in_failed", "Sign-in expired. Please try again.")
    verifier = crypto.unseal(data_key, bytes(row["verifier_sealed"]), b"oidc").decode()
    claims = client.verify(client.exchange(code, verifier), row["nonce"])
    if not has_mfa(claims):
        raise ApiError(403, "mfa_required", "Sign in with multi-factor authentication.")
    auth_time = claims.get("auth_time")
    if isinstance(auth_time, int | float):
        auth_time = int(auth_time)
        if auth_time > time.time() + 60:
            raise ApiError(401, "sign_in_failed", "Sign-in failed.")
        if row["max_age"] == 0 and auth_time < row["started"] - 60:
            raise ApiError(401, "reauth_required", "Please sign in again.")  # IdP ignored prompt=login
    else:
        auth_time = 0  # unknown: sign-in allowed, but step-up is never satisfied without auth_time (D-I)
    return {"subject": f"{claims['iss']}|{claims['sub']}", "claims": claims, "tenant_hint": row["tenant_hint"],
            "amr": [str(a) for a in claims.get("amr", [])], "auth_time": auth_time}


def describe(claims: dict) -> str:
    return json.dumps({k: claims.get(k) for k in ("iss", "amr", "acr")})
