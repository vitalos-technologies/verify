# Data Protection Impact Assessment — Vitalos Verify (applicant identity verification)

| Field | Value |
|---|---|
| Document status | **Pre-filled working draft. Not signed. Not legal advice.** Real identity data must not be processed until Part B is completed and signed by each customer, and Part A is reviewed by a qualified privacy adviser. |
| Version / date | 0.1 / 10 Nov 2026 |
| Structure | Follows the ICO DPIA template steps (UK GDPR Article 35) |
| Prepared from | `docs/spec/12_privacy_DPIA_working_draft.md`, `06_data_model.md`, `07_sessions_and_policy.md`, `11_security_threat_model.md` and the built prototype (`services/api`, `apps/web`) at 10 Nov 2026 |
| Product state | Synthetic-data prototype. The only identity provider is a **mock** (`DummyProvider`, synthetic country `ZZ`). Nothing is deployed. No real personal data has been processed. |
| Vitalos contact | Temitope Agbola, founder, Vitalos Technologies — [Owner to complete: registered company name, number, address, ICO registration number] |
| Privacy adviser / DPO | [Owner to complete: name, firm, date engaged] |

## How to use this document

There are two separate parts. Do not merge them.

| Part | Who completes it | What it covers |
|---|---|---|
| **Part A — Processor assessment (Vitalos)** | Vitalos | How the Vitalos Verify service processes data on a customer's instructions, the controls built into it, and the risks Vitalos manages. Customers can rely on it as input to their own DPIA. |
| **Part B — Controller assessment (customer)** | Each customer (the controller), with Vitalos help | Purpose, lawful basis, Article 9 condition, necessity, alternatives, notices, retention ratification, transfers, residual risk acceptance and sign-off. One per customer. |
| Part C — Vitalos as controller | Vitalos | Vitalos's own processing (console user accounts, security logs, billing). Short. |

Blanks are written as **[Owner to complete: …]** or **[Customer to complete: …]**. A blank is a launch blocker, not a formality (spec 12 §Controller completion fields).

---

# Part A — Processor assessment (Vitalos)

## A1. Why a DPIA is needed (ICO step 1)

A DPIA is needed because the service:

- [x] processes **biometric data for the purpose of uniquely identifying a person** (face match between a selfie and an ID photo) — special category data (UK GDPR Art. 9; ICO guidance S02, S03);
- [x] uses **innovative technology** (automated document and liveness checks supplied by a third-party engine);
- [x] can produce outcomes that affect **access to work** (an applicant may be delayed or not onboarded);
- [x] involves **systematic processing at scale** across many customer organisations;
- [x] may involve **international transfers**, depending on the supplier chosen.

## A2. Description of the processing (ICO step 2)

### Nature: what happens, step by step

```
Customer creates request  →  Applicant opens link  →  Notice (+ consent if chosen)  →  Email code
   →  Capture via supplier (ID document, selfie, liveness)  →  Supplier checks
   →  Vitalos policy decision  →  Customer review / appeal (if needed)  →  Result to customer
   →  Retention clock  →  Deletion (primary, supplier, backups)
```

| # | Step | What data | Where it is built today | Notes |
|---|---|---|---|---|
| 1 | Customer creates a verification (API `POST /v1/verifications` or console "New verification") | Customer's external reference, policy, country, document type, optional applicant email | `services/api/src/vv/service.py`, `api/app.py` | Idempotent create. Unsupported country/document is refused with 422 **before** any capture or charge (`domain/coverage.py`, AT-23). Customers are asked to use a pseudonymous reference, not a name. |
| 2 | Applicant opens link | One-use token (72 h unused-link expiry) | `applicant.py::exchange_token` | Token is exchanged once for a 2-hour HttpOnly session cookie and removed from the URL and history. No subject details are shown before exchange. |
| 3 | Device switch (optional) | One-use QR handoff token, 10 min | `applicant.py::create_handoff`, migration `0002` | Continues the **same** session on a phone; no duplicate verification. |
| 4 | Privacy notice | Notice version, acknowledgement kind (acknowledgement vs consent), time | `applicant.py::acknowledge_notice`, table `notice_acknowledgements` | Acknowledging the notice is recorded separately from consent. Consent is never inferred from acknowledgement. **Notice wording is a placeholder until the controller approves it.** |
| 5 | Email code | Email address (stored only as a keyed hash), 6-digit code (hashed), attempt counts | `applicant.py::send_contact_code / verify_contact_code`, table `contact_challenges` | Proves control of the inbox only — **not** identity. Rate and spend limits (AT-15). Messaging supplier not yet chosen. |
| 6 | Capture via supplier | Document images, selfie / liveness video or frames, device and session signals | `providers/base.py` (adapter contract), `applicant.py::start_attempt` | Restricted capture token scoped to that one session. Supplier secrets never reach the browser. **Today: mock provider only.** |
| 7 | Supplier checks | Document authenticity, expiry, extracted fields, face match result, liveness result, supplier scores and versions | `worker.py`, `events.py` | Supplier callbacks carry no result; Vitalos always fetches the authoritative result (IMP-09). Forged, old or misrouted callbacks cannot approve (AT-06). |
| 8 | Policy decision | Check results, policy version, decision trace | `domain/policy.py`, table `decisions` | Policy version is frozen at session creation (AT-07). Pilot policy: approve only when **every** mandatory check passes. Failed or inconclusive face match, liveness or authenticity go to **human review**, not automatic decline. Only an expired document after retries is declined automatically (IMP-06). |
| 9 | Customer review and appeal | Reviewer identity, reason, decision revision, evidence viewed | `review.py`, migration `0004` | 15-minute claim lease; stale writes refused; failed checks cannot be overwritten (AT-08). Approval by an alternative method needs a second, different reviewer. Appeals go to someone other than the original reviewer and hold evidence from expiry while open. |
| 10 | Evidence access | Sealed evidence object, access receipt | `evidence.py`, migration `0007` | Objects are AES-GCM sealed per object (tenant + evidence ID bound in), stored privately (S3 SSE-KMS in production design). A reveal needs a permitted role, a stated reason, a recent second-factor sign-in (step-up, 15 min) and, for reviewers, an active claim. It returns a 5-minute link bound to that member and tenant. Every reveal and download is audited. |
| 11 | Result to customer | Outcome, reason codes, decision method | Webhooks `webhooks.py`; API | Webhooks are signed and carry outcome only, never images or document numbers. |
| 12 | Export | Case reference, check results, decision version, timestamps | `evidence.py::export_csv` | Default export excludes images and document numbers (AT-24). |
| 13 | Retention and deletion | — | `evidence.py::expire`, `deletion.py`, `tombstones.py`, migrations `0003`, `0010` | See §A6. |

### Tenant isolation

Each customer is a separate tenant. Every tenant table carries `tenant_id` with composite keys and PostgreSQL row-level security (`migrations/0001_foundation.sql`, policy `tenant_isolation`). The application and worker run as non-owner database roles without `BYPASSRLS` (IMP-08). Cross-tenant reads, writes, downloads, exports and queued work are refused without leaking whether an object exists (AT-01: `tests/test_at01_isolation.py`, `tests/test_verifier_isolation.py`). Vitalos platform staff see metadata only — no subject references, contact data or evidence (`platform.py`, migration `0009`, IMP-19).

### Scope

| Item | Value |
|---|---|
| Data subjects | Adult job applicants and contractors invited by a customer. Adults only in the pilot (spec 01). Customer staff (console users). |
| Expected volume | [Owner to complete per pilot: e.g. proposed pilot cap — see `docs/commercial/pilot-plan.md`] |
| Geography of subjects | UK customers; applicants may hold overseas documents. Each country/document type stays disabled until supplier coverage and test evidence exist. |
| Frequency | Once per onboarding, plus retries (max two quality retries in the pilot policy) |

### Data categories

| Category | Examples | Special category? | Retention (Vitalos default) |
|---|---|---|---|
| Customer reference | `external_reference` | No (pseudonymous if customer follows guidance) | Redacted on deletion; outcome kept (IMP-12) |
| Contact data | Applicant email | No | Stored as keyed hash only |
| Identity attributes | Name, date of birth, document number, nationality, expiry (as extracted by supplier) | No, but high-risk | 30 days after final decision |
| Document images | Passport / driving licence images | No, but high-risk (fraud value) | 30 days after final decision |
| **Biometric data** | Selfie, liveness frames/video, face templates or match scores created by the supplier | **Yes — Art. 9 when used to uniquely identify** | 30 days after final decision (Vitalos copies); supplier copies per supplier contract [RFI] |
| Device / session signals | IP-derived rate-limit keys, user agent, capture metadata | No | Rate-limit windows are short-lived; raw supplier callback bodies 7 days (proposed, spec 06) |
| Decision data | Check results, reason codes, policy version, decision revisions, reviewer actions | No (but may reveal adverse outcome) | Minimal decision/audit metadata 12 months (proposed, spec 06) |
| Audit / access receipts | Who revealed what, when, why | No | 12 months (proposed) |
| Inferred traits | **None.** No emotion, ethnicity, age estimate or other trait inference. | — | — |

Excluded by design: face gallery or cross-customer biometric search (ADR-11), training on customer evidence (ADR-12), marketing reuse, session replay of capture screens.

### Context

- Applicants are in an unequal position: they want work from the customer. This affects consent (see Part B, B3).
- Applicants may have older phones, poor connectivity, disabilities or documents the supplier does not support. Device limits must never be treated as fraud (AT-04).
- Identity verification is commonly expected in UK recruitment, but applicants may not expect biometric processing or a third-party supplier.
- The service does **not** establish right to work, DBS, immigration status or AML compliance (spec 01, 13). Customers remain responsible for hiring decisions.
- Prior concerns / public sensitivity: facial recognition is publicly sensitive; ICO has published specific biometric guidance (S01–S03).

### Purpose

Help a requesting business establish that an applicant is the genuine holder of a supported identity document during onboarding, with structured evidence, an explainable outcome and a human review route.

## A3. Data flows and locations

| Flow | From → To | Location | Protection |
|---|---|---|---|
| Applicant browser ↔ Vitalos web/API | Applicant → Vitalos | AWS eu-west-2 (London) — **planned; no infrastructure exists yet** | TLS; HttpOnly, Secure cookies; CSP |
| Applicant browser ↔ supplier capture SDK | Applicant → supplier | **[Owner to complete after supplier selection: supplier processing region(s)]** | Restricted, session-scoped capture token |
| Supplier → Vitalos callback | Supplier → Vitalos | eu-west-2 | Raw-body signature check; no result trusted from callback |
| Vitalos → supplier fetch / delete | Vitalos → supplier | [Supplier region] | Scoped server secret, timeout, correlation ID |
| Evidence store | Vitalos | eu-west-2 S3 (design: `infra/terraform/modules/evidence_storage`) | Private bucket, SSE-KMS, TLS-only, no replication, + app-level AES-GCM seal |
| Database | Vitalos | eu-west-2 RDS PostgreSQL (design: `modules/database`) | Private subnets, encrypted, 35-day backups |
| Webhook to customer | Vitalos → customer HTTPS endpoint | Customer's choice | HMAC signature; outcome only; SSRF-safe delivery (`webhooks.py`) |
| Email code | Vitalos → email supplier → applicant | [Owner to complete: email provider and region, e.g. AWS SES eu-west-2] | Code only, no identity data |
| Logs / monitoring | Vitalos | eu-west-2 CloudWatch (design) | Structured allowlist logging; no tokens, codes or evidence (`log.py`, AT-10) |
| Support access | Vitalos staff | [Owner to complete: staff locations] | Metadata only; no evidence access for platform roles |

## A4. Security controls implemented (with evidence)

| Control | File | Test |
|---|---|---|
| Tenant isolation (RLS, composite keys, non-owner roles) | `migrations/0001_foundation.sql`, `0005` | `tests/test_at01_isolation.py`, `test_verifier_isolation.py` |
| Hashed, scoped API keys; immediate revocation | `auth.py` | `tests/test_at02_revocation.py` |
| Console sign-in: OIDC + PKCE, MFA required, step-up for sensitive actions, CSRF, idle/absolute timeout | `oidc.py`, `auth.py`, migration `0008` | `tests/test_oidc.py`, `test_verifier2_oidc.py` |
| One-use applicant links and handoffs | `applicant.py`, migration `0002` | `tests/test_at03_sessions.py`, `test_handoff.py` |
| Authoritative supplier fetch; forged callback rejection | `events.py`, `worker.py` | `tests/test_flow.py::test_forged_and_stale_callbacks_rejected` |
| Sealed evidence, purpose-bound reveal, receipts | `evidence.py`, `crypto.py` | `tests/test_at24_evidence.py`, `test_verifier2_evidence.py` |
| Signed webhooks; SSRF protection incl. DNS rebinding | `webhooks.py` | `tests/test_at11_webhooks.py`, `test_verifier_ssrf_env.py` |
| Allowlist logging; no PII canaries in logs | `log.py` | `tests/test_at10_telemetry.py` |
| Deletion lifecycle with tombstones outside backups | `deletion.py`, `tombstones.py` | `tests/test_at09_deletion.py`, `test_verifier2_deletion.py` |
| Mocks refused outside dev/test | `config.py` | `tests/test_verifier_ssrf_env.py::test_staging_refuses_mocks` |

Not yet done (must be done before real data): real supplier integration and its contract tests; deployment to AWS; S3 evidence and tombstone buckets created; independent penetration test (`docs/compliance/security-test-brief.md`); manual accessibility testing (`docs/compliance/accessibility-test-pack.md`); CSP nonces (inline scripts still allowed); live sign-in configuration (Google or email magic link plus authenticator-app TOTP — owner decision 10 Nov 2026; built and tested in `signin.py`, migration `0011_signin.sql`, `tests/test_signin.py`, but not yet configured against a real Google OAuth client or SES sender).

## A5. Necessity and proportionality — processor view (ICO step 4, part)

| Question | Built answer |
|---|---|
| Is only the minimum collected? | Contact stored as hash; no inferred traits; customers advised to send pseudonymous references; default exports omit images and document numbers. |
| Is every check needed? | Tenant policy sets required checks. Contact ownership is never counted as identity. Customer must justify biometric checks in Part B. |
| Is there a non-biometric route? | Every applicant screen shows an alternative route link. Approval by an alternative method is recorded as a distinct method and needs a second reviewer. **The actual alternative (e.g. in-person check) is the customer's to define — Part B, B4.** |
| Can the applicant challenge? | Appeals: linked to original decision, different reviewer, evidence held while open. Proposed customer targets: acknowledge in 2 working days, resolve or update in 5 (spec 10). |
| Is automated decision-making limited? | Pilot policy auto-approves only when every check passes; adverse biometric results always go to a human. Only "expired document after retries" auto-declines (IMP-06). |
| Is data kept no longer than needed? | 30-day evidence retention enforced by the worker; 35-day backup expiry tracked. |
| Function creep? | No face gallery, no training on customer data, no cross-customer matching (ADR-11, ADR-12). |

## A6. Retention and deletion

| Item | Period | Status | Enforced by |
|---|---|---|---|
| Unused applicant link | 72 hours | Built (`config.py` `hosted_token_ttl_seconds`) | Session expiry |
| Applicant browser session | 2 hours | Built | Cookie/session expiry |
| QR handoff token | 10 minutes, one use | Built | `applicant.py` |
| **Evidence (images, selfie, liveness, extracted fields)** | **30 days after final decision** | **Owner-approved Vitalos default (10 Nov 2026). Each customer ratifies in its DPA.** | `evidence.py` `RETENTION_DAYS = 30`, `expire()`; paused only by appeal hold or legal hold |
| **Backups (database, evidence object versions)** | **35 days** | **Owner-approved Vitalos default (10 Nov 2026). Each customer ratifies in its DPA.** | RDS `backup_retention_period = 35`; evidence bucket non-current versions 35 days (`infra/terraform/modules`); tracked clock in `deletion.py` |
| Raw supplier callback bodies | 7 days | Proposed (spec 06) — [Owner to confirm] | **Not yet built as a timed expiry.** Bodies are stored sealed (`events.py`) and cleared on subject deletion (`deletion.py`). |
| Minimal decision and audit metadata | 12 months | Proposed (spec 06) — [Owner to confirm] | — |
| Supplier-held copies | [Owner to complete from supplier contract] | Unknown until RFI | Supplier deletion API + confirmation (tracked as a separate deletion target) |

Deletion on request: access blocked first; primary evidence deleted; identifiers redacted (outcomes and checks kept without direct identifiers — IMP-12, controller to ratify); supplier deletion requested and tracked; job is only marked complete once supplier and backup targets are complete. Tombstones are written to a log **outside** database backups and replayed before any restored system serves traffic (IMP-18, AT-09). We never tell applicants deletion from backups is instant; backups expire within 35 days.

## A7. International transfers

**Depends on the supplier. Not yet known.**

| Party | Processing country | Support access country | Transfer mechanism | Status |
|---|---|---|---|---|
| AWS (core hosting) | UK (eu-west-2) — planned | [Owner to complete] | [Adviser to confirm] | Account not created |
| Identity supplier | [Owner to complete after RFI] | [Owner to complete after RFI] | [Adviser to confirm: e.g. UK IDTA / Addendum, adequacy] | No supplier selected |
| AWS Rekognition Face Liveness (if used as a component) | Not offered in London; nearest European region listed is Ireland (S09, checked 10 Nov 2026) | — | [Adviser to confirm] | Not planned unless chosen |
| Email provider | [Owner to complete] | [Owner to complete] | [Adviser to confirm] | Not chosen |

Desk research (see `docs/procurement/supplier-scorecard.md`) found, for example, that one shortlisted supplier's public notice says data may go to a security centre in India for manual checks. Each answer must be confirmed by the supplier in writing.

## A8. Risks (ICO step 5) and measures (ICO step 6)

Scale: Likelihood — Remote / Possible / Probable. Severity — Minimal / Significant / Severe. Residual figures are **Vitalos's proposed view** and must be confirmed by the owner after the security test and by each customer in Part B.

| # | Risk to individuals | Likelihood (before) | Severity | Measures (implemented → file) | Residual (proposed) | Still open |
|---|---|---|---|---|---|---|
| R1 | Identity evidence exposed to another customer | Possible | Severe | RLS + composite keys + non-owner roles (`migrations/0001`); AT-01 tests | Remote / Severe → **Low-Medium** | External pen test |
| R2 | Evidence exposed by staff or a compromised reviewer account | Possible | Severe | MFA required; step-up; reason-gated reveal with claim; 5-min member-bound link; receipts (`evidence.py`, `oidc.py`); platform staff metadata-only (`platform.py`) | Remote / Severe → **Medium** | Sign-in build merge; pen test |
| R3 | Data breach of stored images | Possible | Severe | Private KMS bucket, TLS-only, no replication (Terraform); per-object AES-GCM seal; 30-day expiry | Remote / Severe → **Medium** | Infra not built; key management review |
| R4 | Wrongful rejection delays or loses someone a job | Probable | Significant | No automatic decline on biometric failure; human review; alternative route on every screen; appeals with different reviewer; reasons recorded (`domain/policy.py`, `review.py`) | Possible / Significant → **Medium** | Customer alternative route; supplier error rates unknown |
| R5 | Unequal performance across groups (skin tone, age, disability) | Possible | Significant | Review instead of auto-decline; monitoring by device/document planned (spec 15) | Possible / Significant → **Medium-High until evaluated** | Supplier demographic evidence (RFI); representative evaluation |
| R6 | Consent not freely given (employment) | Probable | Significant | Acknowledgement separate from consent; alternative path offered before capture | **Depends on Part B** | Customer lawful basis decision |
| R7 | Supplier reuses data (training, fraud databases) or processes abroad | Possible | Significant | Contract terms required (see `docs/procurement/supplier-agreement-draft.md`); capability registry blocks unapproved region routes | **High until contract signed** | Supplier DPA |
| R8 | Data kept too long | Possible | Significant | Enforced 30-day expiry; deletion jobs; tombstone replay after restore (`deletion.py`, `tombstones.py`) | Remote / Significant → **Low** | Real backup system test |
| R9 | Stolen or forwarded applicant link used by someone else | Possible | Significant | One-use exchange; short lifetimes; token removed from URL; HttpOnly cookie | Remote / Significant → **Low** | — |
| R10 | Forged supplier result approves an impostor (harm to customer and to the impersonated person) | Possible | Severe | Signature check, authoritative fetch, session binding (`events.py`, IMP-09) | Remote / Severe → **Low-Medium** | Real supplier adapter tests |
| R11 | Personal data leaks into logs or monitoring | Possible | Significant | Allowlist logger; canary tests (`log.py`, AT-10) | Remote → **Low** | Real infra telemetry test |
| R12 | Function creep (gallery, cross-customer matching, training) | Remote | Severe | Not built; prohibited by ADR-11/12; review triggers | **Low** | Governance |
| R13 | Applicant excluded by disability or device | Probable | Significant | Accessible web flow, camera-denied fallback, QR handoff, alternative route (`apps/web`, axe tests) | Possible → **Medium** | Manual AT testing (AT-04) |
| R14 | Webhook sends data to an internal network (SSRF) | Possible | Significant | HTTPS only, private/link-local blocked, DNS pinning (`webhooks.py`) | Remote → **Low** | Pen test |

## A9. Consultation (ICO step 3)

| Who | How | Date | Outcome |
|---|---|---|---|
| Representative applicants (5, incl. at least one assistive-technology user) | Usability and comprehension sessions — `docs/compliance/accessibility-test-pack.md` §5 | [Owner to complete] | [Owner to complete] |
| Customer operational reviewers (≥3) | Discovery interviews — `docs/commercial/interview-kit.md` | [Owner to complete] | [Owner to complete] |
| Privacy adviser | Review of Parts A and B | [Owner to complete] | [Owner to complete] |
| Security tester | External test — `docs/compliance/security-test-brief.md` | [Owner to complete] | [Owner to complete] |
| Supplier | RFI answers — `docs/procurement/rfi-email-drafts.md` | [Owner to complete] | [Owner to complete] |
| ICO prior consultation (Art. 36) | Only if a high residual risk cannot be reduced | [Adviser to advise] | [—] |

## A10. Review triggers

Re-assess before: a new country; minors or age assurance; a new or changed supplier; any face gallery; any training use; a material supplier model change; any new automated adverse outcome; longer retention; managed review by Vitalos staff; a security incident (spec 12).

## A11. Vitalos sign-off (processor part)

| Item | Name | Date | Signature / note |
|---|---|---|---|
| Measures approved by | [Owner to complete] | | |
| Residual risks approved by | [Owner to complete] | | |
| Privacy adviser comments | [Owner to complete] | | |
| Next review date | [Owner to complete] | | |

Blank = not signed.

---

# Part B — Controller assessment (customer completes)

Vitalos provides Part A. The customer, as controller, must decide and record the following. Vitalos does not choose a lawful basis for a customer and does not give legal advice.

## B1. Controller details

| Field | Value |
|---|---|
| Legal entity, address, ICO registration | [Customer to complete] |
| DPO / privacy contact | [Customer to complete] |
| Business owner of onboarding | [Customer to complete] |
| Applicant groups and expected monthly volume | [Customer to complete] |

## B2. Purpose

[Customer to complete: the specific fraud or identity problem; e.g. "impersonation at interview", "fake documents from contractors". Include evidence of the problem — incident counts or losses if available.]

## B3. Lawful basis — options to choose with your adviser

**Article 6 (choose one, record why):**

| Option | When it may fit | Points to weigh |
|---|---|---|
| (f) Legitimate interests | Preventing onboarding fraud | Needs a legitimate interests assessment; applicant can object |
| (b) Steps before a contract at the applicant's request | Applicant is applying for a role or engagement | Must be genuinely necessary for that contract |
| (a) Consent | Rarely ideal in recruitment | Power imbalance (see below) |
| (c) Legal obligation | Only where a specific law requires an identity check | Vitalos does **not** provide right-to-work or DBS checks; do not rely on those laws for this service |

**Article 9 condition for biometric processing (choose one, record why):**

| Option | Points to weigh |
|---|---|
| (a) **Explicit consent** | ICO guidance (S01) discusses explicit consent for biometric recognition. **Employment caveat:** consent from job applicants may not be freely given because of the imbalance of power. It is only valid if refusing has no detriment — so a **genuine, equally available alternative** (e.g. in-person or video document check) must be offered and actually used without penalty. Applicants must be able to withdraw. |
| (b) Employment, social security and social protection law, with a DPA 2018 Schedule 1 Part 1 condition | Requires that the processing is necessary for an obligation or right in employment law. Adviser to confirm whether general identity onboarding meets this; it is not assumed here. Appropriate policy document needed. |
| (g) Substantial public interest, with a DPA 2018 Schedule 1 Part 2 condition (e.g. preventing or detecting unlawful acts; preventing fraud) | Each condition has its own tests (some require that consent could not be sought, or specific anti-fraud arrangements). Adviser to confirm applicability. Appropriate policy document needed. |
| Use a non-biometric route only | Avoids Art. 9 for that applicant; lower assurance. Can be offered as the default alternative. |

Chosen Art. 6 basis: [Customer to complete] Chosen Art. 9 condition: [Customer to complete] Adviser and date: [Customer to complete]

The product supports either model: the notice step records **acknowledgement** and, separately, **explicit consent** when that is the chosen condition (`notice_acknowledgements.kind`).

## B4. Necessity, proportionality and alternatives

| Question | Customer answer |
|---|---|
| Why is biometric face match and liveness needed rather than document-only review? | [Customer to complete] |
| What alternatives were considered (in-person check, video call document check, certified digital identity provider, document-only)? Why rejected or kept? | [Customer to complete] |
| **What alternative will applicants be offered** if they decline, cannot use a camera, or the document is unsupported? Who runs it and how fast? | [Customer to complete] |
| Will any applicant be refused solely on an automated result? (Default pilot policy: no, except expired documents after retries.) | [Customer to complete] |
| Automated decision-making safeguards: confirm against UK GDPR Art. 22 as amended by the Data (Use and Access) Act 2025 — adviser to confirm current rules at launch | [Customer to complete] |
| Who reviews, how are reviewers trained (spec 21 §Customer review SOP)? | [Customer to complete] |

## B5. Retention ratification

| Item | Vitalos default | Customer decision |
|---|---|---|
| Evidence after final decision | 30 days | [Customer to complete: accept / shorter / justified longer] |
| Backups | 35 days rolling | [Customer to complete: accept] |
| Decision and audit metadata | 12 months (proposed) | [Customer to complete] |
| Customer's own copy of results in its ATS/HR system | Customer's policy | [Customer to complete] |

## B6. Notice to applicants

Must name: the customer as controller; purpose; data collected; that a biometric check is used and the alternative; Vitalos (processor) and the supplier category and processing locations; retention; rights and how to exercise them via the customer; how to challenge an outcome. Notice version approved: [Customer to complete] Date: [Customer to complete]

## B7. Transfers

[Customer to complete after Vitalos confirms the supplier chain in §A7.]

## B8. Customer risk acceptance and sign-off

| Risk (from §A8) | Customer additional measures | Residual accepted? (Y/N) |
|---|---|---|
| R4 Wrongful rejection | [Customer to complete] | |
| R5 Unequal performance | [Customer to complete] | |
| R6 Consent / basis | [Customer to complete] | |
| R7 Supplier reuse / transfers | [Customer to complete] | |
| R13 Exclusion | [Customer to complete] | |

| Item | Name | Date |
|---|---|---|
| Measures approved by | [Customer to complete] | |
| Residual risks approved by | [Customer to complete] | |
| DPO advice provided / accepted or overruled (with reasons) | [Customer to complete] | |
| Review date | [Customer to complete] | |

Blank = not signed. No real applicant may be invited until this part is signed.

---

# Part C — Vitalos as controller (own purposes)

| Processing | Data | Lawful basis (to confirm with adviser) | Retention |
|---|---|---|---|
| Console accounts and sign-in (Google or email magic link + authenticator-app second factor — owner decision; built) | Name, work email, sign-in subject, MFA evidence, session records | [Owner to complete] | [Owner to complete] |
| Security and audit logging | Actor IDs, IP-derived rate keys, actions | [Owner to complete] | [Owner to complete] |
| Billing and invoices | Customer company and contact details, usage counts | [Owner to complete] | [Owner to complete] |
| Sales enquiries ("Book a demo" → vitalos.co.uk) | Business contact details | [Owner to complete] | [Owner to complete] |

Vitalos does **not** act as controller of applicant evidence and does not use it for its own purposes.

## Sources

S01–S03 ICO biometric and special category guidance; S09 AWS Face Liveness FAQ — see `docs/spec/22_sources_and_evidence.md`. Recheck all guidance with your adviser before launch.
