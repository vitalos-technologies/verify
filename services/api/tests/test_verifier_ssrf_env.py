"""Verifier: SSRF variants with the real resolver, OTP races, non-prod gating of mocks."""
from __future__ import annotations

import threading
from dataclasses import replace

import pytest
from conftest import create_session
from fastapi.testclient import TestClient

from vv import webhooks
from vv.api.app import create_app
from vv.providers.dummy import DummyProvider

UNSAFE = [
    "https://2130706433/", "https://0177.0.0.1/", "https://0x7f.0.0.1/", "https://127.1/", "https://0/",
    "https://0.0.0.0/", "https://[::]/", "https://[::1]/", "https://[::ffff:127.0.0.1]/", "https://[::ffff:7f00:1]/",
    "https://[::127.0.0.1]/", "https://[fe80::1%25eth0]/", "https://[fc00::1]/", "https://100.64.0.1/",
    "https://169.254.169.254/", "https://localhost./", "https://LOCALHOST/", "https://192.0.0.8/",
    "https://198.18.0.1/", "https://[64:ff9b::7f00:1]/", "https://[64:ff9b::a9fe:a9fe]/", "https://[2002:7f00:1::]/",
    "https://[2001:db8::1]/", "https://224.0.0.1/", "https://255.255.255.255/",
]


@pytest.mark.parametrize("url", UNSAFE)
def test_ssrf_variants_real_resolver(url):
    try:
        out = webhooks.validate_destination(url, webhooks.default_resolver)
    except webhooks.UnsafeDestination:
        return
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"{url}: unexpected {type(exc).__name__}: {exc}")
    pytest.fail(f"ACCEPTED unsafe destination {url} -> {out}")


def test_malformed_urls_are_rejected_not_500(client, make_tenant):  # D4
    t = make_tenant()
    for url in ("https://hooks.customer-a.example:99999/x", "https://[::1/x"):
        r = client.post("/v1/webhook-endpoints", headers=t.headers, json={"url": url, "events": ["verification.created"]})
        assert r.status_code == 422, (url, r.status_code)


def test_otp_concurrent_bruteforce_capped(client, make_tenant, owner):
    t = make_tenant()
    c = create_session(client, t)
    token = c["hosted_url"].rsplit("/", 1)[1]
    assert client.post("/applicant/exchange", json={"token": token}).status_code == 200
    assert client.post("/applicant/contact/send",
                       json={"channel": "email", "destination": "brute@synthetic.example"}).status_code == 200
    code = client.app.state.vv.messenger.last_sent
    cookie = client.cookies.get("vv_applicant")
    guesses = [f"{i:06d}" for i in range(40) if f"{i:06d}" != code]
    res = []

    def go(g):
        with TestClient(client.app) as cc:
            cc.cookies.set("vv_applicant", cookie, path="/applicant")
            res.append(cc.post("/applicant/contact/verify", json={"code": g}).status_code)
    ths = [threading.Thread(target=go, args=(g,)) for g in guesses]
    [t_.start() for t_ in ths]
    [t_.join() for t_ in ths]
    fa = owner.execute("SELECT failed_attempts FROM contact_challenges WHERE session_id = %s",
                       (c["session"]["id"],)).fetchone()["failed_attempts"]
    print("failed_attempts after 40 concurrent guesses:", fa, set(res))
    assert fa == 5
    assert client.post("/applicant/contact/verify", json={"code": code}).status_code == 400


def test_contact_verify_after_decision_still_writes_check(client, worker, make_tenant, settings, owner):
    """D8: contact send/verify refused once the session is no longer active."""
    from conftest import applicant_ready, drain, run_capture
    t = make_tenant()
    c = create_session(client, t)
    applicant_ready(client, c["hosted_url"], settings)
    run_capture(client, "all_pass")
    drain(worker)
    # send blocked after terminal state
    r = client.post("/applicant/contact/send", json={"channel": "email", "destination": "late@synthetic.example"})
    assert r.status_code == 409
    assert client.post("/applicant/contact/verify", json={"code": "123456"}).status_code == 409


def test_staging_refuses_mocks(settings):
    st = replace(settings, environment="staging")
    with pytest.raises(RuntimeError):
        DummyProvider(None, b"x" * 32, "staging")
    with pytest.raises(RuntimeError):
        DummyProvider(None, b"x" * 32, "production")
    app = create_app(st, resolver=lambda h, p: ["93.184.215.14"])
    paths = {r.path for r in app.routes}
    assert "/dummy-provider/capture" not in paths and "/console/dev-login" not in paths
    assert app.state.vv.providers == {}
    assert app.state.vv.messenger is None  # D7: mock messenger not created outside dev/test/ci
    with TestClient(app) as c:
        assert c.post("/callbacks/dummy", content=b"{}").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_staging_load_settings_requires_keys(monkeypatch):
    from vv.config import load_settings
    monkeypatch.setenv("VV_ENV", "production")
    monkeypatch.setenv("VV_APP_DSN", "postgresql://x")
    for k in ("VV_DATA_KEY", "VV_HMAC_PEPPER", "VV_DUMMY_PROVIDER_SECRET"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError):
        load_settings()
