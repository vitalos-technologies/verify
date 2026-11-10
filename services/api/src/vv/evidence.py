"""Evidence objects (VV-010, VV-024): sealed private storage, purpose-bound reveal, receipts, expiry.

- Objects are AES-GCM sealed with a per-object AAD (tenant|evidence id) and never get public URLs.
- Reveal requires a permitted role, a stated reason and an active case assignment for reviewers;
  it returns a 5-minute, single-member, tenant-bound download token. Every reveal and download is audited.
- Default exports carry references and outcomes only, never images or document numbers.
- Expiry deletes objects after the retention deadline unless an appeal hold or legal hold applies.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import time
from pathlib import Path

from vv import crypto
from vv.db import Database
from vv.errors import ApiError, forbidden, not_found
from vv.ids import new_id
from vv.service import audit

RETENTION_DAYS = 30  # owner-approved Vitalos default (10 Nov 2026); each customer controller ratifies in its DPA
DOWNLOAD_TTL_SECONDS = 300
REVEAL_ROLES = {"owner", "administrator", "reviewer"}


class LocalSealedStore:
    """Development/CI object store on local disk. Production uses a private, KMS-encrypted bucket."""

    def __init__(self, root: Path, key: bytes) -> None:
        self.root = root
        self.key = key
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, storage_key: str) -> Path:
        safe = hashlib.sha256(storage_key.encode()).hexdigest()
        return self.root / safe[:2] / safe

    def put(self, storage_key: str, data: bytes, aad: bytes) -> None:
        p = self._path(storage_key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(crypto.seal(self.key, data, aad))
        os.replace(tmp, p)

    def get(self, storage_key: str, aad: bytes) -> bytes:
        return crypto.unseal(self.key, self._path(storage_key).read_bytes(), aad)

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).exists()


class S3SealedStore:
    """Production store: private bucket with SSE-KMS (infra/terraform/modules/evidence_storage) plus the same
    application-level AES-GCM seal, so a bucket-policy mistake alone never exposes plaintext."""

    def __init__(self, bucket: str, kms_key_id: str, key: bytes, client=None) -> None:
        if client is None:
            import boto3
            client = boto3.client("s3", region_name="eu-west-2")
        self.bucket, self.kms_key_id, self.key, self.s3 = bucket, kms_key_id, key, client

    def put(self, storage_key: str, data: bytes, aad: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=storage_key, Body=crypto.seal(self.key, data, aad),
                           ServerSideEncryption="aws:kms", SSEKMSKeyId=self.kms_key_id,
                           ContentType="application/octet-stream")

    def get(self, storage_key: str, aad: bytes) -> bytes:
        return crypto.unseal(self.key, self.s3.get_object(Bucket=self.bucket, Key=storage_key)["Body"].read(), aad)

    def delete(self, storage_key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=storage_key)

    def exists(self, storage_key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception as exc:  # botocore ClientError 404
            if getattr(exc, "response", {}).get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise


def make_store(settings):
    """S3 when VV_EVIDENCE_BUCKET is set, otherwise the local development store."""
    import os
    bucket = os.environ.get("VV_EVIDENCE_BUCKET")
    if bucket:
        return S3SealedStore(bucket, os.environ["VV_EVIDENCE_KMS_KEY_ID"], settings.data_key)
    if not settings.is_non_production:
        raise RuntimeError("VV_EVIDENCE_BUCKET is required outside development/test/ci")
    return LocalSealedStore(settings.evidence_dir, settings.data_key)


def _aad(tenant_id: str, evidence_id: str) -> bytes:
    return f"{tenant_id}|{evidence_id}".encode()


def store(conn, store_: LocalSealedStore, *, tenant_id: str, session_id: str, attempt_id: str, kind: str,
          data: bytes, content_type: str) -> str | None:
    if conn.execute("SELECT 1 FROM evidence WHERE tenant_id = %s AND attempt_id = %s AND kind = %s",
                    (tenant_id, attempt_id, kind)).fetchone():
        return None  # idempotent across duplicate provider events
    evidence_id = new_id("evd")
    key = f"{tenant_id}/{session_id}/{evidence_id}"
    store_.put(key, data, _aad(tenant_id, evidence_id))
    conn.execute("INSERT INTO evidence (tenant_id, id, session_id, attempt_id, kind, storage_key, digest, "
                 "content_type, size_bytes, expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, "
                 "now() + make_interval(days => %s))",
                 (tenant_id, evidence_id, session_id, attempt_id, kind, key, hashlib.sha256(data).hexdigest(),
                  content_type, len(data), RETENTION_DAYS))
    return evidence_id


def list_for_session(conn, tenant_id: str, session_id: str) -> list[dict]:
    return [{"id": r["id"], "kind": r["kind"], "available": r["deleted_at"] is None and not r["blocked"],
             "expires_at": r["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ")}
            for r in conn.execute(
                "SELECT e.*, s.evidence_access_blocked_at IS NOT NULL AS blocked FROM evidence e JOIN sessions s "
                "ON s.tenant_id = e.tenant_id AND s.id = e.session_id WHERE e.tenant_id = %s AND e.session_id = %s "
                "ORDER BY e.created_at", (tenant_id, session_id))]


def _download_token(secret: bytes, tenant_id: str, evidence_id: str, member: str, exp: int) -> str:
    sig = crypto.hmac_sha256_hex(secret, f"evd|{tenant_id}|{evidence_id}|{member}|{exp}".encode())
    return f"{evidence_id}.{exp}.{sig}"


def reveal(conn, *, secret: bytes, tenant_id: str, evidence_id: str, member: str, role: str, reason: str,
           request_id: str) -> dict:
    if role not in REVEAL_ROLES:
        raise forbidden("Your role cannot view identity evidence.")
    if len(reason.strip()) < 10:
        raise ApiError(400, "reason_required", "State why you need to view this evidence.")
    e = conn.execute("SELECT e.*, s.evidence_access_blocked_at FROM evidence e JOIN sessions s ON "
                     "s.tenant_id = e.tenant_id AND s.id = e.session_id WHERE e.tenant_id = %s AND e.id = %s",
                     (tenant_id, evidence_id)).fetchone()
    if e is None:
        raise not_found()
    if e["deleted_at"] is not None or e["evidence_access_blocked_at"] is not None:
        raise ApiError(410, "evidence_unavailable", "This evidence has been deleted or access is blocked.")
    if role == "reviewer":  # reviewers only for cases they hold (review lease or assigned appeal)
        assigned = conn.execute(
            "SELECT 1 FROM reviews WHERE tenant_id = %s AND session_id = %s AND assignee = %s AND status = 'claimed' "
            "AND lease_expires_at > now() UNION ALL SELECT 1 FROM appeals WHERE tenant_id = %s AND session_id = %s "
            "AND assignee = %s AND status = 'claimed'", (tenant_id, e["session_id"], member, tenant_id,
                                                         e["session_id"], member)).fetchone()
        if assigned is None:
            raise forbidden("Claim the case before viewing evidence.")
    audit(conn, tenant_id, "console", member, "evidence.reveal", "evidence", evidence_id, reason=reason.strip(),
          request_id=request_id)
    exp = int(time.time()) + DOWNLOAD_TTL_SECONDS
    token = _download_token(secret, tenant_id, evidence_id, member, exp)
    return {"download_path": f"/console/evidence/download?token={token}", "expires_in": DOWNLOAD_TTL_SECONDS}


def download(db: Database, store_: LocalSealedStore, *, secret: bytes, tenant_id: str, member: str, token: str,
             request_id: str) -> tuple[bytes, str]:
    try:
        evidence_id, exp_s, sig = token.split(".")
        exp = int(exp_s)
    except ValueError:
        raise forbidden("Link invalid.") from None
    expected = _download_token(secret, tenant_id, evidence_id, member, exp)
    if not crypto.constant_time_equal(expected, token) or exp < time.time():
        raise forbidden("Link invalid or expired.")
    with db.tenant_tx(tenant_id) as conn:
        e = conn.execute("SELECT e.*, s.evidence_access_blocked_at FROM evidence e JOIN sessions s ON "
                         "s.tenant_id = e.tenant_id AND s.id = e.session_id WHERE e.tenant_id = %s AND e.id = %s",
                         (tenant_id, evidence_id)).fetchone()
        if e is None or e["deleted_at"] is not None or e["evidence_access_blocked_at"] is not None:
            raise ApiError(410, "evidence_unavailable", "This evidence has been deleted or access is blocked.")
        audit(conn, tenant_id, "console", member, "evidence.download", "evidence", evidence_id, request_id=request_id)
    return store_.get(e["storage_key"], _aad(tenant_id, evidence_id)), e["content_type"]


def delete_for_sessions(conn, store_: LocalSealedStore, tenant_id: str, session_ids: list[str]) -> int:
    rows = list(conn.execute("SELECT id, storage_key FROM evidence WHERE tenant_id = %s AND session_id = ANY(%s) "
                             "AND deleted_at IS NULL", (tenant_id, session_ids)))
    for r in rows:
        store_.delete(r["storage_key"])
        conn.execute("UPDATE evidence SET deleted_at = now() WHERE tenant_id = %s AND id = %s", (tenant_id, r["id"]))
    return len(rows)


def expire(worker_db: Database, store_: LocalSealedStore, limit: int = 200) -> int:
    with worker_db.system_tx() as conn:
        rows = list(conn.execute("SELECT tenant_id, id FROM evidence WHERE deleted_at IS NULL AND expires_at < now() "
                                 "LIMIT %s", (limit,)))
    n = 0
    for r in rows:
        with worker_db.tenant_tx(r["tenant_id"]) as conn:
            e = conn.execute(
                "SELECT e.*, s.appeal_hold_until, s.subject_id FROM evidence e JOIN sessions s ON "
                "s.tenant_id = e.tenant_id AND s.id = e.session_id WHERE e.tenant_id = %s AND e.id = %s "
                "AND e.deleted_at IS NULL FOR UPDATE OF e", (r["tenant_id"], r["id"])).fetchone()
            if e is None:
                continue
            held = conn.execute(
                "SELECT (%s::timestamptz > now()) OR EXISTS (SELECT 1 FROM legal_holds WHERE tenant_id = %s AND "
                "subject_id = %s AND released_at IS NULL AND expires_at > now()) AS h",
                (e["appeal_hold_until"], r["tenant_id"], e["subject_id"])).fetchone()["h"]
            if held:
                continue
            store_.delete(e["storage_key"])
            conn.execute("UPDATE evidence SET deleted_at = now() WHERE tenant_id = %s AND id = %s",
                         (r["tenant_id"], r["id"]))
            n += 1
    return n


EXPORT_COLUMNS = ["case_reference", "verification_id", "state", "decision_revision", "decision_outcome",
                  "decision_method", "government_id", "face_match", "liveness", "email", "created_at",
                  "evidence_refs"]


def export_csv(conn, tenant_id: str, period: str) -> str:
    """Default export: outcomes and references only (no images, document numbers or contact details)."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(EXPORT_COLUMNS)
    rows = conn.execute(
        "SELECT s.*, d.revision, d.outcome, d.method FROM sessions s LEFT JOIN LATERAL (SELECT revision, outcome, "
        "method FROM decisions WHERE tenant_id = s.tenant_id AND session_id = s.id ORDER BY revision DESC LIMIT 1) d "
        "ON true WHERE s.tenant_id = %s AND to_char(s.created_at AT TIME ZONE 'UTC', 'YYYY-MM') = %s "
        "ORDER BY s.created_at", (tenant_id, period))
    from vv.service import latest_checks
    for s in rows:
        checks = {c["type"]: c["result"] for c in latest_checks(conn, tenant_id, s["id"])}
        refs = [e["id"] for e in conn.execute("SELECT id FROM evidence WHERE tenant_id = %s AND session_id = %s "
                                              "AND deleted_at IS NULL", (tenant_id, s["id"]))]
        w.writerow([_cell(s["external_reference"]), s["id"], s["state"], s["revision"] or "", s["outcome"] or "",
                    s["method"] or "", checks.get("government_id", ""), checks.get("face_match", ""),
                    checks.get("liveness", ""), checks.get("email", ""),
                    s["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"), " ".join(refs)])
    return out.getvalue()


def _cell(value: str) -> str:
    # Neutralise spreadsheet formula injection from customer-supplied references.
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value
