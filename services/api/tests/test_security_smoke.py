"""The release security smoke test passes against this build (development mode)."""

from vv.security_smoke import run


def test_security_smoke_passes(client, make_tenant):
    a, b = make_tenant(), make_tenant()
    report = run(client, a.api_key, b.api_key, expect_dev_routes=True)
    assert report["passed"], [r for r in report["results"] if not r["pass"]]
    assert report["total"] >= 30
    assert a.api_key not in str(report)
