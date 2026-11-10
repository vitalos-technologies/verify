# Vitalos Verify — Complete Product and Engineering Pack v1.0

Prepared 10 November 2026. Start here.

This pack specifies a full staged identity-verification product, with supplier-backed onboarding first and selective proprietary capability later. It includes strategy, UX, architecture, data, contracts, security/privacy, delivery, execution prompts, tests and operations. It is a planning baseline: no application, supplier integration, cloud deployment, certification or legal approval has been completed by creating these files.

## Read first
1. 02_decisions_and_assumptions.md — accepted direction and unconfirmed facts.
2. 01_strategy.md and 03_master_requirements.md — scope and measurable requirements.
3. 24_delivery_roadmap.md — 15 milestones, exit gates and dependencies.
4. delivery/tasks.json — 60 planned tasks.
5. prompts/00_master_execution.md — handoff to Claude Code/Codex.

## How to use
Give the complete folder to your coding agent, not just the master prompt. Ask it to inspect the repository and begin M00. External decisions such as actual spending cap, supplier rights and lawful processing must be resolved before live operation. Synthetic prototyping can proceed without pretending those decisions exist. Keep this baseline under version control once the real repository is created.

## Document index
- [Product strategy and commercial thesis](01_strategy.md)
- [Decision register and planning assumptions](02_decisions_and_assumptions.md)
- [Master product requirements and traceability](03_master_requirements.md)
- [Experience, screens and design specification](04_user_experience.md)
- [Technical architecture and trust boundaries](05_architecture.md)
- [Data model and evidence lifecycle](06_data_model.md)
- [Session state machine and decision policy](07_sessions_and_policy.md)
- [Supplier procurement and adapter specification](08_provider_procurement.md)
- [Verification modules: detailed functional specification](09_verification_modules.md)
- [Case management, appeals and operational access](10_review_and_operations_console.md)
- [Security threat model and control plan](11_security_threat_model.md)
- [Privacy architecture and DPIA working draft](12_privacy_DPIA_working_draft.md)
- [Regulatory scope and assurance roadmap](13_regulatory_and_assurance.md)
- [Infrastructure, environments and deployment design](14_infrastructure_and_delivery.md)
- [Testing, biometric evaluation and acceptance plan](15_testing_and_evaluation.md)
- [Pricing hypotheses and unit economics](16_pricing_and_financial_model.md)
- [Pilot, commercial launch and growth plan](17_launch_and_growth.md)
- [Operational runbooks and service ownership](18_operations_runbooks.md)
- [Selective proprietary technology programme](19_proprietary_R_and_D.md)
- [AI-assisted engineering operating model](20_agent_execution_guide.md)
- [Commercial and governance working templates](21_contracts_and_customer_templates.md)
- [Sources, evidence limits and research register](22_sources_and_evidence.md)
- [Programme risks, dependencies and ownership](23_risk_register.md)
- [Stage-by-stage roadmap and milestone gates](24_delivery_roadmap.md)
- [Acceptance scenarios and evidence checklist](25_acceptance_scenarios.md)
- [API, webhook and integration contract guide](26_API_contract_guide.md)

## Machine-readable and execution files
- [Milestones](delivery/milestones.json)
- [Task graph](delivery/tasks.json)
- [Acceptance scenarios](delivery/acceptance_scenarios.json)
- [Financial assumptions](delivery/financial_model.csv)
- [Public API contract](contracts/openapi.json)
- Policy, webhook and task schemas and synthetic examples in contracts/.
- Master, verifier, release and 15 milestone prompts in prompts/.
- [Repository instructions](AGENTS.md)
- [Pack validator](validate_pack.py) and [validation report](VALIDATION_REPORT.json).

## Validation limits
Run python validate_pack.py from this directory. Install jsonschema in an isolated development environment for schema/example validation if unavailable. The validator checks references, dependency cycles, schema examples and required IDs. It does not prove application behaviour, legal compliance, provider performance or deployment readiness. Acceptance scenarios are not_run. See sources register for public evidence and outstanding acquisition work.

## Reading copy
MASTER_BLUEPRINT.md concatenates the authored specifications for convenient reading. Individual documents remain canonical for implementation. Do not edit the combined copy alone. All pricing, timelines and metrics labelled assumptions require validation. No credentials or real personal identity data are included.
