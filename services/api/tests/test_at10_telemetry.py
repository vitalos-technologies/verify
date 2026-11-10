"""AT-10 (partial): synthetic canaries never reach logs or error bodies."""

from __future__ import annotations

import logging

from conftest import applicant_ready, create_session, drain, run_capture

from vv.log import log

CANARY_EMAIL = "canary.zz.9f3a@synthetic.example"
CANARY_REF = "CANARY-REF-7781"


def test_flow_logs_contain_no_canaries_tokens_or_keys(client, worker, make_tenant, settings, caplog):
    caplog.set_level(logging.INFO, logger="vv")
    t = make_tenant()
    created = create_session(client, t, ref=CANARY_REF)
    token = created["hosted_url"].rsplit("/", 1)[1]
    applicant_ready(client, created["hosted_url"], settings, email=CANARY_EMAIL)
    code = client.app.state.vv.messenger.last_sent
    run_capture(client, "all_pass")
    drain(worker)
    client.post("/applicant/contact/verify", json={"code": "999999"})
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert text  # logging happened
    for canary in (CANARY_EMAIL, CANARY_REF, token, t.api_key, t.api_key.split("_", 3)[3], f'"{code}"'):
        assert canary not in text


def test_logger_drops_non_allowlisted_fields(caplog):
    caplog.set_level(logging.INFO, logger="vv")
    log("x", request_id="req_1", email=CANARY_EMAIL, document_number="123", raw_body="secret")
    msg = caplog.records[-1].getMessage()
    assert CANARY_EMAIL not in msg and "123" not in msg and "secret" not in msg
    assert "dropped_fields" in msg


def test_unexpected_errors_are_generic(client, make_tenant):
    t = make_tenant()
    r = client.get("/v1/verifications", params={"cursor": CANARY_REF}, headers=t.headers)
    assert r.status_code == 400 and CANARY_REF not in r.text
