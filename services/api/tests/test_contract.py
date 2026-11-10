"""Responses conform to docs/spec/contracts/openapi.json (implemented operations)."""

from __future__ import annotations

import json

import jsonschema
from conftest import applicant_ready, create_session, drain, idem, run_capture

from vv.config import SERVICE_ROOT

OPENAPI = json.loads((SERVICE_ROOT.parent.parent / "docs/spec/contracts/openapi.json").read_text())
IMPLEMENTED = {"createVerification", "listVerifications", "getVerification", "recordReviewDecision",
               "createWebhookEndpoint", "replayWebhook"}
NOT_YET = {"requestDeletion": "M05-T02", "getDeletion": "M05-T02"}


def check(instance, name):
    schema = {"$ref": f"#/components/schemas/{name}", "components": OPENAPI["components"]}
    jsonschema.validate(instance, schema, format_checker=jsonschema.FormatChecker())


def test_operation_inventory_is_explicit():
    ops = {op["operationId"] for path in OPENAPI["paths"].values() for op in path.values()}
    assert ops == IMPLEMENTED | set(NOT_YET)


def test_routes_exist_for_implemented_operations(app):
    paths = {(m, r.path) for r in app.routes for m in getattr(r, "methods", [])}
    for path, ops in OPENAPI["paths"].items():
        for method, op in ops.items():
            present = (method.upper(), path.replace("{id}", "{session_id}")) in paths
            assert present == (op["operationId"] in IMPLEMENTED), op["operationId"]


def test_payloads_match_schemas(client, worker, make_tenant, settings):
    t = make_tenant()
    created = create_session(client, t)
    check(created, "CreateSessionResponse")
    sid = created["session"]["id"]
    check(client.get(f"/v1/verifications/{sid}", headers=t.headers).json(), "Session")
    check(client.get("/v1/verifications", headers=t.headers).json(), "SessionList")
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "liveness_inconclusive")
    drain(worker)
    view = client.get(f"/v1/verifications/{sid}", headers=t.headers).json()
    check(view, "Session")
    r = client.post(f"/v1/verifications/{sid}/decisions", headers={**t.headers, **idem()},
                    json={"expected_revision": view["revision"], "outcome": "declined", "method": "evidence_review",
                          "reason": "Reviewer could not confirm", "evidence_ids": [view["checks"][0]["id"]]})
    check(r.json(), "Session")
    ep = client.post("/v1/webhook-endpoints", headers=t.headers,
                     json={"url": "https://hooks.customer-a.example/x", "events": ["verification.completed"]}).json()
    check(ep, "WebhookEndpoint")
    drain(worker, 1)
    evt = client.app.state.vv.db
    with evt.tenant_tx(t.id) as conn:
        event_id = conn.execute("SELECT id FROM outbox WHERE resource_id = %s ORDER BY created_at DESC LIMIT 1",
                                (sid,)).fetchone()["id"]
    r = client.post("/v1/webhook-replays", headers={**t.headers, **idem()},
                    json={"event_id": event_id, "endpoint_id": ep["id"]})
    check(r.json(), "Accepted")
    for bad in (client.get("/v1/verifications/ver_nope", headers=t.headers),
                client.get("/v1/verifications"),
                client.post("/v1/verifications", json={"nope": 1}, headers={**t.headers, **idem()})):
        check(bad.json(), "Error")


def test_dev_only_routes_not_exposed_by_default(client):
    assert client.get("/dev/last-contact-code").status_code == 404
