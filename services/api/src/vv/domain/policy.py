"""Decision policy (VV-005, VV-007). Pure functions: same inputs always give the same decision and trace.

Rules follow 07_sessions_and_policy.md: provider error is never fail; missing mandatory
checks cannot approve; contact ownership cannot compensate for failed ID/liveness;
suspected spoofing and biometric uncertainty route to review in the pilot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import jsonschema

from vv.config import SERVICE_ROOT

ENGINE_VERSION = "policy-engine/1"
IDENTITY_FLOOR = ("government_id", "face_match", "liveness")
_SCHEMA_PATH = SERVICE_ROOT.parent.parent / "docs/spec/contracts/policy.schema.json"


class PolicyInvalid(Exception):
    pass


def _schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_definition(definition: dict) -> None:
    try:
        jsonschema.validate(definition, _schema())
    except jsonschema.ValidationError as exc:
        raise PolicyInvalid(f"policy definition invalid: {exc.message}") from None
    missing = [c for c in IDENTITY_FLOOR if c not in definition["required_checks"]]
    if missing:
        # Platform security floor: tenants cannot remove identity checks from an identity policy.
        raise PolicyInvalid(f"security floor requires checks: {', '.join(missing)}")


@dataclass(frozen=True)
class CheckView:
    id: str
    type: str
    result: str
    reasons: tuple[str, ...] = ()


@dataclass
class Evaluation:
    """outcome is a decision outcome, or None when the session must enter `error` (technical failure)."""
    outcome: str | None
    session_state: str
    reason_codes: list[str]
    evidence_check_ids: list[str]
    trace: list[dict] = field(default_factory=list)


def evaluate(definition: dict, checks: list[CheckView], *, quality_retries_used: int) -> Evaluation:
    required: list[str] = list(definition["required_checks"])
    by_type: dict[str, CheckView] = {}
    for c in checks:  # caller passes checks oldest→newest; latest observation per type wins
        by_type[c.type] = c
    trace: list[dict] = []
    evidence_ids = [by_type[t].id for t in required if t in by_type]

    def done(outcome: str | None, state: str, reasons: list[str]) -> Evaluation:
        trace.append({"rule": "result", "outcome": outcome, "state": state})
        return Evaluation(outcome, state, sorted(set(reasons)), evidence_ids, trace)

    # Rule: technical errors. Never a failed identity check.
    errored = [t for t in required if t in by_type and by_type[t].result == "error"]
    trace.append({"rule": "technical_errors", "checks": errored})
    if errored:
        return done(None, "error", ["provider.unavailable"])

    # Rule: explicit high-risk indicators -> review with restricted details.
    attack = [t for t in required if t in by_type and "liveness.suspected_attack" in by_type[t].reasons]
    trace.append({"rule": "high_risk_indicators", "checks": attack})
    if attack:
        return done("review_required", "review_required", ["liveness.suspected_attack"])

    # Capture quality: retry within bounded policy, then customer-assisted alternative via review.
    low_quality = [t for t in required if t in by_type and "capture.low_quality" in by_type[t].reasons
                   and by_type[t].result != "pass"]
    allowed = int(definition["quality_retries"])
    trace.append({"rule": "capture_quality", "checks": low_quality, "retries_used": quality_retries_used,
                  "retries_allowed": allowed})
    if low_quality:
        if quality_retries_used < allowed:
            return done("action_required", "action_required", ["capture.low_quality"])
        return done("review_required", "review_required", ["capture.low_quality"])

    # Rule: required evidence present. Evaluated after high-risk and capture-quality
    # signals because a poor capture legitimately leaves downstream checks not_run.
    missing = [t for t in required if t not in by_type or by_type[t].result == "not_run"]
    trace.append({"rule": "required_evidence", "missing": missing})
    if missing:
        only_contact = all(t in ("email", "phone") for t in missing)
        if only_contact:
            return done("action_required", "action_required", ["evidence.missing"])
        return done("review_required", "review_required", ["evidence.missing"])

    # Rule: document validity, match and liveness.
    reasons: list[str] = []
    gov = by_type.get("government_id")
    if gov and gov.result != "pass" and "document.expired" in gov.reasons:
        trace.append({"rule": "document_expiry", "result": "expired"})
        if quality_retries_used < allowed:
            return done("action_required", "action_required", ["document.expired"])
        return done("declined", "declined", ["document.expired"])
    if gov and gov.result != "pass" and "document.unsupported" in gov.reasons:
        trace.append({"rule": "document_supported", "result": "unsupported"})
        return done("action_required", "action_required", ["document.unsupported"])

    not_passed = [t for t in required if by_type[t].result != "pass"]
    trace.append({"rule": "mandatory_checks_pass", "not_passed": not_passed})
    if not_passed:
        for t in not_passed:
            reasons.extend(by_type[t].reasons or [f"{t}.{by_type[t].result}"])
        # Fail or inconclusive on any mandatory check -> accountable human review (uncertain_action).
        return done(definition["uncertain_action"], "review_required", reasons)

    # Rule: approve only if every mandatory check passed.
    return done("approved", "approved", [])
