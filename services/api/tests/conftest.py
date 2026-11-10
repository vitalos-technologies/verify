"""Test harness: real PostgreSQL, runtime roles with RLS, synthetic data only."""

from __future__ import annotations

import os
from dataclasses import replace

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv import auth, service
from vv.admin import DEV_POLICY, add_member, create_tenant, set_runtime_passwords
from vv.api.app import create_app
from vv.config import load_settings
from vv.domain.coverage import CoverageRegistry
from vv.migrate import apply_migrations
from vv.webhooks import HttpResult
from vv.worker import Worker

OWNER_DSN = os.environ.get("VV_TEST_OWNER_DSN", "postgresql://vv_owner:vv_owner_local@localhost:5432/vv_test")
APP_DSN = os.environ.get("VV_TEST_APP_DSN", "postgresql://vv_app:vv_app_local@localhost:5432/vv_test")
WORKER_DSN = os.environ.get("VV_TEST_WORKER_DSN", "postgresql://vv_worker:vv_worker_local@localhost:5432/vv_test")

PUBLIC_IP = "93.184.215.14"
DNS = {
    "hooks.customer-a.example": [PUBLIC_IP],
    "hooks.customer-b.example": [PUBLIC_IP],
    "private.customer.example": ["10.0.0.5"],
    "metadata.customer.example": ["169.254.169.254"],
    "rebind.customer.example": [PUBLIC_IP],  # tests flip this to a private address after creation
}


def fake_resolver(host: str, port: int) -> list[str]:
    if host not in DNS:
        raise OSError("NXDOMAIN")
    return list(DNS[host])


class FakeTransport:
    """Records deliveries; returns scripted statuses (default 200)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.script: list[int] = []

    def __call__(self, host, port, path, ip, headers, body):
        self.calls.append({"host": host, "ip": ip, "path": path, "headers": headers, "body": body})
        return HttpResult(self.script.pop(0) if self.script else 200)


@pytest.fixture(scope="session")
def settings():
    os.environ.setdefault("VV_ENV", "test")
    os.environ["VV_APP_DSN"] = APP_DSN
    os.environ["VV_WORKER_DSN"] = WORKER_DSN
    with psycopg.connect(OWNER_DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
    apply_migrations(OWNER_DSN)
    set_runtime_passwords(OWNER_DSN, "vv_app_local", "vv_worker_local")
    return replace(load_settings(), environment="test", hosted_base_url="http://testserver")


@pytest.fixture(scope="session")
def app(settings):
    return create_app(settings, resolver=fake_resolver)


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def transport():
    return FakeTransport()


@pytest.fixture()
def worker(settings, transport):
    w = Worker(settings, resolver=fake_resolver, transport=transport)
    yield w
    w.close()


@pytest.fixture()
def owner():
    with psycopg.connect(OWNER_DSN, row_factory=dict_row, autocommit=True) as conn:
        yield conn


class TenantFixture:
    def __init__(self, tenant_id: str, api_key: str, owner_subject: str, owner_membership: str) -> None:
        self.id = tenant_id
        self.api_key = api_key
        self.owner_subject = owner_subject
        self.owner_membership = owner_membership

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


@pytest.fixture()
def make_tenant(settings):
    coverage = CoverageRegistry.load(settings.coverage_path)
    counter = {"n": 0}

    def _make(name: str = "Synthetic Tenant", *, policy: dict | None = None, scopes: list[str] | None = None,
              regions: list[str] | None = None, monthly_cap: int = 100, message_cap: int = 50) -> TenantFixture:
        counter["n"] += 1
        with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
            tid = create_tenant(conn, f"{name} {counter['n']}", regions=regions, monthly_cap=monthly_cap,
                                message_cap=message_cap)
            subject = f"owner-{tid}@synthetic.example"
            mid = add_member(conn, tid, subject, "owner")
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tid,))
            pol = policy or DEV_POLICY
            service.create_policy_draft(conn, tid, pol)
            service.publish_policy(conn, tid, pol["id"], pol["version"], coverage, 250)
            _, raw = auth.create_api_key(conn, settings.hmac_pepper, "test", tid, scopes or sorted(auth.API_SCOPES),
                                         "test", "pytest")
            conn.commit()
        return TenantFixture(tid, raw, subject, mid)

    return _make


_IDEM = {"n": 0}


def idem() -> dict[str, str]:
    _IDEM["n"] += 1
    return {"Idempotency-Key": f"idem-key-{os.getpid()}-{_IDEM['n']:06d}"}


def create_body(ref: str = "worker-ref-001", **over) -> dict:
    body = {"external_reference": ref, "policy_id": "workforce_identity", "policy_version": 1, "country": "ZZ",
            "document_type": "passport"}
    body.update(over)
    return body


def create_session(client, tenant: TenantFixture, **over) -> dict:
    r = client.post("/v1/verifications", json=create_body(**over), headers={**tenant.headers, **idem()})
    assert r.status_code == 201, r.text
    return r.json()


def applicant_ready(client, hosted_url: str, settings, email: str = "applicant.zz@synthetic.example") -> None:
    """Exchange the hosted token, acknowledge the notice and confirm email control."""
    token = hosted_url.rsplit("/", 1)[1]
    assert client.post("/applicant/exchange", json={"token": token}).status_code == 200
    assert client.post("/applicant/notice", json={"notice_version": "notice-synthetic-1"}).status_code == 200
    assert client.post("/applicant/contact/send", json={"channel": "email", "destination": email}).status_code == 200
    assert client.get("/applicant/session").status_code == 200
    code = client.app.state.vv.messenger.last_sent
    r = client.post("/applicant/contact/verify", json={"code": code})
    assert r.status_code == 200, r.text


def run_capture(client, scenario: str) -> dict:
    r = client.post("/applicant/attempts")
    assert r.status_code == 201, r.text
    att = r.json()
    r = client.post("/dummy-provider/capture", json={"capture_token": att["capture_token"], "scenario": scenario})
    assert r.status_code == 200, r.text
    r = client.post(f"/applicant/attempts/{att['attempt_id']}/submitted")
    assert r.status_code == 200, r.text
    return att


def drain(worker: Worker, rounds: int = 3) -> None:
    for _ in range(rounds):
        worker.run_once()
