"""Applicant journey: one-use hosted token exchange, notice acknowledgement, attempts, contact OTP.

VV-003 (expiring sessions), VV-006 (no client-authoritative approval), VV-015 (contact checks).
The applicant browser is untrusted: an SDK "success" only moves the session to processing.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from vv import crypto
from vv.db import Database
from vv.errors import ApiError, conflict
from vv.ids import new_id
from vv.providers.base import ProviderAdapter, ProviderUnavailable
from vv.service import audit, get_session, transition

NOTICE_VERSION = "notice-synthetic-1"  # placeholder: real notices need controller-approved wording (M05)
LINK_INVALID = ApiError(404, "link_invalid", "This link is invalid or has expired. Ask the requesting organisation "
                        "for a new link.")
ACTIVE_FOR_CAPTURE = {"created", "in_progress", "action_required"}

# Contact abuse controls (AT-15). Planning values; tune from measured abuse data.
OTP_TTL_SECONDS = 600
OTP_MAX_FAILED = 5
SESSION_SENDS_PER_15_MIN = 3
SESSION_SENDS_TOTAL = 5
DESTINATION_SENDS_PER_DAY = 5
SEND_COOLDOWN_SECONDS = 30
MESSAGE_COST_MINOR = 5  # assumption for spend tracking only


@dataclass(frozen=True)
class ApplicantContext:
    tenant_id: str
    session_id: str


def exchange_token(db: Database, token: str, ttl_seconds: int) -> tuple[str, ApplicantContext]:
    """Swap the one-use hosted token for a restricted HttpOnly applicant session cookie."""
    if not token or len(token) > 200:
        raise LINK_INVALID
    with db.system_tx() as conn:
        hit = conn.execute("SELECT * FROM vv_lookup_hosted_token(%s)", (crypto.token_hash(token),)).fetchone()
    if hit is None:
        raise LINK_INVALID
    with db.tenant_tx(hit["tenant_id"]) as conn:
        s = conn.execute(
            "SELECT * FROM sessions WHERE tenant_id = %s AND id = %s FOR UPDATE", (hit["tenant_id"], hit["session_id"])
        ).fetchone()
        valid = conn.execute("SELECT %s::timestamptz > now() AND %s::timestamptz > now() AS ok",
                             (s["hosted_token_expires_at"], s["expires_at"])).fetchone()["ok"]
        if s["hosted_token_used_at"] is not None or not valid or s["state"] not in ACTIVE_FOR_CAPTURE:
            raise LINK_INVALID
        conn.execute("UPDATE sessions SET hosted_token_used_at = now() WHERE tenant_id = %s AND id = %s",
                     (s["tenant_id"], s["id"]))
        cookie = crypto.random_token(32)
        conn.execute(
            "INSERT INTO applicant_sessions (tenant_id, id, session_id, token_hash, expires_at) "
            "VALUES (%s,%s,%s,%s, least(now() + make_interval(secs => %s), %s))",
            (s["tenant_id"], new_id("apps"), s["id"], crypto.token_hash(cookie), ttl_seconds, s["expires_at"]))
        audit(conn, s["tenant_id"], "applicant", s["id"], "hosted_token.exchanged", "session", s["id"])
    return cookie, ApplicantContext(hit["tenant_id"], hit["session_id"])


def authenticate_applicant(db: Database, cookie: str | None) -> ApplicantContext:
    if not cookie:
        raise ApiError(401, "applicant_session_required", "Open the link you were sent to continue.")
    with db.system_tx() as conn:
        row = conn.execute("SELECT *, expires_at > now() AS live FROM vv_lookup_applicant_session(%s)",
                           (crypto.token_hash(cookie),)).fetchone()
    if row is None or not row["live"]:
        raise ApiError(401, "applicant_session_expired", "Your session has ended. Open the link again or ask for a "
                       "new one.")
    return ApplicantContext(row["tenant_id"], row["session_id"])


def applicant_view(conn, ctx: ApplicantContext) -> dict:
    s = get_session(conn, ctx.tenant_id, ctx.session_id)
    tenant = conn.execute("SELECT name FROM tenants WHERE id = %s", (ctx.tenant_id,)).fetchone()
    policy = conn.execute("SELECT definition FROM policies WHERE tenant_id = %s AND id = %s",
                          (ctx.tenant_id, s["policy_row_id"])).fetchone()["definition"]
    ack = conn.execute("SELECT 1 FROM notice_acknowledgements WHERE tenant_id = %s AND session_id = %s "
                       "AND notice_version = %s", (ctx.tenant_id, ctx.session_id, NOTICE_VERSION)).fetchone()
    contact = {r["type"] for r in conn.execute(
        "SELECT type FROM checks WHERE tenant_id = %s AND session_id = %s AND type IN ('email','phone') "
        "AND result = 'pass'", (ctx.tenant_id, ctx.session_id))}
    # Applicant-safe status only: no internal fraud detail or reason codes.
    applicant_status = {
        "created": "not_started", "in_progress": "in_progress", "processing": "submitted", "error": "submitted",
        "review_required": "submitted", "action_required": "action_required", "approved": "completed",
        "declined": "completed", "expired": "expired", "cancelled": "cancelled",
    }[s["state"]]
    return {
        "requesting_organisation": tenant["name"],
        "purpose": "Identity check for onboarding",
        "expires_at": s["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": applicant_status,
        "document": {"country": s["country"], "type": s["document_type"]},
        "required_steps": [c for c in policy["required_checks"]],
        "notice_version": NOTICE_VERSION,
        "notice_acknowledged": ack is not None,
        "contact_verified": sorted(contact),
        "alternative_route": "If you cannot complete this online, contact the requesting organisation for its "
                             "alternative identity check.",
    }


def acknowledge_notice(conn, ctx: ApplicantContext, notice_version: str, kind: str) -> None:
    if notice_version != NOTICE_VERSION:
        raise ApiError(409, "notice_outdated", "Please review the current privacy notice.")
    if kind not in ("acknowledgement", "explicit_consent"):
        raise ApiError(400, "invalid_kind", "Unknown acknowledgement kind.")
    conn.execute("INSERT INTO notice_acknowledgements (tenant_id, id, session_id, notice_version, kind) "
                 "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                 (ctx.tenant_id, new_id("ack"), ctx.session_id, notice_version, kind))


# ------------------------------------------------------------------ attempts
def start_attempt(db: Database, ctx: ApplicantContext, provider: ProviderAdapter, request_id: str) -> dict:
    with db.tenant_tx(ctx.tenant_id) as conn:
        s = get_session(conn, ctx.tenant_id, ctx.session_id, for_update=True)
        if s["state"] not in ACTIVE_FOR_CAPTURE:
            raise conflict("session_not_active", "This verification cannot accept new evidence.")
        if conn.execute("SELECT expires_at <= now() AS e FROM sessions WHERE tenant_id=%s AND id=%s",
                        (s["tenant_id"], s["id"])).fetchone()["e"]:
            raise LINK_INVALID
        ack = conn.execute("SELECT 1 FROM notice_acknowledgements WHERE tenant_id = %s AND session_id = %s "
                           "AND notice_version = %s", (ctx.tenant_id, ctx.session_id, NOTICE_VERSION)).fetchone()
        if ack is None:
            raise conflict("notice_required", "Please read and acknowledge the privacy notice first.")
        policy = conn.execute("SELECT definition FROM policies WHERE tenant_id = %s AND id = %s",
                              (ctx.tenant_id, s["policy_row_id"])).fetchone()["definition"]
        for channel in ("email", "phone"):
            if channel in policy["required_checks"] and conn.execute(
                    "SELECT 1 FROM checks WHERE tenant_id = %s AND session_id = %s AND type = %s AND result = 'pass'",
                    (ctx.tenant_id, ctx.session_id, channel)).fetchone() is None:
                raise conflict("contact_required", f"Please confirm your {channel} first.")
        latest = conn.execute("SELECT * FROM attempts WHERE tenant_id = %s AND session_id = %s "
                              "ORDER BY sequence DESC LIMIT 1", (ctx.tenant_id, ctx.session_id)).fetchone()
        if latest and latest["state"] in ("creating", "error") and latest["provider_reference"] is None:
            attempt = latest  # provider call never succeeded: reuse attempt and its idempotency key
        elif latest and latest["state"] == "capturing" and s["state"] == "in_progress":
            attempt = latest  # resume the same capture (e.g. page refresh) without duplicating evidence
        else:
            if s["state"] == "action_required":
                if s["quality_retries_used"] >= int(policy["quality_retries"]):
                    raise conflict("retry_limit_reached", "The retry limit has been reached. Contact the "
                                   "requesting organisation for the alternative route.")
                s = transition(conn, s, "in_progress", extra_sets=", quality_retries_used = quality_retries_used + 1")
            elif s["state"] == "created":
                s = transition(conn, s, "in_progress", emit_event=False)
            if latest:
                conn.execute("UPDATE attempts SET state = 'superseded' WHERE tenant_id = %s AND id = %s "
                             "AND state <> 'completed'", (ctx.tenant_id, latest["id"]))
            attempt = conn.execute(
                "INSERT INTO attempts (tenant_id, id, session_id, sequence, provider, state) "
                "VALUES (%s,%s,%s,%s,%s,'creating') RETURNING *",
                (ctx.tenant_id, new_id("att"), ctx.session_id, (latest["sequence"] + 1) if latest else 1,
                 s["provider"])).fetchone()
    # External call happens outside any database transaction; stable idempotency key = attempt id.
    try:
        handle = provider.create_attempt(session_id=ctx.session_id, attempt_id=attempt["id"],
                                         idempotency_key=attempt["id"], correlation_id=request_id)
    except ProviderUnavailable:
        with db.tenant_tx(ctx.tenant_id) as conn:
            conn.execute("UPDATE attempts SET state = 'error' WHERE tenant_id = %s AND id = %s "
                         "AND provider_reference IS NULL", (ctx.tenant_id, attempt["id"]))
        raise ApiError(503, "provider.unavailable", "The verification service is temporarily unavailable. "
                       "Your progress is saved; please try again shortly.") from None
    with db.tenant_tx(ctx.tenant_id) as conn:
        conn.execute("UPDATE attempts SET provider_reference = %s, state = 'capturing' WHERE tenant_id = %s "
                     "AND id = %s", (handle.provider_reference, ctx.tenant_id, attempt["id"]))
    return {"attempt_id": attempt["id"], "provider": provider.name, "capture_token": handle.capture_token}


def mark_submitted(db: Database, ctx: ApplicantContext, attempt_id: str) -> dict:
    """Client hint that capture finished. Moves to processing; never approves (VV-006)."""
    with db.tenant_tx(ctx.tenant_id) as conn:
        s = get_session(conn, ctx.tenant_id, ctx.session_id, for_update=True)
        a = conn.execute("SELECT * FROM attempts WHERE tenant_id = %s AND id = %s AND session_id = %s FOR UPDATE",
                         (ctx.tenant_id, attempt_id, ctx.session_id)).fetchone()
        if a is None:
            raise ApiError(404, "not_found", "Resource not found.")
        if a["state"] not in ("capturing", "submitted", "completed"):
            raise conflict("attempt_not_capturing", "Start the capture before submitting.")
        if a["state"] == "capturing":
            conn.execute("UPDATE attempts SET state = 'submitted' WHERE tenant_id = %s AND id = %s",
                         (ctx.tenant_id, attempt_id))
        if s["state"] == "in_progress":
            transition(conn, s, "processing", [])
        return applicant_view(conn, ctx)


# ------------------------------------------------------------------ contact verification (VV-015)
class DummyMessenger:
    """Development/test messaging adapter. Records that a message was sent (no code, no address).

    The last code per destination hash is kept in process memory for automated tests only.
    """

    def __init__(self) -> None:
        self.last_code: dict[str, str] = {}
        self.last_sent: str | None = None
        self.last_link: str | None = None

    def send_code(self, conn, channel: str, destination_hash: str, code: str, address: str = "") -> None:
        conn.execute("INSERT INTO dummy_messages (id, channel, destination_hash, template) VALUES (%s,%s,%s,%s)",
                     (new_id("msg"), channel, destination_hash, "contact_code_v1"))
        self.last_code[destination_hash] = code
        self.last_sent = code

    def send_link(self, conn, destination_hash: str, link: str, address: str = "") -> None:
        conn.execute("INSERT INTO dummy_messages (id, channel, destination_hash, template) VALUES (%s,%s,%s,%s)",
                     (new_id("msg"), "email", destination_hash, "magic_link_v1"))
        self.last_link = link


class SesMessenger:
    """Production email via Amazon SES (eu-west-2). Never logs addresses, codes or links."""

    def __init__(self, sender: str, client=None) -> None:
        if client is None:
            import boto3
            client = boto3.client("sesv2", region_name="eu-west-2")
        self.sender, self.ses = sender, client

    def _send(self, address: str, subject: str, text: str) -> None:
        self.ses.send_email(FromEmailAddress=self.sender, Destination={"ToAddresses": [address]},
                            Content={"Simple": {"Subject": {"Data": subject},
                                                "Body": {"Text": {"Data": text}}}})

    def send_code(self, conn, channel: str, destination_hash: str, code: str, address: str = "") -> None:
        self._send(address, "Your verification code", f"Your code is {code}. It expires in 10 minutes.")

    def send_link(self, conn, destination_hash: str, link: str, address: str = "") -> None:
        self._send(address, "Sign in to Vitalos Verify",
                   f"Open this link in the same browser to sign in. It expires in 15 minutes.\n\n{link}\n\n"
                   "If you did not ask for this, ignore this email.")


GENERIC_SENT = {"status": "sent_if_valid",
                "message": "If the address is valid, a code has been sent. It expires in 10 minutes."}
TOO_MANY = ApiError(429, "rate_limited", "Please wait before requesting another code.", {"Retry-After": "60"})


def normalise_destination(channel: str, destination: str) -> str:
    d = destination.strip()
    if channel == "email":
        if "@" not in d or len(d) > 254 or " " in d:
            raise ApiError(400, "invalid_destination", "Enter a valid email address.")
        return d.lower()
    digits = "".join(ch for ch in d if ch.isdigit() or ch == "+")
    if len(digits) < 8 or len(digits) > 16:
        raise ApiError(400, "invalid_destination", "Enter a valid phone number.")
    return digits


def send_contact_code(db: Database, ctx: ApplicantContext, pepper: bytes, messenger: DummyMessenger | None,
                      channel: str, destination: str) -> dict:
    if messenger is None:
        raise ApiError(503, "messaging_unavailable", "Codes cannot be sent right now. Contact the requesting "
                       "organisation for the alternative route.")
    if channel != "email":
        raise ApiError(422, "channel_unsupported", "Phone verification is not enabled (no messaging supplier).")
    dest = normalise_destination(channel, destination)
    dest_hash = crypto.keyed_hash(pepper, "destination", ctx.tenant_id, channel, dest)
    with db.tenant_tx(ctx.tenant_id) as conn:
        s = get_session(conn, ctx.tenant_id, ctx.session_id, for_update=True)  # serialises concurrent sends
        if s["state"] not in ACTIVE_FOR_CAPTURE:
            raise conflict("session_not_active", "This verification cannot accept new evidence.")
        stats = conn.execute(
            "SELECT count(*) FILTER (WHERE created_at > now() - interval '15 minutes') AS recent, count(*) AS total, "
            "coalesce(max(created_at) > now() - make_interval(secs => %s), false) AS cooling "
            "FROM contact_challenges WHERE tenant_id = %s AND session_id = %s",
            (SEND_COOLDOWN_SECONDS, ctx.tenant_id, ctx.session_id)).fetchone()
        if stats["cooling"] or stats["recent"] >= SESSION_SENDS_PER_15_MIN or stats["total"] >= SESSION_SENDS_TOTAL:
            raise TOO_MANY
        # Per-destination (tenant-wide) limit. Also serialise per tenant for the spend cap below.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('vv_msg:' || %s))", (ctx.tenant_id,))
        per_dest = conn.execute("SELECT count(*) AS n FROM contact_challenges WHERE tenant_id = %s AND "
                                "destination_hash = %s AND created_at > now() - interval '1 day'",
                                (ctx.tenant_id, dest_hash)).fetchone()["n"]
        if per_dest >= DESTINATION_SENDS_PER_DAY:
            return GENERIC_SENT  # do not reveal destination-level throttling; nothing sent
        # Spend cap independent of rate limits.
        cap = conn.execute("SELECT daily_message_cap FROM tenants WHERE id = %s", (ctx.tenant_id,)).fetchone()
        sent_today = conn.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s AND charge_type = "
                                  "'message' AND created_at >= date_trunc('day', now())", (ctx.tenant_id,)).fetchone()
        if sent_today["n"] >= cap["daily_message_cap"]:
            raise ApiError(503, "messaging_paused", "Codes cannot be sent right now. Contact the requesting "
                           "organisation for the alternative route.")
        code = f"{secrets.randbelow(10**6):06d}"
        challenge_id = new_id("otp")
        conn.execute(
            "INSERT INTO contact_challenges (tenant_id, id, session_id, channel, destination_hash, code_hash, "
            "expires_at) VALUES (%s,%s,%s,%s,%s,%s, now() + make_interval(secs => %s))",
            (ctx.tenant_id, challenge_id, ctx.session_id, channel, dest_hash,
             crypto.keyed_hash(pepper, "otp", challenge_id, code), OTP_TTL_SECONDS))
        conn.execute("INSERT INTO usage_events (tenant_id, id, session_id, ledger_key, charge_type, amount_minor) "
                     "VALUES (%s,%s,%s,%s,'message',%s)",
                     (ctx.tenant_id, new_id("use"), ctx.session_id, f"msg:{challenge_id}", MESSAGE_COST_MINOR))
        messenger.send_code(conn, channel, dest_hash, code, dest)
    return GENERIC_SENT


def verify_contact_code(db: Database, ctx: ApplicantContext, pepper: bytes, code: str) -> dict:
    bad = ApiError(400, "code_invalid", "That code is invalid or has expired.")
    if not code or not code.isdigit() or len(code) != 6:
        raise bad
    with db.tenant_tx(ctx.tenant_id) as conn:
        s = get_session(conn, ctx.tenant_id, ctx.session_id, for_update=True)
        if s["state"] not in ACTIVE_FOR_CAPTURE:
            raise conflict("session_not_active", "This verification cannot accept new evidence.")
        ch = conn.execute(
            "SELECT *, expires_at > now() AS live FROM contact_challenges WHERE tenant_id = %s AND session_id = %s "
            "ORDER BY created_at DESC LIMIT 1 FOR UPDATE", (ctx.tenant_id, ctx.session_id)).fetchone()
        if ch is None or ch["consumed_at"] is not None or not ch["live"] or ch["failed_attempts"] >= OTP_MAX_FAILED:
            raise bad
        if not crypto.constant_time_equal(ch["code_hash"], crypto.keyed_hash(pepper, "otp", ch["id"], code)):
            conn.execute("UPDATE contact_challenges SET failed_attempts = failed_attempts + 1 WHERE tenant_id = %s "
                         "AND id = %s", (ctx.tenant_id, ch["id"]))
            # commit the failure count even though we return an error
            return {"_error": bad}
        conn.execute("UPDATE contact_challenges SET consumed_at = now() WHERE tenant_id = %s AND id = %s",
                     (ctx.tenant_id, ch["id"]))
        # Contact control is a low-assurance attribute, recorded separately from identity checks.
        conn.execute(
            "INSERT INTO checks (tenant_id, id, session_id, attempt_id, type, result, reasons, provider, "
            "provider_version, observation_id) VALUES (%s,%s,%s,NULL,%s,'pass',%s,'vitalos_contact','contact-1',%s) "
            "ON CONFLICT DO NOTHING",
            (ctx.tenant_id, new_id("chk"), ctx.session_id, ch["channel"], ["contact.control_confirmed"], ch["id"]))
    return {"status": "verified", "channel": ch["channel"],
            "note": "Confirms control of this contact address only; it is not proof of identity."}


# ------------------------------------------------------------------ device handoff (M03-T02)
HANDOFF_TTL_SECONDS = 600
MAX_ACTIVE_HANDOFFS = 3


def create_handoff(conn, ctx: ApplicantContext) -> dict:
    s = get_session(conn, ctx.tenant_id, ctx.session_id, for_update=True)
    if s["state"] not in ACTIVE_FOR_CAPTURE:
        raise conflict("session_not_active", "This verification cannot continue on another device.")
    live = conn.execute("SELECT count(*) AS n FROM applicant_handoffs WHERE tenant_id = %s AND session_id = %s "
                        "AND used_at IS NULL AND expires_at > now()", (ctx.tenant_id, ctx.session_id)).fetchone()["n"]
    if live >= MAX_ACTIVE_HANDOFFS:
        raise TOO_MANY
    token = "h_" + crypto.random_token(24)
    conn.execute("INSERT INTO applicant_handoffs (tenant_id, id, session_id, token_hash, expires_at) "
                 "VALUES (%s,%s,%s,%s, now() + make_interval(secs => %s))",
                 (ctx.tenant_id, new_id("hof"), ctx.session_id, crypto.token_hash(token), HANDOFF_TTL_SECONDS))
    audit(conn, ctx.tenant_id, "applicant", ctx.session_id, "handoff.created", "session", ctx.session_id)
    return {"handoff_token": token, "expires_in": HANDOFF_TTL_SECONDS}


def exchange_handoff(db: Database, token: str, ttl_seconds: int) -> tuple[str, ApplicantContext]:
    if not token or not token.startswith("h_") or len(token) > 200:
        raise LINK_INVALID
    with db.system_tx() as conn:
        hit = conn.execute("SELECT * FROM vv_lookup_handoff(%s)", (crypto.token_hash(token),)).fetchone()
    if hit is None:
        raise LINK_INVALID
    with db.tenant_tx(hit["tenant_id"]) as conn:
        s = get_session(conn, hit["tenant_id"], hit["session_id"], for_update=True)
        used = conn.execute(
            "UPDATE applicant_handoffs SET used_at = now() WHERE tenant_id = %s AND id = %s AND used_at IS NULL "
            "AND expires_at > now() RETURNING id", (hit["tenant_id"], hit["id"])).fetchone()
        live = conn.execute("SELECT %s::timestamptz > now() AS ok", (s["expires_at"],)).fetchone()["ok"]
        if used is None or not live or s["state"] not in ACTIVE_FOR_CAPTURE:
            raise LINK_INVALID
        cookie = crypto.random_token(32)
        conn.execute(
            "INSERT INTO applicant_sessions (tenant_id, id, session_id, token_hash, expires_at) "
            "VALUES (%s,%s,%s,%s, least(now() + make_interval(secs => %s), %s))",
            (s["tenant_id"], new_id("apps"), s["id"], crypto.token_hash(cookie), ttl_seconds, s["expires_at"]))
        audit(conn, s["tenant_id"], "applicant", s["id"], "handoff.exchanged", "session", s["id"])
    return cookie, ApplicantContext(hit["tenant_id"], hit["session_id"])
