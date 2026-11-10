# DRAFT — approved by owner as a negotiation baseline on 10 Nov 2026; not legal advice; not signed; requires solicitor review

# Identity supplier agreement — checklist and key terms

| Field | Value |
|---|---|
| Use | Vitalos's starting position when negotiating with the chosen identity supplier (see `supplier-scorecard.md`). Adapt to the supplier's own paper; do not sign anything based on this alone. |
| Parties | **Vitalos Technologies** [Owner to complete: legal name, company number, address] and **[Supplier legal entity]** |
| Roles | Customer (controller) → Vitalos (processor) → Supplier (**sub-processor**) for applicant identity checks. Where the supplier is self-hosted software that never receives personal data, the data protection schedule may be replaced by a "no access to personal data" warranty. |
| Solicitor | [Owner to complete: firm, date of review] |

## 1. Checklist — must have before signature

Status: ☐ not yet / ☑ agreed / ✖ refused (refused items on the disqualifier list end negotiation — spec 08).

| # | Term | Why | Status | Notes |
|---|---|---|---|---|
| 1 | **Platform / resale rights**: Vitalos may use the service to provide verification to its own business customers, under the Vitalos brand, without each customer contracting with the supplier | Disqualifier if missing (spec 08) | ☐ | |
| 2 | Supplier acts only as **processor/sub-processor** on documented instructions for Vitalos's checks (not as an independent controller) | Matches customer DPA chain (spec 12, 21) | ☐ | |
| 3 | **No training, product improvement, benchmarking or fraud-database use** of customer personal data, images, biometric templates or derived data, without Vitalos's separate written agreement per customer | ADR-12; disqualifier if unacceptable evidence access | ☐ | |
| 4 | **Processing locations** named for processing, storage, backups, logs, support and manual review; UK (or approved) only; no change without prior notice and right to object/terminate | Spec 12 §Retention/transfer control | ☐ | |
| 5 | **Subprocessor list** attached; 30 days' prior notice of changes; right to object; flow-down of equal terms | Spec 21 DPA schedule | ☐ | |
| 6 | **Deletion with confirmation receipts**: deletion via API per verification; completion receipt (reference, time, scope) within [Owner to complete: e.g. 7 days]; backups expire within [e.g. 35] days and are not restored into service without re-applying deletions | AT-09; deletion tracked as a separate target in `deletion.py` | ☐ | |
| 7 | **Retention** configurable to ≤ 30 days after decision (or zero retention after result fetch) | Owner-approved default | ☐ | |
| 8 | **Security incident notice** to Vitalos without undue delay and within [e.g. 24 hours] of awareness, with details needed for controller notifications | Customers' Art. 33 duties | ☐ | |
| 9 | **Model / SDK change notice**: [e.g. 30 days'] notice of material model, threshold or SDK changes; changelog; ability to pin versions; re-test window | Spec 15 §Release evidence | ☐ | |
| 10 | **Evaluation evidence**: copies of PAD/injection/accuracy reports for the exact versions supplied; updates when re-certified | Spec 11, 13, 15 | ☐ | |
| 11 | **Audit**: questionnaire answers, independent reports (ISO 27001 certificate, SOC 2 report), and a right to audit on reasonable notice or via third party | Art. 28(3)(h) | ☐ | |
| 12 | **SLA**: availability, support hours, response times, status page, service credits | Pilot operations | ☐ | |
| 13 | **Exit / data return**: export of results and any held evidence in a documented format; deletion certificate at end; reasonable transition support | Spec 08 portability | ☐ | |
| 14 | **Pricing**: unit prices, minimums, set-up, billable unit and retry definition, credits for technical failures, price-change notice | Spec 16 | ☐ | |
| 15 | Confidentiality, IP (Vitalos owns its data, policies and integrations), liability cap and indemnities appropriate to identity data | Solicitor | ☐ | |
| 16 | International transfer mechanism, if any transfer is approved (e.g. UK IDTA or Addendum) with transfer risk assessment | Adviser | ☐ | |
| 17 | Assistance with data subject rights, DPIAs and regulator enquiries | Art. 28(3)(e)–(f) | ☐ | |
| 18 | Applicant-facing notice: supplier agrees to be named as sub-processor; any end-user terms the supplier shows are approved by Vitalos | Spec 12 §Rights and notices | ☐ | |

## 2. Key terms — draft wording (baseline)

> Plain-English baseline for the solicitor to turn into contract language. Square brackets are open points.

### 2.1 Licence and platform rights
The Supplier grants Vitalos a non-exclusive licence for the Term to use the Services to provide identity verification to Vitalos's business customers ("Customers") as part of Vitalos's own products, under Vitalos's brand. Customers do not need a contract with the Supplier. Vitalos may name the Supplier as a sub-processor. [Exclusivity: none.] [Territory: UK customers; applicants may be anywhere where the Supplier supports the document.]

### 2.2 Data protection schedule (aligned to spec 21 §Data processing agreement schedule)

| Item | Draft content |
|---|---|
| Controller / processor identities | Each Customer is controller; Vitalos is processor; Supplier is Vitalos's sub-processor |
| Subject matter and duration | Identity checks for applicant onboarding, for the Term plus deletion period |
| Nature and purpose | Document authenticity, data extraction, face match and liveness checks, solely to return results to Vitalos |
| Data categories | Document images and extracted fields; selfie/liveness images or video; biometric templates/scores (special category); device/session metadata |
| Data subjects | Adult applicants and contractors of Customers |
| Instructions | Only on Vitalos's documented instructions (API calls and this agreement); notify if an instruction appears unlawful |
| Confidentiality | Staff access on need-to-know basis under confidentiality obligations |
| Security | Measures in [Annex: Supplier security measures]; encryption in transit and at rest; access logging |
| Subprocessors | Listed in [Annex]; 30 days' notice of change; right to object and terminate without penalty |
| Locations / transfers | Only [UK / named locations], including support and backups; no transfer without prior written approval |
| Rights assistance | Help Vitalos respond within [5] working days of request |
| Incident assistance | Notify within [24] hours; cooperate; no public statement naming Vitalos or Customers without consent |
| Deletion / return | Delete per verification on API request with receipt; delete all at end of Term with certificate; backups expire within [35] days |
| Audits | Annual reports and questionnaire; audit on [30] days' notice, at most yearly unless after an incident |
| No secondary use | No training, improvement, analytics on personal data, fraud databases or sharing with authorities except where legally required (with notice to Vitalos where lawful) |

### 2.3 Service levels (placeholders)

| Measure | Draft target |
|---|---|
| API availability (monthly) | [Owner to complete: e.g. 99.5%] |
| Support hours | [UK business hours minimum] |
| P1 response | [e.g. 1 hour] |
| Status page and incident updates | Yes |
| Service credits | [Owner to complete] |

### 2.4 Change management
[30] days' notice of material changes to models, thresholds, SDKs, processing locations or subprocessors. Ability to stay on a pinned version for at least [90] days. Security fixes may be faster with immediate notice.

### 2.5 Pricing (placeholders — no supplier price agreed)

| Item | Amount |
|---|---|
| Set-up fee | [Supplier quote] |
| Monthly / annual minimum | [Supplier quote] — minimums sit outside the proposed monthly cap; owner approval needed |
| Price per completed verification | [Supplier quote] |
| Billable unit, retries, abandoned sessions | [Supplier to define; Vitalos prefers billing only completed verifications] |
| Credits for supplier technical failures | [ ] |
| Price change notice | [90] days |

### 2.6 Term and exit
Initial term [12] months; Vitalos may terminate for convenience on [30–90] days' notice after the pilot, and immediately for a data breach, unapproved location/subprocessor change or loss of evaluation certification. On exit: export, deletion certificate, [60] days' transition support.

## 3. Supplier assessment record (spec 21) — fill on selection

| Field | Value |
|---|---|
| Supplier / legal entity | [ ] |
| Service / version | [ ] |
| Business owner | Temitope Agbola |
| Purpose | Applicant identity checks |
| Data fields | [ ] |
| Countries of processing / support | [ ] |
| Subprocessors | [ ] |
| Retention | [ ] |
| Deletion evidence | [ ] |
| Training-use terms | [ ] |
| Platform/resale rights | [ ] |
| Certification scope and expiry | [ ] |
| Commercial minimums | [ ] |
| Incident contact | [ ] |
| Exit route | [ ] |
| Unresolved risks | [ ] |
| Decision and date | [ ] — blank = not decided |
