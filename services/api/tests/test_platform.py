"""Platform administration and operations APIs: separate sign-in, role separation, metadata only."""

from __future__ import annotations

from conftest import applicant_ready, create_session, drain, run_capture
from fastapi.testclient import TestClient


def _op(owner, subject, role):
    owner.execute("INSERT INTO platform_operators (id, subject, display_name, role) VALUES (%s,%s,%s,%s) "
                  "ON CONFLICT (subject) DO NOTHING", (f"pop_{role}_{abs(hash(subject))}", subject, role.title(), role))


def _login(app, subject):
    c = TestClient(app)
    c.__enter__()
    assert c.post("/platform/dev-login", json={"tenant_id": "-", "user_subject": subject}).status_code == 200
    return c


def test_admin_sees_metadata_only(client, worker, make_tenant, settings, owner):
    t = make_tenant("Platform View")
    created = create_session(client, t, ref="PLATFORM-CANARY-REF")
    applicant_ready(client, created["hosted_url"], settings, email="platform.canary@synthetic.example")
    run_capture(client, "all_pass")
    drain(worker)
    _op(owner, "padmin@synthetic.example", "platform_admin")
    a = _login(client.app, "padmin@synthetic.example")
    r = a.get("/platform/organisations")
    assert r.status_code == 200
    org = next(i for i in r.json()["items"] if i["id"] == t.id)
    assert org["monthly_usage"] >= 1 and org["monthly_completed"] >= 1
    assert {c["key"]: c["enabled"] for c in org["capabilities"]}["government_id"] is True
    assert "PLATFORM-CANARY-REF" not in r.text and "canary" not in r.text
    act = a.get(f"/platform/organisations/{t.id}/activity").json()["items"]
    assert all(set(x) == {"action", "actor_type", "at"} for x in act)
    ops = a.get("/platform/operations").json()
    assert [q["key"] for q in ops["queues"]] == ["identity_checks", "provider_callbacks", "customer_webhooks",
                                                 "evidence_deletion"]
    assert any(p["provider"] == "dummy" and "mock" in p["label"] for p in ops["providers"])
    a.__exit__(None, None, None)


def test_role_separation_and_no_tenant_crossover(client, make_tenant, owner):
    _op(owner, "ops1@synthetic.example", "operations")
    o = _login(client.app, "ops1@synthetic.example")
    assert o.get("/platform/operations").status_code == 200
    assert o.get("/platform/organisations").status_code == 403
    o.__exit__(None, None, None)
    t = make_tenant()
    with TestClient(client.app) as c:
        c.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject})
        assert c.get("/platform/organisations").status_code == 401  # customer session is not platform access
        r = c.post("/platform/dev-login", json={"tenant_id": "-", "user_subject": t.owner_subject})
        assert r.status_code == 401


def test_console_stats_and_create(client, make_tenant):
    t = make_tenant()
    with TestClient(client.app) as c:
        login = c.post("/console/dev-login", json={"tenant_id": t.id, "user_subject": t.owner_subject})
        csrf = login.json()["csrf_token"]
        body = {"external_reference": "console-1", "policy_id": "workforce_identity", "policy_version": 1,
                "country": "ZZ", "document_type": "passport"}
        h = {"X-CSRF-Token": csrf, "Idempotency-Key": "console-key-1"}
        r = c.post("/console/verifications", json=body, headers=h)
        assert r.status_code == 201 and r.json()["hosted_url"].startswith("http://testserver/v/")
        no_csrf = c.post("/console/verifications", json=body, headers={"Idempotency-Key": "console-key-2"})
        assert no_csrf.status_code == 403
        assert c.get("/console/stats").json()["total"] == 1
