# Security threat model and control plan

Version 1.0 | 10 November 2026 | Planning baseline

## Assets and adversaries
Protect identity images, biometric outputs, applicant links, tenant boundaries, API credentials, outcome integrity, billing and audit evidence. Threat actors include fraudulent applicants, compromised customer accounts, malicious tenants, exposed support credentials, compromised dependencies and spoofed suppliers. Model browser, API, queue, provider, storage, admin and export boundaries independently.

| Threat | Control | Verification |
|---|---|---|
| Cross-tenant object reference | Authorised tenant context, composite keys, row policies | Enumerate object access under two test tenants |
| Forged provider approval | Raw-body signature validation, authoritative fetch, session binding | Forged/old callback cannot approve |
| Replay and duplicate billing | Nonces, expiry, unique event IDs, usage uniqueness | Repeated events produce one charge/outcome |
| Capture injection/spoofing | Evaluated supplier SDK, anti-replay and integration assessment | Independent authorised attack evaluation |
| Stolen applicant link | One-use exchange, short lifetime, restrictive cookies | Reuse and wrong-session denial |
| Document parser exploitation | Isolated parsing, content/type/size controls, no outbound network | Malicious fixture quarantined |
| Prompt injection in documents | Untrusted text, no privileged tools, schema/provenance validation | Document instruction cannot alter policy |
| Webhook SSRF | HTTPS allowlist policy, DNS/IP checks, block private/link-local ranges and redirects | Rebinding/private-target tests |
| Operator abuse | Least privilege, MFA, timed grants, immutable audit | Expired elevation fails |
| Sensitive telemetry | Structured allowlist logging, no session replay, redaction | Automated canary PII scans |
| Supplier compromise | Minimal transfer, scoped secrets, kill switch, reconciliation | Outage/compromise tabletop |
| Cost exhaustion | Quotas, per-destination caps, spend reservation | Concurrent requests cannot exceed cap |

## Secrets and authentication
Use managed secrets and workload identities; no cloud keys in repositories or browser code. API keys are hashed and scoped, with rotation overlap and immediate revocation. Require strong MFA for privileged users, prefer phishing-resistant methods where supported. Step-up authentication for evidence export, role elevation and key changes. Session idle/absolute timeouts, CSRF protection for cookie commands, secure cookies and content security policy are required.

## Software supply chain
Pin dependencies, lockfiles, automated vulnerability checks, secret scanning, protected branch reviews and signed/traceable build artifacts. GitHub CI authenticates to cloud by scoped OIDC, not long-lived secrets. PR jobs cannot deploy production or access real evidence. Infrastructure plan and policy checks precede apply. Separate production deployment identity from application runtime and migration roles.

## Assurance release gate
External application penetration test before GA, focused on multi-tenancy, evidence access, webhooks and privilege escalation; separate biometric/injection assessment appropriate to the chosen supplier. No unresolved critical/high findings at release. Medium findings need owner, deadline and compensating controls. Model vendor evaluation is not certification of the whole Vitalos application. Maintain a vulnerability intake and coordinated remediation process.

## Incident handling
Contain exposed paths, revoke credentials and preserve minimal forensic evidence without deleting audit history. Identify affected tenants and records, involve privacy lead, assess contractual/regulatory notification duties and communicate accurately. Do not publish unverified root cause. Restore only from known-good artifacts and rerun deletion tombstones. Full procedure and exercises are in the operations runbook.
