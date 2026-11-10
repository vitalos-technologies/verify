"""AT-01 cross-tenant isolation (VV-001): API, database row policies and queued work."""

from __future__ import annotations

import psycopg
import pytest
from conftest import APP_DSN, WORKER_DSN, applicant_ready, create_session, drain, idem, run_capture
from psycopg.rows import dict_row


def test_api_denies_cross_tenant_access_without_leakage(client, worker, make_tenant, settings):
    a, b = make_tenant("Tenant A"), make_tenant("Tenant B")
    created = create_session(client, a, ref="a-secret-ref")
    sid = created["session"]["id"]
    applicant_ready(client, created["hosted_url"], settings)
    run_capture(client, "liveness_inconclusive")
    drain(worker)

    r = client.get(f"/v1/verifications/{sid}", headers=b.headers)
    assert r.status_code == 404 and "a-secret-ref" not in r.text
    listing = client.get("/v1/verifications", headers=b.headers).json()
    assert all(i["id"] != sid for i in listing["items"])
    r = client.post(f"/v1/verifications/{sid}/decisions", headers={**b.headers, **idem()},
                    json={"expected_revision": 1, "outcome": "approved", "reason": "cross tenant attempt",
                          "method": "alternative_method", "evidence_ids": ["x"]})
    assert r.status_code == 404
    # Webhook replay of A's event using B's credential.
    ep = client.post("/v1/webhook-endpoints", headers=b.headers,
                     json={"url": "https://hooks.customer-b.example/vv", "events": ["verification.completed"]}).json()
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (a.id,))
        evt = conn.execute("SELECT id FROM outbox WHERE resource_id = %s LIMIT 1", (sid,)).fetchone()["id"]
    r = client.post("/v1/webhook-replays", headers={**b.headers, **idem()},
                    json={"event_id": evt, "endpoint_id": ep["id"]})
    assert r.status_code == 404
    # A still sees its own session.
    assert client.get(f"/v1/verifications/{sid}", headers=a.headers).status_code == 200


def test_tenant_id_in_body_is_not_authority(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    body = {"external_reference": "x", "policy_id": "workforce_identity", "policy_version": 1, "country": "ZZ",
            "document_type": "passport", "tenant_id": a.id}
    r = client.post("/v1/verifications", json=body, headers={**b.headers, **idem()})
    assert r.status_code == 400  # unknown fields rejected; tenant comes from the credential only


def test_row_level_security_for_runtime_roles(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    sid = create_session(client, a)["session"]["id"]
    with psycopg.connect(APP_DSN, row_factory=dict_row) as conn:
        # No tenant context: nothing visible.
        assert conn.execute("SELECT count(*) AS n FROM sessions").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM api_keys").fetchone()["n"] == 0
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (b.id,))
        assert conn.execute("SELECT count(*) AS n FROM sessions WHERE id = %s", (sid,)).fetchone()["n"] == 0
        assert conn.execute("UPDATE sessions SET state = 'approved' WHERE id = %s", (sid,)).rowcount == 0
        conn.commit()
        # Writing a row for another tenant is refused by WITH CHECK.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("INSERT INTO audit_events (tenant_id, id, actor_type, actor_id, action, object_type, "
                         "object_id) VALUES (%s, 'aud_x', 'test', 'test', 'x', 'x', 'x')", (a.id,))
        conn.rollback()
        conn.execute("SELECT set_config('app.tenant_id', %s, false)", (b.id,))
        # Composite foreign keys: B cannot reference A's policy row even by guessing its ID.
        pol_a = None
        with psycopg.connect(APP_DSN, row_factory=dict_row) as c2:
            c2.execute("SELECT set_config('app.tenant_id', %s, false)", (a.id,))
            pol_a = c2.execute("SELECT id, subject_id FROM sessions WHERE id = %s", (sid,)).fetchone()
            pol_row = c2.execute("SELECT policy_row_id FROM sessions WHERE id = %s", (sid,)).fetchone()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                "INSERT INTO sessions (tenant_id, id, subject_id, policy_row_id, policy_key, policy_version, "
                "external_reference, country, document_type, coverage_version, coverage_entry_id, provider, state, "
                "expires_at) VALUES (%s,'ver_x',%s,%s,'k',1,'r','ZZ','passport','pilot_1','e','dummy','created',now())",
                (b.id, pol_a["subject_id"], pol_row["policy_row_id"]))
        conn.rollback()


def test_runtime_roles_cannot_bypass_rls_or_mutate_append_only(make_tenant, client):
    a = make_tenant()
    create_session(client, a)
    for dsn in (APP_DSN, WORKER_DSN):
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            role = conn.execute("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()
            assert role == {"rolbypassrls": False, "rolsuper": False}
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
            conn.rollback()
            conn.execute("SELECT set_config('app.tenant_id', %s, false)", (a.id,))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("DELETE FROM audit_events")
            conn.rollback()


def test_worker_scan_cannot_read_other_tenant_domain_rows(client, make_tenant):
    a = make_tenant()
    create_session(client, a)
    with psycopg.connect(WORKER_DSN, row_factory=dict_row) as conn:
        # The worker can list queue rows but not identity-bearing domain tables without tenant context.
        assert conn.execute("SELECT count(*) AS n FROM outbox").fetchone()["n"] >= 1
        assert conn.execute("SELECT count(*) AS n FROM subjects").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM checks").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM sessions WHERE state = 'created' AND expires_at > now()"
                            ).fetchone()["n"] == 0
