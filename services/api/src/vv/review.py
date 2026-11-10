"""Case review queue, claim leases, second review and appeals (VV-008, 10_review_and_operations_console).

- Reviewers claim a time-limited lease; stale clients (old lock_version) cannot act.
- High-impact override (approving by alternative method) needs a second, different reviewer.
- Appeals link to the decision they challenge, go to someone other than the original reviewer where
  possible, and resolve by appending a new decision revision. Evidence and checks are never rewritten.
"""

from __future__ import annotations

import json

from vv.errors import ApiError, conflict, forbidden, not_found
from vv.ids import new_id
from vv.service import (
    _next_revision,
    audit,
    emit,
    get_session,
    latest_checks,
    record_review_decision,
    session_view,
)

LEASE_MINUTES = 15
APPEAL_ACK_DAYS = 2  # proposed customer-operated targets (10_review §Appeals); calendar-day approximation
APPEAL_RESOLVE_DAYS = 5
APPEAL_EVIDENCE_HOLD_DAYS = 30
REVIEW_ROLES = ("owner", "administrator", "reviewer")


def _review(conn, tenant_id: str, review_id: str) -> dict:
    row = conn.execute("SELECT *, coalesce(lease_expires_at > now(), false) AS leased FROM reviews "
                       "WHERE tenant_id = %s AND id = %s FOR UPDATE", (tenant_id, review_id)).fetchone()
    if row is None:
        raise not_found()
    return row


def _ts(value) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _out(row: dict) -> dict:
    return {"id": row["id"], "session_id": row["session_id"], "status": row["status"], "assignee": row["assignee"],
            "lock_version": row["lock_version"],
            "lease_expires_at": _ts(row["lease_expires_at"]),
            "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")}


def queue(conn, tenant_id: str, limit: int = 50) -> dict:
    rows = conn.execute("SELECT *, coalesce(lease_expires_at > now(), false) AS leased FROM reviews "
                        "WHERE tenant_id = %s AND status <> 'closed' ORDER BY created_at LIMIT %s",
                        (tenant_id, min(max(limit, 1), 100)))
    return {"items": [_out(r) for r in rows]}  # ordered by age only; never by inferred traits


def claim(conn, tenant_id: str, review_id: str, member: str) -> dict:
    r = _review(conn, tenant_id, review_id)
    if r["status"] == "closed":
        raise conflict("review_closed", "This case is already decided.")
    if r["status"] == "awaiting_second_review":
        raise conflict("awaiting_second_review", "This case is waiting for a second reviewer.")
    if r["status"] == "claimed" and r["leased"] and r["assignee"] != member:
        raise conflict("review_claimed", "Another reviewer is working on this case.")
    row = conn.execute("UPDATE reviews SET status = 'claimed', assignee = %s, lock_version = lock_version + 1, "
                       "lease_expires_at = now() + make_interval(mins => %s) WHERE tenant_id = %s AND id = %s "
                       "RETURNING *", (member, LEASE_MINUTES, tenant_id, review_id)).fetchone()
    audit(conn, tenant_id, "console", member, "review.claim", "review", review_id)
    return _out(row)


def decide(conn, tenant_id: str, review_id: str, member: str, body: dict, lock_version: int,
           request_id: str) -> dict:
    r = _review(conn, tenant_id, review_id)
    if r["status"] != "claimed" or r["assignee"] != member or not r["leased"]:
        raise conflict("lease_required", "Claim the case (or renew your claim) before deciding.")
    if r["lock_version"] != lock_version:
        raise conflict("revision.stale", "This case changed since you loaded it; reload and retry.")
    if body["method"] == "alternative_method" and body["outcome"] == "approved":
        # High-impact override: record a proposal; a different reviewer must confirm.
        session = get_session(conn, tenant_id, r["session_id"])
        if session["version"] != body["expected_revision"]:
            raise conflict("revision.stale", "The verification changed since you loaded it; reload and retry.")
        known = {c["id"] for c in latest_checks(conn, tenant_id, r["session_id"])}
        if not set(body["evidence_ids"]) <= known:
            raise ApiError(422, "evidence_unknown", "Evidence references must belong to this verification.")
        row = conn.execute("UPDATE reviews SET status = 'awaiting_second_review', proposal = %s, proposed_by = %s, "
                           "assignee = NULL, lease_expires_at = NULL, lock_version = lock_version + 1 "
                           "WHERE tenant_id = %s AND id = %s RETURNING *",
                           (json.dumps(body), member, tenant_id, review_id)).fetchone()
        audit(conn, tenant_id, "console", member, "review.override_proposed", "review", review_id,
              request_id=request_id)
        return {"review": _out(row), "session": None}
    _, session = record_review_decision(conn, tenant_id=tenant_id, session_id=r["session_id"], actor_id=member,
                                        body=body, request_id=request_id, actor_kind="console")
    return {"review": {**_out(r), "status": "closed"}, "session": session}


def second_review(conn, tenant_id: str, review_id: str, member: str, confirm: bool, request_id: str) -> dict:
    r = _review(conn, tenant_id, review_id)
    if r["status"] != "awaiting_second_review":
        raise conflict("no_pending_override", "There is no override waiting for a second review.")
    if r["proposed_by"] == member:
        raise forbidden("A second reviewer must be a different person.")
    if not confirm:
        row = conn.execute("UPDATE reviews SET status = 'open', proposal = NULL, proposed_by = NULL, "
                           "lock_version = lock_version + 1 WHERE tenant_id = %s AND id = %s RETURNING *",
                           (tenant_id, review_id)).fetchone()
        audit(conn, tenant_id, "console", member, "review.override_rejected", "review", review_id)
        return {"review": _out(row), "session": None}
    proposal = r["proposal"]
    _, session = record_review_decision(conn, tenant_id=tenant_id, session_id=r["session_id"],
                                        actor_id=r["proposed_by"], body=proposal, request_id=request_id,
                                        actor_kind="console", second_reviewer=member)
    audit(conn, tenant_id, "console", member, "review.override_confirmed", "review", review_id)
    return {"review": {**_out(r), "status": "closed"}, "session": session}


# ------------------------------------------------------------------ appeals
def _appeal_out(a: dict) -> dict:
    return {"id": a["id"], "session_id": a["session_id"], "status": a["status"],
            "appealed_revision": a["appealed_revision"], "assignee": a["assignee"],
            "ack_due_at": a["ack_due_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "resolve_due_at": a["resolve_due_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "resolved_revision": a["resolved_revision"]}


def create_appeal(conn, tenant_id: str, session_id: str, member: str, summary: str) -> dict:
    s = get_session(conn, tenant_id, session_id, for_update=True)
    if s["state"] not in ("approved", "declined"):
        raise conflict("not_appealable", "Only completed verifications can be appealed.")
    if s["evidence_access_blocked_at"] is not None:
        raise conflict("subject_deleted", "This subject's data has been deleted.")
    rev = conn.execute("SELECT max(revision) AS r FROM decisions WHERE tenant_id = %s AND session_id = %s",
                       (tenant_id, session_id)).fetchone()["r"]
    try:
        a = conn.execute(
            "INSERT INTO appeals (tenant_id, id, session_id, appealed_revision, status, summary, recorded_by, "
            "ack_due_at, resolve_due_at) VALUES (%s,%s,%s,%s,'open',%s,%s, now() + make_interval(days => %s), "
            "now() + make_interval(days => %s)) RETURNING *",
            (tenant_id, new_id("apl"), session_id, rev, summary, member, APPEAL_ACK_DAYS,
             APPEAL_RESOLVE_DAYS)).fetchone()
    except Exception as exc:
        if getattr(exc, "sqlstate", None) == "23505":
            raise conflict("appeal_open", "An appeal is already open for this verification.") from None
        raise
    # Protect evidence from expiry while the appeal is handled (time-limited hold).
    conn.execute("UPDATE sessions SET appeal_hold_until = now() + make_interval(days => %s) WHERE tenant_id = %s "
                 "AND id = %s", (APPEAL_EVIDENCE_HOLD_DAYS, tenant_id, session_id))
    audit(conn, tenant_id, "console", member, "appeal.create", "session", session_id)
    return _appeal_out(a)


def claim_appeal(conn, tenant_id: str, appeal_id: str, member: str) -> dict:
    a = conn.execute("SELECT * FROM appeals WHERE tenant_id = %s AND id = %s FOR UPDATE",
                     (tenant_id, appeal_id)).fetchone()
    if a is None:
        raise not_found()
    if a["status"] == "resolved":
        raise conflict("appeal_resolved", "This appeal is already resolved.")
    original = conn.execute("SELECT actor_id FROM decisions WHERE tenant_id = %s AND session_id = %s AND revision = %s",
                            (tenant_id, a["session_id"], a["appealed_revision"])).fetchone()
    if original and original["actor_id"] == member:
        others = conn.execute("SELECT count(*) AS n FROM memberships WHERE tenant_id = %s AND active AND id <> %s "
                              "AND role = ANY(%s)", (tenant_id, member, list(REVIEW_ROLES))).fetchone()["n"]
        if others > 0:
            raise conflict("conflict_of_interest", "Appeals go to someone other than the original reviewer.")
    a = conn.execute("UPDATE appeals SET status = 'claimed', assignee = %s WHERE tenant_id = %s AND id = %s "
                     "RETURNING *", (member, tenant_id, appeal_id)).fetchone()
    audit(conn, tenant_id, "console", member, "appeal.claim", "appeal", appeal_id)
    return _appeal_out(a)


def resolve_appeal(conn, tenant_id: str, appeal_id: str, member: str, body: dict, request_id: str) -> dict:
    a = conn.execute("SELECT * FROM appeals WHERE tenant_id = %s AND id = %s FOR UPDATE",
                     (tenant_id, appeal_id)).fetchone()
    if a is None:
        raise not_found()
    if a["status"] != "claimed" or a["assignee"] != member:
        raise conflict("claim_required", "Claim the appeal before resolving it.")
    s = get_session(conn, tenant_id, a["session_id"], for_update=True)
    if s["version"] != body["expected_revision"]:
        raise conflict("revision.stale", "The verification changed since you loaded it; reload and retry.")
    checks = latest_checks(conn, tenant_id, s["id"])
    if not set(body["evidence_ids"]) <= {c["id"] for c in checks}:
        raise ApiError(422, "evidence_unknown", "Evidence references must belong to this verification.")
    policy = conn.execute("SELECT * FROM policies WHERE tenant_id = %s AND id = %s",
                          (tenant_id, s["policy_row_id"])).fetchone()
    latest = {c["type"]: c for c in checks}
    failing = [t for t in policy["definition"]["required_checks"]
               if t not in latest or latest[t]["result"] != "pass"]
    if body["outcome"] == "approved" and body["method"] == "evidence_review" and failing:
        raise ApiError(422, "review.alternative_method_required",
                       "Required checks did not pass. Record an alternative-method decision with its rationale.")
    reasons = ["appeal.revised"] + (["review.alternative_method"] if body["method"] == "alternative_method" else [])
    revision = _next_revision(conn, tenant_id, s["id"])
    conn.execute(
        "INSERT INTO decisions (tenant_id, id, session_id, revision, outcome, actor_type, actor_id, method, "
        "reason_codes, reason_text, policy_row_id, policy_key, policy_version, evidence_check_ids, trace, "
        "supersedes_revision) VALUES (%s,%s,%s,%s,%s,'reviewer',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (tenant_id, new_id("dec"), s["id"], revision, body["outcome"], member, body["method"], reasons,
         body["reason"], policy["id"], policy["key"], policy["version"], body["evidence_ids"],
         json.dumps({"appeal": {"id": appeal_id, "appealed_revision": a["appealed_revision"],
                                "failing_required_checks": failing}}), revision - 1))
    # Explicit reopening: a new revision and event, never a silent rewrite.
    s = conn.execute("UPDATE sessions SET state = %s, version = version + 1, updated_at = now() WHERE tenant_id = %s "
                     "AND id = %s AND version = %s RETURNING *",
                     (body["outcome"], tenant_id, s["id"], s["version"])).fetchone()
    emit(conn, tenant_id, "verification.completed", s["id"], s["version"],
         {"state": body["outcome"], "reason_codes": sorted(reasons)})
    a = conn.execute("UPDATE appeals SET status = 'resolved', resolved_revision = %s, resolved_at = now() "
                     "WHERE tenant_id = %s AND id = %s RETURNING *", (revision, tenant_id, appeal_id)).fetchone()
    audit(conn, tenant_id, "console", member, "appeal.resolve", "appeal", appeal_id, reason=body["method"],
          request_id=request_id)
    return {"appeal": _appeal_out(a), "session": session_view(conn, s)}
