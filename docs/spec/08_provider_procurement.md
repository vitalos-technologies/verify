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
