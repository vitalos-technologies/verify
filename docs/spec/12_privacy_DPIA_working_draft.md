# Privacy architecture and DPIA working draft

Version 1.0 | 10 November 2026 | Planning baseline

Status: working assessment requiring facts, accountable owners and professional review before live biometric processing. It is not legal advice, a signed DPIA, a certification or a substitute for a customer's assessment.

## Processing description
Purpose: help a requesting business establish an applicant's identity for onboarding. Proposed flows: invitation, notice/choice, supported ID capture, selfie/liveness, supplier checks, policy result, customer review, retention/deletion. Subjects initially adults. Data includes contact details, identity attributes, document images, biometric processing outputs, device/session signals and decisions. Do not infer sensitive traits or reuse evidence for marketing.

## Roles and grounds
Working model: customer controller for onboarding; Vitalos processor for those instructions; specialist suppliers subprocessors where contract supports that chain. Vitalos may separately be controller for its own account administration/security, requiring a separate purpose and analysis. Independent fraud-network or model-training use would change roles and is excluded. Record an Article 6 basis and, for recognition, an applicable Article 9 condition before capture. Explicit consent cannot be presumed freely given in employment contexts; provide and assess genuine alternatives. Refer to source register S01–S03.

## Necessity and alternatives
Compare non-biometric document review, in-person checking and approved digital-ID routes against the specific fraud problem. Record why the chosen checks are proportionate. Do not demand biometric capture merely because the API supports it. Assess accessibility, poor-device exclusion, false decisions, economic impact and appeal. Customer policy must document the intended effect of automation and applicable safeguards under current law; counsel must verify the relevant rules at launch.

## Risk assessment
| Risk | Initial severity | Mitigation | Residual decision |
|---|---|---|---|
| Identity evidence exposure | High | Minimal collection, encryption, strict access, short retention | Owner review after test |
| False rejection affecting employment | High | Uncertainty handling, alternative, meaningful review/appeal | Customer approval required |
| Invalid consent or legal basis | High | Purpose-specific grounds and alternatives | No real processing until resolved |
| Supplier reuse or foreign access | High | DPA, location/transfer review, no training terms | Supplier acceptance required |
| Unequal model performance | High | Representative evaluation, monitored errors, fallback | Assurance owner approval |
| Retention beyond purpose | Medium/high | Enforced expiry and deletion reconciliation | Exercise evidence required |
| Function creep | High | No gallery/training reuse; change assessment | Product governance required |

## Controller completion fields
Legal entity and contacts; customer purpose; subject categories and expected volumes; chosen legal grounds and necessity; approved alternatives; suppliers and processing/support countries; transfer mechanism where applicable; detailed retention by category; notices; rights response procedure; assessment of automated decisions; consultation feedback; residual risks; DPO/adviser advice; accountable sign-off/date; review trigger. Blank fields remain launch blockers rather than invented facts.

## Rights and notices
Notice identifies requesting controller, purpose, data, suppliers/categories, processing locations, retention criteria, rights and support. Separate required acknowledgement from optional consent. Provide deletion/access routes that do not demand disproportionate new ID evidence. Requests involving customer-controlled data route to that customer; track statutory deadlines based on current jurisdictional advice. Never promise instant deletion from immutable backups; describe restricted retention and expiry accurately.

## Retention/transfer control
Adopt the proposed profile in the data model only after customer ratification. Location controls cover support, logs, backups, model processing and subprocessors, not just the database. AWS London core does not imply every supplier processes in the UK. AWS Face Liveness documentation currently lists Ireland rather than London for European processing; any use needs explicit region/transfer design. A UK-only contract must disable incompatible providers.

## Review triggers
New country, age-assurance/minors, new supplier, face gallery, training use, material model change, automated adverse outcome, longer retention, managed review or a security incident. Reassess before enabling the change. Maintain DPA, subprocessor register, processing record and deletion evidence alongside this assessment.
