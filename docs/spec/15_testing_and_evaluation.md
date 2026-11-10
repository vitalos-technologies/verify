# Testing, biometric evaluation and acceptance plan

Version 1.0 | 10 November 2026 | Planning baseline

## Layers
Unit-test domain transitions and policies; database integration-test tenant isolation and concurrent updates; contract-test provider/event schemas; browser-test applicant and reviewer journeys; security-test access, uploads and webhooks; load-test queues/rate limits; exercise recovery/deletion. Deterministic synthetic fixtures belong in CI. External biometric evaluation uses a separately governed, licensed dataset and cannot be replaced with fake happy-path images.

## Proposed pilot operational targets
At least 85% of users who start a supported journey complete without assisted support; under 15% manual review among eligible completed submissions; metadata API p95 under 500 ms at stated load; zero cross-tenant leaks, missing decision provenance or duplicate charges in acceptance runs. These are planning targets, not observed performance or promises. Report denominator and exclusions, and adjust through controlled decisions after discovery. Fraud/security thresholds cannot be weakened merely to meet conversion targets.

## Biometric metrics
Measure false match rate and false non-match rate at fixed operating threshold, failure to acquire, genuine-user completion, presentation-attack acceptance/rejection and injection attack outcomes. Document test population, capture devices, lighting, document quality, image age and subgroup confidence intervals. Model score is not a probability unless calibrated and documented. NIST performance on a reference dataset does not guarantee Vitalos end-to-end results.

## Statistical sufficiency
For zero observed errors in n independent representative trials, the rough one-sided 95% upper bound is 3/n. Zero errors in 100 trials therefore does not establish a 0.01% error rate. Correlated captures and repeated identities violate naive independence; use subject-disjoint splits and suitable clustered uncertainty. Set numeric security operating points with the assurance specialist and customer risk owner before pilot. Mark them unresolved until evidence exists; do not invent a universal threshold.

## Dataset governance
Document provenance, permitted purposes, participant agreement where applicable, demographic collection grounds, deletion rights, train/test separation, licence and access control. No scraping people's faces. No transfer of production identity evidence to developer laptops or general LLMs. Keep a locked holdout and a separate attack suite; training/evaluation contamination invalidates results. Audit annotation and ground-truth disputes.

## Release evidence
Each acceptance scenario produces test version, environment, commit, policy/adapter versions, result, redacted evidence and reviewer. Failed security cases block release; operational misses require explicit decision with remediation and no false service claims. Third-party reports must match the purchased SDK/model version and deployment mode. Test again after material supplier updates.

## Monitoring after launch
Track quality and completion by supported device/document group, appeals and confirmed fraud with delayed labels. An approval rate alone measures neither accuracy nor fairness. Alert on sudden distribution changes, increased retries or liveness errors. Pause affected methods rather than approving on error. Maintain retrospective evaluation of materially changed decisions without silently rewriting history.
