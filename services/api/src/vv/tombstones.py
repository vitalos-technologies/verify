"""Tombstone log kept OUTSIDE the database backup (verifier finding D-A).

A backup taken before a deletion has no tombstone row, so replay after restore must read an
independent, durable log. Entries hold identifiers only (tenant, internal subject id, deletion id,
state): no names, references or contact data. Production writes to a separate S3 prefix with
object lock/versioning; development uses a local directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class LocalTombstoneLog:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def put(self, entry: dict) -> None:
        p = self.root / f"{entry['deletion_id']}.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, sort_keys=True))
        os.replace(tmp, p)

    def all(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self.root.glob("*.json"))]


class S3TombstoneLog:
    def __init__(self, bucket: str, prefix: str = "tombstones/", client=None) -> None:
        if client is None:
            import boto3
            client = boto3.client("s3", region_name="eu-west-2")
        self.bucket, self.prefix, self.s3 = bucket, prefix, client

    def put(self, entry: dict) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=f"{self.prefix}{entry['deletion_id']}.json",
                           Body=json.dumps(entry, sort_keys=True).encode(), ContentType="application/json")

    def all(self) -> list[dict]:
        out, token = [], None
        while True:
            kw = {"Bucket": self.bucket, "Prefix": self.prefix, **({"ContinuationToken": token} if token else {})}
            page = self.s3.list_objects_v2(**kw)
            for o in page.get("Contents", []):
                out.append(json.loads(self.s3.get_object(Bucket=self.bucket, Key=o["Key"])["Body"].read()))
            if not page.get("IsTruncated"):
                return out
            token = page["NextContinuationToken"]


def make_log(settings):
    bucket = os.environ.get("VV_TOMBSTONE_BUCKET")
    if bucket:
        return S3TombstoneLog(bucket)
    if not settings.is_non_production:
        raise RuntimeError("VV_TOMBSTONE_BUCKET is required outside development/test/ci")
    default = str(settings.evidence_dir.parent / ".tombstones-local")
    return LocalTombstoneLog(Path(os.environ.get("VV_TOMBSTONE_DIR", default)))
