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
