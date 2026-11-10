"""M03-T02 device handoff: same verification continues on a second device; token is one-use and short-lived."""

from __future__ import annotations

from conftest import create_session
from fastapi.testclient import TestClient


def test_handoff_continues_same_session_once(client, make_tenant, owner):
    t = make_tenant()
    created = create_session(client, t)
    client.post("/applicant/exchange", json={"token": created["hosted_url"].rsplit("/", 1)[1]})
    r = client.post("/applicant/handoff")
    assert r.status_code == 201
    token = r.json()["handoff_token"]
    with TestClient(client.app) as phone:
        r = phone.post("/applicant/handoff/exchange", json={"token": token})
        assert r.status_code == 200
        assert phone.post("/applicant/notice", json={"notice_version": "notice-synthetic-1"}).status_code == 200
    with TestClient(client.app) as thief:
        assert thief.post("/applicant/handoff/exchange", json={"token": token}).status_code == 404
    assert owner.execute("SELECT count(*) AS n FROM sessions WHERE tenant_id = %s", (t.id,)).fetchone()["n"] == 1
    # Notice acknowledged on the phone is visible on the original device: one shared server state.
    assert client.get("/applicant/session").json()["notice_acknowledged"] is True


def test_handoff_expiry_limits_and_requires_applicant_session(client, make_tenant, owner):
    t = make_tenant()
    with TestClient(client.app) as anon:
        assert anon.post("/applicant/handoff").status_code == 401
    created = create_session(client, t)
    client.post("/applicant/exchange", json={"token": created["hosted_url"].rsplit("/", 1)[1]})
    tokens = [client.post("/applicant/handoff").json()["handoff_token"] for _ in range(3)]
    assert client.post("/applicant/handoff").status_code == 429
    owner.execute("UPDATE applicant_handoffs SET expires_at = now() - interval '1 second' WHERE tenant_id = %s",
                  (t.id,))
    with TestClient(client.app) as phone:
        assert phone.post("/applicant/handoff/exchange", json={"token": tokens[0]}).status_code == 404
        assert phone.post("/applicant/handoff/exchange", json={"token": "h_forged"}).status_code == 404
        # A hosted (non-handoff) token is not accepted on the handoff route.
        assert phone.post("/applicant/handoff/exchange",
                          json={"token": created["hosted_url"].rsplit("/", 1)[1]}).status_code == 404
