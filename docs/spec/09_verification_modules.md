# Verification modules: detailed functional specification

Version 1.0 | 10 November 2026 | Planning baseline

## Government ID — M04
Input: approved capture session, document country/type and permitted images. Checks: capture quality, supported template, authenticity signals, expiry, extracted field consistency and portrait availability. Preserve extraction confidence and source region; low-confidence fields need confirmation without overwriting original extraction. MRZ checksums and OCR consistency alone do not prove authenticity. Output individual checks with provider/version/provenance, masked attributes and evidence references. Reject unsupported type before collecting unnecessary images. Test glare, blur, expired documents, altered data and legitimate naming variations with lawful fixtures.

## Selfie matching and liveness — M04
Bind live capture to the session and verified reference portrait. Record matching and liveness separately. No shared face gallery; no 1:N search. Distinguish unusable frame, no face, multiple faces, mismatch and suspected attack. Restrict retries and protect capture tokens from replay. Retain only required evidence, with no long-lived reusable biometric template by default. Security evaluation includes presentation and injection threats and end-to-end integration, not just model scores. Deployment blocked until evaluated operating thresholds are fixed.

## Phone and email — M03
Issue single-use codes with short expiry; store hashed codes; limit per-session, per-destination and per-tenant sends, with IP/device risk as additional signals. Do not leak account existence. Use generic responses and progressive abuse controls. Support email invitation with code confirmation separately from the invitation token itself. SIM control and email control are low-assurance contact attributes, not verified legal identity. Messaging spend limits must work independently of rate limits.

## Supplemental Document AI — M08
Start with proof of address from agreed document classes. Input privately uploaded file, declared purpose and reference fields. Scan files, reject active content/oversize archives, extract in a sandbox. Output document type, extracted fields with page/bounding-box provenance, recency and consistency flags. LLM-derived values require schema validation and provenance; document text is untrusted input and cannot issue tool commands. Date/name/address consistency is not authenticity. Advanced tamper detection remains a separately sourced check. Reviewer can compare original and extracted data; amendments preserve originals and actor reason.

## Database checks — M09
Contract for specific sources and permitted purposes; no generic promise of government access. Match supplied name, date of birth/address or approved identifier to licensed source. Return match, partial, no_match, unavailable or not_covered with source time and freshness. A no-match may reflect coverage or stale data and must not automatically be labelled fraud. Avoid excessive identifiers. Distinguish identity-record matching from sanctions/PEP screening; AML screening is not included merely because database checks exist. Test spelling, transliteration, changed addresses and source outage.

## NFC — M10
Use supported native mobile SDK/device flow. Reading chip data is not authentication. Require certificate-chain/signature and data-integrity validation through approved trust material; define whether active/chip authentication is supported for each document. Compare authenticated chip portrait to live selfie under policy. Record validation method, issuer trust version and unsupported outcomes. Unverified decoded chip data cannot receive the same assurance label. Maintain trust-material update procedure and revoked/expired certificate handling based on document standards, not ordinary web-certificate assumptions. Test emulator/injected payloads in authorised fixtures, corrupt signatures and device interruption.

## Age assurance — M11
Separate age estimation from identity recognition. Return threshold result and method, not a falsely exact age. Procure an evaluated age estimator and liveness mechanism, choose an evidence-based challenge threshold above the legal boundary, and offer a justified alternative for borderline users. Do not invent a universal buffer. Retain the minimum threshold assertion where possible, and remove captures promptly under the approved profile. Test underage acceptance, adult rejection, subgroup/device performance and fallback completion. Do not reuse age evidence for identity matching or marketing. Children-related processing requires a separate assessment before launch.

## Digital ID and EUDI — M12
Begin as a verifier/relying party, not a wallet issuer. Verify supported credential format, trusted issuer, signature, validity, holder binding, intended audience, session nonce and status/revocation where applicable. Request only necessary attributes; do not accept screenshots of wallet credentials as equivalent cryptographic evidence. Implement protocol-specific adapters once target wallets, relying-party obligations and current interoperability specifications are confirmed. EUDI is a programme with trust and scheme onboarding, not just a UI checkbox. Negative tests include replay, wrong audience, untrusted issuer and expired credential.

## Cross-module rules
All modules register their supported matrix and cost semantics, emit normalised checks, follow retention profiles and provide an alternative/error path. No future module is enabled by default. A new module needs privacy assessment delta, supplier rights, acceptance fixtures, production monitoring and rollback before release.
