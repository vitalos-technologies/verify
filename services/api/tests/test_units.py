"""Pure unit tests: policy engine, coverage registry, signatures, destination validation."""

from __future__ import annotations

import json

import pytest

from vv import crypto
from vv.admin import DEV_POLICY
from vv.domain.coverage import CoverageRegistry, UnsupportedCapability
from vv.domain.policy import CheckView, PolicyInvalid, evaluate, validate_definition
from vv.webhooks import UnsafeDestination, validate_destination

P = DEV_POLICY


def ev(*checks, used=0, policy=P):
    views = [CheckView(f"c{i}", t, r, tuple(rs)) for i, (t, r, rs) in enumerate(checks)]
    return evaluate(policy, views, quality_retries_used=used)


ALL = [("government_id", "pass", []), ("face_match", "pass", []), ("liveness", "pass", []), ("email", "pass", [])]


def test_all_pass_approves():
    assert ev(*ALL).outcome == "approved"


@pytest.mark.parametrize("drop", ["government_id", "face_match", "liveness"])
def test_missing_identity_check_never_approves(drop):
    out = ev(*[c for c in ALL if c[0] != drop])
    assert out.outcome == "review_required" and "evidence.missing" in out.reason_codes


def test_missing_contact_only_requests_action():
    assert ev(*ALL[:3]).outcome == "action_required"


@pytest.mark.parametrize("check", ["government_id", "face_match", "liveness"])
@pytest.mark.parametrize("result", ["fail", "inconclusive"])
def test_contact_cannot_compensate(check, result):
    rows = [(t, result if t == check else r, rs) for t, r, rs in ALL]
    assert ev(*rows).outcome != "approved"


def test_error_is_never_fail():
    out = ev(("government_id", "error", ["provider.unavailable"]), *ALL[1:])
    assert out.outcome is None and out.session_state == "error"


def test_quality_retries_bounded():
    rows = [("government_id", "inconclusive", ["capture.low_quality"]), ("face_match", "not_run", []), *ALL[2:]]
    assert ev(*rows, used=0).outcome == "action_required"
    assert ev(*rows, used=2).outcome == "review_required"


def test_expired_document_retry_then_decline():
    rows = [("government_id", "fail", ["document.expired"]), *ALL[1:]]
    assert ev(*rows, used=0).outcome == "action_required"
    assert ev(*rows, used=2).outcome == "declined"


def test_latest_observation_wins_and_trace_deterministic():
    rows = [("liveness", "inconclusive", ["liveness.inconclusive"]), *ALL]
    a, b = ev(*rows), ev(*rows)
    assert a.outcome == "approved" and a.trace == b.trace


def test_policy_floor_and_schema():
    validate_definition(P)
    with pytest.raises(PolicyInvalid):
        validate_definition(dict(P, required_checks=["government_id", "email"]))
    with pytest.raises(PolicyInvalid):
        validate_definition(dict(P, uncertain_action="approved"))
    with pytest.raises(PolicyInvalid):
        validate_definition(dict(P, quality_retries=9))


def _registry():
    from vv.config import SERVICE_ROOT
    return CoverageRegistry(json.loads((SERVICE_ROOT / "config/coverage/registry.json").read_text()))


def test_registry_real_entries_default_disabled():
    reg = _registry()
    assert all(not e.enabled for e in reg.entries if e.provider != "dummy")
    assert all(e.country == "ZZ" for e in reg.entries if e.enabled)


def test_registry_resolution():
    reg = _registry()
    kw = dict(required_checks=P["required_checks"], use_case="workforce_onboarding", tenant_regions=["synthetic"],
              coverage_version="pilot_1")
    assert reg.resolve(country="ZZ", document_type="passport", environment="test", **kw).provider == "dummy"
    with pytest.raises(UnsupportedCapability):
        reg.resolve(country="ZZ", document_type="passport", environment="production", **kw)
    with pytest.raises(UnsupportedCapability):
        reg.resolve(country="GB", document_type="passport", environment="test", **kw)
    with pytest.raises(UnsupportedCapability):
        reg.resolve(country="ZZ", document_type="passport", environment="test", **(kw | {"coverage_version": "x"}))


def test_signature_roundtrip_and_tolerance():
    body = b'{"a":1}'
    sig = crypto.sign_webhook(b"s3cret", 1000, body)
    assert crypto.verify_webhook(b"s3cret", 1000, body, sig, now=1100)
    assert not crypto.verify_webhook(b"s3cret", 1000, body, sig, now=1400)
    assert not crypto.verify_webhook(b"s3cret", 1000, body + b" ", sig, now=1000)
    assert crypto.verify_webhook(b"s3cret", 1000, body, "v1=bad, " + sig, now=1000)  # rotation: any active secret


@pytest.mark.parametrize("ip", ["10.0.0.1", "172.16.0.1", "192.168.0.1", "127.0.0.1", "169.254.169.254", "0.0.0.0",
                                "::1", "fc00::1", "fe80::1", "::ffff:10.0.0.1", "100.64.0.1", "224.0.0.1"])
def test_non_public_addresses_rejected(ip):
    with pytest.raises(UnsafeDestination):
        validate_destination("https://h.example/x", lambda h, p: [ip])


def test_public_address_pinned():
    assert validate_destination("https://h.example:8443/x?y=1", lambda h, p: ["93.184.215.14"]) == (
        "h.example", 8443, "/x?y=1", "93.184.215.14")
