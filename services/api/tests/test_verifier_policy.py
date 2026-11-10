"""Verifier: exhaustive security-floor property for the pure policy engine."""
from __future__ import annotations

import itertools

import pytest

from vv.admin import DEV_POLICY
from vv.domain.policy import CheckView, PolicyInvalid, evaluate, validate_definition

RESULTS = ["pass", "fail", "inconclusive", "error", "not_run", None]  # None = absent
REASONS = [(), ("liveness.suspected_attack",), ("capture.low_quality",), ("document.expired",),
           ("document.unsupported",)]


@pytest.mark.parametrize("retries_used", [0, 1, 2, 3])
def test_never_approves_unless_all_required_pass(retries_used):
    n = 0
    for pol in (DEV_POLICY, dict(DEV_POLICY, required_checks=["government_id", "face_match", "liveness"])):
        req = pol["required_checks"]
        for combo in itertools.product(RESULTS, repeat=len(req)):
            for rsn_i in range(len(REASONS)):
                for target in range(len(req)):
                    checks = []
                    for i, (t, r) in enumerate(zip(req, combo, strict=True)):
                        if r is None:
                            continue
                        checks.append(CheckView(f"c{i}", t, r, REASONS[rsn_i] if i == target else ()))
                    ev = evaluate(pol, checks, quality_retries_used=retries_used)
                    n += 1
                    all_pass = all(r == "pass" for r in combo)
                    if ev.outcome == "approved":
                        assert all_pass and ev.session_state == "approved", (combo, rsn_i, target)
                        # passing check flagged suspected attack must not approve
                        assert not (REASONS[rsn_i] == ("liveness.suspected_attack",)), (combo, target)
                    if any(r == "error" for r in combo):
                        assert ev.outcome is None and ev.session_state == "error"
                    assert ev.outcome != "declined" or "document.expired" in ev.reason_codes
    assert n > 1000


def test_extra_unrequired_failures_and_duplicates():
    pol = DEV_POLICY
    # later failing observation of same type wins over earlier pass
    checks = [CheckView("a", "liveness", "pass"), CheckView("b", "government_id", "pass"),
              CheckView("c", "face_match", "pass"), CheckView("d", "email", "pass"),
              CheckView("e", "liveness", "fail", ("liveness.failed",))]
    assert evaluate(pol, checks, quality_retries_used=0).outcome == "review_required"


@pytest.mark.parametrize("mut", [
    {"required_checks": ["government_id", "face_match"]},
    {"uncertain_action": "approved"},
    {"quality_retries": 99},
    {"extra": 1},
])
def test_policy_floor_cannot_be_removed(mut):
    with pytest.raises(PolicyInvalid):
        validate_definition(dict(DEV_POLICY, **mut))
