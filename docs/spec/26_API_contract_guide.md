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
