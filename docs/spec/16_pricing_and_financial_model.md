# Pricing hypotheses and unit economics

Version 1.0 | 10 November 2026 | Planning baseline

## Public benchmarks
Research on 10 November 2026 found Stripe UK's listed ID-and-selfie price of £1.25 per completed verification and Persona Essential starting at $250/month with a 12-month minimum. AWS's published US East liveness example is $0.015/check at its first tier. The latter is not ID verification and must not be used as a full cost benchmark. Verify current quotes, taxes, volumes and platform rights before contracting (S10–S12).

## Proposed experiments, not published offers
Starter hypothesis: £99/month platform plus £2.50 per completed basic verification. Growth hypothesis: £299/month plus negotiated usage, richer integrations and policy controls. Enterprise: annual commitment, scoped support and negotiated processing. Start with a paid, capped pilot if buyers agree. Do not promise these rates until supplier quotes and review/support costs are measured. No unlimited verification plan or free trial that exposes uncapped SMS/provider costs.

## Billing definitions
Session created is not automatically billable. Define the sellable unit as one completed verification package under a frozen commercial version; list whether terminal failed/inconclusive attempts and retries incur charges. Reflect supplier economics without confusing customers. Technical failures receive the agreed credit policy. Each charge has unique ledger key, source session/attempt, quantity, unit price, currency and invoice reference. Adjustments append credit events; never mutate settled invoices.

## Illustrative 1,000-verification month
Revenue: £99 platform + 1,000 × £2.50 = £2,599. Supplier: 1,000 × £1.25 = £1,250. Assumed review burden 10% × four minutes × £20/hour = £133.33. Assumed messaging £30, variable infrastructure £150, variable support £100. Contribution before fixed staff, tax, payment fees and other overhead = £935.67 (36.0%). Review labour may be a customer cost in self-review; retain it in the sensitivity analysis to expose managed-service economics. Every assumption is editable in financial_model.csv.

## Sensitivity
At 20% review and eight minutes each, review cost becomes £533.33 and contribution falls to £535.67 before other omitted costs. Add supplier retries and contract minimums separately: effective supplier unit cost = max(contract minimum, usage charges) / billable completed units. Track cost for abandoned sessions if supplier bills attempts. Low volume can be uneconomic even with a nominal markup.

## Spend controls
Actual monthly cap is unresolved. Before live supplier/cloud use, set owner-approved caps and alerts at 50/80/100%; hard-stop new paid sessions or messaging at the agreed hard threshold while preserving privacy and existing-case access. Reserve estimated cost atomically for concurrent sessions and reconcile actual invoices. Do not present cloud credits as a recurring sustainable cost reduction.
