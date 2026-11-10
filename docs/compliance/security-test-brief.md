# External penetration test — scope and rules of engagement

| Field | Value |
|---|---|
| Status | **Draft brief for quotation.** No tester engaged. No test has been run. |
| Client | Vitalos Technologies — [Owner to complete: legal entity, company number, address] |
| Product | Vitalos Verify (multi-tenant identity verification web app and API) |
| Requirement | Spec 11 §Assurance release gate: external application penetration test before general availability, focused on multi-tenancy, evidence access, webhooks and privilege escalation. No unresolved critical or high findings at release. |
| Preferred supplier type | CREST-accredited penetration testing company (or NCSC CHECK team). Named testers with CREST CRT/CCT-level or equivalent qualifications. [Owner to complete: chosen firm] |
| Budget | [Owner to complete: approved amount — not part of the monthly running-cost cap] |
| Window | [Owner to complete: dates] — ideally after staging is deployed and the real supplier sandbox is integrated |
| Vitalos contact (business hours) | Temitope Agbola — [Owner to complete: phone, email] |
| Emergency stop contact | [Owner to complete] |

## 1. Objectives

1. Find ways one customer (tenant) could read or change another customer's data.
2. Find ways to see identity evidence (document images, selfies) without a legitimate, audited reason.
3. Find ways to approve a verification that should not be approved.
4. Find privilege escalation within a tenant (e.g. reviewer → owner) and from tenant to platform.
5. Find server-side request forgery, injection and authentication flaws.
6. Give a severity-rated report Vitalos can fix and re-test against.

## 2. Environment and data

| Item | Value |
|---|---|
| Environment | **Staging only** — [Owner to complete: staging URL(s), e.g. `https://staging.verify.vitalos.co.uk`] |
| Hosting | AWS eu-west-2 staging account (separate from production) |
| Data | **Synthetic only.** No real identity documents or faces. Testers must not upload real ID documents or real people's photos. Use the supplied synthetic test images or the supplier's sandbox test documents. |
| Identity supplier | [Owner to complete: supplier sandbox, or the built-in mock `DummyProvider` if no supplier is contracted yet — state which in the report] |
| Production | **Out of scope.** No testing against production or vitalos.co.uk marketing site. |
| Source code | Available for a grey-box review on request: [Owner to complete: access method, e.g. read-only GitHub access for the test period] |
| Rate limits | Left on. Tester may ask for a raised limit for a named IP for a set time. |
| Source IPs | [Tester to supply] — Vitalos will tag them in logs |

## 3. In-scope surfaces

| Surface | Path prefix | Auth | Key things to test |
|---|---|---|---|
| Public API | `/v1/*` (verifications, decisions, webhook endpoints, webhook replays, deletions) | Bearer API key (scoped, hashed) | Cross-tenant object access by ID or `external_reference`; scope bypass (e.g. `sessions:read` key writing decisions); idempotency key reuse with a different body; mass assignment of `tenant_id`; deletion of another tenant's subject |
| Applicant journey | `/applicant/*` (exchange, handoff, session, notice, contact send/verify, attempts) and web routes `/v/{token}`, `/h/{token}` | One-use link token → HttpOnly cookie | Link reuse; token leakage via URL, referrer or history; handoff token reuse/expiry; email code brute force and cost exhaustion; attempt injection for another session; skipping the notice step |
| Customer console | `/console/*` and web routes `/app/*` | Sign-in: Google (OIDC) **or** email magic link, then **authenticator-app (TOTP) second factor**; step-up code for sensitive actions; CSRF double-submit | Login CSRF; OIDC state/nonce/PKCE handling; magic-link reuse, expiry, cross-browser use, account enumeration; **MFA bypass** (skipping enrolment, replaying a code, race on verify, lockout bypass); step-up bypass for evidence reveal, API key creation, membership revocation; session fixation; idle/absolute timeout; role escalation (reviewer → administrator → owner); last-owner protection |
| Evidence | `/console/verifications/{id}/evidence`, `/console/evidence/{id}/reveal`, `/console/evidence/download` | Console + role + reason + active claim + step-up | Reveal without claim/reason; reuse of a 5-minute download link by another member or tenant; link after revocation; IDOR on evidence IDs; export (`/console/exports/verifications.csv`) containing images, document numbers or CSV formula injection |
| Reviews and appeals | `/console/reviews/*`, `/console/appeals/*` | Console | Overwriting a failed check; stale lease writes; self second-review; conflicted reviewer on an appeal |
| Platform (Vitalos staff) | `/platform/*` and web routes `/admin`, `/ops` | Separate platform sign-in | Access to subject data or evidence (must be metadata only); tenant-user access to platform routes; platform session fixation |
| Supplier callbacks | `/callbacks/{provider}` | Supplier signature on raw body | **Callback forgery**; replay of an old valid callback; callback for another session; unknown reference; a client-side "success" causing approval |
| Outbound webhooks | Configured via `POST /v1/webhook-endpoints` | API key | **SSRF**: private, loopback, link-local (169.254.169.254), IPv6 and encoded addresses; DNS rebinding; redirects; non-HTTPS; very large responses; signature verification guidance |
| Billing | `/console/usage*`, `/console/invoices/*` | Console | Double charging via concurrent completion; credit beyond original charge; invoice change after issue |

Development-only routes (`/console/dev-login`, `/platform/dev-login`, `/dev/*`, `/dummy-provider/*`) must **not** exist in staging. Confirm they return 404; report as critical if reachable.

## 4. Priority threats (from spec 11)

| Priority | Threat | Expected control | Where in code |
|---|---|---|---|
| P1 | Cross-tenant object reference | Row-level security, composite keys, non-owner DB roles | `migrations/0001_foundation.sql`, `0005`; `db.py` |
| P1 | Evidence access without reason / outside tenant | Sealed objects, reason-gated reveal, member-bound 5-min links, audit | `evidence.py`, `crypto.py` |
| P1 | Forged or replayed supplier callback approves a session | Raw-body signature; worker fetches result from supplier; session binding | `events.py`, `worker.py`, `providers/` |
| P1 | Webhook SSRF | HTTPS only; DNS resolved and pinned; private ranges blocked; no redirects | `webhooks.py` |
| P1 | Privilege escalation (role, tenant, platform) | Permission checks per route; scoped keys; platform separate | `auth.py`, `platform.py`, `api/app.py` |
| P1 | MFA bypass | TOTP required unless IdP asserts MFA; replay protection; lockout | `signin.py`, `oidc.py` (sign-in code was in progress on 10 Nov 2026 — confirm merged version) |
| P2 | Login CSRF / OIDC flaws | State bound to browser cookie; nonce; PKCE S256; `max_age` | `oidc.py` |
| P2 | Applicant link theft | One-use exchange, short lifetimes | `applicant.py` |
| P2 | Email code abuse / cost exhaustion | Per-session and per-destination limits, spend cap | `applicant.py` |
| P2 | Sensitive data in logs or error messages | Allowlist logger; generic errors | `log.py`, `errors.py` |
| P3 | Content Security Policy weaknesses | CSP — **known gap: inline scripts still allowed** (Next.js); report but note as known | `apps/web/next.config.mjs` |

Out of this test (separate assessment): biometric presentation-attack and injection testing of the supplier's capture SDK (spec 11 requires a separate biometric/injection assessment appropriate to the chosen supplier).

## 5. Test accounts Vitalos will provide

| Account | Tenant | Role | Purpose |
|---|---|---|---|
| A-owner | Tenant A (synthetic) | owner | Full tenant rights |
| A-admin | Tenant A | administrator | Policy publishing |
| A-reviewer-1, A-reviewer-2 | Tenant A | reviewer | Leases, second review, appeals |
| A-developer | Tenant A | developer | API keys, webhooks |
| A-auditor | Tenant A | auditor | Read-only |
| B-owner, B-reviewer | Tenant B (synthetic) | owner, reviewer | Cross-tenant attempts |
| API keys | A and B | full scope and narrow scope (e.g. read-only) | API testing |
| Platform-ops, platform-admin | Platform | operations, admin | Platform role separation |
| Authenticator seeds | — | — | Testers enrol their own authenticator app at first sign-in |
| Sign-in mailboxes | — | — | [Owner to complete: test mailboxes that receive magic links, e.g. `pentest-a-owner@<test domain>`] |

Accounts are created only in staging and are disabled at the end of the window.

## 6. Out of scope

- Production and any real customer data.
- vitalos.co.uk marketing website and email systems.
- Denial-of-service and volumetric load testing (a short, agreed rate-limit test is in scope).
- Social engineering and phishing of staff; physical testing.
- AWS, Google, GitHub and supplier platforms themselves (test only Vitalos's configuration and use of them).
- The supplier's own infrastructure beyond its sandbox endpoints that Vitalos calls.
- Uploading real identity documents or images of real people.

## 7. Rules of engagement

- Work only from the agreed IPs and within the window.
- Stop and call the emergency contact if you find: access to another tenant's data, any real personal data, a route to production, or a service outage.
- Do not keep copies of any data beyond the synthetic test data; delete working files at the end and confirm in writing.
- Do not install persistent backdoors. Clean up created objects or list them in the report.
- Vitalos will not change the environment during the window without telling the tester.
- [Owner to complete: signed authorisation letter from Vitalos; tester's insurance and NDA]

## 8. Reporting and severity

- Severity: CVSS v3.1 or v4.0 base score **and** a plain-English business impact. Use Critical / High / Medium / Low / Informational.
- Each finding: title, affected route, steps to reproduce, evidence (synthetic only, redacted), impact, recommendation, references.
- Executive summary for a non-technical founder.
- Critical findings reported by phone/email **within 24 hours** of discovery, not held for the report.
- Draft report within [Owner to complete: e.g. 5 working days]; final after Vitalos comments.
- Release rule (spec 11): no unresolved critical/high at release; medium findings need an owner, a deadline and a compensating control.

## 9. Retest

- One retest of all critical, high and medium findings included in the quote, within [Owner to complete: e.g. 30 days] of the final report.
- Retest letter states finding status: fixed / partly fixed / not fixed.
- Re-test again after a material change: new supplier, new sign-in method, new public route.

## 10. Internal pre-test checklist (run before the tester starts)

All tests below exist in the repository and run against a real PostgreSQL database as the non-owner runtime roles. They use synthetic data and the mock provider. **They are internal and agent-written; they do not replace an independent test.**

### How to run

```bash
docker compose up -d postgres
cd services/api && uv sync --frozen
uv run ruff check src tests
uv run pytest -p no:cacheprovider
```

Browser tests (start their own API, worker and web server on database `vv_e2e`):

```bash
cd apps/web && npm ci && npm run build:e2e && npx playwright install chromium && npm run test:e2e
```

Run one file: `uv run pytest tests/test_at01_isolation.py -q`

### Automated tests mapped to threats

| Threat | Tests | Status on 10 Nov 2026 (`delivery/status.json`) |
|---|---|---|
| Cross-tenant isolation (AT-01) | `tests/test_at01_isolation.py`, `tests/test_verifier_isolation.py` | Pass (local) |
| Revocation (AT-02) | `tests/test_at02_revocation.py` | Pass |
| Idempotency, unsupported scope (AT-03, AT-23) | `tests/test_at03_sessions.py` | Pass |
| Incomplete evidence, forged callback, frozen policy (AT-05/06/07) | `tests/test_flow.py`, `tests/test_verifier_policy.py` | Pass (mock provider) |
| Review concurrency (AT-08) | `tests/test_at08_review.py`, `tests/test_at08_review_leases.py`, `tests/test_verifier2_review.py` | Pass |
| Deletion and restore (AT-09) | `tests/test_at09_deletion.py`, `tests/test_verifier2_deletion.py` | Pass (simulated backups) |
| Telemetry leakage (AT-10) | `tests/test_at10_telemetry.py` | Partial — no real infra telemetry |
| Webhook retries and SSRF (AT-11) | `tests/test_at11_webhooks.py`, `tests/test_verifier_ssrf_env.py` | Pass (fake transport) |
| Billing integrity (AT-12) | `tests/test_at12_billing.py`, `tests/test_verifier2_billing.py` | Pass (synthetic) |
| Recovery (AT-14) | `tests/test_at14_recovery.py` | Partial |
| OTP abuse (AT-15) | `tests/test_at15_contact.py` | Pass (mock messenger) |
| Evidence minimisation and reveal (AT-24) | `tests/test_at24_evidence.py`, `tests/test_verifier2_evidence.py` | Pass |
| OIDC / login CSRF / MFA claims / step-up | `tests/test_oidc.py`, `tests/test_verifier2_oidc.py` | Pass (fake IdP) |
| Magic link, TOTP, replay, lockout, step-up by code | `tests/test_signin.py` | **In progress** (uncommitted on 10 Nov 2026) |
| Guards: mocks refused in staging, keys required | `tests/test_verifier_guards.py`, `tests/test_verifier_ssrf_env.py` | Pass |
| Platform metadata-only | `tests/test_platform.py` | Pass |
| Applicant accessibility and journey (axe WCAG 2.2 A/AA, keyboard, camera denied) | `apps/web/e2e/applicant.spec.ts` | Pass (Chromium only) |
| Console accessibility (axe) and claim/decide | `apps/web/e2e/console.spec.ts` | Pass |
| Console sign-in (browser) | `apps/web/e2e/console-signin.spec.ts` | **In progress** |
| Static infrastructure guard rails | `python3 -I infra/terraform/policy_check.py` | Pass (never applied) |

### Before the window — checklist

- [ ] All tests above green on the commit being tested; record the commit SHA: [Owner to complete]
- [ ] Staging deployed from that SHA with `VV_ENV=staging` (mocks and dev routes refused)
- [ ] `/console/dev-login`, `/platform/dev-login`, `/dev/*`, `/dummy-provider/*` return 404 in staging
- [ ] Real secrets set in AWS Secrets Manager (not defaults); see `docs/infrastructure/aws-setup.md`
- [ ] Test accounts and API keys created (§5); authenticator enrolment works
- [ ] Synthetic test images loaded; supplier sandbox connected (or mock declared)
- [ ] CloudTrail and application logs on; tester IPs noted
- [ ] Backups on; a snapshot taken before the window
- [ ] Emergency contacts confirmed with tester
- [ ] Signed authorisation letter issued
