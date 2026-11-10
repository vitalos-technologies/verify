# Pilot plan and spending cap

| Field | Value |
|---|---|
| Status | **PROPOSED — owner to approve.** No partner, contract, supplier or cloud account exists yet. Nothing here authorises spending. |
| Based on | Spec 02 §Budget (illustrative non-labour envelope £500–£1,500/month), spec 16 §Spend controls (50/80/100% alerts, hard stop), spec 17 §Pilot preparation/execution, `docs/spec/delivery/financial_model.csv` |
| Closes | M00-T04 (approved spending cap) once signed below |

## 1. Proposed monthly spending cap

**Proposed cap: £750 per month non-labour**, for the pilot period.

Why £750: spec 02 gives £500–£1,500 as an illustrative envelope and warns the low end cannot carry meaningful verification volume. £750 covers a minimal two-environment AWS setup plus a capped pilot volume (~100–150 completed verifications at public benchmark supplier prices), without committing to the high end before any pilot revenue or supplier quote exists.

| Line | Proposed monthly allowance | Basis | Notes |
|---|---|---|---|
| AWS staging + production (fixed baseline: database, containers, load balancer, NAT, logs, KMS, backups) | £350 | Planning estimate — **not a quote**; check with AWS Pricing Calculator before approving | Biggest uncertainty. Spec 14: a simpler deployment may be needed if this is exceeded. Keep staging scaled down when not in use. |
| Identity supplier usage (pilot verifications incl. retries) | £250 | ~100–150 completed checks at the public £1.25 Stripe UK benchmark, or ~100 at ~£2 | **Supplier minimums excluded** — see §2 |
| Email (applicant codes, console magic links) | £20 | Low volume | SES or equivalent |
| Tools (domain, monitoring, error tracking free tiers, GitHub) | £80 | Estimate | No paid sign-ups without owner approval |
| Contingency | £50 | — | |
| **Total** | **£750** | | |

### Alerts and hard stop

| Threshold | Spend | Action |
|---|---|---|
| 50% | £375 | Email alert to owner. Review trend in weekly pilot review. |
| 80% | £600 | Email alert. Owner decides: continue, slow invitations, or reduce staging. |
| 100% | £750 | **Hard stop on new paid sessions and messaging** (tenant caps / disable new sessions — see below). Existing cases, outcomes, reviews, exports, deletion and privacy requests keep working (spec 16). |

How it's enforced:
- **AWS Budgets** at 50/80/100% (Terraform module `infra/terraform/modules/budget`; budgets are in USD — owner sets `monthly_limit_usd` from the approved GBP figure: [Owner to complete: exchange rate used]). AWS Budgets alert; they do not stop spend on their own.
- **Application caps**: each tenant has a monthly **verification count** cap (`monthly_session_cap`) and a message cap; new sessions beyond the cap are refused with `quota.monthly_cap_reached` (built — `services/api/src/vv/service.py`). These are counts, not pounds: set them so that count × expected unit cost stays inside the cap. [Owner to complete: per-partner monthly and message caps.] A platform-wide £ hard stop across all tenants is **not built yet** — until it is, the owner enforces 100% by lowering tenant caps or disabling new sessions.
- **Supplier dashboard cap / alert** where the supplier offers one. [Owner to complete after contracting]

### Outside the cap (approve separately)

| Item | Amount |
|---|---|
| Supplier contract minimums or set-up fees | [Owner to complete after RFI] |
| External penetration test | [Owner to complete: quote] |
| Privacy adviser / solicitor (DPIA, DPA, supplier contract) | [Owner to complete: quote] |
| Accessibility participant incentives (5 people) | [Owner to complete] |
| Biometric / injection assessment (spec 11) | [Owner to complete] |
| Insurance (professional indemnity, cyber) | [Owner to complete] |

## 2. Pilot shape (proposed)

| Item | Proposal |
|---|---|
| Partners | 3 design partners (spec 17), each with operational owner, integration owner and controller contact |
| Start | One partner first; add the next only after a clean week of reconciled outcomes |
| Volume cap | Up to **100 completed verifications per month across all partners** to start; per-partner daily cap **10**. Raise only by owner decision with cap headroom. |
| Duration | 8–12 weeks |
| Applicants | Adults only; documents enabled per supplier coverage and test evidence |
| Review | Customer reviewers (trained); Vitalos does not review cases |
| Monitoring | Staffed by Vitalos on pilot days; immediate "disable new sessions" switch |
| Fees | [Owner to decide: free capped pilot vs paid pilot at hypothesis price] |

## 3. Gates before the first real applicant

- [ ] Owner approves this cap (sign below)
- [ ] Supplier contracted with acceptable DPA, no-training and resale/platform terms (`docs/procurement/`)
- [ ] AWS accounts, budgets and CloudTrail set up (`docs/infrastructure/aws-setup.md`)
- [ ] Partner signed pilot agreement and DPA; partner's DPIA Part B signed (`docs/compliance/DPIA.md`)
- [ ] Notice wording approved by the partner (controller)
- [ ] Manual accessibility tests passed (`docs/compliance/accessibility-test-pack.md`)
- [ ] External security test done; no open critical/high (`docs/compliance/security-test-brief.md`) — or owner records an explicit, limited-pilot risk decision with the privacy adviser
- [ ] Deletion tested end to end with the real supplier
- [ ] Synthetic walkthrough with the partner (demo script)

## 4. Weekly pilot review (spec 17)

| Measure | This week | Target (hypothesis) |
|---|---|---|
| Invitations sent | | |
| Start → complete without help | | ≥ 85% |
| Manual review rate (eligible completed) | | < 15% |
| Reviewer minutes per case | | Less than partner's current |
| Retries per completed check | | |
| Supplier errors (separate from applicant outcomes) | | |
| Appeals opened / resolved | | |
| Accessibility issues reported | | 0 blockers |
| Deletion backlog | | 0 overdue |
| Spend to date vs cap | | ≤ 100% |
| Cost per completed verification | | |

Record denominators and sample sizes; small numbers are not proof.

## 5. Owner approval

| Item | Decision | Name | Date |
|---|---|---|---|
| Monthly non-labour cap (£750 proposed) | [Approve / change to £___] | | |
| Pilot volume cap | [ ] | | |
| Free or paid pilot | [ ] | | |

Blank = not approved.
