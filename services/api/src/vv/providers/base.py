"""Provider adapter contract (08_provider_procurement.md). Real adapters must pass the same contract tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ProviderUnavailable(Exception):
    """Timeout/outage. Never an identity failure."""


class EventRejected(Exception):
    """Callback failed authentication or is malformed. Not acknowledged as authoritative."""


@dataclass(frozen=True)
class AttemptHandle:
    provider_reference: str
    capture_token: str  # restricted to this capture session only; never a provider secret


@dataclass(frozen=True)
class ProviderEvent:
    event_id: str
    provider_reference: str


@dataclass(frozen=True)
class ObservedCheck:
    type: str
    result: str
    reasons: tuple[str, ...]
    score: float | None = None
    score_type: str | None = None
    model_version: str | None = None


@dataclass(frozen=True)
class Observation:
    observation_id: str
    provider_reference: str
    status: str  # 'completed' | 'pending'
    provider_version: str
    checks: tuple[ObservedCheck, ...]


class ProviderAdapter(Protocol):
    name: str

    def create_attempt(self, *, session_id: str, attempt_id: str, idempotency_key: str,
                       correlation_id: str) -> AttemptHandle: ...

    def authenticate_event(self, raw_body: bytes, headers: dict[str, str]) -> ProviderEvent: ...

    def fetch_result(self, provider_reference: str, *, correlation_id: str) -> Observation: ...

    def request_deletion(self, provider_reference: str, *, correlation_id: str) -> str: ...
