# Supplier RFI email drafts

| Field | Value |
|---|---|
| Status | **Drafts only. Nothing has been sent.** The owner sends them from their own mailbox after review. |
| From | Temitope Agbola, Founder, Vitalos Technologies — [Owner to complete: email, phone, company number] |
| Basis | Spec 08 §Request for information; gaps from `docs/procurement/supplier-scorecard.md` |
| Before sending | Fill blanks; consider asking each supplier for their NDA first; attach nothing confidential; do not mention any prospect by name |
| Contacts | [Owner to complete for each: sales/partnership contact found via the supplier's website contact form] |

Each email is self-contained (common questions are repeated so each can be sent as-is).

---

## 1. Stripe Identity

**To:** [Owner to complete: Stripe sales contact via stripe.com/contact/sales]
**Subject:** Stripe Identity — platform use by a UK verification provider (pre-sales questions)

Hello,

I'm the founder of Vitalos Technologies, a UK company building Vitalos Verify: an identity-verification workflow for UK recruitment agencies and contractor platforms (applicant journey, case review, appeals and evidence lifecycle). We're choosing an identity-check engine for a small, capped pilot with adult applicants.

Your published use-case page lists "reselling as an independent ID verification service" as unsupported. Before anything else, please confirm:

**A. Could Stripe approve, in writing, Vitalos using Stripe Identity inside Vitalos Verify to verify applicants on behalf of Vitalos's business customers?** If not, we'll keep this as a benchmark only and won't take more of your time.

If yes, we'd be grateful for answers to the questions below.

1. Countries and document types (with versions) supported for UK-based businesses, and how that list changes.
2. What the result and confidence fields mean; whether scores are calibrated.
3. Liveness and injection-attack evaluation reports (lab, standard, level, date) and the exact model/SDK versions tested.
4. Mobile-browser and native support; accessibility conformance of the hosted flow (WCAG level).
5. Demographic and image-quality performance evidence.
6. False-match and false-non-match operating points used in production.
7. Certifications (scope and expiry).
8. Service levels and incident-notification commitments.
9. Processing and storage locations, **including support access**.
10. Subprocessors and how changes are notified.
11. Whether Stripe uses verification data to train or improve models, and whether that can be excluded by contract for all our end users.
12. Retention defaults, the minimum we can configure (we target 30 days after decision), deletion/redaction confirmation, and backup handling.
13. Controller/processor roles for this use and the data processing terms that apply.
14. Platform/resale rights (see A).
15. Minimum spend; pricing at 100, 1,000 and 10,000 completed verifications a month.
16. What counts as a billable verification, including retries and abandoned sessions.
17. Dispute and refund handling for technical failures.
18. Exit: data export and migration support.
19. Sandbox access using synthetic test material.

Thank you,
Temitope Agbola
Founder, Vitalos Technologies — vitalos.co.uk

---

## 2. Regula

**To:** [Owner to complete: Regula sales contact via regulaforensics.com]
**Subject:** RFI — Document Reader SDK + Face SDK for a UK multi-tenant verification platform

Hello,

I'm the founder of Vitalos Technologies (UK). We're building Vitalos Verify, a multi-tenant identity-verification service for UK recruitment agencies and contractor platforms, starting with a small, capped pilot (adults only, roughly [Owner to complete: e.g. 100–150] completed verifications a month at first). We'd like to evaluate Regula Document Reader SDK and Face SDK (liveness and face match), **self-hosted in our own AWS account in London (eu-west-2)**, with capture in the applicant's **mobile browser**.

Specific questions first:

- **A. Platform rights:** may Vitalos use Regula inside a service sold to many business customers under the Vitalos brand? What licence (OEM/partner) is needed?
- **B. Web capture:** are document capture and liveness supported in mobile browsers? Which iBeta/other PAD reports cover the **web** components, and has any **injection-attack** testing been done (e.g. CEN/TS 18099)?
- **C. Licensing data flows:** with an online licence, exactly what data is sent to Regula per transaction? Is an offline licence available for a Linux container deployment? Does any image or personal data ever leave our environment?
- **D.** Company ownership and the locations where the SDKs are developed and supported (we ask every supplier this).

Standard questions:

1. Country/document/version matrix (and how often templates update).
2. Meaning of result/confidence fields; calibration.
3. Liveness and injection evaluation reports with exact versions assessed.
4. Mobile and browser support matrix; accessibility of any provided UI components.
5. Demographic and image-quality performance evidence.
6. False-match / false-non-match operating points and how to set thresholds.
7. Certifications (scope and expiry).
8. Support and incident commitments; security advisory process for SDK vulnerabilities.
9. Processing locations including support access (e.g. if we share logs).
10. Subprocessors, if any.
11. Confirmation that Regula does not receive or train on our customers' data.
12. Retention/deletion — confirm none held by Regula when self-hosted.
13. Any controller/processor terms you require.
14. Platform/resale rights (see A).
15. Licence pricing for 100, 1,000 and 10,000 verifications a month; minimums; set-up.
16. Billable transaction definition, including retries.
17. Dispute handling for faulty transactions.
18. Exit: licence end, data, migration.
19. Trial/sandbox licence for evaluation with synthetic specimens.

Thank you,
Temitope Agbola
Founder, Vitalos Technologies — vitalos.co.uk

---

## 3. Innovatrics

**To:** [Owner to complete: Innovatrics partner/sales contact via innovatrics.com/partner-program]
**Subject:** RFI and partner enquiry — identity verification for a UK recruitment platform

Hello,

I'm the founder of Vitalos Technologies (UK), building Vitalos Verify: identity verification and case management for UK recruitment agencies and contractor platforms. We'd like to evaluate your identity verification toolkit/platform (document, face match, liveness) as an ISV partner, either **self-hosted in our AWS London (eu-west-2) account** or as SaaS if a UK region is available. Capture would be in the applicant's **mobile browser**. We'd start with a small, capped pilot of adults ([Owner to complete: e.g. 100–150] verifications a month).

Specific questions first:

- **A. Partner terms:** does your Partner Program allow Vitalos to provide verification to its own business customers under the Vitalos brand? What are the terms?
- **B. Evidence for web capture:** the CLR Labs PAD certificate we found covers Liveness Service 3.1.0 mainly on Android. What evaluation covers **web/mobile-browser** liveness, and which versions does your CEN/TS 18099 injection-attack certification cover?
- **C. Deployment:** for SaaS, which regions and where is support provided? For self-hosting, does any data go back to Innovatrics (licensing, telemetry)?

Standard questions:

1. Country/document/version matrix.
2. Meaning of result/confidence fields; calibration.
3. Liveness and injection evaluation reports with exact versions assessed.
4. Mobile and browser support; accessibility of UI components.
5. Demographic and image-quality evidence; which NIST FRTE submission corresponds to the shipped algorithm.
6. False-match / false-non-match operating points.
7. Certifications (scope and expiry).
8. Service levels and incident notification.
9. Processing locations including support access.
10. Subprocessors and change notice.
11. Training/product-improvement use of customer data — can it be excluded by contract?
12. Retention, deletion with confirmation, backups.
13. Controller/processor terms (your DPA).
14. Platform/resale rights (see A).
15. Pricing for 100, 1,000, 10,000 verifications a month; minimums; set-up.
16. Billable transaction definition, including retries.
17. Dispute/refund handling.
18. Exit: export and migration support.
19. Sandbox or evaluation licence with synthetic material.

Thank you,
Temitope Agbola
Founder, Vitalos Technologies — vitalos.co.uk

---

## 4. Yoti

**To:** [Owner to complete: Yoti business contact — the G-Cloud 15 service document lists business@yoti.com; confirm before use]
**Subject:** RFI — Yoti IDV embedded in a UK recruitment verification platform

Hello,

I'm the founder of Vitalos Technologies (UK). We're building Vitalos Verify, which provides identity verification and case review to UK recruitment agencies and contractor platforms. We're considering Yoti IDV (embedded SDK or hosted page) for **general identity checks of adult applicants**. We are **not** currently offering right-to-work, right-to-rent or DBS checks.

Specific questions first:

- **A. Platform use:** your Organisation Terms (v4.9, cl. 5.3) require written consent before results are made available to third parties. Would Yoti consent to Vitalos providing verification to its own business customers, and on what terms?
- **B. Data use:** could cl. 5.5 (b) product improvement and (c) internal fraud database use be excluded for our customers' applicants? Could research/training use be switched off entirely?
- **C. Locations:** your privacy notice says data may be sent to your security centre in India for manual checks. Can that be excluded for our checks, or which checks trigger it?
- **D. Role:** please confirm Yoti acts as **processor** (not controller) for non-framework IDV checks requested by Vitalos.
- **E. Alternative route:** is Post Office in-branch verification available to platforms like ours as an assisted alternative for applicants who can't use a camera?

Standard questions:

1. Country/document/version matrix.
2. Meaning of result/confidence fields.
3. Liveness and injection evaluation reports with exact versions assessed.
4. Mobile-browser support; accessibility conformance of the hosted flow.
5. Demographic and image-quality evidence.
6. False-match / false-non-match operating points.
7. Certifications (scope and expiry), including your current DVS register entry.
8. Service levels; incident notice; notice period for platform changes (terms allow changes without prior warning).
9. Processing locations including support access.
10. Subprocessors (terms list affiliates, AWS and Azure) and change notice.
11. Training use (see B).
12. Retention we can configure (we target 30 days after decision), deletion with confirmation, backups.
13. DPA (Schedule 2) — any changes for platform use.
14. Platform/resale rights (see A).
15. Pricing for general IDV at 100, 1,000, 10,000 checks a month; set-up and monthly minimums (we've seen the G-Cloud list for DBS/RTW).
16. Billable check definition, including retries.
17. Dispute/refund handling.
18. Exit: export and migration.
19. Sandbox access with synthetic material.

Thank you,
Temitope Agbola
Founder, Vitalos Technologies — vitalos.co.uk

---

## Tracking

| Supplier | Sent (date) | NDA | Reply | Sandbox | Re-scored |
|---|---|---|---|---|---|
| Stripe | [ ] | [ ] | [ ] | [ ] | [ ] |
| Regula | [ ] | [ ] | [ ] | [ ] | [ ] |
| Innovatrics | [ ] | [ ] | [ ] | [ ] | [ ] |
| Yoti | [ ] | [ ] | [ ] | [ ] | [ ] |
