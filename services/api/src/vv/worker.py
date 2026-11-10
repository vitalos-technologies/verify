"""Background worker: provider events, session expiry, outbox dispatch and webhook delivery.

Runs as the vv_worker database role. Queue rows are untrusted references: every job is
re-resolved against tenant and session state before acting.
"""

from __future__ import annotations

import signal
import time

from vv import deletion, events, webhooks
from vv.config import Settings, load_settings
from vv.db import Database
from vv.log import log
from vv.providers.base import ProviderAdapter
from vv.providers.dummy import DummyProvider


class Worker:
    def __init__(self, settings: Settings, *, resolver: webhooks.Resolver = webhooks.default_resolver,
                 transport: webhooks.Transport = webhooks.pinned_https_transport) -> None:
        self.settings = settings
        self.db = Database(settings.worker_dsn)
        self.providers: dict[str, ProviderAdapter] = {}
        if settings.is_non_production:
            self.providers["dummy"] = DummyProvider(self.db, settings.dummy_provider_secret, settings.environment)
        self.resolver = resolver
        self.transport = transport

    def run_once(self) -> dict[str, int]:
        return {
            "provider_events": events.process_due_events(self.db, self.providers),
            "expired": events.expire_sessions(self.db),
            "deletions": deletion.advance_deletions(self.db, self.providers),
            "dispatched": webhooks.dispatch_outbox(self.db),
            "deliveries": webhooks.deliver_due(self.db, self.settings.data_key, self.resolver, self.transport),
        }

    def close(self) -> None:
        self.db.close()


def main() -> None:
    worker = Worker(load_settings())
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log("worker.started", environment=worker.settings.environment)
    while not stopping:
        try:
            counts = worker.run_once()
            if any(counts.values()):
                log("worker.cycle", count=sum(counts.values()))
        except Exception as exc:  # noqa: BLE001 - keep the loop alive; details stay out of logs
            log("worker.cycle_failed", error_type=type(exc).__name__)
        time.sleep(1)
    worker.close()
