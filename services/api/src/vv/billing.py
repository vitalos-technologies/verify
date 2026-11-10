"""Usage ledger, credits, invoices and supplier reconciliation (VV-012, 16_pricing §Billing definitions).

Prices are the 16_pricing hypotheses until the owner approves real prices (IMP-10).
"""

from __future__ import annotations

import json
import re
from collections import Counter

from vv import crypto
from vv.errors import ApiError, conflict, not_found
from vv.ids import new_id

CHARGEABLE_OUTCOMES = {"approved", "declined"}


def charge_completion(conn, session: dict) -> None:
    """Idempotent: one charge per session regardless of later reviews, appeals or replays."""
    res = conn.execute("SELECT amount_minor, currency FROM usage_events WHERE tenant_id = %s AND ledger_key = %s",
                       (session["tenant_id"], f"reserve:{session['id']}")).fetchone()
    if res is None:
        return
    conn.execute("INSERT INTO usage_events (tenant_id, id, session_id, ledger_key, charge_type, amount_minor, "
                 "currency) VALUES (%s,%s,%s,%s,'completed_verification',%s,%s) ON CONFLICT DO NOTHING",
                 (session["tenant_id"], new_id("use"), session["id"], f"complete:{session['id']}",
                  res["amount_minor"], res["currency"]))


def _period(period: str) -> str:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period or ""):
        raise ApiError(400, "invalid_period", "Period must be YYYY-MM.")
    return period


def add_credit(conn, tenant_id: str, ledger_key: str, amount_minor: int, reason: str, actor_id: str) -> dict:
    if amount_minor <= 0 or len(reason) < 5:
        raise ApiError(400, "invalid_credit", "Credit needs a positive amount and a reason.")
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('vv_credit:' || %s || %s))", (tenant_id, ledger_key))
    charge = conn.execute("SELECT * FROM usage_events WHERE tenant_id = %s AND ledger_key = %s AND charge_type = "
                          "'completed_verification'", (tenant_id, ledger_key)).fetchone()
    if charge is None:
        raise not_found()
    credited = conn.execute("SELECT coalesce(-sum(amount_minor), 0) AS c FROM usage_events WHERE tenant_id = %s AND "
                            "credit_for = %s", (tenant_id, ledger_key)).fetchone()["c"]
    if credited + amount_minor > charge["amount_minor"]:
        raise conflict("credit_exceeds_charge", "Credits cannot exceed the original charge.")
    n = conn.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s AND credit_for = %s",
                     (tenant_id, ledger_key)).fetchone()["n"]
    row = conn.execute(
        "INSERT INTO usage_events (tenant_id, id, session_id, ledger_key, charge_type, amount_minor, currency, "
        "credit_for, reason, actor_id) VALUES (%s,%s,%s,%s,'credit',%s,%s,%s,%s,%s) RETURNING id, ledger_key",
        (tenant_id, new_id("use"), charge["session_id"], f"credit:{ledger_key}:{n + 1}", -amount_minor,
         charge["currency"], ledger_key, reason, actor_id)).fetchone()
    return {"id": row["id"], "ledger_key": row["ledger_key"], "amount_minor": -amount_minor}


def summary(conn, tenant_id: str, period: str) -> dict:
    _period(period)
    rows = list(conn.execute(
        "SELECT ledger_key, charge_type, amount_minor, currency, session_id, credit_for FROM usage_events "
        "WHERE tenant_id = %s AND to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM') = %s ORDER BY created_at, id",
        (tenant_id, period)))
    lines: dict[str, dict] = {}
    for r in rows:
        if r["charge_type"] in ("reservation", "reservation_release"):
            continue  # reservations are spend control, not charges
        line = lines.setdefault(r["charge_type"], {"charge_type": r["charge_type"], "quantity": 0, "amount_minor": 0})
        line["quantity"] += 1
        line["amount_minor"] += r["amount_minor"]
    billable = [lines[k] for k in ("completed_verification", "message", "credit") if k in lines]
    digest = crypto.canonical_digest([[r["ledger_key"], r["amount_minor"]] for r in rows])
    invoice = conn.execute("SELECT id, total_minor, issued_at FROM invoices WHERE tenant_id = %s AND period = %s",
                           (tenant_id, period)).fetchone()
    return {"period": period, "currency": "GBP", "lines": billable,
            "total_minor": sum(line["amount_minor"] for line in billable), "ledger_digest": digest,
            "invoice_id": invoice["id"] if invoice else None,
            "pricing_status": "hypothesis_not_approved_price"}


def issue_invoice(conn, tenant_id: str, period: str, actor_id: str) -> dict:
    s = summary(conn, tenant_id, period)
    if s["invoice_id"]:
        raise conflict("invoice_exists", "This period is already invoiced. Use credits for corrections.")
    if conn.execute("SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM') <= %s AS open", (period,)).fetchone()["open"]:
        raise conflict("period_open", "Invoices can only be issued after the period ends.")
    inv_id = new_id("inv")
    conn.execute("INSERT INTO invoices (tenant_id, id, period, lines, total_minor, ledger_digest, issued_by) "
                 "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (tenant_id, inv_id, period, json.dumps(s["lines"]), s["total_minor"], s["ledger_digest"], actor_id))
    return {**s, "invoice_id": inv_id}


def reconcile_supplier(conn, tenant_id: str, period: str, supplier_lines: list[dict]) -> dict:
    """Match a supplier's billed references to our attempts and charges (AT-12, 18_operations §Billing dispute)."""
    _period(period)
    billed = Counter(str(x["provider_reference"]) for x in supplier_lines)
    ours = {r["provider_reference"]: r for r in conn.execute(
        "SELECT a.provider_reference, a.session_id, s.state, "
        "EXISTS (SELECT 1 FROM usage_events u WHERE u.tenant_id = a.tenant_id AND "
        "u.ledger_key = 'complete:' || a.session_id) AS charged "
        "FROM attempts a JOIN sessions s ON s.tenant_id = a.tenant_id AND s.id = a.session_id "
        "WHERE a.tenant_id = %s AND a.provider_reference IS NOT NULL AND "
        "to_char(a.created_at AT TIME ZONE 'UTC', 'YYYY-MM') = %s", (tenant_id, period))}
    report = {"matched": [], "supplier_duplicates": [], "unknown_to_us": [], "not_billed_by_supplier": [],
              "billed_attempt_not_charged": []}
    for ref, count in sorted(billed.items()):
        if ref not in ours:
            report["unknown_to_us"].append(ref)
            continue
        report["matched"].append(ref)
        if count > 1:
            report["supplier_duplicates"].append(ref)
        if not ours[ref]["charged"]:
            report["billed_attempt_not_charged"].append(ref)  # retries/abandoned: supplier cost, no customer charge
    report["not_billed_by_supplier"] = sorted(set(ours) - set(billed))
    report["counts"] = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    return report
