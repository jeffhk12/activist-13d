# Activist 13D Investment Strategy Project Plan

Agreed September 13, 2026. Incorporates the subsequent course-alignment discussion and feedforward neural-network extension. The original proposal and design record are preserved as historical documents; this plan records the current strategy-first scope. Canonical professor proposal: [V2](PROFESSOR-PROPOSAL-v2.md).

## Objective and resources

Build a long-only corporate-activism strategy using validated intent from initial Schedule 13D disclosures. The first ML task is investment selection. Research success is a credible held-out comparison after costs, including an honest negative or inconclusive result.

- Solo work, 5-10 hours weekly; initial manual validation two hours weekly for three weeks.
- $50 total external model API budget, including pilots, comparisons, retries, and bulk processing. DeepSeek and Kimi are candidates, not yet selected.
- Portfolio scenarios: $100,000 and $100 million, with identical signals, target percentage allocations, and exit rules; execution constraints and costs depend on size.
- Deadline and required model methods await professor feedback. The syllabus permits solo work and non-MATLAB environments. It covers boosting and ANN architectures but explicitly excludes LLM topics; extraction supports the supervised modeling contribution.
- Corporate activism first. If usable observations are inadequate: investigate coverage/identification gaps, simplify models, then consider a separate closed-end-fund strategy. Do not pool different settings solely to inflate sample size.

## Phase 0 Professor proposal

Deliver a two-page professor-facing proposal describing the strategy, actual data status, ML methods, validation, capacity scenarios, and phased execution. Ask about scope, required neural work, and deadlines. Record AI assistance as required by the syllabus. Do not send the proposal automatically.

Gate: professor feedback establishes course constraints and any changes; proposal creation can complete while feedback is pending.

## Phase 1 Data feasibility

Inventory distinct eligible corporate campaigns, filings, amendments, and issuers without equating these units. Resolve historical market-data identifiers and report link failures, coverage by period, follow-up, and missing evidence. Assess Audit Analytics category definitions and historical coverage before using it as a reference set. Verify execution prices, corporate actions, delistings, benchmark data, and cash-rate availability.

Current evidence: 100 discovery filings including the retained ten-filing pilot; 55 quarterly index entries including partial 2026 Q3; schemas and six development probe rows across three WRDS tables. Neither the campaign panel nor the full WRDS extracts exist yet.

Gate: review usable campaign counts and time coverage. Minimum counts, horizons, and split dates are intentionally evidence-dependent; do not select them from final-test returns.

## Phase 2 NLP validation

Freeze versioned categories, prompts, and structured outputs. Require source passages and locations for positive labels. Verify quoted text mechanically and semantic support against human reference labels. Distinguish absence of intent from missing evidence or inability to determine. Preserve uncertainty; exclude unreliable categories from the core trading features.

Archive original source, exact supplied text, model identifier/settings, raw request/response without credentials, timestamp, and hashes. Cached replay must reconstruct research outputs without APIs. Fresh calls assess stability, not exact replay guarantees. Limit input to information available at the initial disclosure; recognize that pretrained-model historical knowledge is not eliminated by prompting.

Label development examples before seeing AI answers or subsequent returns. Freeze the protocol before a separate held-out extraction evaluation. Establish category-specific acceptance thresholds before examining held-out scores; report precision, recall, abstention, sample sizes, and uncertainty. Keep prompt tuning distinct from final evaluation. Solo review is a human reference, not independent multi-coder ground truth; neither provider agreement nor Audit Analytics access proves accuracy.

Compare candidate providers on the same bounded pilot. Measure cost and review throughput before allocating the remaining $50. Include random checks of apparently easy outputs as well as disagreements. Avoid the old proposal's unmeasured five-vote and 500-record audit commitments.

Gate: acceptable categories, reproducibility, measured cost, and review coverage justify bulk processing. Poor evidence cannot be waived to retain observations.

## Phase 3 Strategy specification

Settle and record the prediction target, benchmark definition, configurable medium/long-term horizon candidates, allocation caps, participation/minimum-position rules, cost assumptions, stop-loss and jump-filter candidates, training schedule, initial window, and holdout boundaries. Regression versus classification follows the agreed target; no choice is implied yet.

Entry baseline: first regular-session opening at least one full trading session after publication, subject to verifying historical opening prices. Define the calendar and timestamp rule exactly before implementation. Optional announcement filter: skip, rather than wait for a pullback, based on change from the last close strictly before disclosure to the close preceding eligible entry. This is not a maximum-fill-price guarantee. Compare against no filter. Test stop-loss rules against no stop with gap-aware execution, not guaranteed threshold fills.

Core portfolio: capped equal-sized allocations; unused funds in cash; one position per issuer with no automatic addition or reset of the exit clock. Reduce oversized orders to permitted participation and retain residual cash; skip below the minimum position. Do not assume a day's volume is available at the open. Multi-day accumulation is outside core execution.

Cash: FRED historical short-term Treasury-rate proxy, using prior available data and a documented yield-to-accrual conversion; zero-interest sensitivity. Core accounting excludes taxes and management/performance fees but includes transaction costs. Preserve the ledger for later fee/tax scenarios; user-specific taxes are not assumed.

Gate: decision-complete trading, accounting, timing, and evaluation specification. Freeze settings before final testing.

## Phase 4 Baselines and model development

Compare simple activist-following, structured-feature selection, and identical model families augmented with validated NLP intent features. Use a regularized baseline and gradient-boosted trees. Add a small feedforward neural network as the first neural extension, using matched features and evaluation. Complexity is conditional on campaign count and professor feedback.

Use expanding-window development; rolling-window comparison is robustness. Fit preprocessing and tune within chronological development folds. Only labels matured by each simulated training date enter training; handle campaigns/outcome windows overlapping boundaries to prevent leakage.

Report campaign attrition through eligibility, identifier matching, NLP selection, announcement filters, and actual execution, overall and by period. Report stop-loss effects on holding time and turnover separately. Optional filters must earn inclusion through development evidence; simplify or drop those leaving inadequate trade counts or concentration. Never retune using final holdout performance.

Gate: source traceability, portfolio accounting, point-in-time inputs, and fair baseline comparisons pass before final evaluation.

## Phase 5 Final evaluation and delivery

Evaluate the frozen procedure on a chronological holdout. Any scheduled retraining uses only matured information under previously fixed rules; no discretionary feature or threshold changes based on final results. Report inadequate power as inconclusive rather than reopening the test.

Report returns after costs, risk-adjusted performance, drawdowns, turnover, cash exposure, uncertainty, and both capacity scenarios. Compare the user's monthly HFR event-driven series over common dates after confirming exact name, currency, fees, methodology, and coverage. Include broad-market and beta/alpha context, with exact series and target still open. Aggregate strategy returns appropriately to monthly; do not interpolate monthly HFR returns to daily.

Deliver report, presentation, trade ledger, environment record, archived model outputs, codebooks, and reproducibility bundle. Include rolling-window, label-quality, zero-cash-interest, and disclosure-period robustness where feasible. No causal interpretation of the period split is part of core findings.

## Conditional extensions

After core completion: feedforward neural network if not already required; campaign-duration labels and conventional survival models followed by DeepHit; amendment/new-manager resizing; hedging or shorting; causal disclosure analysis; multi-day execution; separate fee/tax overlays. Sector-related positions remain outside the core scope. None is a silent prerequisite for the first backtest.

## Verification and source ownership

- Verify raw evidence hashes, exact replay, supporting spans, refusal on ambiguity, and absence of credentials from outputs.
- Check causal ordering of publication, decision, entry, and label availability; account for gaps, corporate actions, delistings, and incomplete horizons.
- Check cash conservation, one position per issuer, limits, and both capacity scenarios against hand-worked examples.
- Preserve frozen raw evidence and versioned protocols. No data downloads or research implementation are authorized merely by saving this plan.
- This documentation task owns only these new plan/proposal files and its dedicated builder/output. Preserve existing shared source files. The WRDS workstream owns wrds_access/ and data/raw/wrds/; establish separate ownership before further parallel implementation.

## Sources and provenance

Data checkpoint: output/overnight/EDA.md, output/overnight/MORNING-HANDOFF.md, and wrds_access/README.md. Course alignment: Advanced_Machine_Learning_Syllabus_Fall_2026.pdf in the user's Fall 2026 semester-admin Syllabi folder. Decisions: this planning conversation through September 13, 2026. The full extraction protocol and software-version manifests will be produced in Phase 2; this document does not claim those already exist.
