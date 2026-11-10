# Identity supplier scorecard — desk research

| Field | Value |
|---|---|
| Status | **Desk research from public web pages only, checked 10 Nov 2026. Not supplier-confirmed.** No supplier has been contacted. Scores are provisional and must be re-scored from RFI answers, sandbox tests and contract terms. |
| Method | Spec 08 §Selection method weights and disqualifiers |
| Shortlist | Stripe Identity, Regula, Innovatrics, Yoti (spec 08). AWS Rekognition Face Liveness noted as a **component** only. |
| Use case scored | Adult identity verification for UK recruitment/contractor onboarding, sold by Vitalos to many customers as a platform, web (mobile browser) capture, UK processing preferred, 30-day evidence retention, no supplier training on customer data |

Public marketing pages do not prove access, resale rights, white-labelling, certification inheritance or data residency (spec 08). Every "unknown" below is an RFI question in `docs/procurement/rfi-email-drafts.md`.

## 1. Disqualifier check (spec 08)

Disqualify regardless of score for: unapproved resale; missing lawful processing arrangements; unsupported required region; unverifiable deletion; unacceptable evidence access.

| Supplier | Resale / platform use | Processing arrangements | Region | Deletion | Evidence access / reuse | Result |
|---|---|---|---|---|---|---|
| Stripe Identity | **Public terms prohibit it**: "Reselling as an independent ID verification service… For example, your primary business is selling ID verification to other businesses" is an unsupported use case [S-ST2] | Role wording not stated on the FAQ [S-ST3] | Not stated publicly | Redaction API; "may take up to 4 days" [S-ST4] | Biometric data kept 1 year and non-biometric data 7 years by default (business can delete sooner); images used to improve Stripe's biometrics, with training identifiers only with the user's permission [S-ST3] | **Disqualified unless Stripe gives written approval for Vitalos's platform model** |
| Regula | Unknown — no public reseller/OEM terms found | Self-hosted: Regula may not process applicant data at all (to confirm) | Self-hosted in Vitalos AWS eu-west-2 possible [S-RG1] | Under Vitalos control if self-hosted | Unknown: licence-server telemetry content | **Pass, pending RFI** |
| Innovatrics | Partner Program for system integrators and ISVs exists; terms not public [S-IN3] | Unknown | On-premises / private cloud / SaaS [S-IN1]; SaaS regions not stated | Unknown | Unknown | **Pass, pending RFI** |
| Yoti | Standard terms cl. 5.3: no resale/sublicensing/sharing "except with the prior written consent of Yoti" [S-YO3] | Yoti is **controller** for DBS/RTW/RTR framework checks; **processor** for other IDV checks [S-YO2, S-YO3] | Data kept in UK; may go to Yoti's security centre in **India** for manual checks [S-YO2] | Yoti accesses data up to 28 days, then stores per client retention [S-YO2] | Standard terms cl. 5.5 authorise use of client data to improve products and maintain an internal fraud database; R&D data kept 6 years [S-YO2, S-YO3] | **Conditional — needs negotiated terms** (written resale consent; opt-out of cl. 5.5 b–c; no India transfer or approved transfer) |

## 2. Weighted scorecard (provisional)

Score 1–5 (5 best) from public evidence. Weighted score = Σ(score ÷ 5 × weight). Max 100.

| Criterion (weight) | Stripe Identity | Regula | Innovatrics | Yoti |
|---|---|---|---|---|
| Use-case / document coverage (20%) | 3 — IDs "from over 100 countries"; GA for GB-based businesses [S-ST1, S-ST2] | 5 — "16,000+ document templates"; chip (NFC) reading [S-RG1, S-RG2] | 3 — VIZ, MRZ, barcode, NFC reading; no public country list [S-IN1] | 4 — UK-centred; certified for UK RTW/RTR/DBS identity checks (outside Vitalos's current scope) [S-YO1] |
| Measured security / performance (20%) | 2 — no public PAD/injection report found | 4 — iBeta PAD Level 1 and Level 2 letters for Face SDK mobile builds, latest Android Level 2 Dec 2025 [S-RG3]; no public injection-attack (IAD) certificate found; **web capture not covered by the letters seen** | 5 — CLR Labs ISO/IEC 30107-3 PAD "Substantial", Liveness Service 3.1.0, valid 24 Jun 2026–23 Jun 2028 (mainly Android) [S-IN2]; CEN/TS 18099 injection-attack certification claimed [S-IN1]; NIST FRTE 1:1 "top-ranked" (vendor claim) | 4 — vendor states SOC 2 and ISO 27001; anti-spoofing liveness for DBS standard/enhanced [S-YO1, S-YO4]; independent liveness report not checked |
| Privacy / region / retention (20%) | 2 — location not stated; long default retention; product-improvement use [S-ST3] | 5 — self-hosting keeps evidence in Vitalos's eu-west-2 account (to confirm no data leaves via licensing) | 4 — self-hostable; SaaS region and retention unknown | 3 — UK storage, but India manual-check transfers and data reuse clauses [S-YO2, S-YO3] |
| Commercial / platform rights (15%) | 1 — resale prohibited [S-ST2]; £1.25 per ID+selfie verification public UK price [S-ST1] | 3 — annual licence priced by verification volume; no public prices or reseller terms [S-RG4] | 3 — Partner Program for ISVs; no public prices [S-IN3] | 2 — resale needs written consent [S-YO3]; public G-Cloud list prices (RTW £1.80, DBS £2.00–£2.50, in-branch £8.50, set-up £150 portal / £2,000 integrated, monthly minimum £30 / £500) [S-YO4] — not a quote to Vitalos |
| Capture / accessibility (10%) | 4 — hosted flow, "Localised in 53 languages" [S-ST1]; accessibility conformance unknown | 3 — SDK/web components; Vitalos builds and owns the UI (more control, more work) | 3 — SDK components; accessibility unknown | 4 — hosted page, portal, SDK; **Post Office in-branch route** is a ready non-biometric/assisted alternative [S-YO4] |
| Integration / operations (10%) | 5 — mature API, webhooks, test mode; no servers to run | 2 — Vitalos runs and patches the processing service; licence management | 3 — SaaS or self-hosted options | 4 — portal, hosted page, SDK, API [S-YO5] |
| Portability (5%) | 3 | 4 — results returned to Vitalos; no supplier-held evidence if self-hosted | 4 | 3 |
| **Weighted total** | **52.0** | **75.0** | **73.0** | **69.0** |
| Disqualifier status | **Disqualified (resale)** unless written approval | Pending RFI | Pending RFI | Conditional |

Regula and Innovatrics are within desk-research error of each other. RFI answers decide.

## 3. Recommendation (provisional)

| Route | Supplier | Why | Must be confirmed before contract |
|---|---|---|---|
| **Primary** | **Regula** (Document Reader + Face SDK, self-hosted in Vitalos AWS eu-west-2) | Highest provisional score. Widest public document-template coverage. Self-hosting can keep applicant evidence inside Vitalos's own UK account, which simplifies the processor chain, transfers and the 30-day deletion promise. Independent PAD letters exist for named Face SDK versions. | (1) Written platform/OEM rights to serve many customers. (2) **Web (mobile browser) liveness** evidence, not only native mobile, and any injection-attack testing. (3) What the licence service sends to Regula (no images or personal data). (4) Price for pilot volume and minimums. (5) Ownership, development and support locations (standard supply-chain due diligence for all suppliers). |
| **Fallback** | **Innovatrics** (IDV toolkit / platform, self-hosted or SaaS) | Strongest *current* independent liveness evidence found (PAD certificate valid to 2028; injection-attack certification claimed). Partner Program aimed at ISVs suggests platform rights are obtainable. Self-hosting option. | Same five questions; plus document/country matrix (not public) and SaaS region if used. |
| Parallel option | Yoti | UK-specific; in-branch Post Office route could serve as an assisted alternative; future path if Vitalos ever enters RTW/DBS (separate scope, spec 13). | Written resale consent; exclusion of cl. 5.5 (b)–(c) reuse; no or approved India transfer; processor (not controller) role for Vitalos's checks. |
| Benchmark only | Stripe Identity | Fastest to integrate and has a public UK price, but public terms prohibit Vitalos's model. Ask once whether Stripe would approve; otherwise use only as a price/UX benchmark. | Written approval of platform model. |
| Component | AWS Rekognition Face Liveness | Liveness only — **not** document verification. iBeta PAD Level 1 and 2 (Oct 2023 letter) [S-AW1]. Not offered in London: nearest European region listed is **Ireland** [S-AW1]. Requires the Amplify UI SDK. AWS may use inputs to improve services unless an **AWS Organizations AI services opt-out policy** is applied [S-AW1]. | Only consider if the chosen document supplier lacks acceptable web liveness; needs transfer assessment for Ireland and the opt-out policy (see `docs/infrastructure/aws-setup.md`). |

**Next step:** send all four RFIs in parallel (owner sends; drafts in `rfi-email-drafts.md`), request sandboxes with synthetic material, then re-score this sheet from written answers. Spec 08 procurement exit gate still applies: founder approves economics and rights; privacy owner approves processing and transfers; engineering passes sandbox contract tests; assurance owner validates evaluation scope.

## 4. RFI question register (unknowns found in desk research)

| # | Question | Stripe | Regula | Innovatrics | Yoti |
|---|---|---|---|---|---|
| Q1 | May Vitalos use the service to provide verification to its own business customers (platform/OEM/resale), under Vitalos's brand? | Public terms say no — ask for written approval | ? | ? | Needs written consent (cl. 5.3) |
| Q2 | Country/document/version matrix | ? | ? (16,000+ templates — which are enabled for web) | ? | ? |
| Q3 | Web/mobile-browser capture: PAD and injection evaluation reports for the exact SDK versions | ? | Letters seen are mobile/Android | CLR report mainly Android | ? |
| Q4 | Processing and support locations; subprocessors | ? | Self-hosted: does anything leave our account? | SaaS region? | India manual checks — can it be excluded? |
| Q5 | Retention defaults and minimum configurable retention; deletion API with confirmation | Default 1 yr biometric / 7 yr other; redaction ≤ 4 days | n/a if self-hosted | ? | 28-day access then client retention |
| Q6 | Training / product-improvement use of customer data; can it be switched off contractually? | Product-improvement use stated | ? | ? | Cl. 5.5 authorises it — must be excluded |
| Q7 | Controller/processor role for our use case | ? | ? | ? | Processor for non-framework IDV — confirm |
| Q8 | Price at 100 / 1,000 / 10,000 completed verifications per month; minimums; set-up; billable retry definition | £1.25 public (≤ 2,000/month) | ? | ? | G-Cloud list: RTW £1.80 etc. — ask for our use case |
| Q9 | False-match / false-non-match operating points and demographic evidence | ? | ? | NIST FRTE (which algorithm version?) | ? |
| Q10 | Certification scope and expiry | ? | iBeta letters (versions) | CLR certificate (version 3.1.0, to 2028) | DVS certificate — confirm current entry on the [DVS register](https://www.gov.uk/guidance/find-registered-digital-verification-services) |
| Q11 | SLA, incident notice, model-change notice, exit/export support | ? | ? | ? | Terms allow platform changes "with no prior warning" [S-YO3] — negotiate notice |

## 5. Sources (all accessed 10 Nov 2026)

| ID | Source | What it supports |
|---|---|---|
| S-ST1 | https://stripe.com/gb/identity | £1.25 ID+selfie, 35p ID number lookup, "over 100 countries", 53 languages, live capture, redaction |
| S-ST2 | https://docs.stripe.com/identity/use-cases | GA for businesses in GB, JP, US; unsupported use: reselling as an ID verification service |
| S-ST3 | https://support.stripe.com/questions/stripe-identity-faq | Biometric 1 year / non-biometric 7 years; images used to improve biometric technology; training identifiers only with permission |
| S-ST4 | https://support.stripe.com/questions/managing-your-id-verification-information | Redaction can take up to 4 days (as summarised by search results — re-read before relying) |
| S-RG1 | https://regulaforensics.com/llms.txt | 16,000+ document templates; on-premises or cloud |
| S-RG2 | https://docs.regulaforensics.com/develop/doc-reader-sdk/overview/architecture/ | Mobile SDK chip processing (spec S18) |
| S-RG3 | https://www.ibeta.com/wp-content/uploads/2025/12/251210-Regula-PAD-Level-2-Confirmation-Letter-Android.pdf ; https://ibeta.com/wp-content/uploads/2025/03/250321-Regula-PAD-Level-2-Confirmation-Letter.pdf | iBeta PAD Level 2 letters for named Face SDK versions |
| S-RG4 | https://support.regulaforensics.com/hc/en-us/articles/360036943712-Pricing-SDK-Licensing-Models ; https://docs.regulaforensics.com/develop/doc-reader-sdk/overview/licensing/ | Licence models; online licence counts transactions |
| S-IN1 | https://www.innovatrics.com/identity-verification-integrators/ | On-prem/private cloud/SaaS; VIZ/MRZ/barcode/NFC; CEN/TS 18099 headline; NIST FRTE claim |
| S-IN2 | https://idtechwire.com/innovatrics-liveness-earns-renewed-certification-as-toolkit-resists-injection-tests/ | CLR Labs PAD Substantial, Liveness Service 3.1.0, valid 24 Jun 2026–23 Jun 2028 (secondary source — verify on CLR Cert registry) |
| S-IN3 | https://www.innovatrics.com/partner-program/ | Partner Program for system integrators and ISVs |
| S-YO1 | https://www.biometricupdate.com/202206/yoti-post-office-digital-id-service-first-certified-by-uk-for-employee-vetting | First certified IDSP for RTW/RTR/DBS (2022) |
| S-YO2 | https://www.yoti.com/privacy/identity-verification-ukdiatf | Controller/processor split; 28-day access; UK storage; India manual checks; R&D 6 years; training with client permission; last updated 9 Sep 2026 |
| S-YO3 | https://cdn.aws.yoti.com/wp-content/uploads/2026/06/Yoti-Organisation-TCs-v4.9-19-June-2026.pdf | Standard terms v4.9: cl. 3.1 non-sublicensable licence; cl. 5.3 resale needs written consent; cl. 5.4–5.5 data use incl. product improvement and internal fraud database; Schedule 2 processor terms (AWS, Azure, affiliates as subprocessors) |
| S-YO4 | https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-15/documents/702818/615462452489660-pricing-document-2026-01-28-0928.pdf | G-Cloud 15 public price list (28 Jan 2026) for Yoti ID for DBS/RTW/RTR |
| S-YO5 | https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-15/documents/702818/615462452489660-service-definition-document-2026-01-27-0941.pdf | Delivery modes: SDK, API, no-code portal, web, native app |
| S-AW1 | https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness-faq.html | Regions (Ireland, not London); iBeta PAD L1/L2; AI services opt-out |
