# M02: Secure platform foundation — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 05_architecture.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver secure platform foundation within its defined scope. Dependencies: M01. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Repository and CI: Create monorepo, lock dependencies, run CI with synthetic fixtures and protected review workflow.
2. Tenancy and identity: Implement OIDC, membership roles, MFA enforcement for privileged actions and scoped API keys.
3. Persistence boundaries: Implement composite tenant references, runtime row isolation and private evidence access design.
4. Environment baseline: Provision approved non-production infrastructure with budget alarms and no production evidence.

Exit gate: AT-01/02 pass; CI, role revocation and environment separation demonstrated.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
