"""Runtime configuration from environment variables. No secrets have defaults outside dev/test."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from pathlib import Path

ENVIRONMENTS = {"development", "test", "ci", "staging", "production"}
_NON_PROD = {"development", "test", "ci"}
SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    environment: str
    app_dsn: str
    worker_dsn: str
    owner_dsn: str | None
    data_key: bytes  # AES-256-GCM key sealing webhook secrets and idempotent responses
    hmac_pepper: bytes  # pepper for API-key / OTP / destination hashes
    dummy_provider_secret: bytes
    hosted_base_url: str
    coverage_path: Path
    hosted_token_ttl_seconds: int = 72 * 3600
    applicant_session_ttl_seconds: int = 2 * 3600
    console_idle_seconds: int = 30 * 60
    console_absolute_seconds: int = 12 * 3600
    api_rate_limit_per_minute: int = 600
    session_price_minor: int = 250  # hypothesis only (16_pricing); not an approved price
    extra: dict = field(default_factory=dict)

    @property
    def is_non_production(self) -> bool:
        return self.environment in _NON_PROD


def _key(name: str, environment: str, dev_fallback: bytes) -> bytes:
    raw = _env(name)
    if raw is None:
        if environment in _NON_PROD:
            return dev_fallback
        raise RuntimeError(f"{name} must be set outside development/test")
    key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    if len(key) < 32:
        raise RuntimeError(f"{name} must decode to at least 32 bytes")
    return key[:32]


def load_settings() -> Settings:
    environment = _env("VV_ENV", "development")
    if environment not in ENVIRONMENTS:
        raise RuntimeError(f"VV_ENV must be one of {sorted(ENVIRONMENTS)}")
    app_dsn = _env("VV_APP_DSN")
    worker_dsn = _env("VV_WORKER_DSN", app_dsn)
    if not app_dsn:
        raise RuntimeError("VV_APP_DSN is required")
    # Fixed, clearly-labelled development keys. Never valid outside development/test/ci.
    return Settings(
        environment=environment,
        app_dsn=app_dsn,
        worker_dsn=worker_dsn or app_dsn,
        owner_dsn=_env("VV_OWNER_DSN"),
        data_key=_key("VV_DATA_KEY", environment, b"dev-only-data-key-not-a-secret!!"),
        hmac_pepper=_key("VV_HMAC_PEPPER", environment, b"dev-only-hmac-pepper-not-secret!"),
        dummy_provider_secret=_key("VV_DUMMY_PROVIDER_SECRET", environment, b"dev-only-dummy-provider-secret!!"),
        hosted_base_url=_env("VV_HOSTED_BASE_URL", "http://localhost:8000") or "",
        coverage_path=Path(_env("VV_COVERAGE_PATH", str(SERVICE_ROOT / "config/coverage/registry.json")) or ""),
    )
