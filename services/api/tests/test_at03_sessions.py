"""AT-03 creation idempotency and session/link expiry (VV-003); AT-23 unsupported scope (VV-023)."""

from __future__ import annotations

import threading

from conftest import create_body, create_session, drain
from fastapi.testclient import TestClient


def test_concurrent_identical_creates_return_one_session_and_one_reservation(client, make_tenant, owner):
    t = make_tenant()
    headers = {**t.headers, "Idempotency-Key": "concurrent-key-0001"}
    results: list = []

    def go():
        with TestClient(client.app) as c:
            results.append(c.post("/v1/verifications", json=create_body("conc-1"), headers=headers))

    threads = [threading.Thread(target=go) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert {r.status_code for r in results} == {201}
    assert len({r.json()["session"]["id"] for r in results}) == 1
    assert len({r.json()["hosted_url"] for r in results}) == 1
    n = owner.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s AND charge_type = 'reservation'",
                      (t.id,)).fetchone()["n"]
    assert n == 1
    # Same key, different body -> conflict.
    r = client.post("/v1/verifications", json=create_body("conc-2"), headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "idempotency_key_reused"
    # Missing key -> 400.
    assert client.post("/v1/verifications", json=create_body(), headers=t.headers).status_code == 400
    # Keys are scoped per tenant: another tenant may use the same key value.
    other = make_tenant()
    r = client.post("/v1/verifications", json=create_body("conc-1"),
                    headers={**other.headers, "Idempotency-Key": "concurrent-key-0001"})
    assert r.status_code == 201
    # The stored response is sealed: the hosted token is not stored in plaintext.
    token = results[0].json()["hosted_url"].rsplit("/", 1)[1]
    row = owner.execute("SELECT response_sealed FROM idempotency_keys WHERE key = 'concurrent-key-0001' AND "
                        "tenant_id = %s", (t.id,)).fetchone()
    assert token.encode() not in bytes(row["response_sealed"])


def test_hosted_link_is_one_use_and_not_exposed_in_reads(client, make_tenant):
    t = make_tenant()
    created = create_session(client, t)
    token = created["hosted_url"].rsplit("/", 1)[1]
    read = client.get(f"/v1/verifications/{created['session']['id']}", headers=t.headers)
    assert token not in read.text and "hosted_url" not in read.json()
    assert client.post("/applicant/exchange", json={"token": token}).status_code == 200
    with TestClient(client.app) as thief:
        r = thief.post("/applicant/exchange", json={"token": token})
        assert r.status_code == 404 and r.json()["code"] == "link_invalid"
        assert thief.get("/applicant/session").status_code == 401


def test_cookie_scoped_and_hardened(client, make_tenant):
    t = make_tenant()
    created = create_session(client, t)
    r = client.post("/applicant/exchange", json={"token": created["hosted_url"].rsplit("/", 1)[1]})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/applicant" in cookie
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_expired_link_and_session_expiry_release_reservation(client, worker, make_tenant, owner):
    t = make_tenant()
    created = create_session(client, t)
    sid = created["session"]["id"]
    owner.execute("UPDATE sessions SET expires_at = now() - interval '1 second', hosted_token_expires_at = now() - "
                  "interval '1 second' WHERE id = %s", (sid,))
    r = client.post("/applicant/exchange", json={"token": created["hosted_url"].rsplit("/", 1)[1]})
    assert r.status_code == 404
    drain(worker, 1)
    view = client.get(f"/v1/verifications/{sid}", headers=t.headers).json()
    assert view["state"] == "expired"
    rows = owner.execute("SELECT charge_type, amount_minor FROM usage_events WHERE session_id = %s ORDER BY "
                         "created_at", (sid,)).fetchall()
    assert [(r["charge_type"], r["amount_minor"]) for r in rows] == [("reservation", 250),
                                                                    ("reservation_release", -250)]
    ev = owner.execute("SELECT event_type FROM outbox WHERE resource_id = %s ORDER BY created_at", (sid,)).fetchall()
    assert [e["event_type"] for e in ev] == ["verification.created", "verification.expired"]


def test_monthly_cap_enforced_under_concurrency(client, make_tenant, owner):
    t = make_tenant(monthly_cap=3)
    results: list = []

    def go(i):
        with TestClient(client.app) as c:
            results.append(c.post("/v1/verifications", json=create_body(f"cap-{i}"),
                                  headers={**t.headers, "Idempotency-Key": f"cap-key-{i:08d}"}))

    threads = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 3 and codes.count(429) == 5
    assert owner.execute("SELECT count(*) AS n FROM sessions WHERE tenant_id = %s", (t.id,)).fetchone()["n"] == 3


def test_list_pagination_cursor(client, make_tenant):
    t = make_tenant()
    ids = [create_session(client, t, ref=f"page-{i}")["session"]["id"] for i in range(5)]
    seen, cursor = [], None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = client.get("/v1/verifications", params=params, headers=t.headers).json()
        seen += [i["id"] for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(ids))
    assert client.get("/v1/verifications", params={"limit": 101}, headers=t.headers).status_code == 400
    assert client.get("/v1/verifications", params={"cursor": "garbage!"}, headers=t.headers).status_code == 400


def test_unsupported_scope_rejected_before_capture_or_charge(client, make_tenant, owner):  # AT-23
    t = make_tenant()
    for body in (create_body(country="GB"), create_body(country="IE"), create_body(document_type="id_card"),
                 create_body(country="FR")):
        r = client.post("/v1/verifications", json=body, headers={**t.headers, "Idempotency-Key": f"unsup-{body}"[:64]})
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "policy.unsupported_region"
        assert "Alternative:" in r.json()["message"]
    # Tenant whose region policy excludes the provider's processing region.
    uk_only = make_tenant(regions=["uk"])
    r = client.post("/v1/verifications", json=create_body(),
                    headers={**uk_only.headers, "Idempotency-Key": "uk-only-1"})
    assert r.status_code == 422
    for tid in (t.id, uk_only.id):
        assert owner.execute("SELECT count(*) AS n FROM sessions WHERE tenant_id = %s", (tid,)).fetchone()["n"] == 0
        assert owner.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s", (tid,)).fetchone()["n"] == 0
    # Unpublished policy version.
    r = client.post("/v1/verifications", json=create_body(policy_version=9), headers={**t.headers,
                    "Idempotency-Key": "unpub-0001"})
    assert r.status_code == 422 and r.json()["code"] == "policy.not_published"
