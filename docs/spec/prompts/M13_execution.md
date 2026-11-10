# M13: Selective proprietary replacement — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 19_proprietary_R_and_D.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver selective proprietary replacement within its defined scope. Dependencies: M07. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Business and data case: Choose component and establish economic thesis plus lawful dataset provenance.
2. Offline evaluation: Build subject-disjoint evaluation with locked holdout and explicit security floors.
3. Shadow comparison: Run approved shadow evaluation with no decision influence and measured costs.
4. Replacement decision: Approve limited rollout only after independent evidence; otherwise retain supplier baseline.

Exit gate: AT-21 passes; gate may conclude continued licensing is preferable; no automatic model replacement.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
