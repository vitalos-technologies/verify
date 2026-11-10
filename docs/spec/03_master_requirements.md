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
