"""Platform administration and operations APIs (metadata only; no subject data or evidence).

Platform staff authenticate separately from customer consoles. Development sign-in only until the
platform IdP is configured (same OIDC + MFA module as the console).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from vv import crypto
from vv.db import Database
from vv.domain.coverage import CoverageRegistry
from vv.errors import ApiError, unauthenticated
from vv.ids import new_id

CAPABILITIES = [("government_id", "Government ID"), ("liveness", "Selfie & liveness"), ("email", "Phone & email"),
                ("document", "Document AI"), ("nfc", "NFC")]
QUEUE_LABELS = {"identity_checks": "Identity checks", "provider_callbacks": "Provider callbacks",
                "customer_webhooks": "Customer webhooks", "evidence_deletion": "Evidence deletion"}
DELAY_MINUTES = 10  # 18_operations proposed alert: oldest processing job above 10 minutes


def create_session(conn, operator_id: str, absolute_seconds: int = 8 * 3600) -> tuple[str, str]:
    token, csrf = crypto.random_token(32), crypto.random_token(24)
    conn.execute("INSERT INTO platform_sessions (id, operator_id, token_hash, csrf_hash, absolute_expires_at) "
                 "VALUES (%s,%s,%s,%s, now() + make_interval(secs => %s))",
                 (new_id("pses"), operator_id, crypto.token_hash(token), crypto.token_hash(csrf), absolute_seconds))
    return token, csrf


def authenticate(db: Database, token: str | None, idle_seconds: int = 30 * 60) -> dict:
    if not token:
        raise unauthenticated()
    with db.system_tx() as conn:
        row = conn.execute(
            "SELECT s.id, s.last_seen_at, s.absolute_expires_at, s.revoked_at, o.id AS operator_id, o.role, "
            "o.display_name, o.active, now() AS now FROM platform_sessions s JOIN platform_operators o ON "
            "o.id = s.operator_id WHERE s.token_hash = %s", (crypto.token_hash(token),)).fetchone()
        if (row is None or row["revoked_at"] or not row["active"] or row["absolute_expires_at"] <= row["now"]
                or row["last_seen_at"] + timedelta(seconds=idle_seconds) <= row["now"]):
            raise unauthenticated()
        conn.execute("UPDATE platform_sessions SET last_seen_at = now() WHERE id = %s", (row["id"],))
    return row


def _iso(ts: datetime | None) -> str | None:
    return ts.astimezone(UTC).isoformat() if ts else None


def organisations(conn, coverage: CoverageRegistry) -> dict:
    rows = list(conn.execute("SELECT * FROM vv_platform_organisations()"))
    available = {c for e in coverage.entries if e.enabled for c in e.checks} | {"email"}
    items = []
    for r in rows:
        required = set(r["required_checks"] or [])
        enabled = {k: (k in required or (k == "liveness" and "face_match" in required)) for k, _ in CAPABILITIES}
        attention = r["status"] != "active" or (r["monthly_session_cap"] and
                                                r["month_sessions"] >= 0.9 * r["monthly_session_cap"])
        items.append({
            "id": r["id"], "name": r["name"], "status": "attention" if attention and r["status"] == "active"
            else r["status"], "plan": "Pilot",  # commercial plans not yet defined (M06 pricing decision)
            "enabled_checks": sum(enabled.values()), "total_checks": len(CAPABILITIES),
            "capabilities": [{"key": k, "label": label, "enabled": enabled[k], "available": k in available}
                             for k, label in CAPABILITIES],
            "monthly_usage": r["month_sessions"], "monthly_completed": r["month_completed"],
            "monthly_cap": r["monthly_session_cap"], "members": r["members"], "created_at": _iso(r["created_at"]),
        })
    return {"items": items, "stats": {
        "active": sum(1 for i in items if i["status"] in ("active", "attention")),
        "pilot": sum(1 for i in items if i["plan"] == "Pilot"),
        "monthly_verifications": sum(i["monthly_usage"] for i in items),
        "attention": sum(1 for i in items if i["status"] != "active"),
    }}


def activity(conn, tenant_id: str) -> dict:
    return {"items": [{"action": r["action"], "actor_type": r["actor_type"], "at": _iso(r["created_at"])}
                      for r in conn.execute("SELECT * FROM vv_platform_tenant_activity(%s, 10)", (tenant_id,))]}


def operations(conn, providers: list[str]) -> dict:
    now = conn.execute("SELECT now() AS n").fetchone()["n"]
    queues = []
    for r in conn.execute("SELECT * FROM vv_platform_queues()"):
        age = (now - r["oldest"]).total_seconds() / 60 if r["oldest"] else None
        queues.append({"key": r["queue"], "label": QUEUE_LABELS[r["queue"]], "pending": r["pending"],
                       "oldest_minutes": round(age, 1) if age is not None else None,
                       "health": "delayed" if age is not None and age > DELAY_MINUTES else "healthy"})
    days = 30
    health: dict[str, dict] = {p: {"total": 0, "failed": 0, "series": [None] * days} for p in providers}
    start = (now - timedelta(days=days - 1)).date()
    for r in conn.execute("SELECT * FROM vv_platform_provider_health(%s)", (days,)):
        h = health.setdefault(r["provider"], {"total": 0, "failed": 0, "series": [None] * days})
        h["total"] += r["total"]
        h["failed"] += r["failed"]
        idx = (r["day"] - start).days
        if 0 <= idx < days:
            h["series"][idx] = round(100 * (1 - r["failed"] / r["total"]), 2) if r["total"] else None
    prov = [{"provider": p, "label": "Dummy provider (mock)" if p == "dummy" else p,
             "success_rate": round(100 * (1 - h["failed"] / h["total"]), 2) if h["total"] else None,
             "events": h["total"], "health": "no_data" if not h["total"] else
             ("degraded" if h["failed"] / h["total"] > 0.05 else "healthy"), "series": h["series"]}
            for p, h in sorted(health.items())]
    c = conn.execute("SELECT * FROM vv_platform_counters()").fetchone()
    return {
        "environment": "development",
        "stats": {"processing_now": next(q["pending"] for q in queues if q["key"] == "identity_checks"),
                  "delayed_jobs": sum(q["pending"] for q in queues if q["health"] == "delayed"),
                  "open_incidents": 0, "deletions_due_today": c["deletions_due_today"]},
        "queues": queues, "providers": prov,
        "attention": {"failed_webhooks": c["failed_webhooks"], "quarantined_events": c["quarantined_events"],
                      "error_sessions": c["error_sessions"]},
        "incidents": [], "support_grants": [],
        "notes": "Incident tracking and support access grants are not built yet (M07/M14).",
    }


def dumps(o) -> str:
    return json.dumps(o, default=str)


def require(op: dict, roles: set[str]) -> None:
    if op["role"] not in roles:
        raise ApiError(403, "forbidden", "Your platform role cannot view this.")
