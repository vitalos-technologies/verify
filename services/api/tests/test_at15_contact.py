"""AT-15 OTP abuse controls (VV-015)."""

from __future__ import annotations

import threading

from conftest import create_session
from fastapi.testclient import TestClient

EMAIL = "otp.canary@synthetic.example"


def _exchange(client, t):
    created = create_session(client, t)
    token = created["hosted_url"].rsplit("/", 1)[1]
    assert client.post("/applicant/exchange", json={"token": token}).status_code == 200
    return created["session"]["id"]


def _send(client, dest=EMAIL):
    return client.post("/applicant/contact/send", json={"channel": "email", "destination": dest})


def test_single_use_code_and_wrong_attempt_lockout(client, make_tenant, owner):
    t = make_tenant()
    sid = _exchange(client, t)
    r = _send(client)
    assert r.status_code == 200 and r.json()["status"] == "sent_if_valid"
    code = client.app.state.vv.messenger.last_sent
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert client.post("/applicant/contact/verify", json={"code": wrong}).status_code == 400
    # Locked after 5 failures even with the right code.
    assert client.post("/applicant/contact/verify", json={"code": code}).status_code == 400
    # New code (after cooldown) works once.
    owner.execute("UPDATE contact_challenges SET created_at = created_at - interval '20 minutes' WHERE session_id = %s",
                  (sid,))
    assert _send(client).status_code == 200
    code = client.app.state.vv.messenger.last_sent
    r = client.post("/applicant/contact/verify", json={"code": code})
    assert r.status_code == 200 and "not proof of identity" in r.json()["note"]
    assert client.post("/applicant/contact/verify", json={"code": code}).status_code == 400  # reuse
    # Codes and destinations are stored only as keyed hashes.
    rows = owner.execute("SELECT * FROM contact_challenges WHERE session_id = %s", (sid,)).fetchall()
    assert all(code not in str(r) and EMAIL not in str(r) for r in rows)


def test_expired_code_rejected(client, make_tenant, owner):
    t = make_tenant()
    sid = _exchange(client, t)
    _send(client)
    code = client.app.state.vv.messenger.last_sent
    owner.execute("UPDATE contact_challenges SET expires_at = now() - interval '1 second' WHERE session_id = %s",
                  (sid,))
    r = client.post("/applicant/contact/verify", json={"code": code})
    assert r.status_code == 400 and r.json()["code"] == "code_invalid"


def test_cooldown_and_per_session_limits_under_concurrency(client, make_tenant, owner):
    t = make_tenant()
    _exchange(client, t)
    cookie = client.cookies.get("vv_applicant")
    results = []

    def go():
        with TestClient(client.app) as c:
            c.cookies.set("vv_applicant", cookie, path="/applicant")
            results.append(c.post("/applicant/contact/send", json={"channel": "email", "destination": EMAIL}))

    threads = [threading.Thread(target=go) for _ in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1 and codes.count(429) == 5
    assert all(r.headers.get("retry-after") for r in results if r.status_code == 429)


def test_per_destination_limit_is_silent_and_spend_cap_holds(client, make_tenant, owner):
    t = make_tenant(message_cap=7)
    sent_before = owner.execute("SELECT count(*) AS n FROM dummy_messages").fetchone()["n"]
    # Same destination across 6 sessions: only 5 messages are actually sent, responses identical.
    for _ in range(6):
        with TestClient(client.app) as c:
            _exchange(c, t)
            r = _send(c, "same.dest@synthetic.example")
            assert r.status_code == 200 and r.json()["status"] == "sent_if_valid"
    sent = owner.execute("SELECT count(*) AS n FROM dummy_messages").fetchone()["n"] - sent_before
    assert sent == 5
    # Spend cap: 7 messages/day. Two more distinct destinations reach it; the next is refused.
    for i in range(2):
        with TestClient(client.app) as c:
            _exchange(c, t)
            assert _send(c, f"other{i}@synthetic.example").status_code == 200
    with TestClient(client.app) as c:
        _exchange(c, t)
        r = _send(c, "late@synthetic.example")
        assert r.status_code == 503 and r.json()["code"] == "messaging_paused"
    n = owner.execute("SELECT count(*) AS n FROM usage_events WHERE tenant_id = %s AND charge_type = 'message'",
                      (t.id,)).fetchone()["n"]
    assert n == 7


def test_phone_channel_disabled_without_supplier(client, make_tenant):
    t = make_tenant()
    _exchange(client, t)
    r = client.post("/applicant/contact/send", json={"channel": "phone", "destination": "+447700900123"})
    assert r.status_code == 422


def test_contact_check_cannot_compensate_for_failed_identity(client, worker, make_tenant, settings):
    from conftest import applicant_ready, drain, run_capture
    t = make_tenant()
    created = create_session(client, t)
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "face_no_match")
    drain(worker)
    view = client.get(f"/v1/verifications/{created['session']['id']}", headers=t.headers).json()
    assert view["state"] == "review_required"
