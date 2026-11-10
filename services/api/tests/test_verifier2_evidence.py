"""Independent verifier (AT-24 / VV-010): reveal, tokens, export, expiry, serving."""

from __future__ import annotations

import csv
import io
import time
from datetime import UTC, datetime

import psycopg
from conftest import OWNER_DSN, applicant_ready, create_session, drain, run_capture
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from vv import evidence
from vv.admin import add_member

PERIOD = datetime.now(UTC).strftime("%Y-%m")


def _browser(app, tenant_id, subject):
    c = TestClient(app)
    c.__enter__()
    r = c.post("/console/dev-login", json={"tenant_id": tenant_id, "user_subject": subject})
    c.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return c


def _member(t, role, tag=""):
    sub = f"v2{tag}-{role}-{t.id}@synthetic.example"
    with psycopg.connect(OWNER_DSN, row_factory=dict_row) as conn:
        mid = add_member(conn, t.id, sub, role)
    return sub, mid


def _case(client, worker, t, settings, scenario="all_pass", ref="v2-ev"):
    with TestClient(client.app) as b:
        c = create_session(b, t, ref=ref)
        applicant_ready(b, c["hosted_url"], settings, email=f"{ref.strip('=+-@')}.canary@synthetic.example")
        run_capture(b, scenario)
    drain(worker)
    return c["session"]["id"]


def test_reveal_requires_step_up(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    sid = _case(client, worker, t, settings, ref="v2-stepup")
    a = _browser(client.app, t.id, t.owner_subject)
    ev = a.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    owner.execute("UPDATE console_sessions SET auth_time = now() - interval '20 minutes' WHERE tenant_id = %s",
                  (t.id,))
    r = a.post(f"/console/evidence/{ev}/reveal", json={"reason": "Investigating applicant query"})
    assert r.status_code == 401 and r.json()["code"] == "step_up_required"
    a.__exit__(None, None, None)


def test_token_forgery_and_cross_tenant_replay(client, worker, make_tenant, settings, owner):
    t, u = make_tenant(), make_tenant()
    sid = _case(client, worker, t, settings, ref="v2-tok")
    a = _browser(client.app, t.id, t.owner_subject)
    x = _browser(client.app, u.id, u.owner_subject)
    ev = a.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    path = a.post(f"/console/evidence/{ev}/reveal", json={"reason": "Investigating applicant query"}).json()[
        "download_path"]
    token = path.split("token=")[1]
    eid, exp, sig = token.split(".")
    # Same token from a member of another tenant -> 403 (tenant is in the MAC)
    assert x.get(path).status_code == 403
    # Extend expiry without re-signing -> 403
    assert a.get(f"/console/evidence/download?token={eid}.{int(exp) + 3600}.{sig}").status_code == 403
    # Swap evidence id (other evidence of same case) -> 403
    other = [i["id"] for i in a.get(f"/console/verifications/{sid}/evidence").json()["items"] if i["id"] != ev][0]
    assert a.get(f"/console/evidence/download?token={other}.{exp}.{sig}").status_code == 403
    # Malformed tokens -> 403 not 500
    for bad in ("", "a.b", "a.b.c.d", "x.notint.y", ev + ".1." + "0" * 64):
        assert a.get("/console/evidence/download", params={"token": bad}).status_code == 403, bad
    # Same member, still valid: link is multi-use within its 5 minutes (each use audited)
    assert a.get(path).status_code == 200 and a.get(path).status_code == 200
    n = owner.execute("SELECT count(*) AS n FROM audit_events WHERE object_id = %s AND action = 'evidence.download'",
                      (ev,)).fetchone()["n"]
    assert n == 2
    # Expired token minted with the right key -> 403
    old = evidence._download_token(settings.data_key, t.id, ev, a.get("/console/me").json()["membership_id"],
                                   int(time.time()) - 1)
    assert a.get("/console/evidence/download", params={"token": old}).status_code == 403
    for c in (a, x):
        c.__exit__(None, None, None)


def test_served_evidence_headers(client, worker, make_tenant, settings):
    t = make_tenant()
    sid = _case(client, worker, t, settings, ref="v2-svg")
    a = _browser(client.app, t.id, t.owner_subject)
    ev = a.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    path = a.post(f"/console/evidence/{ev}/reveal", json={"reason": "Investigating applicant query"}).json()[
        "download_path"]
    r = a.get(path)
    print("download headers:", dict(r.headers))
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "script-src" not in r.headers["content-security-policy"]
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"
    a.__exit__(None, None, None)


def test_export_formula_injection_and_minimisation(client, worker, make_tenant, settings):
    t = make_tenant()
    refs = ["=HYPERLINK(\"http://x\")", "+1+1", "-2", "@SUM(A1)", "\t=1", " =1+1", "\n=1+1", "＝1+1"]
    for i, r in enumerate(refs):
        create_session(client, t, ref=r)
    _case(client, worker, t, settings, ref="v2-export-ok")
    a = _browser(client.app, t.id, t.owner_subject)
    body = a.get("/console/exports/verifications.csv", params={"period": PERIOD}).text
    rows = list(csv.reader(io.StringIO(body)))
    cells = {row[0] for row in rows[1:]}
    print("export first cells:", cells)
    for c in cells:
        assert c[:1] not in ("=", "+", "-", "@", "\t", "\r"), c
    assert "canary" not in body and "synthetic.example" not in body and "SYNTHETIC" not in body
    a.__exit__(None, None, None)


def test_expiry_respects_legal_hold(client, worker, make_tenant, settings, owner):
    t = make_tenant()
    ref = "v2-exp-hold"
    sid = _case(client, worker, t, settings, ref=ref)
    o = _browser(client.app, t.id, t.owner_subject)
    assert o.post("/console/legal-holds", json={"subject_id": ref, "owner": "privacy@synthetic.example",
                                                "reason": "Pending employment tribunal claim", "days": 30}
                  ).status_code == 201
    owner.execute("UPDATE evidence SET expires_at = now() - interval '1 second' WHERE session_id = %s", (sid,))
    evidence.expire(worker.db, worker.store)
    assert owner.execute("SELECT count(*) AS n FROM evidence WHERE session_id = %s AND deleted_at IS NULL",
                         (sid,)).fetchone()["n"] == 2
    owner.execute("UPDATE legal_holds SET released_at = now() WHERE tenant_id = %s", (t.id,))
    evidence.expire(worker.db, worker.store)
    rows = owner.execute("SELECT storage_key FROM evidence WHERE session_id = %s AND deleted_at IS NOT NULL",
                         (sid,)).fetchall()
    assert len(rows) == 2 and not any(worker.store.exists(r["storage_key"]) for r in rows)
    o.__exit__(None, None, None)


def test_reviewer_link_survives_lease_loss(client, worker, make_tenant, settings, owner):
    """Observation: a reviewer's link stays valid for its 5 minutes after their lease expires/is taken over."""
    t = make_tenant()
    sid = _case(client, worker, t, settings, "liveness_inconclusive", ref="v2-lease-ev")
    rs, _ = _member(t, "reviewer", "a")
    r = _browser(client.app, t.id, rs)
    review = next(i for i in r.get("/console/reviews").json()["items"] if i["session_id"] == sid)
    r.post(f"/console/reviews/{review['id']}/claim")
    ev = r.get(f"/console/verifications/{sid}/evidence").json()["items"][0]["id"]
    path = r.post(f"/console/evidence/{ev}/reveal", json={"reason": "Reviewing liveness frames"}).json()[
        "download_path"]
    owner.execute("UPDATE reviews SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (review["id"],))
    print("download after lease expiry:", r.get(path).status_code)
    r.__exit__(None, None, None)
