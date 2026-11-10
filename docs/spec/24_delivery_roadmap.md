# Stage-by-stage roadmap and milestone gates

Version 1.0 | 10 November 2026 | Planning baseline

## Schedule interpretation
Planning windows are estimates from a future agreed kickoff, not deadlines or commitments. Procurement, legal assessment and independent testing can lengthen the critical path. Expansion waves overlap only with staffed owners and CI capacity. Founder-led capacity must be replanned after the first two milestones. No milestone is currently implemented.

The core critical path is M00 → M01 → M02 → M03 → M04 → M05 → M06 → M07. M08/M09/M11/M12/M13/M14 branch after GA; M10 follows M08 as a conservative mobile/document capability sequencing choice. External work can begin earlier, but feature activation cannot bypass its dependencies.

| Milestone | Owner | Planning window | Exit gate |
|---|---|---|---|
| M00 — Product and commercial definition | Founder/product | Weeks 1–2 | Buyer evidence, chosen initial segment, named owners and actual cost cap recorded; no real-data processing. |
| M01 — Supplier and processing feasibility | Engineering/privacy | Weeks 2–4 | Contracted or explicitly selected pilot route with no unresolved disqualifying rights/location issue; privacy assessment plan approved. |
| M02 — Secure platform foundation | Engineering | Weeks 3–5 | AT-01/02 pass; CI, role revocation and environment separation demonstrated. |
| M03 — Applicant sessions and contact checks | Product/engineering | Weeks 5–7 | AT-03/04/15/23 pass; no client-authoritative success or unbounded messaging. |
| M04 — Identity evidence and decision pipeline | Engineering/assurance | Weeks 7–9 | AT-05/06/07/11 pass; result provenance and no approval on technical errors proven. |
| M05 — Review, privacy and security readiness | Engineering/privacy/security | Weeks 9–11 | AT-08/09/10/24 pass; no unresolved critical/high issue; lawful processing and accountable review established. |
| M06 — Controlled commercial pilot | Founder/product/engineering | Weeks 12–16 | AT-12/13 pass; actual pilot evidence supports commercial direction and captures gaps without invented accuracy claims. |
| M07 — General availability | Founder/security/operations | After pilot gates | AT-14 plus full regression pass; scope-limited launch signed with actual evidence and support capacity. |
| M08 — Supplemental Document AI | Product/engineering | Expansion wave 1 | AT-16 passes; extraction never masquerades as authenticity; approved module economics and data lifecycle. |
| M09 — Authoritative database checks | Commercial/engineering/privacy | Expansion wave 1 | AT-17 passes; access is contracted and no-match is not automatically fraud. |
| M10 — NFC document assurance | Engineering/assurance | Expansion wave 2 | AT-18 passes; decoded-only chip data cannot receive authenticated status. |
| M11 — Age assurance | Product/privacy/assurance | Expansion wave 2 | AT-19 passes; specialist review and use-case compliance assessment completed before real minor data. |
| M12 — Digital ID and EUDI | Engineering/privacy/assurance | Expansion wave 3 | AT-20 passes; named scheme onboarding and protocol conformance evidenced. |
| M13 — Selective proprietary replacement | Research/privacy/assurance | Separate R&D programme | AT-21 passes; gate may conclude continued licensing is preferable; no automatic model replacement. |
| M14 — Managed review and market expansion | Operations/commercial/privacy | Demand-led expansion | AT-22 passes; operational staffing and exact regulatory/service scope match commercial claims. |

## Task graph and evidence
delivery/tasks.json contains 60 dependency-linked tasks. Their implementation must be refined into repository-specific subtasks during planning without changing the parent acceptance gate. All tasks begin planned. Attach code commits, redacted test/assessment artifacts and review records; external non-code tasks require authentic contract, interview or assessment records. The pack validator checks graph integrity, not real-world milestone completion.

## Definition of done
Requirement implemented or external deliverable obtained; relevant tests/assessment pass; negative behaviour verified; security/privacy implications addressed; docs updated; reviewer signs; deploy/rollback impact stated; no hidden mocks; no unsupported marketing claims. GA additionally requires operational readiness, actual budget and release authority.
