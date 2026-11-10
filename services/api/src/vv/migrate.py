"""Minimal forward-only SQL migration runner (expand/contract discipline; no automatic down-migrations)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(owner_dsn: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(owner_dsn, autocommit=False) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())""")
        conn.execute("SELECT pg_advisory_xact_lock(727274)")
        done = {r[0]: r[1] for r in conn.execute("SELECT version, checksum FROM schema_migrations")}
        for path in sorted(directory.glob("*.sql")):
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            if path.stem in done:
                if done[path.stem] != checksum:
                    raise RuntimeError(f"migration {path.name} changed after being applied")
                continue
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)", (path.stem, checksum))
            applied.append(path.stem)
        conn.commit()
    return applied
