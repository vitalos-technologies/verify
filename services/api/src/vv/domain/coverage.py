"""Capability enablement matrix (VV-023). Unsupported requests are rejected before capture or charge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class UnsupportedCapability(Exception):
    def __init__(self, message: str, alternative: str | None = None) -> None:
        super().__init__(message)
        self.alternative = alternative


@dataclass(frozen=True)
class CoverageEntry:
    id: str
    country: str
    document_type: str
    provider: str
    checks: tuple[str, ...]
    processing_region: str
    use_cases: tuple[str, ...]
    enabled: bool
    alternative: str | None


class CoverageRegistry:
    DEFAULT_ALTERNATIVE = "Ask the requesting organisation for its alternative identity check route."

    def __init__(self, data: dict) -> None:
        self.version: str = data["registry_version"]
        self.providers: dict = data["providers"]
        self.entries = [
            CoverageEntry(
                id=e["id"], country=e["country"], document_type=e["document_type"], provider=e["provider"],
                checks=tuple(e["checks"]), processing_region=e["processing_region"],
                use_cases=tuple(e["use_cases"]), enabled=bool(e.get("enabled", False)),
                alternative=e.get("alternative"),
            )
            for e in data["entries"]
        ]

    @classmethod
    def load(cls, path: Path) -> CoverageRegistry:
        return cls(json.loads(path.read_text()))

    def resolve(self, *, country: str, document_type: str, required_checks: list[str], use_case: str,
                tenant_regions: list[str], environment: str, coverage_version: str) -> CoverageEntry:
        if coverage_version != self.version:
            raise UnsupportedCapability("Policy references a coverage version that is not active.")
        matches = [e for e in self.entries if e.country == country and e.document_type == document_type]
        if not matches:
            raise UnsupportedCapability("This country and document type are not supported.", self.DEFAULT_ALTERNATIVE)
        alternative = next((e.alternative for e in matches if e.alternative), self.DEFAULT_ALTERNATIVE)
        id_checks = {"government_id", "face_match", "liveness"}
        for entry in matches:
            provider = self.providers.get(entry.provider, {})
            if not entry.enabled:
                continue
            if environment not in provider.get("allowed_environments", []):
                continue
            if use_case not in entry.use_cases:
                continue
            if entry.processing_region not in tenant_regions:
                continue
            if not {c for c in required_checks if c in id_checks} <= set(entry.checks):
                continue
            return entry
        raise UnsupportedCapability(
            "This country, document type or processing region is not enabled for your organisation.", alternative)
