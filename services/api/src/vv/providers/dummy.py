"""DummyProvider: deterministic synthetic supplier for development and CI.

THIS IS NOT A REAL VERIFICATION PROVIDER. It never inspects images; outcomes come from
named synthetic scenarios. It is refused in staging/production by configuration.
Its "remote" state lives in dummy_provider_* tables to imitate an external system.
"""

from __future__ import annotations

import json
import time

from vv import crypto
from vv.db import Database
from vv.ids import new_id
from vv.providers.base import (
    AttemptHandle,
    EventRejected,
    Observation,
    ObservedCheck,
    ProviderEvent,
    ProviderUnavailable,
)

PROVIDER_VERSION = "dummy-1.0.0"
MODEL = "dummy-model-0"

P, F, INC, E = "pass", "fail", "inconclusive", "error"
SCENARIOS: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "all_pass": [("government_id", P, ()), ("face_match", P, ()), ("liveness", P, ())],
    "liveness_missing": [("government_id", P, ()), ("face_match", P, ())],
    "liveness_inconclusive": [("government_id", P, ()), ("face_match", P, ()),
                              ("liveness", INC, ("liveness.inconclusive",))],
    "liveness_attack": [("government_id", P, ()), ("face_match", P, ()),
                        ("liveness", F, ("liveness.suspected_attack",))],
    "liveness_fail": [("government_id", P, ()), ("face_match", P, ()), ("liveness", F, ("liveness.failed",))],
    "face_no_match": [("government_id", P, ()), ("face_match", F, ("face.no_match",)), ("liveness", P, ())],
    "document_expired": [("government_id", F, ("document.expired",)), ("face_match", P, ()), ("liveness", P, ())],
    "authenticity_failed": [("government_id", F, ("document.authenticity_failed",)), ("face_match", P, ()),
                            ("liveness", P, ())],
    "low_quality": [("government_id", INC, ("capture.low_quality",)), ("face_match", "not_run", ()),
                    ("liveness", P, ())],
    "provider_error": [("government_id", E, ("provider.unavailable",)), ("face_match", P, ()), ("liveness", P, ())],
}
OUTAGE_SCENARIO = "provider_outage"  # fetch_result raises ProviderUnavailable


def _specimen(label: str) -> bytes:
    """A synthetic placeholder image. Contains no person or document data."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200"><rect width="100%" height="100%" '
            f'fill="#eee"/><text x="16" y="104" font-family="sans-serif" font-size="16">{label}</text></svg>').encode()


class DummyProvider:
    name = "dummy"

    deletion_confirm_delay_seconds = 0  # tests raise this to simulate slow supplier deletion

    def __init__(self, db: Database, secret: bytes, environment: str) -> None:
        if environment not in {"development", "test", "ci"}:
            raise RuntimeError("DummyProvider is disabled outside development/test/ci")
        self.db = db
        self.secret = secret

    # -- adapter contract -------------------------------------------------
    def create_attempt(self, *, session_id: str, attempt_id: str, idempotency_key: str,
                       correlation_id: str) -> AttemptHandle:
        capture_token = "dmycap_" + crypto.random_token(24)
        with self.db.system_tx() as conn:
            row = conn.execute(
                "SELECT provider_reference FROM dummy_provider_attempts WHERE idempotency_key = %s",
                (idempotency_key,)).fetchone()
            if row:  # idempotent: rotate capture token for the same reference
                conn.execute("UPDATE dummy_provider_attempts SET capture_token_hash = %s WHERE provider_reference = %s",
                             (crypto.token_hash(capture_token), row["provider_reference"]))
                return AttemptHandle(row["provider_reference"], capture_token)
            reference = new_id("dmyref")
            conn.execute(
                "INSERT INTO dummy_provider_attempts (provider_reference, capture_token_hash, idempotency_key) "
                "VALUES (%s, %s, %s)", (reference, crypto.token_hash(capture_token), idempotency_key))
        return AttemptHandle(reference, capture_token)

    def authenticate_event(self, raw_body: bytes, headers: dict[str, str]) -> ProviderEvent:
        lowered = {k.lower(): v for k, v in headers.items()}
        sig = lowered.get("x-dummy-signature", "")
        ts_raw = lowered.get("x-dummy-timestamp", "")
        try:
            ts = int(ts_raw)
        except ValueError:
            raise EventRejected("missing timestamp") from None
        if not crypto.verify_webhook(self.secret, ts, raw_body, sig, now=int(time.time())):
            raise EventRejected("bad signature or stale timestamp")
        try:
            body = json.loads(raw_body)
            return ProviderEvent(event_id=str(body["event_id"]), provider_reference=str(body["reference"]))
        except (ValueError, KeyError, TypeError):
            raise EventRejected("malformed body") from None

    def fetch_result(self, provider_reference: str, *, correlation_id: str) -> Observation:
        with self.db.system_tx() as conn:
            row = conn.execute("SELECT * FROM dummy_provider_attempts WHERE provider_reference = %s",
                               (provider_reference,)).fetchone()
        if row is None:
            raise ProviderUnavailable("unknown reference")
        if row["scenario"] == OUTAGE_SCENARIO:
            raise ProviderUnavailable("simulated outage")
        if row["status"] != "completed":
            return Observation(f"obs_{provider_reference}_pending", provider_reference, "pending", PROVIDER_VERSION, ())
        checks = tuple(
            ObservedCheck(type=t, result=r, reasons=reasons, score=1.0 if r == P else 0.0,
                          score_type="dummy_fixed_0_1_uncalibrated", model_version=MODEL)
            for t, r, reasons in SCENARIOS[row["scenario"]]
        )
        evidence = (("document_front", _specimen("SYNTHETIC DOCUMENT SPECIMEN"), "image/svg+xml"),
                    ("selfie", _specimen("SYNTHETIC SELFIE PLACEHOLDER"), "image/svg+xml"))
        return Observation(f"obs_{provider_reference}", provider_reference, "completed", PROVIDER_VERSION, checks,
                           evidence)

    def request_deletion(self, provider_reference: str, *, correlation_id: str) -> str:
        with self.db.system_tx() as conn:
            conn.execute("UPDATE dummy_provider_attempts SET deletion_requested_at = coalesce(deletion_requested_at, "
                         "now()) WHERE provider_reference = %s", (provider_reference,))
        return f"dmydel_{provider_reference}"

    def deletion_confirmed(self, provider_reference: str, *, correlation_id: str) -> bool:
        with self.db.system_tx() as conn:
            row = conn.execute(
                "UPDATE dummy_provider_attempts SET status = 'deleted', scenario = NULL WHERE provider_reference = %s "
                "AND deletion_requested_at <= now() - make_interval(secs => %s) RETURNING status",
                (provider_reference, self.deletion_confirm_delay_seconds)).fetchone()
        return row is not None

    # -- simulated supplier-side behaviour (hosted capture + callback) -----
    def simulate_capture(self, capture_token: str, scenario: str) -> str:
        if scenario not in SCENARIOS and scenario != OUTAGE_SCENARIO:
            raise ValueError("unknown synthetic scenario")
        with self.db.system_tx() as conn:
            row = conn.execute(
                "UPDATE dummy_provider_attempts SET scenario = %s, status = 'completed', completed_at = now() "
                "WHERE capture_token_hash = %s AND status = 'awaiting_capture' RETURNING provider_reference",
                (scenario, crypto.token_hash(capture_token))).fetchone()
        if row is None:
            raise PermissionError("capture token invalid or already used")
        return row["provider_reference"]

    def build_callback(self, provider_reference: str, event_id: str | None = None,
                       timestamp: int | None = None) -> tuple[bytes, dict[str, str]]:
        body = json.dumps({"event_id": event_id or new_id("dmyevt"), "reference": provider_reference,
                           "type": "attempt.completed"}).encode()
        ts = int(time.time()) if timestamp is None else timestamp
        return body, {"X-Dummy-Timestamp": str(ts), "X-Dummy-Signature": crypto.sign_webhook(self.secret, ts, body),
                      "Content-Type": "application/json"}
