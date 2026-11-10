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
