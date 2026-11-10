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
