"""Static guard-rail checks on the Terraform source (runs without Terraform or credentials).

Fails if a guard rail from 11_security/14_infrastructure is missing. Complements `terraform validate`.
"""
import pathlib
import re
import sys

root = pathlib.Path(__file__).parent
src = {p: p.read_text() for p in root.rglob("*.tf")}
allsrc = "\n".join(src.values())
rules = {
    "evidence public access fully blocked": all(f"{k} = true" in src[root / "modules/evidence_storage/main.tf"]
        or re.search(rf"{k}\s*=\s*true", src[root / "modules/evidence_storage/main.tf"])
        for k in ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets")),
    "evidence bucket denies non-TLS": '"aws:SecureTransport" = "false"' in allsrc,
    "evidence KMS encryption": 'sse_algorithm     = "aws:kms"' in allsrc,
    "no evidence replication": "aws_s3_bucket_replication_configuration" not in allsrc,
    "database not public": re.search(r"publicly_accessible\s*=\s*false", allsrc) is not None,
    "database encrypted": re.search(r"storage_encrypted\s*=\s*true", allsrc) is not None,
    "database backups 35 days": re.search(r"backup_retention_period\s*=\s*35", allsrc) is not None,
    "region pinned eu-west-2": 'region              = "eu-west-2"' in allsrc,
    "no wildcard IAM actions": re.search(r'Action\s*=\s*"\*"', allsrc) is None and '"*:*"' not in allsrc,
    "no long-lived access keys": "aws_iam_access_key" not in allsrc,
    "queues encrypted": allsrc.count("sqs_managed_sse_enabled   = true") + allsrc.count("sqs_managed_sse_enabled    = true") >= 2,
    "images by digest": "@sha256:" in allsrc,
    "budget alerts 50/80/100": "[50, 80, 100]" in allsrc,
}
failed = [k for k, ok in rules.items() if not ok]
for k, ok in rules.items():
    print(("PASS " if ok else "FAIL ") + k)
sys.exit(1 if failed else 0)
