"""Automated security smoke test for a running Verify stack (staging): run before and after every release
and before the external penetration test. Synthetic data only; needs two test-tenant API keys.

Checks: security headers, unauthenticated access, cross-tenant isolation, idempotency, unsupported scope,
SSRF on webhook URLs, forged provider callbacks, development routes, and error-body leakage.
Exit status is non-zero when any check fails. Output is a redacted JSON report (no keys or tokens).
"""

from __future__ import annotations

import json
import secrets
import sys

import httpx

BODY = {"policy_id": "workforce_identity", "policy_version": 1, "country": "ZZ", "document_type": "passport"}


def run(client: httpx.Client, key_a: str, key_b: str, *, expect_dev_routes: bool = False) -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"check": name, "pass": bool(ok), **({"detail": detail} if detail and not ok else {})})

    a = {"Authorization": f"Bearer {key_a}"}
    b = {"Authorization": f"Bearer {key_b}"}

    r = client.get("/healthz")
    for h, want in (("x-content-type-options", "nosniff"), ("referrer-policy", "no-referrer"),
                    ("cache-control", "no-store")):
        check(f"header {h}", r.headers.get(h) == want, str(r.headers.get(h)))
    check("header content-security-policy", "default-src 'none'" in r.headers.get("content-security-policy", ""))

    for method, path in (("GET", "/v1/verifications"), ("POST", "/v1/verifications"), ("GET", "/v1/deletions/x"),
                         ("POST", "/v1/webhook-endpoints"), ("GET", "/console/me"), ("GET", "/platform/operations")):
        check(f"unauthenticated {method} {path} denied", client.request(method, path).status_code in (401, 403))
    check("malformed bearer denied", client.get("/v1/verifications",
                                                headers={"Authorization": "Bearer vvk_test_x_y"}).status_code == 401)

    ref = f"smoke-{secrets.token_hex(4)}"
    key = f"smoke-{secrets.token_hex(8)}"
    ha = {**a, "Idempotency-Key": key}
    r1 = client.post("/v1/verifications", json={**BODY, "external_reference": ref}, headers=ha)
    r2 = client.post("/v1/verifications", json={**BODY, "external_reference": ref}, headers=ha)
    created = r1.status_code == 201
    check("create verification", created, str(r1.status_code))
    if created:
        sid = r1.json()["session"]["id"]
        check("idempotent replay returns same session", r2.status_code == 201 and r2.json()["session"]["id"] == sid)
        r3 = client.post("/v1/verifications", json={**BODY, "external_reference": ref + "x"},
                         headers={**a, "Idempotency-Key": key})
        check("idempotency key reuse with different body conflicts", r3.status_code == 409)
        cross = client.get(f"/v1/verifications/{sid}", headers=b)
        check("tenant B cannot read tenant A verification", cross.status_code == 404 and ref not in cross.text)
        listing = client.get("/v1/verifications", headers=b)
        check("tenant B listing excludes tenant A", listing.status_code == 200 and sid not in listing.text)
        dec = client.post(f"/v1/verifications/{sid}/decisions", headers={**b, "Idempotency-Key": f"x-{key}"},
                          json={"expected_revision": 1, "outcome": "approved", "reason": "cross tenant probe",
                                "method": "alternative_method", "evidence_ids": ["x"]})
        check("tenant B cannot decide tenant A case", dec.status_code in (403, 404))
        check("hosted URL not exposed on read", "hosted_url" not in client.get(f"/v1/verifications/{sid}",
                                                                               headers=a).text)
    unsup = client.post("/v1/verifications", json={**BODY, "country": "GB", "external_reference": ref + "-gb"},
                        headers={**a, "Idempotency-Key": f"g-{key}"})
    check("disabled country refused before capture (422)", unsup.status_code == 422)

    for url in ("https://127.0.0.1/x", "https://169.254.169.254/latest", "https://[::1]/x", "http://example.com/x",
                "https://localhost/x", "https://10.0.0.1/x", "https://user:pw@example.com/x"):
        r = client.post("/v1/webhook-endpoints", json={"url": url, "events": ["verification.completed"]}, headers=a)
        check(f"SSRF webhook URL refused: {url}", r.status_code in (400, 422), str(r.status_code))

    forged = client.post("/callbacks/dummy", content=b'{"event_id":"e","reference":"r"}',
                         headers={"X-Dummy-Timestamp": "1", "X-Dummy-Signature": "v1=00"})
    check("forged provider callback refused", forged.status_code in (401, 404))

    for path in ("/console/dev-login", "/platform/dev-login", "/dummy-provider/capture"):
        status = client.post(path, json={}).status_code
        if expect_dev_routes:
            check(f"dev route present (development): {path}", status != 404)
        else:
            check(f"dev route absent: {path}", status in (404, 405), str(status))
    check("openapi.json hidden outside development",
          expect_dev_routes or client.get("/openapi.json").status_code == 404)

    bad = client.get("/v1/verifications", params={"cursor": "<script>alert(1)</script>"}, headers=a)
    check("errors are generic (no reflection)", bad.status_code == 400 and "<script>" not in bad.text)

    failed = [r for r in results if not r["pass"]]
    return {"passed": not failed, "total": len(results), "failed": len(failed), "results": results}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os
    p = argparse.ArgumentParser(prog="vv-security-smoke")
    p.add_argument("--base-url", required=True)
    p.add_argument("--dev", action="store_true", help="target is a development stack (dev routes expected)")
    args = p.parse_args(argv)
    key_a, key_b = os.environ.get("VV_SMOKE_KEY_A"), os.environ.get("VV_SMOKE_KEY_B")
    if not key_a or not key_b:
        print("Set VV_SMOKE_KEY_A and VV_SMOKE_KEY_B (two test tenants).", file=sys.stderr)
        return 2
    with httpx.Client(base_url=args.base_url, timeout=15, follow_redirects=False) as c:
        report = run(c, key_a, key_b, expect_dev_routes=args.dev)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1
