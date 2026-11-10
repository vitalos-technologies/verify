"""Console sign-in: Google or email magic link, then an authenticator code (owner decision 10 Nov 2026).

- First factor: Google (OIDC, verified email) or a one-use 15-minute magic link bound to the browser
  that requested it. Responses never reveal whether an address has an account.
- Second factor: TOTP (RFC 6238, SHA-1, 6 digits, 30 s, ±1 step) enrolled per person, with replay
  protection. Required unless the IdP itself asserts MFA in `amr`.
- Step-up for sensitive actions: re-enter a current code (no new login needed).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from vv import crypto
from vv.errors import ApiError

MAGIC_TTL = 15 * 60
PENDING_TTL = 10 * 60
MAX_TOTP_FAILURES = 5
ISSUER = "Vitalos Verify"


def email_subject(email: str) -> str:
    e = email.strip().lower()
    if "@" not in e or len(e) > 254 or " " in e:
        raise ApiError(400, "invalid_email", "Enter a valid email address.")
    return f"email|{e}"


# ------------------------------------------------------------------ TOTP
def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def match_step(secret: str, code: str, now: float | None = None) -> int | None:
    if not code or not code.isdigit() or len(code) != 6:
        return None
    current = int((now if now is not None else time.time()) // 30)
    for step in (current - 1, current, current + 1):
        if hmac.compare_digest(totp(secret, step), code):
            return step
    return None


def otpauth_uri(secret: str, account: str) -> str:
    return (f"otpauth://totp/{quote(ISSUER)}:{quote(account)}?secret={secret}&issuer={quote(ISSUER)}"
            "&algorithm=SHA1&digits=6&period=30")


# ------------------------------------------------------------------ magic links
def start_magic(conn, data_key: bytes, email: str, tenant_hint: str | None) -> tuple[str | None, str]:
    """Returns (token or None, browser binding). Token is None when no active membership exists."""
    subject = email_subject(email)
    binding = crypto.random_token(24)
    exists = conn.execute("SELECT 1 FROM vv_memberships_for_subject(%s) LIMIT 1", (subject,)).fetchone()
    recent = conn.execute("SELECT count(*) AS n FROM magic_links WHERE subject = %s AND created_at > now() - "
                          "interval '1 hour'", (subject,)).fetchone()["n"]
    if exists is None or recent >= 5:
        return None, binding  # same response either way: no account enumeration
    token = "ml_" + crypto.random_token(32)
    conn.execute("INSERT INTO magic_links (token_hash, subject, binding_hash, tenant_hint, expires_at) "
                 "VALUES (%s,%s,%s,%s, now() + make_interval(secs => %s))",
                 (crypto.token_hash(token), subject, crypto.token_hash(binding), tenant_hint, MAGIC_TTL))
    return token, binding


def finish_magic(conn, token: str, binding: str | None) -> dict:
    row = conn.execute("UPDATE magic_links SET used_at = now() WHERE token_hash = %s AND used_at IS NULL AND "
                       "expires_at > now() AND binding_hash = %s RETURNING subject, tenant_hint",
                       (crypto.token_hash(token or ""), crypto.token_hash(binding or ""))).fetchone()
    if row is None:
        raise ApiError(401, "link_invalid", "This sign-in link has expired or was opened in another browser.")
    return {"subjects": [row["subject"]], "first_factor": "email", "tenant_hint": row["tenant_hint"]}


# ------------------------------------------------------------------ pending login + second factor
def create_pending(conn, subjects: list[str], first_factor: str, tenant_hint: str | None) -> str:
    token = crypto.random_token(32)
    conn.execute("INSERT INTO login_pending (token_hash, subjects, first_factor, tenant_hint, expires_at) "
                 "VALUES (%s,%s,%s,%s, now() + make_interval(secs => %s))",
                 (crypto.token_hash(token), subjects, first_factor, tenant_hint, PENDING_TTL))
    return token


def load_pending(conn, token: str | None, *, lock: bool = False) -> dict:
    sql = ("SELECT * FROM login_pending WHERE token_hash = %s AND used_at IS NULL AND expires_at > now() "
           "AND failed < %s")
    row = conn.execute(sql + (" FOR UPDATE" if lock else ""),
                       (crypto.token_hash(token or ""), MAX_TOTP_FAILURES)).fetchone()
    if row is None:
        raise ApiError(401, "sign_in_expired", "Sign-in expired. Please start again.")
    return row


def mfa_subject(subjects: list[str]) -> str:
    """One authenticator per person: prefer the email identity, which both Google and magic links share."""
    return next((s for s in subjects if s.startswith("email|")), subjects[0])


def enrolment(conn, data_key: bytes, subject: str) -> dict:
    row = conn.execute("SELECT * FROM user_mfa WHERE subject = %s FOR UPDATE", (subject,)).fetchone()
    if row and row["confirmed_at"]:
        return {"enrolled": True}
    secret = new_secret()
    sealed = crypto.seal(data_key, secret.encode(), subject.encode())
    conn.execute("INSERT INTO user_mfa (subject, secret_sealed) VALUES (%s,%s) ON CONFLICT (subject) DO UPDATE "
                 "SET secret_sealed = EXCLUDED.secret_sealed, created_at = now()", (subject, sealed))
    account = subject.split("|", 1)[1]
    return {"enrolled": False, "secret": secret, "otpauth_uri": otpauth_uri(secret, account)}


def check_code(conn, data_key: bytes, subject: str, code: str) -> bool:
    row = conn.execute("SELECT * FROM user_mfa WHERE subject = %s FOR UPDATE", (subject,)).fetchone()
    if row is None:
        return False
    secret = crypto.unseal(data_key, bytes(row["secret_sealed"]), subject.encode()).decode()
    step = match_step(secret, code)
    if step is None or step <= row["last_step"]:
        return False  # wrong, or a code already used (replay)
    conn.execute("UPDATE user_mfa SET last_step = %s, confirmed_at = coalesce(confirmed_at, now()) "
                 "WHERE subject = %s", (step, subject))
    return True


def is_enrolled(conn, subject: str) -> bool:
    row = conn.execute("SELECT confirmed_at FROM user_mfa WHERE subject = %s", (subject,)).fetchone()
    return bool(row and row["confirmed_at"])
