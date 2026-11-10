"""AT-24 export minimisation and VV-010 evidence access receipts; evidence expiry and deletion."""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, idem, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv.admin import add_member

PERIOD = datetime.now(UTC).strftime("%Y-%m")


def _browser(app, tenant_id, subject):
    c = TestClient(app)
    c.__enter__()
    r = c.post("/console/dev-login", json={"tenant_id": tenant_id, "user_subject": subject})
    c.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return c


def _member(t, role):
    sub = f"{role}-{t.id}@synthetic.example"
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        mid = add_member(conn, t.id, sub, role)
    return sub, mid


def _case(client, worker, t, settings, scenario="all_pass", ref="ev-ref"):
    with TestClient(client.app) as b:
        c = create_session(b, t, ref=ref)
        applicant_ready(b, c["hosted_url"], settings, email=f"{ref}.canary@synthetic.example")
        run_capture(b, scenario)
    drain(worker)
    return c["session"]["id"]


def test_evidence_stored_sealed_and_revealed_with_receipt(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid = _case(client, worker, t, settings)
    admin_sub, _ = _member(t, "administrator")
    a = _browser(client.app, t.id, admin_sub)
    items = a.get(f"/console/verifications/{sid}/evidence").json()["items"]
    assert sorted(i["kind"] for i in items) == ["document_front", "selfie"]
    # Stored object is sealed: plaintext marker absent on disk.
    row = owner.execute("SELECT storage_key FROM evidence WHERE id = %s", (items[0]["id"],)).fetchone()
    raw = client.app.state.vv.store._path(row["storage_key"]).read_bytes()
    assert b"SYNTHETIC" not in raw
    assert a.post(f"/console/evidence/{items[0]['id']}/reveal", json={"reason": "short"}).status_code == 400
    r = a.post(f"/console/evidence/{items[0]['id']}/reveal", json={"reason": "Checking document for appeal"})
    assert r.status_code == 200
    dl = a.get(r.json()["download_path"])
    assert dl.status_code == 200 and b"SYNTHETIC" in dl.content and dl.headers["cache-control"] == "no-store"
    acts = [x["action"] for x in owner.execute("SELECT action FROM audit_events WHERE object_id = %s ORDER BY "
                                               "created_at", (items[0]["id"],)).fetchall()]
    assert acts == ["evidence.reveal", "evidence.download"]
    a.__exit__(None, None, None)


def test_link_is_member_bound_expires_and_dies_on_revocation(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid = _case(client, worker, t, settings, ref="ev-2")
    admin_sub, admin_mid = _member(t, "administrator")
    dev_sub, _ = _member(t, "developer")
    a = _browser(client.app, t.id, admin_sub)
    d = _browser(client.app, t.id, dev_sub)
    ev = a.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    assert d.post(f"/console/evidence/{ev}/reveal", json={"reason": "Developer curiosity xx"}).status_code == 403
    path = a.post(f"/console/evidence/{ev}/reveal", json={"reason": "Investigating applicant query"}).json()[
        "download_path"]
    assert d.get(path).status_code == 403  # bound to the revealing member
    tampered = path[:-1] + ("0" if path[-1] != "0" else "1")
    assert a.get(tampered).status_code == 403
    # Revoke the admin: existing link stops working.
    o = _browser(client.app, t.id, t.owner_subject)
    assert o.post(f"/console/memberships/{admin_mid}/revoke", json={"reason": "left company"}).status_code == 200
    assert a.get(path).status_code == 401
    # Another tenant cannot use or see it.
    other = make_tenant()
    x = _browser(client.app, other.id, other.owner_subject)
    assert x.post(f"/console/evidence/{ev}/reveal", json={"reason": "cross tenant attempt"}).status_code == 404
    for c in (a, d, o, x):
        c.__exit__(None, None, None)


def test_reviewer_needs_claim_to_reveal(client, worker, make_tenant, settings):
    t = make_tenant()
    sid = _case(client, worker, t, settings, "liveness_inconclusive", ref="ev-3")
    rev_sub, _ = _member(t, "reviewer")
    r = _browser(client.app, t.id, rev_sub)
    ev = r.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    assert r.post(f"/console/evidence/{ev}/reveal", json={"reason": "Reviewing liveness"}).status_code == 403
    review = next(i for i in r.get("/console/reviews").json()["items"] if i["session_id"] == sid)
    r.post(f"/console/reviews/{review['id']}/claim")
    assert r.post(f"/console/evidence/{ev}/reveal", json={"reason": "Reviewing liveness"}).status_code == 200
    r.__exit__(None, None, None)


def test_default_export_minimised_and_audited(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    _case(client, worker, t, settings, ref="=HYPERLINK(1)")
    o = _browser(client.app, t.id, t.owner_subject)
    r = o.get("/console/exports/verifications.csv", params={"period": PERIOD})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    text = r.text
    assert "canary" not in text and "SYNTHETIC" not in text and "@" not in text
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["case_reference"] == "'=HYPERLINK(1)"  # formula injection neutralised
    assert rows[0]["decision_outcome"] == "approved" and rows[0]["liveness"] == "pass"
    assert len(rows[0]["evidence_refs"].split()) == 2
    assert owner.execute("SELECT count(*) AS n FROM audit_events WHERE tenant_id = %s AND action = "
                         "'export.verifications'", (t.id,)).fetchone()["n"] == 1
    o.__exit__(None, None, None)


def test_expiry_deletes_objects_unless_held(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    held = _case(client, worker, t, settings, "liveness_inconclusive", ref="ev-held")
    free = _case(client, worker, t, settings, ref="ev-free")
    owner.execute("UPDATE sessions SET appeal_hold_until = now() + interval '1 day' WHERE id = %s", (held,))
    owner.execute("UPDATE evidence SET expires_at = now() - interval '1 second' WHERE tenant_id = %s", (t.id,))
    drain(worker, 1)
    rows = {r["session_id"]: r for r in owner.execute(
        "SELECT session_id, bool_and(deleted_at IS NOT NULL) AS gone FROM evidence WHERE tenant_id = %s "
        "GROUP BY session_id", (t.id,)).fetchall()}
    assert rows[free]["gone"] is True and rows[held]["gone"] is False
    keys = [r["storage_key"] for r in owner.execute("SELECT storage_key FROM evidence WHERE session_id = %s",
                                                     (free,)).fetchall()]
    assert not any(client.app.state.vv.store.exists(k) for k in keys)


def test_subject_deletion_removes_objects(client, worker, make_tenant, settings, owner, caplog):
    caplog.set_level(logging.INFO, logger="vv")
    t = make_tenant()
    sid = _case(client, worker, t, settings, ref="ev-del")
    keys = [r["storage_key"] for r in owner.execute("SELECT storage_key FROM evidence WHERE session_id = %s",
                                                     (sid,)).fetchall()]
    assert all(client.app.state.vv.store.exists(k) for k in keys)
    client.post("/v1/deletions", headers={**t.headers, **idem()},
                json={"subject_id": "ev-del", "reason": "Erasure", "controller_authorisation_reference": "C-1"})
    drain(worker, 2)
    assert not any(client.app.state.vv.store.exists(k) for k in keys)
    assert "SYNTHETIC" not in "\n".join(r.getMessage() for r in caplog.records)


class _StubS3:
    def __init__(self):
        self.objects: dict[str, dict] = {}

    def put_object(self, **kw):
        self.objects[kw["Key"]] = kw

    def get_object(self, Bucket, Key):  # noqa: N803
        return {"Body": io.BytesIO(self.objects[Key]["Body"])}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop(Key, None)

    def head_object(self, Bucket, Key):  # noqa: N803
        if Key not in self.objects:
            err = Exception("404")
            err.response = {"Error": {"Code": "404"}}
            raise err


def test_s3_store_seals_and_requests_kms():
    from vv.evidence import S3SealedStore
    s3 = _StubS3()
    store = S3SealedStore("bucket", "kms-key", b"k" * 32, client=s3)
    store.put("t/s/e", b"SYNTHETIC", b"t|e")
    obj = s3.objects["t/s/e"]
    assert obj["ServerSideEncryption"] == "aws:kms" and obj["SSEKMSKeyId"] == "kms-key"
    assert b"SYNTHETIC" not in obj["Body"]
    assert store.get("t/s/e", b"t|e") == b"SYNTHETIC" and store.exists("t/s/e")
    store.delete("t/s/e")
    assert not store.exists("t/s/e")


def test_production_requires_bucket(settings, monkeypatch):
    from dataclasses import replace

    import pytest

    from vv.evidence import make_store
    monkeypatch.delenv("VV_EVIDENCE_BUCKET", raising=False)
    with pytest.raises(RuntimeError):
        make_store(replace(settings, environment="production"))
