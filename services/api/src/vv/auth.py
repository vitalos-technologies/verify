"""Principals: tenant-scoped API keys and console (browser) sessions. VV-001, VV-002.

The tenant always derives from the verified credential, never from the request body.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from vv import crypto
from vv.db import Database
from vv.errors import ApiError, forbidden, unauthenticated
from vv.ids import new_id

API_SCOPES = frozenset({"sessions:create", "sessions:read", "decisions:write", "deletions:create",
                        "deletions:read", "webhooks:manage"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({"billing:manage", "legal_holds:manage",
                        "memberships:manage", "policies:manage", "api_keys:manage", "webhooks:manage",
                        "sessions:read", "sessions:create", "decisions:write", "audit:read"}),
    "administrator": frozenset({"policies:manage", "sessions:read", "sessions:create", "decisions:write"}),
    "reviewer": frozenset({"sessions:read", "decisions:write"}),
    "developer": frozenset({"api_keys:manage", "webhooks:manage", "sessions:read"}),
    "auditor": frozenset({"audit:read"}),
}


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    actor_type: str  # 'api_key' | 'console'
    actor_id: str
    permissions: frozenset[str]
    console_session_id: str | None = None
    auth_age_seconds: float | None = None

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise forbidden()

    def require_recent_auth(self, max_age_seconds: int = 15 * 60) -> None:
        """Step-up: sensitive console actions need a recent sign-in (11_security §Secrets and authentication)."""
        if self.actor_type == "console" and (self.auth_age_seconds is None or self.auth_age_seconds > max_age_seconds):
            raise ApiError(401, "step_up_required", "Sign in again to continue.")


def _now() -> datetime:
    return datetime.now(UTC)


# ------------------------------------------------------------------ API keys
def generate_api_key(environment: str) -> tuple[str, str, str]:
    """Returns (raw_key, prefix, secret). raw_key is shown exactly once."""
    env = "live" if environment == "production" else "test"
    prefix = crypto.random_token(9).replace("-", "x").replace("_", "y")
    secret = crypto.random_token(32)
    return f"vvk_{env}_{prefix}_{secret}", prefix, secret


def create_api_key(conn, pepper: bytes, environment: str, tenant_id: str, scopes: list[str], label: str,
                   created_by: str, expires_at: datetime | None = None) -> tuple[str, str]:
    unknown = set(scopes) - API_SCOPES
    if unknown or not scopes:
        raise ApiError(400, "invalid_scopes", "Unknown or empty scopes.")
    raw, prefix, secret = generate_api_key(environment)
    key_id = new_id("key")
    conn.execute(
        "INSERT INTO api_keys (tenant_id, id, prefix, secret_hash, scopes, label, created_by, expires_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, key_id, prefix, crypto.keyed_hash(pepper, "api_key", secret), sorted(set(scopes)), label,
         created_by, expires_at))
    return key_id, raw


def authenticate_api_key(db: Database, pepper: bytes, authorization: str | None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthenticated()
    raw = authorization[len("Bearer "):].strip()
    parts = raw.split("_", 3)
    if len(parts) != 4 or parts[0] != "vvk":
        raise unauthenticated()
    _, _, prefix, secret = parts
    with db.system_tx() as conn:
        row = conn.execute("SELECT * FROM vv_lookup_api_key(%s)", (prefix,)).fetchone()
    if row is None:
        crypto.keyed_hash(pepper, "api_key", secret)  # similar timing for unknown prefixes
        raise unauthenticated()
    if not crypto.constant_time_equal(row["secret_hash"], crypto.keyed_hash(pepper, "api_key", secret)):
        raise unauthenticated()
    if row["revoked_at"] is not None or (row["expires_at"] is not None and row["expires_at"] <= _now()):
        raise unauthenticated()
    if row["tenant_status"] == "suspended":
        raise forbidden("This organisation is suspended.")
    return Principal(row["tenant_id"], "api_key", row["id"], frozenset(row["scopes"]))


# ------------------------------------------------------------------ console sessions
def create_console_session(conn, tenant_id: str, membership_id: str, absolute_seconds: int, *,
                           auth_method: str = "dev", amr: list[str] | None = None,
                           auth_time: int | None = None) -> tuple[str, str]:
    token = crypto.random_token(32)
    csrf = crypto.random_token(24)
    conn.execute(
        "INSERT INTO console_sessions (tenant_id, id, membership_id, token_hash, csrf_hash, absolute_expires_at, "
        "auth_method, amr, auth_time) VALUES (%s,%s,%s,%s,%s, now() + make_interval(secs => %s), %s, %s, "
        "coalesce(to_timestamp(%s), now()))",
        (tenant_id, new_id("cses"), membership_id, crypto.token_hash(token), crypto.token_hash(csrf), absolute_seconds,
         auth_method, amr or [], auth_time))
    return token, csrf


def authenticate_console(db: Database, token: str | None, csrf: str | None, *, mutating: bool,
                         idle_seconds: int) -> Principal:
    if not token:
        raise unauthenticated()
    with db.system_tx() as conn:
        row = conn.execute("SELECT * FROM vv_lookup_console_session(%s)", (crypto.token_hash(token),)).fetchone()
    now = _now()
    if (row is None or row["revoked_at"] is not None or not row["membership_active"]
            or row["absolute_expires_at"] <= now or row["last_seen_at"] + timedelta(seconds=idle_seconds) <= now):
        raise unauthenticated()
    if row["tenant_status"] == "suspended":
        raise forbidden("This organisation is suspended.")
    if mutating and (not csrf or not crypto.constant_time_equal(row["csrf_hash"], crypto.token_hash(csrf))):
        raise ApiError(403, "csrf_failed", "Request could not be verified.")
    with db.tenant_tx(row["tenant_id"]) as conn:
        conn.execute("UPDATE console_sessions SET last_seen_at = now() WHERE tenant_id = %s AND id = %s",
                     (row["tenant_id"], row["id"]))
    return Principal(row["tenant_id"], "console", row["membership_id"], ROLE_PERMISSIONS[row["role"]],
                     console_session_id=row["id"], auth_age_seconds=(now - row["auth_time"]).total_seconds())


def revoke_membership(conn, tenant_id: str, membership_id: str, reason: str) -> None:
    row = conn.execute("SELECT role, active FROM memberships WHERE tenant_id = %s AND id = %s FOR UPDATE",
                       (tenant_id, membership_id)).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Resource not found.")
    if row["role"] == "owner" and row["active"]:
        owners = conn.execute("SELECT count(*) AS n FROM memberships WHERE tenant_id = %s AND role = 'owner' "
                              "AND active", (tenant_id,)).fetchone()["n"]
        if owners <= 1:
            raise ApiError(409, "last_owner", "The last active owner cannot be removed.")
    conn.execute("UPDATE memberships SET active = false, revoked_at = now(), revoked_reason = %s "
                 "WHERE tenant_id = %s AND id = %s", (reason, tenant_id, membership_id))
    conn.execute("UPDATE console_sessions SET revoked_at = now() WHERE tenant_id = %s AND membership_id = %s "
                 "AND revoked_at IS NULL", (tenant_id, membership_id))
