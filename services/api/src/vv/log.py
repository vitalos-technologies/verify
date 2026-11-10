"""Structured allowlist logging. Fields not in the allowlist are dropped, never printed.

Logs carry correlation IDs, status and timings only: no document numbers, images,
tokens, contact details or raw payloads (05_architecture, AT-10).
"""

from __future__ import annotations

import json
import logging
import sys
import time

ALLOWED_FIELDS = frozenset({
    "request_id", "tenant_id", "session_id", "attempt_id", "event_id", "delivery_id", "endpoint_id",
    "provider", "state", "from_state", "to_state", "outcome", "status_code", "duration_ms", "method", "route",
    "error_type", "error_code", "count", "attempt", "operation", "reason_codes", "policy_version", "check_type",
    "result", "environment",
})

_logger = logging.getLogger("vv")
if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log(event: str, level: int = logging.INFO, **fields: object) -> None:
    safe = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}
    dropped = sorted(k for k in fields if k not in ALLOWED_FIELDS)
    record = {"ts": round(time.time(), 3), "event": event, **safe}
    if dropped:
        record["dropped_fields"] = dropped
    _logger.log(level, json.dumps(record, default=str))
