"""Operator CLI (owner DSN). `vv-admin seed-dev` creates a synthetic tenant for local use only."""

from __future__ import annotations

import argparse
import json
import os

import psycopg
from psycopg.rows import dict_row

from vv import auth, service
from vv.config import load_settings
from vv.domain.coverage import CoverageRegistry
from vv.ids import new_id
from vv.migrate import apply_migrations

DEV_POLICY = {
    "id": "workforce_identity", "version": 1, "required_checks": ["government_id", "face_match", "liveness", "email"],
    "quality_retries": 2, "uncertain_action": "review_required", "coverage_version": "pilot_1",
    "retention_profile": "pilot_proposed_30d",
}


def owner_conn(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, row_factory=dict_row)


def set_runtime_passwords(dsn: str, app_password: str, worker_password: str) -> None:
    """DEV/CI ONLY: give the runtime roles LOGIN with local passwords. Production uses IaC-managed roles."""
    with owner_conn(dsn) as conn:
        conn.execute(psycopg.sql.SQL("ALTER ROLE vv_app LOGIN PASSWORD {}").format(psycopg.sql.Literal(app_password)))
        conn.execute(psycopg.sql.SQL("ALTER ROLE vv_worker LOGIN PASSWORD {}").format(
            psycopg.sql.Literal(worker_password)))


def create_tenant(conn: psycopg.Connection, name: str, *, tenant_id: str | None = None,
                  regions: list[str] | None = None, monthly_cap: int = 100, message_cap: int = 50) -> str:
    tid = tenant_id or new_id("ten")
    conn.execute("INSERT INTO tenants (id, name, region_policy, monthly_session_cap, daily_message_cap) "
                 "VALUES (%s,%s,%s,%s,%s)", (tid, name, regions or ["synthetic"], monthly_cap, message_cap))
    return tid


def add_member(conn: psycopg.Connection, tenant_id: str, subject: str, role: str) -> str:
    mid = new_id("mem")
    conn.execute("INSERT INTO memberships (tenant_id, id, user_subject, role) VALUES (%s,%s,%s,%s)",
                 (tenant_id, mid, subject, role))
    return mid


def seed_dev(dsn: str) -> dict:
    settings = load_settings()
    if not settings.is_non_production:
        raise SystemExit("seed-dev is only available in development/test/ci")
    coverage = CoverageRegistry.load(settings.coverage_path)
    with owner_conn(dsn) as conn:
        tid = create_tenant(conn, "Synthetic Recruitment Ltd (demo)")
        add_member(conn, tid, "owner@synthetic.example", "owner")
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tid,))
        service.create_policy_draft(conn, tid, DEV_POLICY)
        service.publish_policy(conn, tid, DEV_POLICY["id"], 1, coverage, settings.session_price_minor)
        _, raw = auth.create_api_key(conn, settings.hmac_pepper, settings.environment, tid,
                                     sorted(auth.API_SCOPES), "dev seed", "vv-admin")
    return {"tenant_id": tid, "owner_subject": "owner@synthetic.example", "api_key": raw,
            "note": "Synthetic development tenant. The API key is shown once."}


def main() -> None:
    parser = argparse.ArgumentParser(prog="vv-admin")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    roles = sub.add_parser("dev-roles")
    roles.add_argument("--app-password", default=os.environ.get("VV_APP_PASSWORD", "vv_app_local"))
    roles.add_argument("--worker-password", default=os.environ.get("VV_WORKER_PASSWORD", "vv_worker_local"))
    sub.add_parser("seed-dev")
    args = parser.parse_args()
    dsn = os.environ.get("VV_OWNER_DSN")
    if not dsn:
        raise SystemExit("VV_OWNER_DSN is required")
    if args.cmd == "migrate":
        print(json.dumps({"applied": apply_migrations(dsn)}))
    elif args.cmd == "dev-roles":
        if load_settings().is_non_production is False:
            raise SystemExit("dev-roles is only available in development/test/ci")
        set_runtime_passwords(dsn, args.app_password, args.worker_password)
        print(json.dumps({"status": "ok"}))
    elif args.cmd == "seed-dev":
        print(json.dumps(seed_dev(dsn), indent=2))
