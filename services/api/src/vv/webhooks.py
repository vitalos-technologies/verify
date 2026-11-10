"""Signed outbound webhooks with SSRF protection (VV-011, 26_API_contract_guide).

- Stable event ID across retries; fresh timestamp/signature per attempt.
- X-Vitalos-Signature: v1=hex(HMAC-SHA256(secret, f"{ts}." + raw_body)); X-Vitalos-Key-Id names the secret.
- Destination must be HTTPS and every resolved address public. The connection is pinned to the
  validated IP so a DNS rebind between check and connect cannot reach a private address.
- Redirects are never followed.
"""

from __future__ import annotations

import ipaddress
import json
import random
import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from http.client import HTTPSConnection
from urllib.parse import urlsplit

from vv import crypto
from vv.db import Database
from vv.errors import ApiError
from vv.ids import new_id
from vv.log import log

EVENT_TYPES = frozenset({"verification.created", "verification.processing", "verification.action_required",
                         "verification.review_required", "verification.completed", "verification.expired",
                         "verification.cancelled", "deletion.updated"})
RETRY_SCHEDULE = [0, 60, 300, 1800, 7200, 28800, 86400]  # seconds after previous attempt
MAX_ATTEMPTS = len(RETRY_SCHEDULE)

Resolver = Callable[[str, int], list[str]]


class UnsafeDestination(Exception):
    pass


def default_resolver(host: str, port: int) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast
                                   or addr.is_reserved or addr.is_unspecified)


def validate_destination(url: str, resolver: Resolver) -> tuple[str, int, str, str]:
    """Returns (host, port, path, pinned_ip) or raises UnsafeDestination."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise UnsafeDestination("HTTPS URL required")
    if parts.username or parts.password:
        raise UnsafeDestination("credentials in URL not allowed")
    host = parts.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".internal") or host.endswith(".local"):
        raise UnsafeDestination("internal hostname")
    port = parts.port or 443
    try:
        literal = ipaddress.ip_address(host)
        ips = [str(literal)]
    except ValueError:
        try:
            ips = resolver(host, port)
        except OSError:
            raise UnsafeDestination("hostname does not resolve") from None
    if not ips or not all(_is_public(ip) for ip in ips):
        raise UnsafeDestination("destination resolves to a non-public address")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return host, port, path, ips[0]


@dataclass
class HttpResult:
    status: int | None
    error: str | None = None


Transport = Callable[[str, int, str, str, dict[str, str], bytes], HttpResult]


def pinned_https_transport(host: str, port: int, path: str, ip: str, headers: dict[str, str],
                           body: bytes) -> HttpResult:
    class _Pinned(HTTPSConnection):
        def connect(self) -> None:
            sock = socket.create_connection((ip, port), timeout=self.timeout)
            self.sock = self._context.wrap_socket(sock, server_hostname=host)  # type: ignore[attr-defined]

    conn = _Pinned(host, port, timeout=10, context=ssl.create_default_context())
    try:
        conn.request("POST", path, body=body, headers={**headers, "Host": host})
        return HttpResult(conn.getresponse().status)
    except (OSError, ssl.SSLError) as exc:
        return HttpResult(None, type(exc).__name__)
    finally:
        conn.close()


# ------------------------------------------------------------------ endpoint management
def create_endpoint(conn, data_key: bytes, tenant_id: str, url: str, events: list[str], resolver: Resolver) -> dict:
    unknown = set(events) - EVENT_TYPES
    if unknown or not events:
        raise ApiError(400, "invalid_events", "Unknown or empty event types.")
    try:
        validate_destination(url, resolver)
    except UnsafeDestination as exc:
        raise ApiError(422, "unsafe_destination", f"Webhook URL rejected: {exc}.") from None
    endpoint_id = new_id("whe")
    secret = "whsec_" + crypto.random_token(32)
    secrets_doc = [{"kid": new_id("whk"), "secret": secret}]
    conn.execute("INSERT INTO webhook_endpoints (tenant_id, id, url, events, secrets_sealed) VALUES (%s,%s,%s,%s,%s)",
                 (tenant_id, endpoint_id, url, sorted(set(events)),
                  crypto.seal(data_key, json.dumps(secrets_doc).encode(), endpoint_id.encode())))
    return {"id": endpoint_id, "url": url, "signing_secret": secret}


def replay(conn, tenant_id: str, event_id: str, endpoint_id: str) -> dict:
    ev = conn.execute("SELECT id FROM outbox WHERE tenant_id = %s AND id = %s", (tenant_id, event_id)).fetchone()
    ep = conn.execute("SELECT id FROM webhook_endpoints WHERE tenant_id = %s AND id = %s",
                      (tenant_id, endpoint_id)).fetchone()
    if ev is None or ep is None:
        raise ApiError(404, "not_found", "Resource not found.")
    row = conn.execute(
        "INSERT INTO webhook_deliveries (tenant_id, id, event_id, endpoint_id) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (tenant_id, event_id, endpoint_id) DO UPDATE SET state = 'pending', next_attempt_at = now(), "
        "attempt = 0 RETURNING id, state", (tenant_id, new_id("whd"), event_id, endpoint_id)).fetchone()
    return {"id": row["id"], "state": row["state"]}


# ------------------------------------------------------------------ dispatcher + sender (worker)
def dispatch_outbox(worker_db: Database, limit: int = 100) -> int:
    with worker_db.system_tx() as conn:
        rows = list(conn.execute("SELECT tenant_id, id FROM outbox WHERE dispatched_at IS NULL ORDER BY created_at "
                                 "LIMIT %s", (limit,)))
    for r in rows:
        with worker_db.tenant_tx(r["tenant_id"]) as conn:
            ev = conn.execute("SELECT * FROM outbox WHERE tenant_id = %s AND id = %s AND dispatched_at IS NULL "
                              "FOR UPDATE SKIP LOCKED", (r["tenant_id"], r["id"])).fetchone()
            if ev is None:
                continue
            for ep in conn.execute("SELECT id FROM webhook_endpoints WHERE tenant_id = %s AND status = 'active' "
                                   "AND %s = ANY(events)", (r["tenant_id"], ev["event_type"])):
                conn.execute("INSERT INTO webhook_deliveries (tenant_id, id, event_id, endpoint_id) "
                             "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                             (r["tenant_id"], new_id("whd"), ev["id"], ep["id"]))
            conn.execute("UPDATE outbox SET dispatched_at = now() WHERE tenant_id = %s AND id = %s",
                         (r["tenant_id"], r["id"]))
    return len(rows)


def envelope(ev: dict) -> dict:
    return {"id": ev["id"], "type": ev["event_type"], "occurred_at": ev["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tenant_reference": ev["tenant_id"], "resource_id": ev["resource_id"],
            "resource_version": ev["resource_version"], "data": ev["payload"]}


def deliver_due(worker_db: Database, data_key: bytes, resolver: Resolver = default_resolver,
                transport: Transport = pinned_https_transport, limit: int = 50) -> int:
    with worker_db.system_tx() as conn:
        rows = list(conn.execute("SELECT tenant_id, id FROM webhook_deliveries WHERE state = 'pending' AND "
                                 "next_attempt_at <= now() ORDER BY next_attempt_at LIMIT %s", (limit,)))
    for r in rows:
        with worker_db.tenant_tx(r["tenant_id"]) as conn:
            d = conn.execute("SELECT * FROM webhook_deliveries WHERE tenant_id = %s AND id = %s AND state = 'pending' "
                             "FOR UPDATE SKIP LOCKED", (r["tenant_id"], r["id"])).fetchone()
            if d is None:
                continue
            ep = conn.execute("SELECT * FROM webhook_endpoints WHERE tenant_id = %s AND id = %s",
                              (r["tenant_id"], d["endpoint_id"])).fetchone()
            ev = conn.execute("SELECT * FROM outbox WHERE tenant_id = %s AND id = %s",
                              (r["tenant_id"], d["event_id"])).fetchone()
            attempt = d["attempt"] + 1
            try:
                host, port, path, ip = validate_destination(ep["url"], resolver)
            except UnsafeDestination:
                conn.execute("UPDATE webhook_deliveries SET state = 'blocked', attempt = %s, last_error = "
                             "'unsafe_destination' WHERE tenant_id = %s AND id = %s",
                             (attempt, r["tenant_id"], d["id"]))
                log("webhook.blocked", tenant_id=r["tenant_id"], delivery_id=d["id"], endpoint_id=ep["id"])
                continue
            secrets_doc = json.loads(crypto.unseal(data_key, bytes(ep["secrets_sealed"]), ep["id"].encode()))
            body = json.dumps(envelope(ev), separators=(",", ":")).encode()
            ts = int(time.time())
            headers = {"Content-Type": "application/json", "User-Agent": "VitalosVerify-Webhooks/1",
                       "X-Vitalos-Event-Id": ev["id"], "X-Vitalos-Timestamp": str(ts),
                       "X-Vitalos-Key-Id": secrets_doc[0]["kid"],
                       "X-Vitalos-Signature": ", ".join(crypto.sign_webhook(s["secret"].encode(), ts, body)
                                                        for s in secrets_doc)}
            result = transport(host, port, path, ip, headers, body)
            if result.status is not None and 200 <= result.status < 300:
                conn.execute("UPDATE webhook_deliveries SET state = 'delivered', attempt = %s, last_status = %s, "
                             "delivered_at = now(), last_error = NULL WHERE tenant_id = %s AND id = %s",
                             (attempt, result.status, r["tenant_id"], d["id"]))
            elif attempt >= MAX_ATTEMPTS:
                conn.execute("UPDATE webhook_deliveries SET state = 'failed', attempt = %s, last_status = %s, "
                             "last_error = %s WHERE tenant_id = %s AND id = %s",
                             (attempt, result.status, result.error, r["tenant_id"], d["id"]))
            else:
                delay = RETRY_SCHEDULE[attempt] * random.uniform(0.9, 1.1)  # noqa: S311 (jitter, not security)
                conn.execute("UPDATE webhook_deliveries SET attempt = %s, last_status = %s, last_error = %s, "
                             "next_attempt_at = now() + make_interval(secs => %s) WHERE tenant_id = %s AND id = %s",
                             (attempt, result.status, result.error, delay, r["tenant_id"], d["id"]))
            log("webhook.attempt", tenant_id=r["tenant_id"], delivery_id=d["id"], event_id=ev["id"],
                attempt=attempt, status_code=result.status)
    return len(rows)
