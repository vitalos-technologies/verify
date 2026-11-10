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
