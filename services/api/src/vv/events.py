"""Provider callback ingestion and authoritative processing (VV-005, VV-006).

Callbacks are authenticated on the raw body, stored once per provider event ID and
acknowledged. They carry no result: the worker fetches the authoritative observation
from the provider, binds it to the attempt and evaluates the session's frozen policy.
"""

from __future__ import annotations

from vv import crypto
from vv.db import Database
from vv.errors import ApiError
from vv.ids import new_id
from vv.log import log
from vv.providers.base import EventRejected, ProviderAdapter, ProviderUnavailable
from vv.service import TERMINAL, evaluate_and_record, get_session, transition

MAX_FETCH_ATTEMPTS = 5
MAX_PENDING_POLLS = 120  # ~1 hour at 30 s; afterwards the event fails and session expiry applies
CLAIM_LEASE_SECONDS = 300
RETRY_BACKOFF_SECONDS = [5, 30, 120, 600, 1800]


def ingest_callback(db: Database, provider: ProviderAdapter, data_key: bytes, raw_body: bytes,
                    headers: dict[str, str]) -> dict:
    try:
        event = provider.authenticate_event(raw_body, headers)
    except EventRejected:
        log("provider_callback.rejected", provider=provider.name)
        raise ApiError(401, "callback_rejected", "Callback could not be authenticated.") from None
    with db.system_tx() as conn:
        inserted = conn.execute(
            "INSERT INTO provider_events (provider, event_id, provider_reference, raw_body) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING event_id",
            (provider.name, event.event_id, event.provider_reference,
             crypto.seal(data_key, raw_body, f"{provider.name}|{event.event_id}".encode()))).fetchone()
    log("provider_callback.accepted", provider=provider.name, event_id=event.event_id,
        state="new" if inserted else "duplicate")
    return {"received": True}


def _finish(db: Database, provider: str, event_id: str, state: str, note: str, tenant_id: str | None = None,
            session_id: str | None = None) -> str:
    with db.system_tx() as conn:
        conn.execute("UPDATE provider_events SET processing_state = %s, outcome_note = %s, tenant_id = "
                     "coalesce(%s, tenant_id), session_id = coalesce(%s, session_id) WHERE provider = %s AND "
                     "event_id = %s", (state, note, tenant_id, session_id, provider, event_id))
    log("provider_event.finished", provider=provider, event_id=event_id, state=state, session_id=session_id)
    return state


def process_event(db: Database, providers: dict[str, ProviderAdapter], provider_name: str, event_id: str,
                  store=None) -> str:
    # Atomic claim with a lease: only one worker processes an event; a crashed worker's claim expires.
    with db.system_tx() as conn:
        ev = conn.execute(
            "UPDATE provider_events SET processing_state = 'processing', attempts = attempts + 1, "
            "next_attempt_at = now() + make_interval(secs => %s) WHERE provider = %s AND event_id = %s "
            "AND processing_state IN ('pending','retry','processing') AND next_attempt_at <= now() RETURNING *",
            (CLAIM_LEASE_SECONDS, provider_name, event_id)).fetchone()
        if ev is None:
            return "skipped"
        bound = conn.execute("SELECT * FROM vv_resolve_provider_reference(%s, %s)",
                             (provider_name, ev["provider_reference"])).fetchone()
    ev = dict(ev, attempts=ev["attempts"] - 1)  # attempts before this claim, as used below
    if bound is None:
        return _finish(db, provider_name, event_id, "quarantined", "unknown provider reference")
    tenant_id, session_id, attempt_id = bound["tenant_id"], bound["session_id"], bound["attempt_id"]
    provider = providers[provider_name]
    with db.tenant_tx(tenant_id) as conn:
        blocked = conn.execute("SELECT evidence_access_blocked_at IS NOT NULL AS b FROM sessions WHERE tenant_id = %s "
                               "AND id = %s", (tenant_id, session_id)).fetchone()["b"]
    if blocked:  # subject deletion requested: do not fetch or store further evidence
        return _finish(db, provider_name, event_id, "ignored", "subject deletion requested", tenant_id, session_id)

    try:
        observation = provider.fetch_result(ev["provider_reference"], correlation_id=event_id)
    except ProviderUnavailable:
        attempts = ev["attempts"] + 1
        if attempts >= MAX_FETCH_ATTEMPTS:
            with db.tenant_tx(tenant_id) as conn:
                s = get_session(conn, tenant_id, session_id, for_update=True)
                if s["state"] in ("in_progress", "processing"):
                    if s["state"] == "in_progress":
                        s = transition(conn, s, "processing")
                    transition(conn, s, "error", ["provider.unavailable"], emit_event=False)
            return _finish(db, provider_name, event_id, "failed", "provider unavailable after retries",
                           tenant_id, session_id)
        _retry(db, provider_name, event_id, RETRY_BACKOFF_SECONDS[min(attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)],
               tenant_id, session_id)
        return "retry"

    if observation.provider_reference != ev["provider_reference"]:
        return _finish(db, provider_name, event_id, "quarantined", "observation reference mismatch",
                       tenant_id, session_id)
    if observation.status != "completed":
        if ev["attempts"] + 1 >= MAX_PENDING_POLLS:
            return _finish(db, provider_name, event_id, "failed", "provider result still pending; gave up",
                           tenant_id, session_id)
        _retry(db, provider_name, event_id, 30, tenant_id, session_id)
        return "retry"

    with db.tenant_tx(tenant_id) as conn:
        s = get_session(conn, tenant_id, session_id, for_update=True)
        attempt = conn.execute("SELECT * FROM attempts WHERE tenant_id = %s AND id = %s FOR UPDATE",
                               (tenant_id, attempt_id)).fetchone()
        latest_seq = conn.execute("SELECT max(sequence) AS m FROM attempts WHERE tenant_id = %s AND session_id = %s",
                                  (tenant_id, session_id)).fetchone()["m"]
        if s["state"] in TERMINAL or s["state"] in ("review_required", "action_required"):
            note = "late event for decided session; decision unchanged"
            conn_state = "ignored"
        elif attempt["sequence"] != latest_seq or attempt["state"] == "superseded":
            note, conn_state = "event for superseded attempt", "ignored"
        else:
            conn_state = "processed"
            note = "evaluated"
            for c in observation.checks:
                conn.execute(
                    "INSERT INTO checks (tenant_id, id, session_id, attempt_id, type, result, reasons, provider, "
                    "provider_version, model_version, score, score_type, observation_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (tenant_id, f"chk_{observation.observation_id}_{c.type}"[:120], session_id, attempt_id, c.type,
                     c.result, list(c.reasons), provider_name, observation.provider_version, c.model_version,
                     c.score, c.score_type, observation.observation_id))
            conn.execute("UPDATE attempts SET state = 'completed' WHERE tenant_id = %s AND id = %s",
                         (tenant_id, attempt_id))
            if store is not None:
                from vv import evidence
                for kind, data, ctype in observation.evidence:
                    evidence.store(conn, store, tenant_id=tenant_id, session_id=session_id, attempt_id=attempt_id,
                                   kind=kind, data=data, content_type=ctype)
            if s["state"] == "in_progress":
                s = transition(conn, s, "processing")
            s, result = evaluate_and_record(conn, s)
            log("session.evaluated", tenant_id=tenant_id, session_id=session_id, state=s["state"],
                outcome=result.outcome, reason_codes=result.reason_codes)
    return _finish(db, provider_name, event_id, conn_state, note, tenant_id, session_id)


def _retry(db: Database, provider: str, event_id: str, delay: float, tenant_id: str | None = None,
           session_id: str | None = None) -> None:
    with db.system_tx() as conn:
        conn.execute("UPDATE provider_events SET processing_state = 'retry', next_attempt_at = now() + "
                     "make_interval(secs => %s), tenant_id = coalesce(%s, tenant_id), session_id = "
                     "coalesce(%s, session_id) WHERE provider = %s AND event_id = %s",
                     (delay, tenant_id, session_id, provider, event_id))
    log("provider_event.retry", provider=provider, event_id=event_id)


def process_due_events(db: Database, providers: dict[str, ProviderAdapter], limit: int = 50, store=None) -> int:
    with db.system_tx() as conn:
        due = list(conn.execute("SELECT provider, event_id, attempts FROM provider_events WHERE processing_state IN "
                                "('pending','retry','processing') AND next_attempt_at <= now() "
                                "ORDER BY next_attempt_at LIMIT %s", (limit,)))
    for row in due:
        if row["provider"] not in providers:
            continue
        try:
            process_event(db, providers, row["provider"], row["event_id"], store)
        except Exception as exc:  # noqa: BLE001 - one bad event must not stall the queue (D1)
            log("provider_event.failed_unexpectedly", provider=row["provider"], event_id=row["event_id"],
                error_type=type(exc).__name__)
            if row["attempts"] + 1 >= MAX_FETCH_ATTEMPTS * 4:
                _finish(db, row["provider"], row["event_id"], "failed", f"unexpected {type(exc).__name__}")
            else:
                _retry(db, row["provider"], row["event_id"], RETRY_BACKOFF_SECONDS[min(row["attempts"], 4)])
    return len(due)


def expire_sessions(worker_db: Database, limit: int = 100) -> int:
    """Expire unused/abandoned sessions and release their usage reservation (not billable).

    Requires the worker role: its worker_scan policy exposes only expired, still-open sessions.
    """

    with worker_db.system_tx() as conn:
        rows = list(conn.execute("SELECT tenant_id, id FROM sessions WHERE state IN ('created','in_progress',"
                                 "'action_required','processing','error') AND expires_at < now() LIMIT %s", (limit,)))
    for r in rows:
        with worker_db.tenant_tx(r["tenant_id"]) as conn:
            s = get_session(conn, r["tenant_id"], r["id"], for_update=True)
            if s["state"] not in ("created", "in_progress", "action_required", "processing", "error"):
                continue
            transition(conn, s, "expired", ["session.expired"])
            res = conn.execute("SELECT amount_minor FROM usage_events WHERE tenant_id = %s AND ledger_key = %s",
                               (r["tenant_id"], f"reserve:{r['id']}")).fetchone()
            if res:
                conn.execute("INSERT INTO usage_events (tenant_id, id, session_id, ledger_key, charge_type, "
                             "amount_minor) VALUES (%s,%s,%s,%s,'reservation_release',%s) ON CONFLICT DO NOTHING",
                             (r["tenant_id"], new_id("use"), r["id"], f"release:{r['id']}", -res["amount_minor"]))
    return len(rows)
