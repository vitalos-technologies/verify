# Vitalos Verify

Multi-tenant identity-verification platform (pre-pilot prototype).

**Status:** synthetic-data prototype covering parts of M02–M04. No real supplier is integrated; the only enabled provider is the **DummyProvider (a mock)**, and the only enabled "country" is the synthetic code `ZZ`. Nothing is deployed and no real identity data has been processed. See [`delivery/status.json`](delivery/status.json) for evidence-based task status.

- Specification pack (canonical): [`docs/spec/README.md`](docs/spec/README.md)
- Agent/engineering rules: [`AGENTS.md`](AGENTS.md)
- Implementation decisions: [`docs/decisions.md`](docs/decisions.md)

## What exists

| Area | Requirement | State |
|---|---|---|
| Tenancy, roles, scoped API keys, revocation; OIDC + PKCE sign-in with MFA and step-up | VV-001, VV-002 | Implemented (fake IdP in tests; IdP not chosen) |
| PostgreSQL isolation: composite keys, row-level security, non-owner runtime roles | VV-001 | Implemented |
| Sessions: idempotent create, expiry, one-use link, QR device handoff | VV-003 | Implemented |
| Coverage matrix (real entries disabled), 422 before capture/charge | VV-023 | Implemented |
| Applicant web journey + accessibility tests | VV-004 | Implemented (dummy capture; manual device/screen-reader tests outstanding) |
| Email contact codes with abuse and spend limits | VV-015 | Implemented (dummy messenger) |
| Provider adapter, authenticated callbacks, authoritative fetch | VV-005, VV-006 | Dummy provider only |
| Versioned policies, fixture replay, decision traces | VV-007 | Implemented |
| Review queue, leases, second review, appeals; console UI | VV-008 | Implemented |
| Deletion lifecycle, legal holds, tombstone replay | VV-009 | Implemented (backup expiry is a tracked clock) |
| Sealed evidence, purpose-bound reveal receipts, minimal exports | VV-010, VV-024 | Implemented (local store; S3 adapter pending) |
| Signed webhooks, retries, replay, SSRF protection | VV-011 | Implemented |
| Usage ledger, credits, invoices, supplier reconciliation | VV-012 | Implemented (hypothesis prices) |
| Workforce client (verification, tenant binding, ordering) | VV-013 | Client only; not wired into Workforce |
| Recovery exercise (isolated restore, tombstones, RTO) | VV-014 | Synthetic exercise; no production infra |
| Terraform baseline (staging) | M02-T04 | Code + CI validation; never applied |

## Run locally

Needs PostgreSQL 16, Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d postgres
```

```bash
cp .env.example .env
```

```bash
./scripts/dev.sh --seed
```

`--seed` prints a synthetic tenant and an API key (shown once). Then:

```bash
curl -s -X POST localhost:8000/v1/verifications -H "Authorization: Bearer $KEY" -H "Idempotency-Key: demo-0001" \
  -H 'Content-Type: application/json' \
  -d '{"external_reference":"worker-1","policy_id":"workforce_identity","policy_version":1,"country":"ZZ","document_type":"passport"}'
```

Applicant web app (separate terminal):

```bash
cd apps/web && npm install && VV_ENABLE_DUMMY_PROVIDER=1 npm run dev
```

Open the `hosted_url` from the create response, replacing `localhost:8000` with `localhost:3000`
(set `VV_HOSTED_BASE_URL=http://localhost:3000` in `.env` to get the right link directly).

## Test

```bash
cd services/api && uv run pytest
```

Browser tests (start their own isolated API, worker and web server on `vv_e2e`):

```bash
cd apps/web && npm run build:e2e && npm run test:e2e
```

Tests use a real PostgreSQL database (`vv_test`, see `scripts/init-db.sql`) and run as the non-owner runtime roles, so row-level security is exercised. Test modules are named after acceptance scenarios (AT-01, AT-02, …).
