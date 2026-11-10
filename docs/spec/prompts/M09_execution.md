# M09: Authoritative database checks — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 09_verification_modules.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver authoritative database checks within its defined scope. Dependencies: M07. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Source contracts: Obtain permitted-purpose agreements and country/source coverage.
2. Matching adapter: Implement source provenance, freshness, partial/no-match/unavailable semantics.
3. Policy integration: Route ambiguous matches to review, cap identifier collection and cost.
4. Coverage validation: Test legitimate variations, stale records and outages before enabling each source.

Exit gate: AT-17 passes; access is contracted and no-match is not automatically fraud.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
