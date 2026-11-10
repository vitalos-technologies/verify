# Vitalos Verify — Master Blueprint v1.0

Reading copy. Individual numbered specifications are canonical.

# Product strategy and commercial thesis

Version 1.0 | 10 November 2026 | Planning baseline

## Mandate
Build Vitalos Verify as a multi-tenant identity-verification platform sold independently and consumed by Vitalos Workforce through the same public API. Deliver the entire reference portfolio in stages. Begin with specialist engines; replace selected capabilities only after commercial, technical and assurance evidence supports doing so. Vitalos owns the product, policies, integrations, evidence lifecycle and customer relationships.

## Initial customer and job
Primary hypothesis: UK recruitment agencies and contractor platforms need to verify applicants, follow up incomplete cases and resolve exceptions without spreadsheets. Interview 10 prospective buyers, including at least three operational reviewers, before freezing the pilot package. Ask for last month's volume, handling time, drop-off, fraud losses, document mix, procurement requirements and current supplier invoices where voluntarily shared. Secure three written pilot intents with named operational owners. These are discovery targets, not existing customers.

The initial service establishes identity assurance for onboarding. Do not represent it as proof of right to work, professional qualifications, DBS clearance, immigration status or full AML compliance. Those workflows have distinct evidence and scheme requirements. Customers remain responsible for their hiring decisions.

## Value proposition
One request produces a guided applicant journey, structured verification evidence, an explainable outcome and a complete operational case. Differentiate through workforce integrations, accessible exception handling, transparent usage costs, evidence exports and reliable follow-up. A cosmetic wrapper around a supplier has weak defensibility; operational integration and measurable outcomes are the investment thesis.

## Product boundaries
No public facial search, surveillance, emotion inference or cross-customer biometric identification. No biometric training on customer evidence by default. No unsupported country claims. Phone/email control, document authenticity, face match, liveness and business eligibility remain distinct facts. Verify provides an identity result; Workforce applies its own employment workflow.

## Discovery decisions
Choose a document/country matrix from pilot demand. UK customer location does not imply UK-only applicants. Begin procurement with UK passports/driving licences, Irish passports and commonly requested overseas passports; every country/type remains disabled until provider coverage and test evidence exist. Adult-only pilot. Expand to minors only through the separate age-assurance programme.

## Commercial validation gates
Proceed to real-data pilot only with an accountable customer, agreed data roles, provider rights and tested deletion. Proceed to general availability after at least two pilot organisations show repeat usage and willingness to pay, all security gates pass, and actual contribution economics are understood. If reviewers spend more time than the existing process, fix operations before adding modules. Stop or narrow the segment if buyers require a scheme status that Vitalos cannot supply.

## Metrics and experiments
Instrument invitation-to-start, start-to-complete, first-attempt completion, retry rate, review rate, review minutes, appeals, supplier failures and contribution per completed request. Separate applicant abandonment from technical failure and rejected evidence. Compare cohorts by flow version and supported device; collect demographic evaluation attributes only under a separately justified evaluation protocol. Never infer protected traits for operational decisions.

Run one-variable experiments on guidance and flow ordering with fixed security floors. No experiment may reduce required checks or conceal processing. Pilot success targets are hypotheses in the quality plan; record sample sizes and uncertainty alongside improvements.


---

# Decision register and planning assumptions

Version 1.0 | 10 November 2026 | Planning baseline

## Accepted direction
The user accepted the recommended staged full portfolio, hybrid build/buy approach, first-market recommendation, customer-led review and Vitalos Verify working brand. The shared-chat reference could not be retrieved; this is an original implementation pack and does not claim to reproduce unseen documents.

| ID | Decision or assumption | Status | Revisit trigger |
|---|---|---|---|
| ADR-01 | Full portfolio in staged releases | Accepted direction | Buyer demand changes sequencing |
| ADR-02 | Specialist engines first, selective proprietary R&D | Accepted direction | Replacement gates pass |
| ADR-03 | Workforce/recruitment first; regulated schemes separately gated | Recommended baseline | Discovery evidence |
| ADR-04 | UK customers first, supported international documents | Planning assumption | Country demand and legal assessment |
| ADR-05 | Standalone SaaS/API plus Workforce integration | Recommended baseline | Distribution evidence |
| ADR-06 | AWS London core, separate development/staging/production | Planning assumption | Cost, region, supplier requirements |
| ADR-07 | New repository: suggested vitalos-technologies/vitalos-verify | Proposed, not created | Owner selects repository |
| ADR-08 | Founder with Claude Code/Codex; specialist external reviews | Planning assumption | Capacity and budget |
| ADR-09 | Customer reviewers first; managed service later | Accepted recommendation | Staffing and liability ready |
| ADR-10 | Modular application and worker processes | Engineering recommendation | Measured scaling/isolation need |
| ADR-11 | No persistent face gallery in initial release | Security/product baseline | Separate lawful purpose and design review |
| ADR-12 | No default training use of customer material | Privacy baseline | Separate explicit research programme |

## Budget and schedule
No actual budget, launch date, cloud account, repository, supplier contract or credentials have been confirmed. This pack authorises no spending and creates no infrastructure. Planning target: 12–16 weeks to a limited pilot if supplier contracting and external reviews proceed promptly; founder-only delivery can take longer. Full portfolio planning horizon: 9–18 months, with proprietary biometric research potentially longer. Milestone completion is evidence-based rather than calendar-based.

Illustrative pilot non-labour envelope: £500–£1,500/month for infrastructure, tools and limited verification usage, plus separately quoted security/privacy work and provider minimums. At £1.25/check, 1,000 checks alone cost £1,250: the low end cannot support that volume plus everything else. These envelopes are budgeting scenarios, not prices or approved caps.

## Unresolved decisions with owners
Founder: legal entity, domain, repository, actual cap, pilot commitments and accountable operational owner, due M00. Engineering: contracted provider, region matrix, identity-provider choice, due M01. Privacy adviser/customer controller: lawful basis, Article 9 condition, notices, retention and international processing assessment, due M01 before real data. Security reviewer: independent test scope and acceptance, due M05. Product: price experiments and supported document matrix, due M06. Domain availability and trademark clearance for Vitalos Verify remain unverified.

Record every change with date, owner, alternatives, cost, security implications, migration and affected requirements. Lowering a release gate is a policy change requiring owner review; an agent must not remove a gate to make a task pass.


---

# Master product requirements and traceability

Version 1.0 | 10 November 2026 | Planning baseline

## Requirement conventions
MUST means release-blocking for its target milestone. SHOULD requires a documented exception if omitted. Experimental capabilities are disabled for production until their own gates pass. Requirements map to milestone IDs and acceptance scenarios; individual tasks appear in delivery/tasks.json.

| ID | Requirement | Milestone | Acceptance evidence |
|---|---|---|---|
| VV-001 | Tenant-scoped users, roles and objects | M02 | AT-01 cross-tenant denial |
| VV-002 | Strong admin authentication and scoped API credentials | M02 | AT-02 revoked access |
| VV-003 | Idempotent, expiring verification sessions | M03 | AT-03 duplicate creation |
| VV-004 | Accessible capture and alternative path | M03 | AT-04 mobile/keyboard tests |
| VV-005 | Independently recorded ID, match and liveness checks | M04 | AT-05 partial evidence |
| VV-006 | Signed server callbacks; no client-authoritative approval | M04 | AT-06 callback forgery |
| VV-007 | Versioned policies and complete reason codes | M04 | AT-07 policy replay |
| VV-008 | Review ownership, appeal and immutable revisions | M05 | AT-08 conflicting reviewers |
| VV-009 | Retention and supplier deletion tracking | M05 | AT-09 full deletion lifecycle |
| VV-010 | Redacted audit logs and evidence access receipts | M05 | AT-10 leakage inspection |
| VV-011 | Reliable signed outbound webhooks | M04 | AT-11 retry/replay |
| VV-012 | Usage ledger and explicit billing semantics | M06 | AT-12 invoice reconciliation |
| VV-013 | Workforce integration via public API | M06 | AT-13 tenant binding |
| VV-014 | Restore, incident and supplier-outage procedures | M07 | AT-14 recovery exercise |
| VV-015 | Phone/email verification separated from identity | M03 | AT-15 OTP abuse |
| VV-016 | Supplemental document extraction with provenance | M08 | AT-16 inconsistent document |
| VV-017 | Contracted database checks and explainable no-match | M09 | AT-17 unavailable source |
| VV-018 | NFC verification with authenticated chip evidence | M10 | AT-18 untrusted chip data |
| VV-019 | Age assurance with uncertainty and fallback | M11 | AT-19 borderline result |
| VV-020 | Digital ID issuer/holder/session validation | M12 | AT-20 credential replay |
| VV-021 | Proprietary replacements require evaluation gates | M13 | AT-21 shadow regression |
| VV-022 | Managed review separated from tenant self-review | M14 | AT-22 operator scope |
| VV-023 | Jurisdiction and capability enablement matrix | M01 | AT-23 unsupported request |
| VV-024 | Customer exports omit unnecessary identity evidence | M05 | AT-24 export access |

## Release packages
Pilot package: VV-001–015, VV-023–024; limited tenants and supported matrix. General availability: pilot requirements plus operational M07 gates. Expansion modules ship independently after M08–M12 acceptance. R&D never silently changes existing assurances. Managed review is an optional service release after M14.

## User stories
Tenant administrator creates a workforce-onboarding policy without choosing biometric model thresholds directly. Applicant understands who requested the check and what happens to the evidence. Reviewer sees conflicts and source facts, requests a retry, or records an accountable decision. Developer receives stable status events and can reconcile by API. Privacy operator can discover and delete a subject's evidence with controller approval. Vitalos support can troubleshoot metadata without browsing passports.

## Product non-functional baseline
Target WCAG 2.2 AA for customer and applicant surfaces; accessibility test evidence required. Internal API p95 under 500 ms for ordinary metadata reads at pilot load, excluding external checks. Initial capacity scenario: 10,000 sessions/month and 100 simultaneous active capture sessions; test and revise from measured demand. GA service target 99.9% monthly core API availability, proposed rather than contractual. End-to-end verification latency and supplier availability are separately reported. Proposed RPO 15 minutes and RTO four hours require restore evidence before GA.

## Acceptance authority
Engineering signs functional and recovery evidence; independent security reviewer signs assessment disposition; privacy adviser and relevant controller approve processing design; founder owns commercial release. One person may hold multiple internal roles but should not self-certify independent security or regulatory status. All task statuses in this pack begin as planned.


---

# Experience, screens and design specification

Version 1.0 | 10 November 2026 | Planning baseline

## Visual direction
Use a restrained white workspace with charcoal typography, generous spacing and one muted brand accent. No glowing gradients or decorative sci-fi graphics. Marketing can use black sections sparingly. Design for mobile applicants first, with full-size icons, clear capture guidance and short sentences. Adopt a shared component system with accessible primitives; pin dependency versions at implementation.

## Surface inventory
| Surface | Routes or screens | Core actions |
|---|---|---|
| Public | Home, product, solutions/workforce, pricing, developers, security, privacy, status link | Understand product, trial request, sign in |
| Applicant | /v/{token}, introduction, privacy, method, document, selfie, processing, outcome, alternative | Complete or challenge request |
| Customer | Overview, verifications, case detail, policies, team, integrations, usage/billing, settings | Operate own verification programme |
| Operations | Supplier health, processing queues, deletion failures, support access, incidents | Resolve service problems |
| Superadmin | Organisations, entitlements, billing administration, feature gates, audited access | Govern platform |

## Applicant journey
1. Display requesting business, purpose, expiry, expected evidence and controller contact. Do not expose subject details before token exchange.
2. Present the versioned privacy notice and required acknowledgement; capture explicit consent separately only if it is the approved condition. Offer the alternative path before capture.
3. Detect supported capture capability; let users switch device using a short-lived QR handoff without duplicating the verification.
4. Guide document capture with blur/glare feedback and clear accepted document types. Explain why a retry is required without revealing exploitable fraud thresholds.
5. Run supplier-bound live selfie capture. Accessible instructions, audio/text alternatives to instructions and a non-biometric operational route must be considered; unsupported devices are not fraud.
6. Show processing asynchronously. Refreshing or leaving the page does not lose server state. Never show success merely because the SDK callback fired.
7. Show submitted, action required or completed. The requesting business determines detailed disclosure appropriate to the use case; provide support and challenge routes.

## Customer case page
Header: case reference, status, policy version, creation/expiry and assigned reviewer. Checks: distinct ID authenticity, expiry, face match, liveness and contact ownership, each showing result and reason. Timeline: submission, supplier events, requests, review and deletion. Evidence viewer: masked by default, authorised reveal with reason and audit. Action bar: claim case, request more information, record decision, escalate. Never label a person a fraudster solely from a score.

## States required on every relevant screen
Loading, empty, permission denied, expired, invalid input, supplier outage, retry limit reached, offline, deleted and unexpected error. Failed capture must distinguish poor quality from suspected attack. Billing hold blocks new billable sessions, not access to existing outcomes or privacy requests. Lists use cursor pagination and filter by status/time/policy, with no PII in URLs.

## Accessibility and interaction acceptance
Keyboard navigation, visible focus, labelled inputs, error summary, screen-reader announcements for status changes, reduced motion and sufficient contrast. Test 320px and 390px widths, 200% zoom, current iOS Safari and Android Chrome plus a low-memory Android device. No passport/selfie images in session replay. File upload fallback is permitted only where the verification policy supports its lower assurance; it must not substitute for required live capture.

## Design deliverables
Create flows, responsive wireframes, design tokens, component inventory and interactive prototype before production UI. Review with five representative applicants including an accessibility participant where feasible. Record friction and comprehension findings. Final marketing claims must match shipped modules and verified coverage; hide future products behind an explicitly labelled roadmap.


---

# Technical architecture and trust boundaries

Version 1.0 | 10 November 2026 | Planning baseline

## Components
Use a TypeScript web application for public/customer/admin surfaces and a Python API with worker processes for orchestration. Proposed frameworks: Next.js and FastAPI, versions selected and locked during M02. PostgreSQL is the source of truth; S3 private buckets hold evidence; SQS transports asynchronous jobs; a transactional outbox links database changes to events. Use a managed OIDC service such as Cognito for customer identity and enforce application roles separately. This is a proposed stack, not installed software.

Separate modules: tenancy/identity, verification sessions, policy engine, provider adapters, evidence lifecycle, reviews, events/webhooks, usage/billing, integrations and operations. Deploy API and workers separately but share versioned domain contracts. Extract services only when measured isolation or scaling needs justify it.

## Trust boundaries
Applicant browser is untrusted. Capture SDK responses are hints; the backend fetches or validates signed provider evidence. Customer browser is trusted only for authenticated, authorised commands. Providers are external processors with narrow credentials and allowlisted endpoints. Queue messages are untrusted references resolved again against tenant and session state. Evidence storage requires separate permissions from ordinary metadata access. Operators receive temporary purpose-bound access.

## Submission sequence
Customer creates a session with policy and external reference. API validates tenant entitlement and supported matrix, writes session plus usage reservation transactionally and returns a one-use hosted token. Browser exchanges token for a restricted HttpOnly session and starts an approved provider capture session. Supplier callback is authenticated, durably stored and acknowledged; worker fetches authoritative results, normalises each check and evaluates the frozen policy. A transaction writes outcome, audit and outbox event. Dispatcher delivers signed customer webhook. Customer may reconcile using GET even if webhook delivery fails.

## Consistency and failure design
Use database uniqueness for idempotency and event deduplication. Lock or compare session version during transitions. Queue delivery is at-least-once; workers must be idempotent. External calls cannot share a database transaction: record intent, make the call with stable idempotency where supported, record result and reconcile uncertain outcomes before retrying billable actions. A provider timeout produces error/pending, not a failed identity check. Payment and webhook state are independent of verification evidence.

## Security architecture
TLS on all connections; managed encryption for database, object storage, backups and queues. Separate keys or stronger isolation where contract/risk requires it. Tenant identifier derives from verified principal, never only the request body. Composite foreign keys prevent cross-tenant relationships. PostgreSQL row policies add defence in depth; runtime roles cannot bypass them. Worker and migration privileges are distinct. Use short-lived cloud roles and secret rotation.

## Data minimisation
Prefer provider-hosted capture and minimal returned attributes where supplier terms permit. Store evidence only when required for the agreed purpose. Do not copy raw videos simply for convenience. Hashes remain potentially linkable; do not describe hashing as anonymisation. Logs contain correlation IDs, status and timings, not document numbers, images, tokens or raw payloads. An audit trail records evidence access without retaining evidence itself indefinitely.

## Repository layout
apps/web, services/api, services/worker, packages/contracts, infra/terraform, tests, docs, evals and scripts. The same API serves Workforce; no direct database access from Workforce. Keep environment configuration distinct; test fixtures must be synthetic or expressly licensed for evaluation. CI uses a dummy provider with deterministic fixtures and a contract-test suite for each actual adapter.


---

# Data model and evidence lifecycle

Version 1.0 | 10 November 2026 | Planning baseline

## Logical entities
| Entity | Key fields | Invariants |
|---|---|---|
| tenants | id, status, region_policy, retention_profile | No inherited access from Workforce |
| memberships | tenant_id, user_id, role, active | Role changes audit; last owner protected |
| api_keys | id, tenant_id, hash, scopes, expires_at | Raw key returned once; hash only |
| policies | tenant_id, id, version, required_checks, matrix_version | Published versions immutable |
| subjects | tenant_id, id, external_reference | Pseudonymous reference preferred |
| sessions | tenant_id, id, subject_id, policy_version, state, version, expires_at | Frozen policy, optimistic concurrency |
| attempts | tenant_id, id, session_id, sequence, provider_reference | Retry creates attempt, not overwritten evidence |
| checks | tenant_id, id, attempt_id, type, result, reasons, model_version | One final result revision per provider observation |
| evidence | tenant_id, id, attempt_id, location_reference, digest, expires_at | No public URLs; explicit lifecycle |
| provider_events | provider, event_id, session_id, received_at, processing_state | Unique provider event ID; raw retention limited |
| decisions | tenant_id, id, session_id, revision, outcome, actor, reason | Append-only; supersedes prior revision |
| reviews | tenant_id, id, session_id, assignee, lock_version, status | Claim lease and optimistic concurrency |
| notices | tenant_id, id, version, purpose, effective_at | Version retained without evidence duplication |
| acknowledgements | tenant_id, subject_id, notice_version, kind, time | Consent not inferred from ordinary acknowledgement |
| deletion_jobs | tenant_id, subject_id, targets, legal_hold, state | Supplier/backup completion independently tracked |
| usage_events | tenant_id, id, session_id, charge_type, amount, currency | Deduplicated ledger; adjustments append |
| outbox | id, tenant_id, event_type, payload, created_at | Same transaction as domain change |
| webhook_deliveries | tenant_id, event_id, endpoint_id, attempt, state | Stable event ID across delivery retries |
| audit_events | tenant_id, id, actor, action, object_ref, timestamp | Append-only during justified retention |

## Constraints and indexing
All tenant-owned relationships use (tenant_id, id) composite references. Index sessions by tenant, creation timestamp and ID; reviews by tenant/status/assignee; evidence by expiry and lifecycle; outbox by dispatch state and next attempt. Use UTC timestamps, explicit currency and integer minor units. Store provider-native scores with score type and version; scores from different providers are not interchangeable. Encrypt sensitive extracted fields and avoid unrestricted JSON payloads in primary tables.

## Lifecycle defaults requiring controller ratification
Proposed operational profile: unused link expires after 72 hours; sensitive captures expire 30 days after final decision; raw webhook bodies expire after seven days; review evidence inherits capture deadline unless a justified hold applies; minimal decision/audit metadata retained for 12 months; infrastructure backups retained for 35 days. These are design proposals, not legal retention periods. Scheme-specific records require a separate profile; never silently extend the whole dataset.

On deletion request: authenticate requester through proportionate means, identify controller, locate subject records, evaluate legal holds, deny new evidence access, delete primary evidence, request supplier deletion, redact extracted fields, preserve only justified minimal audit, and track backup expiry. Mark primary_deleted while backups await expiry; only mark complete when every required target is complete. Restore procedures replay deletion tombstones before serving restored data. Legal holds need owner, lawful reason, scope, expiry and periodic review.

## Migration strategy
Expand/contract migrations, reversible code rollbacks, tested backups and explicit destructive-change review. Add nullable field, backfill in bounded batches, verify, then enforce constraints. Never allow agent-generated migrations to drop production evidence or disable row policies without an explicit reviewed migration plan. Schema evolution must preserve past policy/decision reproducibility.

## Exports and reports
Default exports contain case reference, check types/results, decision version, timestamps and evidence references; exclude images and document numbers. Evidence export needs separate permission and auditable purpose. Download links expire, are tenant-bound and are never delivered in routine webhook payloads.


---

# Session state machine and decision policy

Version 1.0 | 10 November 2026 | Planning baseline

## Session states
created -> in_progress -> processing -> approved | declined | review_required | action_required. created/in_progress/action_required may become expired or cancelled. processing may become error after reconciled provider failure. error may return to processing only through a recorded retry. action_required returns to in_progress with a new attempt. review_required resolves through a decision revision, not by rewriting check evidence. Terminal decisions cannot change through late callbacks; a reopening creates an explicit new revision and event. Deletion is an orthogonal lifecycle state.

## Checks and decisions
Check result enum: pass, fail, inconclusive, error, not_run. Decision outcome enum: approved, declined, review_required, action_required. Capture quality failure is normally action_required; provider error is never fail. Missing mandatory checks cannot approve. Contact ownership cannot compensate for failed ID/liveness. Tenant administrators configure required checks and supported scope; only platform assurance owners can change provider thresholds within validated ranges.

## Policy evaluation order
1. Verify session active, subject binding, attempt ownership and evidence freshness.
2. Resolve technical errors; retry only within bounded attempt/cost policy, otherwise hold.
3. Confirm all required evidence exists; missing evidence requests action or review.
4. Evaluate explicit high-risk indicators under the policy. For pilot, suspected spoofing routes to review with restricted details rather than declaring fraud.
5. Evaluate document expiry, identity match and liveness using provider-specific validated settings.
6. Approve only if every mandatory check passes and no review trigger remains.
7. Persist policy version, evidence IDs, normalised reasons, provider versions and decision revision atomically.

## Example pilot policy
Require supported government ID, authenticity pass, unexpired document, face match pass and liveness pass. Email control is required for the invitation workflow but not identity assurance. Allow two quality retries, then customer-assisted alternative. A mismatch or inconclusive biometric outcome routes to review. A reviewer cannot convert failed liveness into a successful biometric check; they may record an alternative assurance decision with method and rationale, clearly distinguished in the result. Customers must not treat it as equivalent assurance without their own policy.

## Policy change and evaluation
Draft -> validated -> published -> retired. Publishing requires fixture replay, supported-matrix check, cost preview and permission. Existing sessions keep their original version; new sessions use the new version. Store a compact decision trace with rule identifiers, not hidden model reasoning. A dry-run reports differences and never sends production events or bills users. Security floors cannot be removed by a tenant.

## Reason code vocabulary
document.expired; document.unsupported; document.authenticity_failed; capture.low_quality; face.no_match; liveness.inconclusive; liveness.suspected_attack; provider.unavailable; evidence.missing; session.expired; policy.unsupported_region; review.alternative_method. Separate internal fraud detail from applicant-safe messages. Every displayed message has a localisation key and support path.


---

# Supplier procurement and adapter specification

Version 1.0 | 10 November 2026 | Planning baseline

## Selection method
Evaluate an integrated provider for speed and a component supplier for strategic flexibility. Shortlist Stripe Identity, Regula, Innovatrics and Yoti for relevant capabilities; AWS liveness is a component, not a complete ID verification substitute. No supplier has been selected or contacted. Do not assume access, redistribution rights, white labelling, certification inheritance or data residency from a public marketing page.

Weight scorecard: use-case/document coverage 20%, measured security/performance 20%, privacy/region/retention 20%, commercial/platform rights 15%, capture/accessibility 10%, integration/operations 10%, portability 5%. Disqualify unapproved resale, missing lawful processing arrangements, unsupported required region, unverifiable deletion or unacceptable evidence access regardless of weighted score.

## Request for information
Obtain country/document/version matrix; confidence semantics; liveness and injection evaluation reports; exact model/SDK versions assessed; mobile support; demographic/quality evidence; false-match and false-non-match operating points; certification scope/expiry; service and incident commitments; processing locations including support; subprocessors; training use; retention/deletion and backup terms; controller/processor contract; platform/resale rights; minimum spend; billable retry definition; dispute/refund handling; exit export and migration support. Request sandbox access using synthetic material.

## Adapter interface
create_attempt(session, policy, idempotency_key) -> provider reference and restricted capture token; authenticate_event(raw_body, headers) -> event identity; fetch_result(reference) -> immutable provider observation; normalise(observation) -> check results; request_deletion(reference) -> deletion job; reconcile(reference) -> known state. All calls include correlation ID and a bounded timeout. Provider secrets never enter the browser. Restricted SDK tokens are limited to the exact capture session.

## Capability registry
Each adapter declares supported check types, countries, document types, capture modes, regions, maximum evidence age, deletion support, score semantics and approved use cases. Routing requires capability match plus tenant processing permission. Unsupported requests return a clear 422 before capture or charge. A fallback provider may not silently receive evidence under a different purpose/region; approve that route in advance and communicate it in notices.

## Reliability
Circuit-break new calls on sustained provider failures, preserve existing sessions, expose pending status and reconcile timed-out calls. Backoff with jitter; deduplicate provider event IDs and reference lookups. Separate vendor errors from applicant outcomes in dashboards. Do not call a second supplier simply to obtain a passing result after a security failure. Fallback addresses availability or an approved alternative method, preserving original evidence.

## Procurement exit gate
Founder approves contract economics and rights, privacy owner approves processing and transfers, engineering passes sandbox contract tests, assurance owner validates evaluation scope. A signed contract does not establish actual accuracy; production enablement requires the controlled test and pilot gates.


---

# Verification modules: detailed functional specification

Version 1.0 | 10 November 2026 | Planning baseline

## Government ID — M04
Input: approved capture session, document country/type and permitted images. Checks: capture quality, supported template, authenticity signals, expiry, extracted field consistency and portrait availability. Preserve extraction confidence and source region; low-confidence fields need confirmation without overwriting original extraction. MRZ checksums and OCR consistency alone do not prove authenticity. Output individual checks with provider/version/provenance, masked attributes and evidence references. Reject unsupported type before collecting unnecessary images. Test glare, blur, expired documents, altered data and legitimate naming variations with lawful fixtures.

## Selfie matching and liveness — M04
Bind live capture to the session and verified reference portrait. Record matching and liveness separately. No shared face gallery; no 1:N search. Distinguish unusable frame, no face, multiple faces, mismatch and suspected attack. Restrict retries and protect capture tokens from replay. Retain only required evidence, with no long-lived reusable biometric template by default. Security evaluation includes presentation and injection threats and end-to-end integration, not just model scores. Deployment blocked until evaluated operating thresholds are fixed.

## Phone and email — M03
Issue single-use codes with short expiry; store hashed codes; limit per-session, per-destination and per-tenant sends, with IP/device risk as additional signals. Do not leak account existence. Use generic responses and progressive abuse controls. Support email invitation with code confirmation separately from the invitation token itself. SIM control and email control are low-assurance contact attributes, not verified legal identity. Messaging spend limits must work independently of rate limits.

## Supplemental Document AI — M08
Start with proof of address from agreed document classes. Input privately uploaded file, declared purpose and reference fields. Scan files, reject active content/oversize archives, extract in a sandbox. Output document type, extracted fields with page/bounding-box provenance, recency and consistency flags. LLM-derived values require schema validation and provenance; document text is untrusted input and cannot issue tool commands. Date/name/address consistency is not authenticity. Advanced tamper detection remains a separately sourced check. Reviewer can compare original and extracted data; amendments preserve originals and actor reason.

## Database checks — M09
Contract for specific sources and permitted purposes; no generic promise of government access. Match supplied name, date of birth/address or approved identifier to licensed source. Return match, partial, no_match, unavailable or not_covered with source time and freshness. A no-match may reflect coverage or stale data and must not automatically be labelled fraud. Avoid excessive identifiers. Distinguish identity-record matching from sanctions/PEP screening; AML screening is not included merely because database checks exist. Test spelling, transliteration, changed addresses and source outage.

## NFC — M10
Use supported native mobile SDK/device flow. Reading chip data is not authentication. Require certificate-chain/signature and data-integrity validation through approved trust material; define whether active/chip authentication is supported for each document. Compare authenticated chip portrait to live selfie under policy. Record validation method, issuer trust version and unsupported outcomes. Unverified decoded chip data cannot receive the same assurance label. Maintain trust-material update procedure and revoked/expired certificate handling based on document standards, not ordinary web-certificate assumptions. Test emulator/injected payloads in authorised fixtures, corrupt signatures and device interruption.

## Age assurance — M11
Separate age estimation from identity recognition. Return threshold result and method, not a falsely exact age. Procure an evaluated age estimator and liveness mechanism, choose an evidence-based challenge threshold above the legal boundary, and offer a justified alternative for borderline users. Do not invent a universal buffer. Retain the minimum threshold assertion where possible, and remove captures promptly under the approved profile. Test underage acceptance, adult rejection, subgroup/device performance and fallback completion. Do not reuse age evidence for identity matching or marketing. Children-related processing requires a separate assessment before launch.

## Digital ID and EUDI — M12
Begin as a verifier/relying party, not a wallet issuer. Verify supported credential format, trusted issuer, signature, validity, holder binding, intended audience, session nonce and status/revocation where applicable. Request only necessary attributes; do not accept screenshots of wallet credentials as equivalent cryptographic evidence. Implement protocol-specific adapters once target wallets, relying-party obligations and current interoperability specifications are confirmed. EUDI is a programme with trust and scheme onboarding, not just a UI checkbox. Negative tests include replay, wrong audience, untrusted issuer and expired credential.

## Cross-module rules
All modules register their supported matrix and cost semantics, emit normalised checks, follow retention profiles and provide an alternative/error path. No future module is enabled by default. A new module needs privacy assessment delta, supplier rights, acceptance fixtures, production monitoring and rollback before release.


---

# Case management, appeals and operational access

Version 1.0 | 10 November 2026 | Planning baseline

## Roles
Tenant owner manages membership and billing; administrator publishes policy; reviewer accesses assigned cases; developer manages API/webhooks; auditor reads minimal audit exports. Vitalos support has metadata-only access. Security/privacy operators have separately granted scopes. Billing operators cannot reveal identity images. No universal support role with permanent document access.

## Case workflow
Create review when policy finds ambiguity or requests an alternative. Queue prioritises age and service commitment, not inferred protected traits. Reviewer claims a time-limited lease; stale clients cannot overwrite a newer decision. Display required checks, supplier findings, provenance, previous attempts and applicant communications. Available actions: request additional evidence, approve by documented method, decline with reason, escalate or close as incomplete. Record the reviewer, policy and exact evidence used. A second-review rule applies to high-impact overrides and managed-review disputes.

## Meaningful review
Reviewer must be able to change the business outcome and request new evidence; merely clicking through automated output is insufficient. Reviewers may not erase failed checks or assert a biometric pass contrary to evidence. If an alternative route succeeds, record the distinct method and assurance level. Provide applicant-safe reasons and a challenge path. Do not infer nationality or work eligibility from appearance.

## Appeals
Create an appeal linked to the original decision, preserve minimum necessary history, assign someone other than original reviewer where possible, acknowledge through the requesting organisation, and record a reasoned revised decision. Proposed customer-operated target: acknowledge in two working days and resolve or update within five; contract actual commitments before selling them. Protect evidence expiry while an authorised, time-limited appeal hold applies.

## Support access
Support creates a ticket, states purpose and requests time-bounded elevation. Tenant approval is required for ordinary content support where contract defines it; emergency security access follows a separately approved break-glass process. Log actor, reason, scope, start/end, objects viewed and outcome. Automatically expire grants and notify relevant owner. Require MFA and prohibit bulk export through support roles.

## Managed review expansion
Do not offer 24/7 human review before staff and coverage exist. M14 defines training, quality sampling, confidentiality, access locations, service hours, conflicts and escalation. Customer/Vitalos decision responsibilities must be contractual. Sampling evaluates reviewer consistency and false overrides using a lawful, minimised dataset. AI summaries remain assistive and must cite source fields; reviewers can inspect original evidence and reject a summary.


---

# Security threat model and control plan

Version 1.0 | 10 November 2026 | Planning baseline

## Assets and adversaries
Protect identity images, biometric outputs, applicant links, tenant boundaries, API credentials, outcome integrity, billing and audit evidence. Threat actors include fraudulent applicants, compromised customer accounts, malicious tenants, exposed support credentials, compromised dependencies and spoofed suppliers. Model browser, API, queue, provider, storage, admin and export boundaries independently.

| Threat | Control | Verification |
|---|---|---|
| Cross-tenant object reference | Authorised tenant context, composite keys, row policies | Enumerate object access under two test tenants |
| Forged provider approval | Raw-body signature validation, authoritative fetch, session binding | Forged/old callback cannot approve |
| Replay and duplicate billing | Nonces, expiry, unique event IDs, usage uniqueness | Repeated events produce one charge/outcome |
| Capture injection/spoofing | Evaluated supplier SDK, anti-replay and integration assessment | Independent authorised attack evaluation |
| Stolen applicant link | One-use exchange, short lifetime, restrictive cookies | Reuse and wrong-session denial |
| Document parser exploitation | Isolated parsing, content/type/size controls, no outbound network | Malicious fixture quarantined |
| Prompt injection in documents | Untrusted text, no privileged tools, schema/provenance validation | Document instruction cannot alter policy |
| Webhook SSRF | HTTPS allowlist policy, DNS/IP checks, block private/link-local ranges and redirects | Rebinding/private-target tests |
| Operator abuse | Least privilege, MFA, timed grants, immutable audit | Expired elevation fails |
| Sensitive telemetry | Structured allowlist logging, no session replay, redaction | Automated canary PII scans |
| Supplier compromise | Minimal transfer, scoped secrets, kill switch, reconciliation | Outage/compromise tabletop |
| Cost exhaustion | Quotas, per-destination caps, spend reservation | Concurrent requests cannot exceed cap |

## Secrets and authentication
Use managed secrets and workload identities; no cloud keys in repositories or browser code. API keys are hashed and scoped, with rotation overlap and immediate revocation. Require strong MFA for privileged users, prefer phishing-resistant methods where supported. Step-up authentication for evidence export, role elevation and key changes. Session idle/absolute timeouts, CSRF protection for cookie commands, secure cookies and content security policy are required.

## Software supply chain
Pin dependencies, lockfiles, automated vulnerability checks, secret scanning, protected branch reviews and signed/traceable build artifacts. GitHub CI authenticates to cloud by scoped OIDC, not long-lived secrets. PR jobs cannot deploy production or access real evidence. Infrastructure plan and policy checks precede apply. Separate production deployment identity from application runtime and migration roles.

## Assurance release gate
External application penetration test before GA, focused on multi-tenancy, evidence access, webhooks and privilege escalation; separate biometric/injection assessment appropriate to the chosen supplier. No unresolved critical/high findings at release. Medium findings need owner, deadline and compensating controls. Model vendor evaluation is not certification of the whole Vitalos application. Maintain a vulnerability intake and coordinated remediation process.

## Incident handling
Contain exposed paths, revoke credentials and preserve minimal forensic evidence without deleting audit history. Identify affected tenants and records, involve privacy lead, assess contractual/regulatory notification duties and communicate accurately. Do not publish unverified root cause. Restore only from known-good artifacts and rerun deletion tombstones. Full procedure and exercises are in the operations runbook.


---

# Privacy architecture and DPIA working draft

Version 1.0 | 10 November 2026 | Planning baseline

Status: working assessment requiring facts, accountable owners and professional review before live biometric processing. It is not legal advice, a signed DPIA, a certification or a substitute for a customer's assessment.

## Processing description
Purpose: help a requesting business establish an applicant's identity for onboarding. Proposed flows: invitation, notice/choice, supported ID capture, selfie/liveness, supplier checks, policy result, customer review, retention/deletion. Subjects initially adults. Data includes contact details, identity attributes, document images, biometric processing outputs, device/session signals and decisions. Do not infer sensitive traits or reuse evidence for marketing.

## Roles and grounds
Working model: customer controller for onboarding; Vitalos processor for those instructions; specialist suppliers subprocessors where contract supports that chain. Vitalos may separately be controller for its own account administration/security, requiring a separate purpose and analysis. Independent fraud-network or model-training use would change roles and is excluded. Record an Article 6 basis and, for recognition, an applicable Article 9 condition before capture. Explicit consent cannot be presumed freely given in employment contexts; provide and assess genuine alternatives. Refer to source register S01–S03.

## Necessity and alternatives
Compare non-biometric document review, in-person checking and approved digital-ID routes against the specific fraud problem. Record why the chosen checks are proportionate. Do not demand biometric capture merely because the API supports it. Assess accessibility, poor-device exclusion, false decisions, economic impact and appeal. Customer policy must document the intended effect of automation and applicable safeguards under current law; counsel must verify the relevant rules at launch.

## Risk assessment
| Risk | Initial severity | Mitigation | Residual decision |
|---|---|---|---|
| Identity evidence exposure | High | Minimal collection, encryption, strict access, short retention | Owner review after test |
| False rejection affecting employment | High | Uncertainty handling, alternative, meaningful review/appeal | Customer approval required |
| Invalid consent or legal basis | High | Purpose-specific grounds and alternatives | No real processing until resolved |
| Supplier reuse or foreign access | High | DPA, location/transfer review, no training terms | Supplier acceptance required |
| Unequal model performance | High | Representative evaluation, monitored errors, fallback | Assurance owner approval |
| Retention beyond purpose | Medium/high | Enforced expiry and deletion reconciliation | Exercise evidence required |
| Function creep | High | No gallery/training reuse; change assessment | Product governance required |

## Controller completion fields
Legal entity and contacts; customer purpose; subject categories and expected volumes; chosen legal grounds and necessity; approved alternatives; suppliers and processing/support countries; transfer mechanism where applicable; detailed retention by category; notices; rights response procedure; assessment of automated decisions; consultation feedback; residual risks; DPO/adviser advice; accountable sign-off/date; review trigger. Blank fields remain launch blockers rather than invented facts.

## Rights and notices
Notice identifies requesting controller, purpose, data, suppliers/categories, processing locations, retention criteria, rights and support. Separate required acknowledgement from optional consent. Provide deletion/access routes that do not demand disproportionate new ID evidence. Requests involving customer-controlled data route to that customer; track statutory deadlines based on current jurisdictional advice. Never promise instant deletion from immutable backups; describe restricted retention and expiry accurately.

## Retention/transfer control
Adopt the proposed profile in the data model only after customer ratification. Location controls cover support, logs, backups, model processing and subprocessors, not just the database. AWS London core does not imply every supplier processes in the UK. AWS Face Liveness documentation currently lists Ireland rather than London for European processing; any use needs explicit region/transfer design. A UK-only contract must disable incompatible providers.

## Review triggers
New country, age-assurance/minors, new supplier, face gallery, training use, material model change, automated adverse outcome, longer retention, managed review or a security incident. Reassess before enabling the change. Maintain DPA, subprocessor register, processing record and deletion evidence alongside this assessment.


---

# Regulatory scope and assurance roadmap

Version 1.0 | 10 November 2026 | Planning baseline

## Claim discipline
Identity checking is one input to customer compliance. Do not sell full KYC/AML, right-to-work, DBS, right-to-rent, eIDAS or age-assurance compliance solely because ID/selfie APIs pass. Certification and registration attach to a defined service and scope. Supplier status is evidence about that supplier, not an automatic Vitalos certification.

## UK workforce path
M00–M07: general onboarding identity assurance with accurately limited claims. In parallel, map desired workforce use cases to current UK digital verification services trust framework and supplementary codes. Obtain advice from an appropriate conformity assessment body, identify required assurance and evidence, and budget independently. Government sources now distinguish current framework versions and service registration. Verify requirements and current certificates at procurement and again before launch (S04–S06).

## Age assurance path
Before M11, define service type, age threshold, geographic rules and child-data implications. Select evaluated methods and a fallback, then test effectiveness, robustness, reliability and fairness for the complete flow. A facial estimate is not an exact birth date. Keep privacy and age-assurance evaluations separate but coordinated. Do not claim regulatory approval without a specific verifiable basis (S07).

## EU/digital ID path
Before M12, confirm target wallet availability, verifier/relying-party registration obligations, trust lists, protocols, certification and attribute policy in each jurisdiction. EUDI readiness is not uniform adoption. Integrate cryptographic credential verification with consent/attribute minimisation and replay resistance. Verify current standards rather than freezing guessed protocol versions in this pack (S08).

## Evidence programme
Maintain certification/assessment register with service name, issuing body, scope, version, issue/expiry, limitations and link. Include security audit, supplier PAD/face evaluation, accessibility assessment, data-protection review and disaster-recovery exercise. Do not call NIST testing a blanket product certification. ISO/IEC presentation-attack assessment does not establish immunity to every injection attack; document tested threat classes.

## Launch matrix
For each country/use case/module: legal applicability assessment, supplier contract, supported documents, processing geography, notices, retention, test results, claim wording and accountable owner. Default disabled if incomplete. Exporting the software to a new region does not automatically enable collection from that region.


---

# Infrastructure, environments and deployment design

Version 1.0 | 10 November 2026 | Planning baseline

## Proposed AWS topology
Core region eu-west-2 London. Separate cloud accounts or equivalently strong boundaries for development, staging and production. Route 53/approved DNS and ACM certificates; CloudFront for static assets only; load balancer to ECS Fargate API/web and worker services; RDS PostgreSQL; S3 evidence buckets; SQS and dead-letter queues; KMS; Secrets Manager; CloudWatch and CloudTrail. WAF/rate limiting as justified. Private database, encrypted storage and restricted egress. Evaluate networking/NAT and database baseline costs before approving the topology; a pilot cost cap may require a simpler managed deployment with equivalent security.

## Residency
Explicit region matrix per service, logs, backups and supplier. No automatic cross-region evidence replication. A separately approved EU supplier region can coexist with UK core only under disclosed, reviewed processing terms. Region capability must be checked in account before provisioning; AWS liveness is not assumed available in London (S09).

## Infrastructure as code specification
Terraform modules: account_baseline, network, compute, database, evidence_storage, queues, identity, observability and DNS. Inputs include region, allowed environments, deletion protection, retention, tenant limits and budget alerts. Store remote state encrypted with locking and restricted access. Policy checks deny public evidence buckets, public database ingress, unrestricted runtime IAM and unencrypted persistence. This pack contains a design, not executable production Terraform or cloud changes.

## Deployment flow
PR -> lint/types/unit/contract/security checks -> review -> immutable build -> staging deployment -> migration test -> smoke and acceptance tests -> release record -> controlled production rollout -> monitor -> promote or rollback. Source SHA, image digest, migration version, configuration digest and policy versions recorded. Canary uses permitted synthetic transactions; do not upload real IDs into staging. Health checks avoid sensitive data.

## Rollback
Keep previous application image deployable; expand/contract schemas tolerate mixed versions. For a bad adapter/model change, disable new sessions for affected capability, preserve evidence and route existing work for reconciliation. Do not mass-reclassify old decisions automatically. Data rollback is a separate recovery procedure, not routine app rollback. Replaying queues after rollback requires deduplication and correct schema versions.

## Recovery
Automated backups, point-in-time recovery where supported and protected backup access. Proposed GA RPO 15 minutes/RTO four hours; prove with a timed isolated restore, application reconciliation, deletion tombstone replay and evidence access verification. A database snapshot alone does not restore provider sessions, object evidence or external webhooks. Maintain recovery manifest across these systems.

## Environment gates
Development uses dummy/sandbox suppliers and synthetic data. Staging mimics isolation and IAM but excludes live biometric data. Pilot production has tenant allowlist, capped volume and staffed incident contact. General production requires M07 gates and approved actual cost cap. No deployment credentials in prompts, docs or screenshots.


---

# Testing, biometric evaluation and acceptance plan

Version 1.0 | 10 November 2026 | Planning baseline

## Layers
Unit-test domain transitions and policies; database integration-test tenant isolation and concurrent updates; contract-test provider/event schemas; browser-test applicant and reviewer journeys; security-test access, uploads and webhooks; load-test queues/rate limits; exercise recovery/deletion. Deterministic synthetic fixtures belong in CI. External biometric evaluation uses a separately governed, licensed dataset and cannot be replaced with fake happy-path images.

## Proposed pilot operational targets
At least 85% of users who start a supported journey complete without assisted support; under 15% manual review among eligible completed submissions; metadata API p95 under 500 ms at stated load; zero cross-tenant leaks, missing decision provenance or duplicate charges in acceptance runs. These are planning targets, not observed performance or promises. Report denominator and exclusions, and adjust through controlled decisions after discovery. Fraud/security thresholds cannot be weakened merely to meet conversion targets.

## Biometric metrics
Measure false match rate and false non-match rate at fixed operating threshold, failure to acquire, genuine-user completion, presentation-attack acceptance/rejection and injection attack outcomes. Document test population, capture devices, lighting, document quality, image age and subgroup confidence intervals. Model score is not a probability unless calibrated and documented. NIST performance on a reference dataset does not guarantee Vitalos end-to-end results.

## Statistical sufficiency
For zero observed errors in n independent representative trials, the rough one-sided 95% upper bound is 3/n. Zero errors in 100 trials therefore does not establish a 0.01% error rate. Correlated captures and repeated identities violate naive independence; use subject-disjoint splits and suitable clustered uncertainty. Set numeric security operating points with the assurance specialist and customer risk owner before pilot. Mark them unresolved until evidence exists; do not invent a universal threshold.

## Dataset governance
Document provenance, permitted purposes, participant agreement where applicable, demographic collection grounds, deletion rights, train/test separation, licence and access control. No scraping people's faces. No transfer of production identity evidence to developer laptops or general LLMs. Keep a locked holdout and a separate attack suite; training/evaluation contamination invalidates results. Audit annotation and ground-truth disputes.

## Release evidence
Each acceptance scenario produces test version, environment, commit, policy/adapter versions, result, redacted evidence and reviewer. Failed security cases block release; operational misses require explicit decision with remediation and no false service claims. Third-party reports must match the purchased SDK/model version and deployment mode. Test again after material supplier updates.

## Monitoring after launch
Track quality and completion by supported device/document group, appeals and confirmed fraud with delayed labels. An approval rate alone measures neither accuracy nor fairness. Alert on sudden distribution changes, increased retries or liveness errors. Pause affected methods rather than approving on error. Maintain retrospective evaluation of materially changed decisions without silently rewriting history.


---

# Pricing hypotheses and unit economics

Version 1.0 | 10 November 2026 | Planning baseline

## Public benchmarks
Research on 10 November 2026 found Stripe UK's listed ID-and-selfie price of £1.25 per completed verification and Persona Essential starting at $250/month with a 12-month minimum. AWS's published US East liveness example is $0.015/check at its first tier. The latter is not ID verification and must not be used as a full cost benchmark. Verify current quotes, taxes, volumes and platform rights before contracting (S10–S12).

## Proposed experiments, not published offers
Starter hypothesis: £99/month platform plus £2.50 per completed basic verification. Growth hypothesis: £299/month plus negotiated usage, richer integrations and policy controls. Enterprise: annual commitment, scoped support and negotiated processing. Start with a paid, capped pilot if buyers agree. Do not promise these rates until supplier quotes and review/support costs are measured. No unlimited verification plan or free trial that exposes uncapped SMS/provider costs.

## Billing definitions
Session created is not automatically billable. Define the sellable unit as one completed verification package under a frozen commercial version; list whether terminal failed/inconclusive attempts and retries incur charges. Reflect supplier economics without confusing customers. Technical failures receive the agreed credit policy. Each charge has unique ledger key, source session/attempt, quantity, unit price, currency and invoice reference. Adjustments append credit events; never mutate settled invoices.

## Illustrative 1,000-verification month
Revenue: £99 platform + 1,000 × £2.50 = £2,599. Supplier: 1,000 × £1.25 = £1,250. Assumed review burden 10% × four minutes × £20/hour = £133.33. Assumed messaging £30, variable infrastructure £150, variable support £100. Contribution before fixed staff, tax, payment fees and other overhead = £935.67 (36.0%). Review labour may be a customer cost in self-review; retain it in the sensitivity analysis to expose managed-service economics. Every assumption is editable in financial_model.csv.

## Sensitivity
At 20% review and eight minutes each, review cost becomes £533.33 and contribution falls to £535.67 before other omitted costs. Add supplier retries and contract minimums separately: effective supplier unit cost = max(contract minimum, usage charges) / billable completed units. Track cost for abandoned sessions if supplier bills attempts. Low volume can be uneconomic even with a nominal markup.

## Spend controls
Actual monthly cap is unresolved. Before live supplier/cloud use, set owner-approved caps and alerts at 50/80/100%; hard-stop new paid sessions or messaging at the agreed hard threshold while preserving privacy and existing-case access. Reserve estimated cost atomically for concurrent sessions and reconcile actual invoices. Do not present cloud credits as a recurring sustainable cost reduction.


---

# Pilot, commercial launch and growth plan

Version 1.0 | 10 November 2026 | Planning baseline

## Pilot preparation
Recruit three design partners in the target segment. Each has an operational sponsor, developer/integration owner and controller contact. Agree allowed use case, supported documents, maximum volume, success metrics, review responsibility, fees and termination/data deletion. Use a synthetic walkthrough before live activation. No partner or contract currently exists.

## Pilot execution
Start one tenant with a small daily cap and staffed monitoring, then expand only after reconciled outcomes and review feedback. Weekly review: funnel, cost, errors, appeals, provider quality, accessibility and deletion backlog. Record qualitative feedback alongside measured data. Do not deliberately expose applicants to failing flows for an experiment. Keep an immediate disable-new-sessions control.

## Go/no-go for GA
M07 evidence passed; customer contract/processing terms agreed; billing reconciles; no critical/high security findings; meaningful alternative/review path; support rota and incident contact; tested recovery; verified scope/claims; provider contract and capacity; actual price/cap approved. Outstanding certification cannot be hidden in small print while marketing implies it. Founder signs release record with specialist inputs.

## Customer onboarding runbook
Verify customer organisation and purpose; configure tenant, policy, region and retention; appoint admins/reviewers; train on uncertainty and escalation; create sandbox API keys; test signed webhook and reconciliation; agree invoice unit; perform synthetic acceptance; activate capped production; review first week. Customer requests for prohibited surveillance or unsupported identification are declined or escalated before activation.

## Marketing scope
Explain who the product is for, the capture-to-review journey, supported checks, privacy controls, integration and transparent pricing. Security page states implemented controls and actual assessment status, not aspirational badges. Publish evidence-backed case studies only with permission. Developer docs include sandbox, API examples, signature validation and failure semantics. Capture leads through ordinary business contact forms, never a public real-ID demo.

## Growth sequencing
First deepen recruitment/contractor integrations. Add address-document checks if pilot demand supports them. Add database/NFC/digital ID/age assurance under distinct business cases and module gates. Enter regulated financial services only after appropriate scope, operational controls and due diligence; the first workforce architecture is reusable but not automatically sufficient. Quarterly review retention, gross contribution, sales cycle, repeat usage and support effort before expanding headcount or R&D.


---

# Operational runbooks and service ownership

Version 1.0 | 10 November 2026 | Planning baseline

## Ownership and targets
Founder is initial service owner; appoint a primary and backup incident contact before real-data pilot. Proposed pilot coverage is UK business hours; no 24/7 claim without coverage. GA core API SLO target 99.9%, evaluated separately from suppliers and applicant completion. Proposed alerts: provider failures above 5% over 10 minutes with minimum 20 requests; oldest processing job above 10 minutes; deletion past due; webhook delivery backlog; any evidence exposure or isolation alarm. Tune using actual baseline.

## Provider outage
1. Confirm failure with status and internal metrics, without exposing applicant evidence.
2. Open incident; pause new attempts for affected capability and show a service-delay message.
3. Preserve pending sessions, cost reservations and provider references.
4. Reconcile uncertain calls before retry; use only pre-approved alternative routes.
5. Resume gradually, drain queues, reconcile charges/outcomes and notify affected customers.

## Suspected data breach
1. Activate incident lead/privacy/security contacts; preserve timeline and restricted forensic evidence.
2. Contain the route or revoke credentials; avoid destructive cleanup of logs.
3. Determine scope: tenants, subjects, data classes, locations and access history.
4. Assess required notifications and deadlines with privacy lead; prepare factual communications.
5. Remediate, independently verify containment, restore carefully and monitor.
6. Complete post-incident review with owner and dated actions. Never let an agent independently declare regulatory notification unnecessary.

## Deletion failure
Restrict access immediately when appropriate, retry idempotently, inspect provider deletion status and open supplier ticket without sending unnecessary evidence. Track primary, supplier and backup states separately. Escalate overdue deadlines to privacy owner. Do not mark completion on the basis of an HTTP request alone when supplier processing is asynchronous.

## Recovery exercise
Restore into an isolated environment with outbound provider/webhook calls disabled. Validate checksums and database/object consistency, apply deletion tombstones, verify tenant roles, reconcile outbox and provider state, measure RPO/RTO, then destroy exercise copies under policy. Production cutover requires incident owner decision and customer communication as applicable.

## Webhook backlog
Inspect endpoint status, signing-key rotation and retry schedule. Block unsafe URLs and private-network destinations. Alert customer developer; keep API reconciliation available. Manual replay reuses event ID and records operator/reason; it cannot create another charge. Quarantine permanently failing endpoints after the documented delivery window.

## Billing dispute
Trace invoice to usage ledger and provider invoice references; redact unrelated subject details. Determine duplicate, technical failure, retry or commercial misunderstanding. Issue a credit event under approved policy; do not modify evidence or past outcomes. Reconcile daily during pilot and monthly thereafter.

## Routine cadence
Daily pilot: processing, spend, errors, deletion and review queues. Weekly: incidents, access grants, supplier changes, customer feedback. Monthly: restore sample, invoice reconciliation, permission review and SLO report. Quarterly: full recovery/tabletop, privacy/coverage review and supplier certificate expiry. Every material incident gets a blameless review with measurable follow-up.


---

# Selective proprietary technology programme

Version 1.0 | 10 November 2026 | Planning baseline

## Investment thesis
Build proprietary capability only when it improves measured customer outcomes, economics or strategic independence. Candidate order: capture-quality assistance, document classification/extraction, rule-based consistency checks, then carefully scoped fraud models. Face matching, liveness and age estimation require substantially greater dataset, evaluation and assurance effort; they are not assumed achievable within the pilot timeline.

## Gates
R0 business case: volume, supplier cost, failure costs, specialist staffing and attainable improvement. R1 lawful dataset: provenance/licence, permitted purpose, representativeness, subject-disjoint split and deletion. R2 offline evaluation: locked holdout, baseline comparison, uncertainty, subgroup/device analysis and adversarial assessment. R3 shadow: no customer decision influence, bounded approved processing, compare outcomes and costs. R4 limited production: independent review, documented thresholds, rollback and explicit enablement. R5 expansion: sustained monitoring, incident handling and performance against contractual promises.

## Replacement criteria
Define a component-specific security floor before training. Candidate must be no worse than the deployed baseline at the agreed operating point with adequate evidence, meet latency/availability and subgroup requirements, and have economically credible total cost including annotation, compute, experts, maintenance and assurance. Better aggregate accuracy alone does not permit replacement. Record both false acceptance harm and exclusion harm.

## Model operations
Version training data manifests, code, dependencies, model weights, evaluation and deployment configuration. Signed artifact promotion; no unreviewed auto-retraining. Keep baseline rollback available and preserve original decision provenance. Monitor drift and delayed fraud labels; retraining requires documented dataset rights and re-evaluation. Suppliers may update models: contract for notice/version observability where possible and reassess material changes.

## Prohibited shortcuts
No scraped facial galleries, production evidence used by default, general LLM face comparison, fabricated certification, threshold tuning on locked holdout or evaluation claims based on tiny samples. Open-source code licences and pretrained-weight/data licences are distinct and both must permit the intended commercial use.

## Financing decision
M13 can conclude that continued licensing is best. That is a valid milestone outcome. Do not fund a proprietary biometric engine merely to satisfy the word proprietary. Maintain a research budget separate from production service budgets and require explicit approval for dataset purchase, specialist contracts or GPU commitments.


---

# AI-assisted engineering operating model

Version 1.0 | 10 November 2026 | Planning baseline

## Operating principle
Use founder-led agents for bounded implementation, tests and documentation. Human accountable owners remain responsible for contracts, privacy decisions, assurance and release. This is a proposed orchestration design; no agents, repository, cloud resources or application were launched by producing the pack.

## Roles
Coordinator reads the canonical requirements and selects dependency-ready work. Implementer changes one bounded module on an isolated branch/worktree. Verifier independently checks acceptance criteria and negative paths. Security reviewer inspects trust-boundary changes. Release controller assembles evidence and reports readiness; it cannot invent approvals. Prefer no more than two concurrent implementation tasks until CI capacity is measured. Parallel work must avoid shared schema/API ownership conflicts.

## Task lifecycle
planned -> ready -> in_progress -> review -> verified -> merged. blocked and abandoned require reason. Milestone completed only when all mandatory tasks pass and gate evidence is signed. Task record includes dependencies, owner role, specification links, acceptance, test artifacts, commit/PR and unresolved risk. Agents may not mark acceptance from prose alone.

## Repository rules
Read AGENTS.md, README and relevant domain spec before editing. Maintain smallest useful change. No production identity data in fixtures or prompts. No credentials in outputs. Use sandbox providers. No schema destruction, paid service purchase, new processing jurisdiction, policy weakening or production deployment without the owner's concrete authorisation. Do not repeatedly rebase every open PR; coordinate merge order and cancel superseded CI. Use reusable dependency caches and parallelise independent tests within actual runner capacity.

## Context and cost
Each task starts with only canonical docs, dependency outputs and current repository findings. Record tool/API spend in a local task ledger without secrets. Founder selects actual agent token and cloud budgets before execution. At a budget threshold, checkpoint work and report; do not silently switch to weaker security validation. Save commit and evidence before handoff. A failed test requires diagnosis; editing the test solely to accept broken behaviour is not completion.

## Independent verification
Verifier compares implemented behaviour to requirement and acceptance evidence, runs critical negative cases and checks actual diff. For biometric performance and legal/regulatory decisions, an agent review is preparation, not independent specialist assurance. No recursive unbounded sub-agent spawning. Coordinator assigns explicit scope, files and stop conditions.

## Milestone completion report
State implemented outcome, requirement IDs, tests/evidence, deployment state, migrations, security/privacy changes, known gaps, cost and next dependency-ready task. Say planned, implemented, verified and deployed distinctly. Report mock integrations as mocks. No production-ready claim when contract, evaluation or processing gates remain open.


---

# Commercial and governance working templates

Version 1.0 | 10 November 2026 | Planning baseline

These are drafting checklists, not executed agreements. Obtain appropriate legal review and complete business-specific facts before customer signature.

## Pilot statement of work
Parties/legal names; permitted onboarding purpose; initial adult population; supported document/country matrix; named users; period and volume cap; included checks; customer review responsibility; Vitalos support hours; measurable pilot objectives; fees and billable unit; supplier dependencies; data roles; retention; evidence export; termination/deletion; exclusions including scheme claims; contacts; acceptance meeting and change control.

## Data processing agreement schedule
Controller and processor identities; subject matter/duration; nature/purpose; data/subject categories; documented instructions; confidentiality; technical/organisational controls; subprocessors and change notice; processing locations/transfers; rights assistance; incident assistance; deletion/return and backup handling; audits; controller responsibilities; limitations requiring legal advice. Do not state that a supplier DPA automatically covers all Vitalos processing.

## Supplier assessment record
Supplier/legal entity, service/version, business owner, purpose, data fields, countries, processing/support locations, subprocessors, retention, deletion evidence, training-use terms, platform/resale rights, certification scope and expiry, commercial minimums, incident contact, exit route, unresolved risks and decision/date.

## Release record
Release ID, source SHA/artifact digest, milestone, supported scope, migrations, policy/adapter versions, functional tests, isolation/security evidence, privacy approval, supplier agreements, performance evidence, rollback exercise, known risks and owner decision. Required sign-offs must be actual named people and dates; blank means not signed.

## Customer review SOP acknowledgement
Reviewer trained on distinct checks and uncertainty; may request alternative; must not overwrite evidence; no downloads to personal devices; applicant challenge route; escalation contact; confidentiality and access location; training date and refresher schedule.

## Incident record
Incident ID, discovery time, reporter, severity, affected systems/tenants/data, containment, decision log, privacy assessment, communications, recovery evidence, root cause confidence, corrective actions with dates and owner, closure review.

## Change request
Proposer, problem, affected requirements/modules, proposed change, alternative, cost, processing impact, migration, test evidence, rollback, approval and implementation reference. Changes to threshold, provider, country or retention require corresponding privacy/assurance assessment.


---

# Sources, evidence limits and research register

Version 1.0 | 10 November 2026 | Planning baseline

Public sources reviewed during this conversation on 10 November 2026. Vendor claims are not independently verified performance results. Architecture, pricing proposals, budgets, milestones and targets are Vitalos planning recommendations, not source facts. No supplier quotes, customer interviews, penetration tests, legal opinions or biometric experiments have yet been obtained. Recheck volatile claims before procurement and launch.

| ID | Source | Relevance |
|---|---|---|
| S01 | [ICO lawful processing of biometric data](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/how-do-we-process-biometric-data-lawfully/) | Article 6 and Article 9 grounds; verify current guidance with adviser |
| S02 | [ICO biometric recognition](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/biometric-recognition/) | Recognition involves special category processing |
| S03 | [ICO special category data](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/special-category-data) | DPIA and additional conditions |
| S04 | [UK DVS framework collection](https://www.gov.uk/government/collections/uk-digital-verification-services-trust-framework) | Current framework versions; recheck before certification |
| S05 | [Join DVS register](https://www.gov.uk/guidance/join-the-digital-verification-services-register) | Service certification and supplementary codes |
| S06 | [Find registered DVS](https://www.gov.uk/guidance/find-registered-digital-verification-services) | Validate exact supplier service scope |
| S07 | [Ofcom age assurance](https://www.ofcom.org.uk/online-safety/protecting-children/age-assurance) | Evaluate complete method effectiveness |
| S08 | [European Digital Identity](https://commission.europa.eu/topics/digital-economy-and-society/european-digital-identity_en) | Wallet programme context; not universal availability |
| S09 | [AWS Face Liveness FAQ](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness-faq.html) | Available European region lists Ireland; do not assume London |
| S10 | [Stripe UK Identity](https://stripe.com/gb/identity) | Public ID/selfie pricing benchmark; contract terms require quote |
| S11 | [Persona pricing](https://withpersona.com/pricing) | Essential entry benchmark; actual package quote needed |
| S12 | [AWS Rekognition pricing](https://aws.amazon.com/rekognition/pricing/) | Component pricing differs from full verification |
| S13 | [Persona selfie recognition](https://withpersona.com/product/verifications/selfie-recognition/) | Vendor feature claims, not independent validation |
| S14 | [Persona government ID](https://withpersona.com/product/verifications/government-id) | Reference portfolio scope |
| S15 | [Persona Document AI](https://withpersona.com/product/verifications/document-ai) | Supplemental documents and fraud features |
| S16 | [Persona database checks](https://withpersona.com/product/verifications/authoritative-databases-issuing-sources) | Coverage differs from ID image checks |
| S17 | [Persona webhooks](https://docs.withpersona.com/webhooks) | Event-driven integration pattern |
| S18 | [Regula architecture](https://docs.regulaforensics.com/develop/doc-reader-sdk/overview/architecture/) | Mobile SDK for chip processing |
| S19 | [Innovatrics toolkit](https://developers.innovatrics.com/docs/enterprise-identity/idv-toolkit/) | Client/server verification components |
| S20 | [Yoti age verification](https://developers.yoti.com/age-verification) | Age assurance integration options |
| S21 | [NIST face verification evaluation](https://pages.nist.gov/frvt/html/frvt11.html) | Performance assessment, not Vitalos certification |
| S22 | [NIST demographic effects](https://pages.nist.gov/frvt/html/frvt_demographics.html) | Subgroup evaluation context |

## Evidence acquisition backlog
Attach buyer interviews and pilot intents at M00; provider contracts, exact coverage and region matrix at M01; API/adapter fixture evidence at M04; DPIA and security review at M05; pilot operational/cost measurements at M06; restore and independent penetration test at M07; component-specific evaluations for M08–M13. Keep confidential artifacts outside the public repository and link only redacted evidence references.


---

# Programme risks, dependencies and ownership

Version 1.0 | 10 November 2026 | Planning baseline

| Risk | Impact | Owner | Response and gate |
|---|---|---|---|
| Supplier resale rights unavailable | Product model invalid | Founder | Obtain written rights before integration commitment, M01 |
| UK-only customer terms conflict with provider region | Processing breach | Privacy/engineering | Capability routing and alternative supplier, M01 |
| Invalid biometric legal ground | Live processing cannot proceed | Customer/privacy | Resolve before any real-data pilot, M05 |
| Insufficient buyer demand | Commercial failure | Founder | Ten interviews/three intents; narrow segment, M00 |
| Founder capacity too small | Schedule slippage | Founder | Bounded WIP, separate specialists, revise date |
| Poor mobile completion | Low conversion/exclusion | Product | Device evaluation and meaningful fallback, M03/M06 |
| Provider outages | Stalled onboarding | Engineering | Pending states, reconciliation, pre-approved fallback |
| High review/retry costs | Negative margin | Commercial | Measure attempt economics before pricing, M06 |
| Cross-tenant evidence exposure | Severe privacy/security harm | Security | Defence in depth and independent tests, M05/M07 |
| Unsupported compliance claims | Customer harm and liability | Founder/legal | Claim register and launch matrix |
| Model demographic disparity | Unfair exclusion | Assurance | Representative evaluation, uncertainty, alternative |
| Deletion not propagated | Retention breach | Privacy/engineering | Supplier receipts and backup tombstones |
| Scope expands before core reliability | Delayed pilot | Product | Separate expansion milestones and gates |
| Agent marks mocks as production | False readiness | Engineering | Evidence-based status and independent verifier |
| Proprietary models lack data rights | Unusable R&D | Research/privacy | R1 gate; retain supplier baseline |

## External dependencies
Cloud and DNS account access, repository ownership, payment processing account, supplier procurement, customer design partners, privacy adviser, security assessor, evaluation dataset and support coverage. None are presumed available. Work on synthetic interfaces can continue while contracts progress, but real-data activation cannot bypass missing dependencies.

## Escalation
Any evidence exposure, unauthorised collection or policy bypass pauses affected live processing. Budget exhaustion pauses new spend while preserving rights requests and access to existing cases. Schedule pressure does not lower identity assurance or privacy gates. Risk acceptance requires a named accountable person and does not override legal obligations.


---

# Stage-by-stage roadmap and milestone gates

Version 1.0 | 10 November 2026 | Planning baseline

## Schedule interpretation
Planning windows are estimates from a future agreed kickoff, not deadlines or commitments. Procurement, legal assessment and independent testing can lengthen the critical path. Expansion waves overlap only with staffed owners and CI capacity. Founder-led capacity must be replanned after the first two milestones. No milestone is currently implemented.

The core critical path is M00 → M01 → M02 → M03 → M04 → M05 → M06 → M07. M08/M09/M11/M12/M13/M14 branch after GA; M10 follows M08 as a conservative mobile/document capability sequencing choice. External work can begin earlier, but feature activation cannot bypass its dependencies.

| Milestone | Owner | Planning window | Exit gate |
|---|---|---|---|
| M00 — Product and commercial definition | Founder/product | Weeks 1–2 | Buyer evidence, chosen initial segment, named owners and actual cost cap recorded; no real-data processing. |
| M01 — Supplier and processing feasibility | Engineering/privacy | Weeks 2–4 | Contracted or explicitly selected pilot route with no unresolved disqualifying rights/location issue; privacy assessment plan approved. |
| M02 — Secure platform foundation | Engineering | Weeks 3–5 | AT-01/02 pass; CI, role revocation and environment separation demonstrated. |
| M03 — Applicant sessions and contact checks | Product/engineering | Weeks 5–7 | AT-03/04/15/23 pass; no client-authoritative success or unbounded messaging. |
| M04 — Identity evidence and decision pipeline | Engineering/assurance | Weeks 7–9 | AT-05/06/07/11 pass; result provenance and no approval on technical errors proven. |
| M05 — Review, privacy and security readiness | Engineering/privacy/security | Weeks 9–11 | AT-08/09/10/24 pass; no unresolved critical/high issue; lawful processing and accountable review established. |
| M06 — Controlled commercial pilot | Founder/product/engineering | Weeks 12–16 | AT-12/13 pass; actual pilot evidence supports commercial direction and captures gaps without invented accuracy claims. |
| M07 — General availability | Founder/security/operations | After pilot gates | AT-14 plus full regression pass; scope-limited launch signed with actual evidence and support capacity. |
| M08 — Supplemental Document AI | Product/engineering | Expansion wave 1 | AT-16 passes; extraction never masquerades as authenticity; approved module economics and data lifecycle. |
| M09 — Authoritative database checks | Commercial/engineering/privacy | Expansion wave 1 | AT-17 passes; access is contracted and no-match is not automatically fraud. |
| M10 — NFC document assurance | Engineering/assurance | Expansion wave 2 | AT-18 passes; decoded-only chip data cannot receive authenticated status. |
| M11 — Age assurance | Product/privacy/assurance | Expansion wave 2 | AT-19 passes; specialist review and use-case compliance assessment completed before real minor data. |
| M12 — Digital ID and EUDI | Engineering/privacy/assurance | Expansion wave 3 | AT-20 passes; named scheme onboarding and protocol conformance evidenced. |
| M13 — Selective proprietary replacement | Research/privacy/assurance | Separate R&D programme | AT-21 passes; gate may conclude continued licensing is preferable; no automatic model replacement. |
| M14 — Managed review and market expansion | Operations/commercial/privacy | Demand-led expansion | AT-22 passes; operational staffing and exact regulatory/service scope match commercial claims. |

## Task graph and evidence
delivery/tasks.json contains 60 dependency-linked tasks. Their implementation must be refined into repository-specific subtasks during planning without changing the parent acceptance gate. All tasks begin planned. Attach code commits, redacted test/assessment artifacts and review records; external non-code tasks require authentic contract, interview or assessment records. The pack validator checks graph integrity, not real-world milestone completion.

## Definition of done
Requirement implemented or external deliverable obtained; relevant tests/assessment pass; negative behaviour verified; security/privacy implications addressed; docs updated; reviewer signs; deploy/rollback impact stated; no hidden mocks; no unsupported marketing claims. GA additionally requires operational readiness, actual budget and release authority.


---

# Acceptance scenarios and evidence checklist

Version 1.0 | 10 November 2026 | Planning baseline

## AT-01 — Cross-tenant isolation

Requirement: VV-001.

Procedure: Create tenants A and B and objects in each. Attempt reads, writes, downloads, exports and queued work using A against B.

Expected: Deny access without object/PII leakage; no cross-tenant references persist.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-02 — Credential revocation

Requirement: VV-002.

Procedure: Revoke a scoped key/membership and repeat sensitive commands, including an existing browser session.

Expected: Access denied within documented revocation window; audit reason recorded.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-03 — Creation idempotency

Requirement: VV-003.

Procedure: Submit identical creation key/body concurrently; then reuse key with different body.

Expected: Same session and one reservation for identical requests; conflict for changed body.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-04 — Accessible capture

Requirement: VV-004.

Procedure: Complete supported journey using small-screen mobile, keyboard and screen reader; deny camera access.

Expected: Usable guidance and alternative path; no false fraud result for device limitations.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-05 — Incomplete evidence

Requirement: VV-005.

Procedure: Return ID pass and match pass but missing/inconclusive liveness.

Expected: No automatic approval; required check remains visible.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-06 — Forged callback

Requirement: VV-006.

Procedure: Send invalid signature, expired signature and callback for another session; fire client SDK success.

Expected: No authoritative approval; invalid events rejected or quarantined.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-07 — Frozen policy

Requirement: VV-007.

Procedure: Publish policy v2 while session bound to v1 processes; replay v1 evidence.

Expected: Original version used and reproducible trace retained.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-08 — Review concurrency

Requirement: VV-008.

Procedure: Two reviewers act on same case revision; attempt to overwrite failed liveness.

Expected: Only valid revision wins; stale write conflicts; original check immutable.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-09 — Deletion lifecycle

Requirement: VV-009.

Procedure: Delete subject, delay supplier completion, restore a backup containing old evidence.

Expected: Access blocked; state not complete prematurely; tombstone reapplied before restored service.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-10 — Telemetry leakage

Requirement: VV-010.

Procedure: Use synthetic canary names/numbers/tokens in test evidence; scan logs/traces/errors.

Expected: No sensitive canaries or raw evidence in telemetry; access events retained.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-11 — Webhook retries

Requirement: VV-011.

Procedure: Return 500 then 200; duplicate event; configure private IP endpoint and DNS-rebinding fixture.

Expected: Stable signed event ID, bounded retries, no duplicate effect and no private-network delivery.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-12 — Invoice integrity

Requirement: VV-012.

Procedure: Reconcile duplicates, failed calls, retries, credit and supplier invoice to usage ledger.

Expected: Each charge accounted for; credit append-only; concurrent caps enforced.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-13 — Workforce integration

Requirement: VV-013.

Procedure: Integrate two Workforce tenants and receive out-of-order outcome events.

Expected: Correct tenant and newest decision version; identity result never asserted as work eligibility.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-14 — Recovery

Requirement: VV-014.

Procedure: Restore database/object references, replay deletion tombstones and reconcile queues in isolation.

Expected: Measured RPO/RTO meet approved targets; no unintended supplier calls or customer webhooks.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-15 — OTP abuse

Requirement: VV-015.

Procedure: Repeated/concurrent sends, wrong code attempts, expired/reused code and spend cap reached.

Expected: Rate/cost limits hold; code single-use; contact result not legal identity.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-16 — Document extraction

Requirement: VV-016.

Procedure: Submit inconsistent address/date, low-confidence text and malicious instructions embedded in a document.

Expected: Provenance/uncertainty shown; no privileged instruction execution; authenticity separate.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-17 — Database limitations

Requirement: VV-017.

Procedure: Return no coverage, no match, partial and unavailable from source fixtures.

Expected: Distinct outcomes; no-match never automatically labels fraud.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-18 — Untrusted NFC

Requirement: VV-018.

Procedure: Read valid-format chip payload with bad signature/untrusted issuer and interrupt capture.

Expected: Cannot claim authenticated chip identity; safe retry/fallback with retained reason.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-19 — Borderline age

Requirement: VV-019.

Procedure: Run near-boundary evaluated cases, failed liveness and alternative-route cases.

Expected: Uncertainty/fallback policy applied; no exact-age claim; approved retention enforced.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-20 — Credential replay

Requirement: VV-020.

Procedure: Use wrong nonce/audience, stale credential, untrusted issuer and replayed presentation.

Expected: Cryptographic/session failures rejected; only approved attributes returned.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-21 — R&D promotion

Requirement: VV-021.

Procedure: Candidate has higher aggregate score but worse subgroup/security-floor results.

Expected: Promotion denied; baseline remains live; shadow never changes customer decisions.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-22 — Managed reviewer scope

Requirement: VV-022.

Procedure: Reviewer attempts unassigned tenant export after access grant expiry.

Expected: Access denied and audited; second-review rules enforced.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-23 — Unsupported scope

Requirement: VV-023.

Procedure: Request disabled country/document/provider region combination.

Expected: Reject before capture/charge; approved alternative described.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.

## AT-24 — Export minimisation

Requirement: VV-024.

Procedure: Default export then privileged evidence export; revoke user and retry link.

Expected: Default omits unnecessary PII; privileged access expires/revokes and is audited.

Evidence: environment, commit, fixture ID, redacted output and reviewer. Status: not run.


---

# API, webhook and integration contract guide

Version 1.0 | 10 November 2026 | Planning baseline

## Contract status
contracts/openapi.json is a proposed OpenAPI 3.1 contract for the initial external API. It is machine-readable and structurally validated by the included validator, but has not been tested against a running implementation. Internal admin/auth/upload/consent APIs require implementation-stage contracts; they are deliberately not exposed as public unrestricted endpoints. Example host uses the reserved .example domain and is not live.

## Authentication and tenant boundary
Bearer API key, scoped to one tenant and operations. Derive tenant from credential; never accept a caller's tenant_id as authority. Rate-limit by tenant/key and return 429 with Retry-After. Scope examples: sessions:create/read, decisions:write, deletions:create/read, webhooks:manage. Customer browser uses authenticated application sessions and server-side authorisation rather than storing service keys. API errors include code, safe message, request_id and optional field errors, never raw supplier exceptions.

## Idempotency and concurrency
Require Idempotency-Key on create/decision/deletion/replay operations. Scope keys by tenant and operation; store request digest and response for at least seven days (proposed). Identical request returns original response; conflicting payload returns 409. Decisions include expected_revision; stale revision returns 409. GET lists use opaque cursor and limit <=100. Timestamp values are RFC3339 UTC. Object IDs are opaque strings.

## Hosted token exchange
Created session may include a short-lived one-use hosted URL. Browser exchanges token server-side, then removes it from address/history. Set no-referrer and avoid third-party analytics. URL is returned only to an authorised session creator, not routine list/read responses. Expiry and refresh are separate from session expiry. Evidence downloads are omitted from this public contract pending scoped evidence-access API review.

## Outbound webhook protocol
Envelope: id, type, occurred_at, tenant_reference, resource_id, resource_version and data containing minimal status/reasons. Header X-Vitalos-Timestamp is epoch seconds; X-Vitalos-Signature is v1=hex HMAC-SHA256 over timestamp + '.' + exact raw body using endpoint secret. Receiver checks constant-time signature, five-minute timestamp tolerance and stable event-ID deduplication. Sender generates fresh timestamp/signature on each retry; secret rotation supports overlapping active secrets with a key identifier. Do not log secrets or bodies with sensitive fields.

Proposed retries: immediate, 1 minute, 5 minutes, 30 minutes, 2 hours, 8 hours and 24 hours with jitter. Persist attempts; customer can reconcile through GET and request replay. At-least-once delivery means client must handle duplicates and out-of-order resource versions. Acknowledge after durable receipt. A 2xx is delivery acknowledgement, not proof customer business processing succeeded. Endpoint URLs must pass SSRF protections described in security plan.

## Event catalogue
verification.created; verification.processing; verification.action_required; verification.review_required; verification.completed; verification.expired; verification.cancelled; deletion.updated. Completed events include outcome and decision revision, not a passport or face embedding. New decision revision creates a new event. Deletion status is independent of verification outcome.

## Workforce integration
Store tenant-specific Verify credential in Workforce server secrets. Create session with opaque worker reference; receive signed events; fetch authoritative latest result before applying a consequential workflow transition. Keep identity verification separate from right-to-work/qualification checks. On deletion, coordinate controller instructions across both products rather than assuming deletion in one deletes the other.
