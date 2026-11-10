# M03: Applicant sessions and contact checks — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 04_user_experience.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver applicant sessions and contact checks within its defined scope. Dependencies: M02. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Session API: Implement idempotency, expiry, scoped token exchange and attempt lifecycle.
2. Applicant capture UX: Build mobile flow, versioned notice, capability checks, device handoff and alternative path.
3. Contact verification: Implement OTP expiry, send limits, abuse protection and spend reservation.
4. Accessible journey validation: Test keyboard/screen reader/mobile/error states and unsupported documents before capture.

Exit gate: AT-03/04/15/23 pass; no client-authoritative success or unbounded messaging.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
