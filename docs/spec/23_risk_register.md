# Programme risks, dependencies and ownership

Version 1.0 | 10 November 2026 | Planning baseline

| Risk | Impact | Owner | Response and gate |
|---|---|---|---|
| Supplier resale rights unavailable | Product model invalid | Founder | Obtain written rights before integration commitment, M01 |
| UK-only customer terms conflict with provider region | Processing breach | Privacy/engineering | Capability routing and alternative supplier, M01 |
| Invalid biometric legal ground | Live processing cannot proceed | Customer/privacy | Resolve before any real-data pilot, M05 |
| Insufficient buyer demand | Commercial failure | Founder | Ten interviews/three intents; narrow segment, M00 |
| Founder capacity too small | Schedule slippage | Founder | Bounded WIP, separate specialists, revise date |
| Poor mobile completion | Low conversion/exclusion | Product | Device evaluation and meaningful fallback, M03/M06 |
| Provider outages | Stalled onboarding | Engineering | Pending states, reconciliation, pre-approved fallback |
| High review/retry costs | Negative margin | Commercial | Measure attempt economics before pricing, M06 |
| Cross-tenant evidence exposure | Severe privacy/security harm | Security | Defence in depth and independent tests, M05/M07 |
| Unsupported compliance claims | Customer harm and liability | Founder/legal | Claim register and launch matrix |
| Model demographic disparity | Unfair exclusion | Assurance | Representative evaluation, uncertainty, alternative |
| Deletion not propagated | Retention breach | Privacy/engineering | Supplier receipts and backup tombstones |
| Scope expands before core reliability | Delayed pilot | Product | Separate expansion milestones and gates |
| Agent marks mocks as production | False readiness | Engineering | Evidence-based status and independent verifier |
| Proprietary models lack data rights | Unusable R&D | Research/privacy | R1 gate; retain supplier baseline |

## External dependencies
Cloud and DNS account access, repository ownership, payment processing account, supplier procurement, customer design partners, privacy adviser, security assessor, evaluation dataset and support coverage. None are presumed available. Work on synthetic interfaces can continue while contracts progress, but real-data activation cannot bypass missing dependencies.

## Escalation
Any evidence exposure, unauthorised collection or policy bypass pauses affected live processing. Budget exhaustion pauses new spend while preserving rights requests and access to existing cases. Schedule pressure does not lower identity assurance or privacy gates. Risk acceptance requires a named accountable person and does not override legal obligations.
