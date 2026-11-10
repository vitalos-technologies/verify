"""Subject deletion lifecycle (VV-009, 06_data_model §Lifecycle, AT-09).

requested -> (on_hold) -> in_progress -> primary_deleted -> awaiting_backup_expiry -> complete
                                                    \\-> error (supplier deletion failing; escalate)

- Access to the subject's evidence is blocked and open sessions are cancelled at request time.
- Primary redaction, supplier deletion (with receipts and asynchronous confirmation) and backup
  expiry are tracked separately. An HTTP 2xx from a supplier is not completion.
- A tombstone records what must be re-applied after any backup restore (replay_tombstones).
- Decisions, checks and audit rows hold no direct identifiers and stay as minimal audit.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from vv.db import Database
from vv.errors import ApiError, conflict, not_found
from vv.ids import new_id
from vv.log import log
from vv.providers.base import ProviderAdapter, ProviderUnavailable
from vv.service import audit, emit, transition

BACKUP_RETENTION_DAYS = 35  # 14_infrastructure proposal; must match the real backup policy
SUPPLIER_MAX_ATTEMPTS = 5
CANCELLABLE = {"created", "in_progress", "action_required"}


def _view(conn, job: dict) -> dict:
    pending = []
    if job["primary_state"] != "done":
        pending.append("primary")
    for t in conn.execute("SELECT provider, provider_reference, state FROM deletion_supplier_targets WHERE "
                          "tenant_id = %s AND deletion_id = %s ORDER BY provider, provider_reference",
                          (job["tenant_id"], job["id"])):
        if t["state"] != "confirmed":
            pending.append(f"supplier:{t['provider']}")
    if job["state"] != "complete":
        pending.append("backups")
    return {"id": job["id"], "state": job["state"], "pending_targets": sorted(set(pending))}


def _set_state(conn, job: dict, state: str, extra: str = "", params: tuple = ()) -> dict:
    row = conn.execute(
        f"UPDATE deletion_jobs SET state = %s, version = version + 1, updated_at = now(){extra} "  # noqa: S608
        "WHERE tenant_id = %s AND id = %s AND version = %s RETURNING *",
        (state, *params, job["tenant_id"], job["id"], job["version"])).fetchone()
    if row is None:
        raise conflict("revision.stale", "Deletion changed concurrently.")
    emit(conn, row["tenant_id"], "deletion.updated", row["id"], row["version"], {"state": state, "reason_codes": []})
    return row


def _active_hold(conn, tenant_id: str, subject_id: str) -> bool:
    return conn.execute("SELECT 1 FROM legal_holds WHERE tenant_id = %s AND subject_id = %s AND released_at IS NULL "
                        "AND expires_at > now()", (tenant_id, subject_id)).fetchone() is not None


def request_deletion(conn, *, tenant_id: str, actor_id: str, body: dict, request_id: str) -> tuple[int, dict]:
    ref = body["subject_id"]
    subject = conn.execute("SELECT * FROM subjects WHERE tenant_id = %s AND (id = %s OR external_reference = %s) "
                           "FOR UPDATE", (tenant_id, ref, ref)).fetchone()
    if subject is None:
        raise not_found()
    if conn.execute("SELECT 1 FROM deletion_jobs WHERE tenant_id = %s AND subject_id = %s AND state <> 'complete'",
                    (tenant_id, subject["id"])).fetchone():
        raise conflict("deletion_in_progress", "A deletion for this subject is already in progress.")
    job_id = new_id("del")
    sessions = list(conn.execute("SELECT * FROM sessions WHERE tenant_id = %s AND subject_id = %s FOR UPDATE",
                                 (tenant_id, subject["id"])))
    state = "on_hold" if _active_hold(conn, tenant_id, subject["id"]) else "requested"
    job = conn.execute(
        "INSERT INTO deletion_jobs (tenant_id, id, subject_id, reason, controller_authorisation_reference, state, "
        "requested_by) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
        (tenant_id, job_id, subject["id"], body["reason"], body["controller_authorisation_reference"], state,
         actor_id)).fetchone()
    conn.execute("INSERT INTO deletion_tombstones (tenant_id, subject_id, deletion_id, session_ids) "
                 "VALUES (%s,%s,%s,%s)", (tenant_id, subject["id"], job_id, [s["id"] for s in sessions]))
    # Deny new evidence access immediately, even while a legal hold delays erasure.
    conn.execute("UPDATE sessions SET evidence_access_blocked_at = coalesce(evidence_access_blocked_at, now()) "
                 "WHERE tenant_id = %s AND subject_id = %s", (tenant_id, subject["id"]))
    conn.execute("UPDATE applicant_sessions SET expires_at = least(expires_at, now()) WHERE tenant_id = %s AND "
                 "session_id = ANY(%s)", (tenant_id, [s["id"] for s in sessions]))
    for s in sessions:
        if s["state"] in CANCELLABLE:
            transition(conn, s, "cancelled", ["subject.deletion_requested"])
        for a in conn.execute("SELECT provider, provider_reference FROM attempts WHERE tenant_id = %s AND "
                              "session_id = %s AND provider_reference IS NOT NULL", (tenant_id, s["id"])):
            conn.execute("INSERT INTO deletion_supplier_targets (tenant_id, deletion_id, provider, provider_reference) "
                         "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                         (tenant_id, job_id, a["provider"], a["provider_reference"]))
    emit(conn, tenant_id, "deletion.updated", job_id, 1, {"state": state, "reason_codes": []})
    audit(conn, tenant_id, "api_key", actor_id, "deletion.request", "subject", subject["id"],
          reason=body["controller_authorisation_reference"], request_id=request_id)
    return 202, _view(conn, job)


def get_deletion(conn, tenant_id: str, deletion_id: str) -> dict:
    job = conn.execute("SELECT * FROM deletion_jobs WHERE tenant_id = %s AND id = %s",
                       (tenant_id, deletion_id)).fetchone()
    if job is None:
        raise not_found()
    return _view(conn, job)


def place_legal_hold(conn, tenant_id: str, subject_id: str, owner: str, reason: str, days: int) -> str:
    if not owner or len(reason) < 10 or not 1 <= days <= 365:
        raise ApiError(400, "invalid_hold", "A hold needs an owner, a lawful reason and an expiry of 1-365 days.")
    hold_id = new_id("hold")
    conn.execute("INSERT INTO legal_holds (tenant_id, id, subject_id, owner, reason, expires_at) "
                 "VALUES (%s,%s,%s,%s,%s, now() + make_interval(days => %s))",
                 (tenant_id, hold_id, subject_id, owner, reason, days))
    return hold_id


def _redact_primary(conn, tenant_id: str, subject_id: str, session_ids: list[str]) -> None:
    conn.execute("UPDATE subjects SET external_reference = 'deleted:' || id, deleted_at = coalesce(deleted_at, now()) "
                 "WHERE tenant_id = %s AND id = %s", (tenant_id, subject_id))
    conn.execute("UPDATE sessions SET external_reference = 'deleted', evidence_access_blocked_at = "
                 "coalesce(evidence_access_blocked_at, now()) WHERE tenant_id = %s AND id = ANY(%s)",
                 (tenant_id, session_ids))
    conn.execute("UPDATE contact_challenges SET destination_hash = 'deleted', code_hash = 'deleted' "
                 "WHERE tenant_id = %s AND session_id = ANY(%s)", (tenant_id, session_ids))
    conn.execute("UPDATE provider_events SET raw_body = NULL WHERE tenant_id = %s AND session_id = ANY(%s)",
                 (tenant_id, session_ids))


def advance_deletions(worker_db: Database, providers: dict[str, ProviderAdapter], limit: int = 50) -> int:
    with worker_db.system_tx() as conn:
        rows = list(conn.execute("SELECT tenant_id, id FROM deletion_jobs WHERE state <> 'complete' "
                                 "ORDER BY updated_at LIMIT %s", (limit,)))
    for r in rows:
        try:
            _advance_one(worker_db, providers, r["tenant_id"], r["id"])
        except ApiError:
            continue  # concurrent change; retried next cycle
    return len(rows)


def _advance_one(db: Database, providers: dict[str, ProviderAdapter], tenant_id: str, deletion_id: str) -> None:
    with db.tenant_tx(tenant_id) as conn:
        job = conn.execute("SELECT * FROM deletion_jobs WHERE tenant_id = %s AND id = %s FOR UPDATE SKIP LOCKED",
                           (tenant_id, deletion_id)).fetchone()
        if job is None:
            return
        if job["state"] in ("requested", "on_hold"):
            if _active_hold(conn, tenant_id, job["subject_id"]):
                if job["state"] == "requested":
                    _set_state(conn, job, "on_hold")
                return
            job = _set_state(conn, job, "in_progress")
        if job["primary_state"] != "done":
            tomb = conn.execute("SELECT session_ids FROM deletion_tombstones WHERE tenant_id = %s AND deletion_id = %s",
                                (tenant_id, deletion_id)).fetchone()
            _redact_primary(conn, tenant_id, job["subject_id"], tomb["session_ids"])
            conn.execute("UPDATE deletion_jobs SET primary_state = 'done' WHERE tenant_id = %s AND id = %s",
                         (tenant_id, deletion_id))
            job = dict(job, primary_state="done")
            if job["state"] == "in_progress":
                job = _set_state(conn, job, "primary_deleted")
        targets = list(conn.execute("SELECT * FROM deletion_supplier_targets WHERE tenant_id = %s AND deletion_id = %s "
                                    "AND state <> 'confirmed'", (tenant_id, deletion_id)))

    # Supplier calls happen outside database transactions.
    results: list[tuple[dict, str, str | None]] = []
    for t in targets:
        provider = providers.get(t["provider"])
        try:
            if provider is None:
                raise ProviderUnavailable("adapter not loaded")
            if t["state"] in ("pending", "error"):
                receipt = provider.request_deletion(t["provider_reference"], correlation_id=deletion_id)
                results.append((t, "requested", receipt))
            elif provider.deletion_confirmed(t["provider_reference"], correlation_id=deletion_id):
                results.append((t, "confirmed", t["receipt"]))
        except ProviderUnavailable:
            results.append((t, "error", t["receipt"]))

    with db.tenant_tx(tenant_id) as conn:
        job = conn.execute("SELECT * FROM deletion_jobs WHERE tenant_id = %s AND id = %s FOR UPDATE",
                           (tenant_id, deletion_id)).fetchone()
        for t, state, receipt in results:
            conn.execute("UPDATE deletion_supplier_targets SET state = %s, receipt = %s, attempts = attempts + 1, "
                         "updated_at = now() WHERE tenant_id = %s AND deletion_id = %s AND provider = %s AND "
                         "provider_reference = %s", (state, receipt, tenant_id, deletion_id, t["provider"],
                                                     t["provider_reference"]))
        failing = conn.execute("SELECT count(*) AS n FROM deletion_supplier_targets WHERE tenant_id = %s AND "
                               "deletion_id = %s AND state = 'error' AND attempts >= %s",
                               (tenant_id, deletion_id, SUPPLIER_MAX_ATTEMPTS)).fetchone()["n"]
        open_targets = conn.execute("SELECT count(*) AS n FROM deletion_supplier_targets WHERE tenant_id = %s AND "
                                    "deletion_id = %s AND state <> 'confirmed'",
                                    (tenant_id, deletion_id)).fetchone()["n"]
        if failing and job["state"] != "error":
            _set_state(conn, job, "error", ", last_error = %s", ("supplier deletion failing; escalate",))
            log("deletion.escalate", tenant_id=tenant_id, state="error")
            return
        if job["state"] in ("primary_deleted", "error") and open_targets == 0 and job["primary_state"] == "done":
            job = _set_state(conn, job, "awaiting_backup_expiry",
                             ", backup_expires_at = now() + make_interval(days => %s)", (BACKUP_RETENTION_DAYS,))
        if job["state"] == "awaiting_backup_expiry" and conn.execute(
                "SELECT %s::timestamptz <= now() AS due", (job["backup_expires_at"],)).fetchone()["due"]:
            _set_state(conn, job, "complete")


def replay_tombstones(owner_dsn: str) -> int:
    """After restoring a backup, re-apply every deletion before serving traffic (18_operations §Recovery)."""
    with psycopg.connect(owner_dsn, row_factory=dict_row) as conn:
        tombs = list(conn.execute("SELECT * FROM deletion_tombstones"))
        for t in tombs:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (t["tenant_id"],))
            _redact_primary(conn, t["tenant_id"], t["subject_id"], t["session_ids"])
            conn.execute("UPDATE applicant_sessions SET expires_at = least(expires_at, now()) WHERE tenant_id = %s "
                         "AND session_id = ANY(%s)", (t["tenant_id"], t["session_ids"]))
        conn.commit()
    return len(tombs)
