"""Recovery exercise (AT-14, 18_operations §Recovery exercise, 14_infrastructure §Recovery).

Restores a logical backup into an isolated database with every outbound path disabled, replays
deletion tombstones before anything could serve data, verifies consistency and evidence objects,
measures RTO/RPO, then destroys the exercise copy. Produces a redacted JSON report (counts only).

This exercises the procedure on synthetic data. It is not evidence about production backups,
PITR or cross-system restore, which need the real infrastructure (M02-T04/M07).
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from vv.deletion import replay_tombstones
from vv.evidence import LocalSealedStore

TABLES = ["tenants", "memberships", "sessions", "attempts", "checks", "decisions", "evidence", "outbox",
          "webhook_deliveries", "deletion_jobs", "deletion_tombstones", "usage_events", "audit_events"]


def _with_db(dsn: str, dbname: str) -> str:
    p = urlsplit(dsn)
    return urlunsplit((p.scheme, p.netloc, "/" + dbname, p.query, p.fragment))


def _counts(conn) -> dict[str, int]:
    return {t: conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(t))).fetchone()["n"]
            for t in TABLES}


def run_exercise(source_owner_dsn: str, store: LocalSealedStore, *, keep: bool = False, log=None) -> dict:
    started = time.monotonic()
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    restore_db = f"vv_restore_{stamp}"
    report: dict = {"exercise": "logical_restore_isolated", "started_at": datetime.now(UTC).isoformat(),
                    "restore_database": restore_db, "steps": []}

    def step(name: str, **info) -> None:
        report["steps"].append({"step": name, "t_seconds": round(time.monotonic() - started, 2), **info})

    with psycopg.connect(source_owner_dsn, row_factory=dict_row) as src:
        source_counts = _counts(src)
        latest = src.execute("SELECT greatest((SELECT max(created_at) FROM audit_events), "
                             "(SELECT max(created_at) FROM outbox)) AS t").fetchone()["t"]
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "backup.dump"
        subprocess.run(["pg_dump", "--format=custom", "--no-owner", "--file", str(dump), source_owner_dsn],  # noqa: S603,S607 - fixed argv, no shell
                       check=True, capture_output=True)
        backup_taken = datetime.now(UTC)
        step("backup_taken", bytes=dump.stat().st_size)
        with psycopg.connect(source_owner_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restore_db)))
        restore_dsn = _with_db(source_owner_dsn, restore_db)
        try:
            restored = subprocess.run(["pg_restore", "--no-owner", "--dbname", restore_dsn, str(dump)],  # noqa: S603,S607
                                      capture_output=True, text=True)
            # Role/grant notices on an isolated copy are acceptable; a missing schema is not.
            step("restored", pg_restore_exit=restored.returncode)
            with psycopg.connect(restore_dsn, row_factory=dict_row) as r:
                # Isolation: no outbound effects from the copy (customer webhooks, supplier calls).
                r.execute("UPDATE webhook_endpoints SET status = 'disabled'")
                r.execute("UPDATE webhook_deliveries SET state = 'blocked', last_error = 'recovery_exercise' "
                          "WHERE state = 'pending'")
                r.execute("UPDATE provider_events SET processing_state = 'quarantined', outcome_note = "
                          "'recovery_exercise' WHERE processing_state IN ('pending','retry','processing')")
                r.commit()
            step("outbound_disabled")
            replayed = replay_tombstones(restore_dsn, store=None, log=log)  # objects are not restored into the copy
            step("tombstones_replayed", **replayed)
            with psycopg.connect(restore_dsn, row_factory=dict_row) as r:
                restored_counts = _counts(r)
                leaked = r.execute(
                    "SELECT count(*) AS n FROM deletion_tombstones t JOIN sessions s ON s.tenant_id = t.tenant_id "
                    "AND s.subject_id = t.subject_id WHERE s.evidence_access_blocked_at IS NULL").fetchone()["n"]
                migrations = [x["version"] for x in r.execute("SELECT version FROM schema_migrations ORDER BY 1")]
                rls = r.execute("SELECT count(*) AS n FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity").fetchone()["n"]
                missing_objects = sum(
                    1 for e in r.execute("SELECT storage_key FROM evidence WHERE deleted_at IS NULL")
                    if not store.exists(e["storage_key"]))
                outbound = r.execute("SELECT (SELECT count(*) FROM webhook_deliveries WHERE state = 'pending') + "
                                     "(SELECT count(*) FROM provider_events WHERE processing_state IN "
                                     "('pending','retry','processing')) AS n").fetchone()["n"]
            step("verified")
        finally:
            if not keep:
                with psycopg.connect(source_owner_dsn, autocommit=True) as admin:
                    admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(restore_db)))
                step("exercise_copy_destroyed")

    rto = time.monotonic() - started
    report.update({
        "source_counts": source_counts, "restored_counts": restored_counts,
        "counts_match": source_counts == restored_counts,
        "migrations": migrations, "tables_with_rls": rls,
        "tombstone_leaks_after_replay": leaked,
        "evidence_objects_missing": missing_objects,
        "outbound_work_remaining": outbound,
        "measured_rto_seconds": round(rto, 2),
        "rpo_seconds_at_backup": round((backup_taken - latest).total_seconds(), 2) if latest else None,
        "targets": {"rto_seconds": 4 * 3600, "rpo_seconds": 15 * 60, "status": "proposed_not_approved"},
        "limitations": "Logical dump of synthetic data on one host; not PITR, cross-region, object-store or "
                       "provider-state recovery.",
    })
    report["passed"] = (report["counts_match"] and leaked == 0 and missing_objects == 0 and outbound == 0
                        and rto < 4 * 3600)
    return report
