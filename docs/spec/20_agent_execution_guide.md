# AI-assisted engineering operating model

Version 1.0 | 10 November 2026 | Planning baseline

## Operating principle
Use founder-led agents for bounded implementation, tests and documentation. Human accountable owners remain responsible for contracts, privacy decisions, assurance and release. This is a proposed orchestration design; no agents, repository, cloud resources or application were launched by producing the pack.

## Roles
Coordinator reads the canonical requirements and selects dependency-ready work. Implementer changes one bounded module on an isolated branch/worktree. Verifier independently checks acceptance criteria and negative paths. Security reviewer inspects trust-boundary changes. Release controller assembles evidence and reports readiness; it cannot invent approvals. Prefer no more than two concurrent implementation tasks until CI capacity is measured. Parallel work must avoid shared schema/API ownership conflicts.

## Task lifecycle
planned -> ready -> in_progress -> review -> verified -> merged. blocked and abandoned require reason. Milestone completed only when all mandatory tasks pass and gate evidence is signed. Task record includes dependencies, owner role, specification links, acceptance, test artifacts, commit/PR and unresolved risk. Agents may not mark acceptance from prose alone.

## Repository rules
Read AGENTS.md, README and relevant domain spec before editing. Maintain smallest useful change. No production identity data in fixtures or prompts. No credentials in outputs. Use sandbox providers. No schema destruction, paid service purchase, new processing jurisdiction, policy weakening or production deployment without the owner's concrete authorisation. Do not repeatedly rebase every open PR; coordinate merge order and cancel superseded CI. Use reusable dependency caches and parallelise independent tests within actual runner capacity.

## Context and cost
Each task starts with only canonical docs, dependency outputs and current repository findings. Record tool/API spend in a local task ledger without secrets. Founder selects actual agent token and cloud budgets before execution. At a budget threshold, checkpoint work and report; do not silently switch to weaker security validation. Save commit and evidence before handoff. A failed test requires diagnosis; editing the test solely to accept broken behaviour is not completion.

## Independent verification
Verifier compares implemented behaviour to requirement and acceptance evidence, runs critical negative cases and checks actual diff. For biometric performance and legal/regulatory decisions, an agent review is preparation, not independent specialist assurance. No recursive unbounded sub-agent spawning. Coordinator assigns explicit scope, files and stop conditions.

## Milestone completion report
State implemented outcome, requirement IDs, tests/evidence, deployment state, migrations, security/privacy changes, known gaps, cost and next dependency-ready task. Say planned, implemented, verified and deployed distinctly. Report mock integrations as mocks. No production-ready claim when contract, evaluation or processing gates remain open.
