"""Verification domain services: sessions, idempotency, attempts, decisions, outbox and audit.

All functions taking `conn` expect a tenant-bound transaction (Database.tenant_tx).
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any

from vv import crypto
from vv.domain.coverage import CoverageRegistry, UnsupportedCapability
from vv.domain.policy import ENGINE_VERSION, CheckView, Evaluation, PolicyInvalid, evaluate, validate_definition
from vv.errors import ApiError, conflict, not_found
from vv.ids import new_id

TERMINAL = {"approved", "declined", "expired", "cancelled"}
TRANSITIONS: dict[str, set[str]] = {
    "created": {"in_progress", "expired", "cancelled"},
    "in_progress": {"processing", "expired", "cancelled"},
    "processing": {"approved", "declined", "review_required", "action_required", "error"},
    "error": {"processing"},
    "action_required": {"in_progress", "expired", "cancelled"},
    "review_required": {"approved", "declined", "action_required"},
}
STATE_EVENTS = {
    "processing": "verification.processing",
    "action_required": "verification.action_required",
    "review_required": "verification.review_required",
    "approved": "verification.completed",
    "declined": "verification.completed",
    "expired": "verification.expired",
    "cancelled": "verification.cancelled",
}
USE_CASE = "workforce_onboarding"


# ------------------------------------------------------------------ audit / outbox
def audit(conn, tenant_id: str, actor_type: str, actor_id: str, action: str, object_type: str, object_id: str,
          reason: str | None = None, request_id: str | None = None) -> None:
    conn.execute(
        "INSERT INTO audit_events (tenant_id, id, actor_type, actor_id, action, object_type, object_id, reason, "
        "request_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, new_id("aud"), actor_type, actor_id, action, object_type, object_id, reason, request_id))


def emit(conn, tenant_id: str, event_type: str, resource_id: str, resource_version: int, data: dict) -> str:
    event_id = new_id("evt")
    conn.execute(
        "INSERT INTO outbox (tenant_id, id, event_type, resource_id, resource_version, payload) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (tenant_id, event_id, event_type, resource_id, resource_version, json.dumps(data)))
    return event_id


# ------------------------------------------------------------------ idempotency (VV-003)
def run_idempotent(conn, data_key: bytes, tenant_id: str, operation: str, key: str | None, body: Any, fn):
    """Executes fn(conn) -> (status, body) once per (tenant, operation, key).

    Concurrent identical requests serialise on the unique key: the second waits for the
    first transaction, then replays its stored response. A different body returns 409.
    Errors raised by fn roll back the whole transaction, so the key stays unused.
    """
    if not key or not (8 <= len(key) <= 128):
        raise ApiError(400, "idempotency_key_required", "An Idempotency-Key header of 8-128 characters is required.")
    digest = crypto.canonical_digest(body)
    aad = f"{tenant_id}|{operation}|{key}".encode()
    inserted = conn.execute(
        "INSERT INTO idempotency_keys (tenant_id, operation, key, request_digest) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT DO NOTHING RETURNING key", (tenant_id, operation, key, digest)).fetchone()
    if inserted is None:
        row = conn.execute("SELECT request_digest, response_status, response_sealed FROM idempotency_keys "
                           "WHERE tenant_id = %s AND operation = %s AND key = %s",
                           (tenant_id, operation, key)).fetchone()
        if row["request_digest"] != digest:
            raise conflict("idempotency_key_reused", "This Idempotency-Key was used with a different request.")
        if row["response_status"] is None:
            raise conflict("idempotency_in_progress", "The original request is still being processed.")
        return row["response_status"], json.loads(crypto.unseal(data_key, bytes(row["response_sealed"]), aad))
    status, response = fn(conn)
    conn.execute("UPDATE idempotency_keys SET response_status = %s, response_sealed = %s "
                 "WHERE tenant_id = %s AND operation = %s AND key = %s",
                 (status, crypto.seal(data_key, json.dumps(response).encode(), aad), tenant_id, operation, key))
    return status, response


# ------------------------------------------------------------------ policies (VV-007)
FIXTURES = [
    # (name, checks, expected outcome) — security-floor replay run at publication
    ("all_pass", [("government_id", "pass", ()), ("face_match", "pass", ()), ("liveness", "pass", ())], "approved"),
    ("liveness_missing", [("government_id", "pass", ()), ("face_match", "pass", ())], "review_required"),
    ("liveness_inconclusive", [("government_id", "pass", ()), ("face_match", "pass", ()),
                               ("liveness", "inconclusive", ("liveness.inconclusive",))], "review_required"),
    ("suspected_attack", [("government_id", "pass", ()), ("face_match", "pass", ()),
                          ("liveness", "fail", ("liveness.suspected_attack",))], "review_required"),
    ("provider_error", [("government_id", "error", ("provider.unavailable",)), ("face_match", "pass", ()),
                        ("liveness", "pass", ())], None),
]


def create_policy_draft(conn, tenant_id: str, definition: dict) -> dict:
    try:
        validate_definition(definition)
    except PolicyInvalid as exc:
        raise ApiError(400, "policy_invalid", str(exc)) from None
    row_id = new_id("pol")
    try:
        conn.execute(
            "INSERT INTO policies (tenant_id, id, key, version, status, definition, definition_digest) "
            "VALUES (%s,%s,%s,%s,'draft',%s,%s)",
            (tenant_id, row_id, definition["id"], definition["version"], json.dumps(definition),
             crypto.canonical_digest(definition)))
    except Exception as exc:  # unique violation
        if getattr(exc, "sqlstate", None) == "23505":
            raise conflict("policy_version_exists", "This policy version already exists.") from None
        raise
    return {"id": row_id, "key": definition["id"], "version": definition["version"], "status": "draft"}


def publish_policy(conn, tenant_id: str, key: str, version: int, coverage: CoverageRegistry,
                   price_minor: int) -> dict:
    row = conn.execute("SELECT * FROM policies WHERE tenant_id = %s AND key = %s AND version = %s FOR UPDATE",
                       (tenant_id, key, version)).fetchone()
    if row is None:
        raise not_found()
    if row["status"] != "draft":
        raise conflict("policy_not_draft", "Only draft policies can be published.")
    definition = row["definition"]
    validate_definition(definition)
    report: dict[str, Any] = {"engine": ENGINE_VERSION, "fixtures": []}
    if definition["coverage_version"] != coverage.version:
        raise ApiError(422, "policy.unsupported_region", "Policy coverage version is not active.")
    enabled = [e.id for e in coverage.entries if e.enabled]
    report["supported_matrix"] = enabled
    for name, checks, expected in FIXTURES:
        views = [CheckView(f"fx_{i}", t, r, reasons) for i, (t, r, reasons) in enumerate(checks)]
        if "email" in definition["required_checks"]:
            views.append(CheckView("fx_email", "email", "pass"))
        if "phone" in definition["required_checks"]:
            views.append(CheckView("fx_phone", "phone", "pass"))
        result = evaluate(definition, views, quality_retries_used=0)
        ok = result.outcome == expected
        report["fixtures"].append({"name": name, "expected": expected, "actual": result.outcome, "ok": ok})
        if not ok:
            raise ApiError(422, "policy_fixture_failed", f"Fixture replay failed: {name}.")
    report["cost_preview"] = {"per_completed_verification_minor": price_minor, "currency": "GBP",
                              "status": "hypothesis_not_approved_price"}
    conn.execute("UPDATE policies SET status = 'published', published_at = now(), validation_report = %s "
                 "WHERE tenant_id = %s AND id = %s", (json.dumps(report), tenant_id, row["id"]))
    return {"id": row["id"], "key": key, "version": version, "status": "published", "validation_report": report}


# ------------------------------------------------------------------ sessions (VV-003, VV-023)
def _cursor_encode(created_at: datetime, session_id: str) -> str:
    return base64.urlsafe_b64encode(json.dumps([created_at.isoformat(), session_id]).encode()).decode().rstrip("=")


def _cursor_decode(cursor: str) -> tuple[str, str]:
    try:
        created, sid = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        datetime.fromisoformat(created)
        return created, str(sid)
    except Exception:  # noqa: BLE001
        raise ApiError(400, "invalid_cursor", "Cursor is invalid.") from None


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def latest_checks(conn, tenant_id: str, session_id: str) -> list[dict]:
    """Checks considered for the current decision: latest attempt's provider checks plus contact checks."""
    latest = conn.execute("SELECT id FROM attempts WHERE tenant_id = %s AND session_id = %s "
                          "ORDER BY sequence DESC LIMIT 1", (tenant_id, session_id)).fetchone()
    return list(conn.execute(
        "SELECT * FROM checks WHERE tenant_id = %s AND session_id = %s AND (attempt_id IS NULL OR attempt_id = %s) "
        "ORDER BY created_at, id", (tenant_id, session_id, latest["id"] if latest else None)))


def session_view(conn, session: dict) -> dict:
    policy = conn.execute("SELECT definition FROM policies WHERE tenant_id = %s AND id = %s",
                          (session["tenant_id"], session["policy_row_id"])).fetchone()
    required = policy["definition"]["required_checks"]
    by_type: dict[str, dict] = {}
    for c in latest_checks(conn, session["tenant_id"], session["id"]):
        by_type[c["type"]] = c
    checks = []
    for t in list(required) + [t for t in by_type if t not in required]:
        c = by_type.get(t)
        if c is None:  # required check stays visible even when evidence is missing (AT-05)
            checks.append({"id": f"chk_pending_{t}", "type": t, "result": "not_run", "reasons": ["evidence.missing"]})
        else:
            item = {"id": c["id"], "type": c["type"], "result": c["result"], "reasons": list(c["reasons"])}
            if c["provider_version"]:
                item["provider_version"] = c["provider_version"]
            checks.append(item)
    return {
        "id": session["id"], "external_reference": session["external_reference"], "state": session["state"],
        "revision": session["version"], "policy_id": session["policy_key"],
        "policy_version": session["policy_version"], "created_at": _iso(session["created_at"]),
        "expires_at": _iso(session["expires_at"]), "checks": checks,
    }


def create_session(conn, *, tenant_id: str, actor_id: str, body: dict, coverage: CoverageRegistry, environment: str,
                   hosted_base_url: str, hosted_ttl: int, price_minor: int, request_id: str) -> tuple[int, dict]:
    tenant = conn.execute("SELECT * FROM tenants WHERE id = %s", (tenant_id,)).fetchone()
    if tenant["status"] != "active":
        raise ApiError(403, "billing_hold" if tenant["status"] == "billing_hold" else "tenant_inactive",
                       "New verifications are paused for this organisation.")
    policy = conn.execute("SELECT * FROM policies WHERE tenant_id = %s AND key = %s AND version = %s "
                          "AND status = 'published'", (tenant_id, body["policy_id"], body["policy_version"])).fetchone()
    if policy is None:
        raise ApiError(422, "policy.not_published", "The requested policy version is not published.")
    definition = policy["definition"]
    try:
        entry = coverage.resolve(country=body["country"], document_type=body["document_type"],
                                 required_checks=definition["required_checks"], use_case=USE_CASE,
                                 tenant_regions=list(tenant["region_policy"]), environment=environment,
                                 coverage_version=definition["coverage_version"])
    except UnsupportedCapability as exc:
        message = str(exc) + (f" Alternative: {exc.alternative}" if exc.alternative else "")
        raise ApiError(422, "policy.unsupported_region", message) from None

    # Spend control: serialise reservations per tenant so concurrent requests cannot exceed the cap.
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('vv_reserve:' || %s))", (tenant_id,))
    used = conn.execute(
        "SELECT coalesce(sum(CASE charge_type WHEN 'reservation' THEN 1 WHEN 'reservation_release' THEN -1 "
        "ELSE 0 END), 0) AS n FROM usage_events WHERE tenant_id = %s AND created_at >= date_trunc('month', now())",
        (tenant_id,)).fetchone()["n"]
    if used >= tenant["monthly_session_cap"]:
        raise ApiError(429, "quota.monthly_cap_reached", "The monthly verification cap for this organisation has been "
                       "reached. Existing verifications are unaffected.")

    subject = conn.execute(
        "INSERT INTO subjects (tenant_id, id, external_reference) VALUES (%s,%s,%s) "
        "ON CONFLICT (tenant_id, external_reference) DO UPDATE SET external_reference = EXCLUDED.external_reference "
        "RETURNING id", (tenant_id, new_id("sub"), body["external_reference"])).fetchone()
    session_id = new_id("ver")
    hosted_token = crypto.random_token(32)
    session = conn.execute(
        "INSERT INTO sessions (tenant_id, id, subject_id, policy_row_id, policy_key, policy_version, "
        "external_reference, country, document_type, coverage_version, coverage_entry_id, provider, state, "
        "hosted_token_hash, hosted_token_expires_at, expires_at) VALUES "
        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'created',%s, now() + make_interval(secs => %s), "
        "now() + make_interval(secs => %s)) RETURNING *",
        (tenant_id, session_id, subject["id"], policy["id"], policy["key"], policy["version"],
         body["external_reference"], body["country"], body["document_type"], coverage.version, entry.id,
         entry.provider, crypto.token_hash(hosted_token), hosted_ttl, hosted_ttl)).fetchone()
    conn.execute("INSERT INTO usage_events (tenant_id, id, session_id, ledger_key, charge_type, amount_minor) "
                 "VALUES (%s,%s,%s,%s,'reservation',%s)",
                 (tenant_id, new_id("use"), session_id, f"reserve:{session_id}", price_minor))
    emit(conn, tenant_id, "verification.created", session_id, 1, {"state": "created", "reason_codes": []})
    audit(conn, tenant_id, "api_key", actor_id, "verification.create", "session", session_id, request_id=request_id)
    return 201, {"session": session_view(conn, session),
                 "hosted_url": f"{hosted_base_url.rstrip('/')}/v/{hosted_token}"}


def get_session(conn, tenant_id: str, session_id: str, *, for_update: bool = False) -> dict:
    sql = "SELECT * FROM sessions WHERE tenant_id = %s AND id = %s"
    if for_update:
        sql += " FOR UPDATE"
    row = conn.execute(sql, (tenant_id, session_id)).fetchone()
    if row is None:
        raise not_found()
    return row


def list_sessions(conn, tenant_id: str, *, cursor: str | None, limit: int, state: str | None) -> dict:
    if not 1 <= limit <= 100:
        raise ApiError(400, "invalid_limit", "limit must be between 1 and 100.")
    params: list[Any] = [tenant_id]
    sql = "SELECT * FROM sessions WHERE tenant_id = %s"
    if state:
        sql += " AND state = %s"
        params.append(state)
    if cursor:
        created, sid = _cursor_decode(cursor)
        sql += " AND (created_at, id) < (%s::timestamptz, %s)"
        params += [created, sid]
    sql += " ORDER BY created_at DESC, id DESC LIMIT %s"
    params.append(limit + 1)
    rows = list(conn.execute(sql, params))
    page = rows[:limit]
    next_cursor = _cursor_encode(page[-1]["created_at"], page[-1]["id"]) if len(rows) > limit else None
    return {"items": [session_view(conn, r) for r in page], "next_cursor": next_cursor}


def transition(conn, session: dict, to_state: str, reason_codes: list[str] | None = None, *,
               emit_event: bool = True, extra_sets: str = "") -> dict:
    """Optimistic-concurrency state change; returns the updated session row."""
    from_state = session["state"]
    if to_state not in TRANSITIONS.get(from_state, set()):
        raise conflict("invalid_transition", f"Cannot move from {from_state} to {to_state}.")
    row = conn.execute(
        f"UPDATE sessions SET state = %s, version = version + 1, updated_at = now(){extra_sets} "  # noqa: S608
        "WHERE tenant_id = %s AND id = %s AND version = %s RETURNING *",
        (to_state, session["tenant_id"], session["id"], session["version"])).fetchone()
    if row is None:
        raise conflict("revision.stale", "The verification changed; reload and retry.")
    if emit_event and to_state in STATE_EVENTS:
        emit(conn, row["tenant_id"], STATE_EVENTS[to_state], row["id"], row["version"],
             {"state": to_state, "reason_codes": sorted(set(reason_codes or []))})
    return row


# ------------------------------------------------------------------ evaluation and decisions (VV-005/007/008)
def _next_revision(conn, tenant_id: str, session_id: str) -> int:
    return conn.execute("SELECT coalesce(max(revision), 0) + 1 AS r FROM decisions WHERE tenant_id = %s "
                        "AND session_id = %s", (tenant_id, session_id)).fetchone()["r"]


def evaluate_and_record(conn, session: dict) -> tuple[dict, Evaluation]:
    """Evaluate the session's frozen policy version and persist outcome, trace and event atomically."""
    policy = conn.execute("SELECT * FROM policies WHERE tenant_id = %s AND id = %s",
                          (session["tenant_id"], session["policy_row_id"])).fetchone()
    checks = latest_checks(conn, session["tenant_id"], session["id"])
    views = [CheckView(c["id"], c["type"], c["result"], tuple(c["reasons"])) for c in checks]
    result = evaluate(policy["definition"], views, quality_retries_used=session["quality_retries_used"])
    if session["state"] != "processing":
        session = transition(conn, session, "processing")
    if result.outcome is None:
        return transition(conn, session, "error", result.reason_codes, emit_event=False), result
    revision = _next_revision(conn, session["tenant_id"], session["id"])
    conn.execute(
        "INSERT INTO decisions (tenant_id, id, session_id, revision, outcome, actor_type, actor_id, method, "
        "reason_codes, policy_row_id, policy_key, policy_version, evidence_check_ids, trace, supersedes_revision) "
        "VALUES (%s,%s,%s,%s,%s,'policy_engine',%s,'automated',%s,%s,%s,%s,%s,%s,%s)",
        (session["tenant_id"], new_id("dec"), session["id"], revision, result.outcome, ENGINE_VERSION,
         result.reason_codes, policy["id"], policy["key"], policy["version"], result.evidence_check_ids,
         json.dumps({"engine": ENGINE_VERSION, "policy_digest": policy["definition_digest"], "steps": result.trace}),
         revision - 1 if revision > 1 else None))
    session = transition(conn, session, result.session_state, result.reason_codes)
    return session, result


def record_review_decision(conn, *, tenant_id: str, session_id: str, actor_id: str, body: dict,
                           request_id: str) -> tuple[int, dict]:
    session = get_session(conn, tenant_id, session_id, for_update=True)
    if session["version"] != body["expected_revision"]:
        raise conflict("revision.stale", "The verification changed since you loaded it; reload and retry.")
    if session["state"] != "review_required":
        raise conflict("not_reviewable", "This verification is not awaiting review.")
    checks = latest_checks(conn, tenant_id, session_id)
    check_ids = {c["id"] for c in checks}
    if not set(body["evidence_ids"]) <= check_ids:
        raise ApiError(422, "evidence_unknown", "Evidence references must belong to this verification.")
    policy = conn.execute("SELECT * FROM policies WHERE tenant_id = %s AND id = %s",
                          (tenant_id, session["policy_row_id"])).fetchone()
    required = policy["definition"]["required_checks"]
    latest = {c["type"]: c for c in checks}
    failing = [t for t in required if t not in latest or latest[t]["result"] != "pass"]
    reason_codes: list[str] = []
    if body["outcome"] == "approved" and body["method"] == "evidence_review" and failing:
        # A reviewer cannot assert a pass contrary to recorded evidence (VV-008).
        raise ApiError(422, "review.alternative_method_required",
                       "Required checks did not pass. Record an alternative-method decision with its rationale.")
    if body["method"] == "alternative_method":
        reason_codes.append("review.alternative_method")
    revision = _next_revision(conn, tenant_id, session_id)
    conn.execute(
        "INSERT INTO decisions (tenant_id, id, session_id, revision, outcome, actor_type, actor_id, method, "
        "reason_codes, reason_text, policy_row_id, policy_key, policy_version, evidence_check_ids, trace, "
        "supersedes_revision) VALUES (%s,%s,%s,%s,%s,'reviewer',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, new_id("dec"), session_id, revision, body["outcome"], actor_id, body["method"], reason_codes,
         body["reason"], policy["id"], policy["key"], policy["version"], body["evidence_ids"],
         json.dumps({"review": {"failing_required_checks": failing, "expected_revision": body["expected_revision"]}}),
         revision - 1 if revision > 1 else None))
    session = transition(conn, session, body["outcome"], reason_codes)
    audit(conn, tenant_id, "api_key", actor_id, "decision.record", "session", session_id,
          reason=body["method"], request_id=request_id)
    return 200, session_view(conn, session)
