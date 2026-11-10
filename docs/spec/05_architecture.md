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
