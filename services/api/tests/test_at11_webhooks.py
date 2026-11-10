"""AT-11 webhook retries, signatures, replay and SSRF (VV-011)."""

from __future__ import annotations

import json
import time

import jsonschema
from conftest import DNS, applicant_ready, create_session, drain, idem, run_capture

from vv import crypto
from vv.config import SERVICE_ROOT

WEBHOOK_SCHEMA = json.loads((SERVICE_ROOT.parent.parent / "docs/spec/contracts/webhook.schema.json").read_text())


def _endpoint(client, t, url="https://hooks.customer-a.example/vv", events=None):
    r = client.post("/v1/webhook-endpoints", headers=t.headers,
                    json={"url": url, "events": events or ["verification.completed", "verification.created"]})
    return r


def _verify(call, secret):
    ts = int(call["headers"]["X-Vitalos-Timestamp"])
    return crypto.verify_webhook(secret.encode(), ts, call["body"], call["headers"]["X-Vitalos-Signature"],
                                 now=int(time.time()))


def test_retry_after_500_keeps_event_id_and_resigns(client, worker, transport, make_tenant, settings, owner):
    t = make_tenant()
    ep = _endpoint(client, t).json()
    assert ep["signing_secret"].startswith("whsec_")
    sid = create_session(client, t)["session"]["id"]
    transport.script = [500]
    drain(worker, 1)
    assert len(transport.calls) == 1
    owner.execute("UPDATE webhook_deliveries SET next_attempt_at = now() WHERE tenant_id = %s", (t.id,))
    drain(worker, 1)
    assert len(transport.calls) == 2
    first, second = transport.calls
    assert first["headers"]["X-Vitalos-Event-Id"] == second["headers"]["X-Vitalos-Event-Id"]
    assert json.loads(first["body"])["id"] == json.loads(second["body"])["id"]
    assert _verify(first, ep["signing_secret"]) and _verify(second, ep["signing_secret"])
    assert not _verify(second, "whsec_wrong")
    env = json.loads(second["body"])
    jsonschema.validate(env, WEBHOOK_SCHEMA)
    assert env["resource_id"] == sid and env["type"] == "verification.created"
    assert first["ip"] == "93.184.215.14" and first["host"] == "hooks.customer-a.example"
    d = owner.execute("SELECT state, attempt FROM webhook_deliveries WHERE tenant_id = %s", (t.id,)).fetchone()
    assert d == {"state": "delivered", "attempt": 2}


def test_completed_event_carries_outcome_only(client, worker, transport, make_tenant, settings):
    t = make_tenant()
    _endpoint(client, t, events=["verification.completed"])
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings, email="hook.canary@synthetic.example")
    run_capture(client, "all_pass")
    drain(worker, 4)
    bodies = [json.loads(c["body"]) for c in transport.calls]
    completed = [b for b in bodies if b["type"] == "verification.completed"]
    assert len(completed) == 1
    assert completed[0]["data"] == {"state": "approved", "reason_codes": []}
    raw = b"".join(c["body"] for c in transport.calls)
    assert b"hook.canary" not in raw and b"passport" not in raw


def test_bounded_retries_then_failed(client, worker, transport, make_tenant, owner):
    t = make_tenant()
    _endpoint(client, t)
    create_session(client, t)
    transport.script = [503] * 20
    for _ in range(10):
        drain(worker, 1)
        owner.execute("UPDATE webhook_deliveries SET next_attempt_at = now() WHERE tenant_id = %s", (t.id,))
    d = owner.execute("SELECT state, attempt FROM webhook_deliveries WHERE tenant_id = %s", (t.id,)).fetchone()
    assert d == {"state": "failed", "attempt": 7}
    assert len(transport.calls) == 7


def test_manual_replay_reuses_event_id_and_is_audited(client, worker, transport, make_tenant, owner):
    t = make_tenant()
    ep = _endpoint(client, t).json()
    create_session(client, t)
    drain(worker, 1)
    evt = json.loads(transport.calls[0]["body"])["id"]
    r = client.post("/v1/webhook-replays", json={"event_id": evt, "endpoint_id": ep["id"]},
                    headers={**t.headers, **idem()})
    assert r.status_code == 202 and r.json()["state"] == "pending"
    drain(worker, 1)
    assert [json.loads(c["body"])["id"] for c in transport.calls] == [evt, evt]
    assert owner.execute("SELECT count(*) AS n FROM audit_events WHERE tenant_id = %s AND action = 'webhook.replay'",
                         (t.id,)).fetchone()["n"] == 1
    # Replay never creates a new charge.
    assert owner.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s", (t.id,)).fetchone()["n"] == 1


def test_ssrf_destinations_rejected(client, make_tenant):
    t = make_tenant()
    for url in ["https://private.customer.example/x", "https://metadata.customer.example/latest",
                "https://127.0.0.1/x", "https://[::1]/x", "https://10.1.2.3/x", "https://localhost/x",
                "https://user:pw@hooks.customer-a.example/x", "https://nxdomain.customer.example/x"]:
        r = _endpoint(client, t, url=url)
        assert r.status_code == 422, url
    assert _endpoint(client, t, url="http://hooks.customer-a.example/x").status_code == 400


def test_dns_rebinding_blocked_at_delivery(client, worker, transport, make_tenant, owner):
    t = make_tenant()
    assert _endpoint(client, t, url="https://rebind.customer.example/hook").status_code == 201
    DNS["rebind.customer.example"] = ["93.184.215.14", "192.168.1.10"]
    try:
        create_session(client, t)
        drain(worker, 1)
    finally:
        DNS["rebind.customer.example"] = ["93.184.215.14"]
    assert transport.calls == []
    d = owner.execute("SELECT state FROM webhook_deliveries WHERE tenant_id = %s", (t.id,)).fetchone()
    assert d["state"] == "blocked"
