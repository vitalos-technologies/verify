# M07: General availability — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 18_operations_runbooks.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver general availability within its defined scope. Dependencies: M06. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Independent assessment: Complete external application test and relevant biometric integration evaluation; resolve high/critical findings.
2. Recovery exercise: Prove restore, deletion tombstones, queue reconciliation and proposed RPO/RTO.
3. Service readiness: Establish support coverage, incident contact, SLOs, status communications and invoice operations.
4. Release decision: Review complete release record, claims, pricing, supplier terms, rollback and signed launch decision.

Exit gate: AT-14 plus full regression pass; scope-limited launch signed with actual evidence and support capacity.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
