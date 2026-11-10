# M10: NFC document assurance — execution prompt

Read README.md, 02_decisions_and_assumptions.md, 09_verification_modules.md, 03_master_requirements.md, 20_agent_execution_guide.md and delivery/tasks.json. Inspect the actual repository before changing it; this pack may precede application scaffolding.

Objective: deliver nfc document assurance within its defined scope. Dependencies: M08. These dependencies require evidence; planned status is not completion.

Execute in order:
1. Mobile capability design: Select native SDK, supported devices, documents and handoff flow.
2. Chip authentication: Implement authenticated chip evidence and versioned trust-material validation.
3. Portrait binding: Bind chip portrait to session selfie and record exact assurance method.
4. Device and attack evaluation: Test interrupted reads, invalid signatures, trust material and injection fixtures.

Exit gate: AT-18 passes; decoded-only chip data cannot receive authenticated status.

First report repository findings, missing access and a concrete bounded implementation plan. Continue reversible authorised implementation using synthetic data. Do not fabricate supplier contracts, customer commitments, legal decisions, test results or certification. Mark externally blocked tasks precisely and continue independent work.

For each change implement meaningful positive and negative tests, run relevant checks, inspect the diff and collect redacted evidence. Use a separate verifier for the task when the orchestration environment supports it; do not claim independence for a self-review. Do not introduce paid services or production processing without actual owner-approved configuration and authority.

Report requirement IDs satisfied, source commits, tests, unresolved issues, costs, deployment state and next dependency-ready task. Stop milestone promotion when the gate is unmet. Update task status only from actual evidence.
