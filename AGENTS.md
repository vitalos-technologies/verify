# Vitalos Verify engineering instructions

Read README.md, 02_decisions_and_assumptions.md and 20_agent_execution_guide.md first. Requirement IDs and milestone gates are authoritative. All tasks start planned; this pack is documentation, not a built product.

Use synthetic data and approved sandboxes. Never commit identity evidence, secrets or applicant tokens. Preserve tenant isolation and immutable policy/decision revisions. Provider outage is not identity failure. Never claim certification, legal clearance, test completion or production deployment without evidence.

Work on one dependency-ready task at a time unless explicitly coordinating isolated agents. Separate implementation from verification. Do not weaken tests or security gates to finish. Ask for missing external decisions only when they block the next concrete action; continue independent reversible work.

Owner authority is required for spending, production changes, live identity collection and changes to processing scope. At milestone completion report source commits, test evidence, actual status, unresolved risks and next task. Do not publish a website or application merely because this documentation pack exists.

## Repository specifics
- Canonical spec: `docs/spec/` (do not edit task statuses there; it is the planning baseline). Track status in `delivery/status.json` from evidence only.
- Code: `services/api` (Python, FastAPI, psycopg). Run `uv run ruff check src tests` and `uv run pytest` before every commit.
- Migrations are forward-only SQL in `services/api/migrations`; never edit an applied file, add a new one.
- Runtime DB roles (`vv_app`, `vv_worker`) must never own tables or get BYPASSRLS. New tenant tables need `tenant_id`, composite keys and a `tenant_isolation` policy.
- The DummyProvider and `ZZ` coverage are mocks; never describe them as real verification.
- Record deviations from the spec in `docs/decisions.md`.
- UI copy rule (owner instruction, 2026-11-10): minimal text. Short heading plus at most one short line per screen; no explanatory paragraphs or repeated information. Keep only what a user needs to act; the alternative route stays in the footer.
- Send updated screenshots to the owner whenever UI changes.
