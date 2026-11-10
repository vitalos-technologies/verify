# Selective proprietary technology programme

Version 1.0 | 10 November 2026 | Planning baseline

## Investment thesis
Build proprietary capability only when it improves measured customer outcomes, economics or strategic independence. Candidate order: capture-quality assistance, document classification/extraction, rule-based consistency checks, then carefully scoped fraud models. Face matching, liveness and age estimation require substantially greater dataset, evaluation and assurance effort; they are not assumed achievable within the pilot timeline.

## Gates
R0 business case: volume, supplier cost, failure costs, specialist staffing and attainable improvement. R1 lawful dataset: provenance/licence, permitted purpose, representativeness, subject-disjoint split and deletion. R2 offline evaluation: locked holdout, baseline comparison, uncertainty, subgroup/device analysis and adversarial assessment. R3 shadow: no customer decision influence, bounded approved processing, compare outcomes and costs. R4 limited production: independent review, documented thresholds, rollback and explicit enablement. R5 expansion: sustained monitoring, incident handling and performance against contractual promises.

## Replacement criteria
Define a component-specific security floor before training. Candidate must be no worse than the deployed baseline at the agreed operating point with adequate evidence, meet latency/availability and subgroup requirements, and have economically credible total cost including annotation, compute, experts, maintenance and assurance. Better aggregate accuracy alone does not permit replacement. Record both false acceptance harm and exclusion harm.

## Model operations
Version training data manifests, code, dependencies, model weights, evaluation and deployment configuration. Signed artifact promotion; no unreviewed auto-retraining. Keep baseline rollback available and preserve original decision provenance. Monitor drift and delayed fraud labels; retraining requires documented dataset rights and re-evaluation. Suppliers may update models: contract for notice/version observability where possible and reassess material changes.

## Prohibited shortcuts
No scraped facial galleries, production evidence used by default, general LLM face comparison, fabricated certification, threshold tuning on locked holdout or evaluation claims based on tiny samples. Open-source code licences and pretrained-weight/data licences are distinct and both must permit the intended commercial use.

## Financing decision
M13 can conclude that continued licensing is best. That is a valid milestone outcome. Do not fund a proprietary biometric engine merely to satisfy the word proprietary. Maintain a research budget separate from production service budgets and require explicit approval for dataset purchase, specialist contracts or GPU commitments.
