# Experience, screens and design specification

Version 1.0 | 10 November 2026 | Planning baseline

## Visual direction
Use a restrained white workspace with charcoal typography, generous spacing and one muted brand accent. No glowing gradients or decorative sci-fi graphics. Marketing can use black sections sparingly. Design for mobile applicants first, with full-size icons, clear capture guidance and short sentences. Adopt a shared component system with accessible primitives; pin dependency versions at implementation.

## Surface inventory
| Surface | Routes or screens | Core actions |
|---|---|---|
| Public | Home, product, solutions/workforce, pricing, developers, security, privacy, status link | Understand product, trial request, sign in |
| Applicant | /v/{token}, introduction, privacy, method, document, selfie, processing, outcome, alternative | Complete or challenge request |
| Customer | Overview, verifications, case detail, policies, team, integrations, usage/billing, settings | Operate own verification programme |
| Operations | Supplier health, processing queues, deletion failures, support access, incidents | Resolve service problems |
| Superadmin | Organisations, entitlements, billing administration, feature gates, audited access | Govern platform |

## Applicant journey
1. Display requesting business, purpose, expiry, expected evidence and controller contact. Do not expose subject details before token exchange.
2. Present the versioned privacy notice and required acknowledgement; capture explicit consent separately only if it is the approved condition. Offer the alternative path before capture.
3. Detect supported capture capability; let users switch device using a short-lived QR handoff without duplicating the verification.
4. Guide document capture with blur/glare feedback and clear accepted document types. Explain why a retry is required without revealing exploitable fraud thresholds.
5. Run supplier-bound live selfie capture. Accessible instructions, audio/text alternatives to instructions and a non-biometric operational route must be considered; unsupported devices are not fraud.
6. Show processing asynchronously. Refreshing or leaving the page does not lose server state. Never show success merely because the SDK callback fired.
7. Show submitted, action required or completed. The requesting business determines detailed disclosure appropriate to the use case; provide support and challenge routes.

## Customer case page
Header: case reference, status, policy version, creation/expiry and assigned reviewer. Checks: distinct ID authenticity, expiry, face match, liveness and contact ownership, each showing result and reason. Timeline: submission, supplier events, requests, review and deletion. Evidence viewer: masked by default, authorised reveal with reason and audit. Action bar: claim case, request more information, record decision, escalate. Never label a person a fraudster solely from a score.

## States required on every relevant screen
Loading, empty, permission denied, expired, invalid input, supplier outage, retry limit reached, offline, deleted and unexpected error. Failed capture must distinguish poor quality from suspected attack. Billing hold blocks new billable sessions, not access to existing outcomes or privacy requests. Lists use cursor pagination and filter by status/time/policy, with no PII in URLs.

## Accessibility and interaction acceptance
Keyboard navigation, visible focus, labelled inputs, error summary, screen-reader announcements for status changes, reduced motion and sufficient contrast. Test 320px and 390px widths, 200% zoom, current iOS Safari and Android Chrome plus a low-memory Android device. No passport/selfie images in session replay. File upload fallback is permitted only where the verification policy supports its lower assurance; it must not substitute for required live capture.

## Design deliverables
Create flows, responsive wireframes, design tokens, component inventory and interactive prototype before production UI. Review with five representative applicants including an accessibility participant where feasible. Record friction and comprehension findings. Final marketing claims must match shipped modules and verified coverage; hide future products behind an explicitly labelled roadmap.
