# Investor Identity, Ownership and Disclosed Intent in Initial 13D Investment Selection

Project Proposal V4 — Progress update and direction for review

Jeff Lu | QFGB 890H Advanced Machine Learning | Fall 2026

Prepared for Professor Dmitry Udler | September 26, 2026

## Research question and contribution

Can an outside investor improve investment selection using information available when an initial Schedule 13D becomes public? I propose three comparisons: simple disclosure following; supervised learning using structured company, filing and investor information; and the additional contribution of disclosed investment intentions extracted from text.

The intended contribution is a reproducible comparison of these information sets under common execution, benchmark and portfolio conventions. Profitable simple following, useful manager identification and incremental ML or NLP performance are hypotheses, not assumptions. A negative or inconclusive result remains a valid research outcome. The analysis estimates predictive associations, not the causal effect of activism.

V4 updates V3 with the historical baseline conclusion, completed factual preparation and a more precise role for NLP. Phase 1 has been synthesized with unresolved accounting exceptions. Phase 2 has prepared data but has not trained a predictive model. Phase 3 intent-feature extraction and evaluation have not begun.

## Phase 1: historical baseline and what it establishes

The baseline studies delayed entry after eligible initial disclosures, broader HFR-linked manager candidates and a fixed focused activist-candidate subset. It distinguishes standalone initial forms from first observed party–issuer pairs; neither a header name match nor a first appearance in the archive proves an economic manager identity or a first-ever campaign. Unmatched filers are not automatically passive or non-activist.

Historical tests use stock-appropriate Russell size-segment ETF proxies, with SPY as broad-market context, and subsequent industry/year/size comparisons. Portfolio accounting incorporates delayed opening-price entry, modeled transaction costs, liquidity limits, cash interest and overlapping-position rules. The long-horizon convention enters at the second exchange session after the acceptance date under the frozen calendar rule; an observed opening price is an execution assumption, not guaranteed fill availability. Baseline targets remain 5% per issuer, at most 20 issuers, with $100,000 and $100 million account scenarios. Higher concentration and amendment-driven position changes have not been adopted.

The original short-horizon work was followed by a 2024–2025 historical test and an exploratory 2018–2025 revision using 504 exchange sessions (approximately 24 months) as primary, with 12, 18 and 36 months supporting. The horizon expansion occurred after earlier results were inspected; it is not preregistered independent confirmation.

| Evidence | Result | Interpretation |
|---|---|---|
| Focused two-year events | 56 calculable events; mean gross Russell-proxy excess +8.66 percentage points; 95% interval −17.34 to +40.43 | Favorable average with substantial uncertainty |
| Typical two-year focused event | Median excess −14.91 points; 41.1% beat the proxy | The favorable mean does not describe the typical event |
| Two-year industry/year/size comparison | 17 matched focused events; mean difference −8.08 points versus controls | The smaller matched comparison does not support the broader positive mean |
| Later six-month historical test | Five focused benchmark-matched events; mean excess −6.18 points | No confirmation in this small later sample |
| Long-horizon funded accounts | 30 of 48 scenarios complete; primary $100,000 18/24/36-month scenarios incomplete | No full-period primary long-horizon portfolio performance can be claimed |

Event results are equally weighted, gross cumulative stock-minus-proxy returns; they are not net funded-account returns or risk-adjusted alpha. Samples differ and overlap and must not be pooled by adding their counts. For the two-year first-pair schedule, only 694 of 2,107 events have calculable common benchmark observations; the focused subset has 56 of 67. Selective coverage limits generalization. Sparse signals and liquidity constraints also leave substantial cash in some accounts.

The historical baseline is established, but a reliable investable edge is not. Aratana's acquisition settlement remains an explicit accounting exception: replacement shares and a contingent right require supported valuation and execution treatment. Delisting cannot be assumed to mean an executable cash exit. Hill International remains a disclosed, retrospectively requested exclusion. An accounting addendum must preserve prior results and apply general rules rather than remove inconvenient observations. [Evidence E1]

## Phase 2: structured-data preparation and supervised learning

Two offline runs have processed and audited 15,813 initial-filing candidates from 2013–2025, drawn from the 75,631-record SEC universe. Selection excludes protected review observations, Hill International, post-2025 records, unresolved sources and records not classified as standalone initial candidates. This is a factual staging universe, broader than hedge funds; it is not a count of tradable securities, validated managers or independent campaigns.

All 15,813 candidates passed the implemented source/schema/citation and internal-consistency checks. That does not certify semantic accuracy or complete extraction. Header filer/issuer identifiers and acceptance timestamps are present throughout. At least one ownership percentage was extracted in 12,673 filings; every extracted ownership row has a percentage in 11,961. Only 1,132 filings contain at least one extracted cover-person CIK. Stable header identity therefore does not solve attribution of every disclosed holder to a manager. Coverage also varies substantially by year. [Evidence E2–E3]

Strictly prior header-CIK histories have been prepared and independently recalculated: previous submissions by a reporter, previous issuers associated with that reporter, and previous reporting-party identifiers at the current issuer. Same-time filings cannot enter each other's history. These are restricted-cache activity proxies, not evidence of ongoing holdings or independent investors. Activity in company B does not establish a position in company A. The histories begin in 2013 and omit protected issuers and Hill; left-censoring and exclusions must remain explicit.

The remaining feature work is to validate dated investor/manager mappings, resolve ownership attribution where evidence permits, and construct lagged company size, industry, liquidity, volatility and prior-return measures. Fundamentals must respect publication dates. Any manager performance feature must use only outcomes already matured at the training cutoff. Missing identities and previously unseen managers require explicit handling; no identities may be chosen because they performed well.

The proposed first predictive target is continuous 504-session cumulative return relative to the historically assigned Russell size-segment ETF proxy. This aligns with the longer-term investment question, but is a proposed V4 target, not a frozen or fitted model specification. Execution timing, endpoint/accounting treatment, missing-label policy and benchmark mapping will be frozen before fitting. A shorter horizon may be retained as a declared feasibility comparison; target choice must not be optimized on final-test performance.

Begin with regularized linear regression using an elastic-net penalty, followed by gradient-boosted trees under the same development folds. Report prediction error and cross-sectional ranking usefulness, then test a predeclared ranking-to-portfolio rule after costs. If classification is chosen instead, its outcome threshold and regularized logistic baseline must be frozen first. A small neural network is an optional extension subject to effective sample size and course requirements, not a promised component.

## Two distinct roles for NLP

### Ownership and identity interpretation for Phase 2 preparation

A single filing may separately report a fund, its manager and a controller, each referencing the same shares. NLP may help identify stated relationships, qualified holdings and explicit overlap. It must not infer common control from similar names, sum overlapping holdings, or treat a missing amount as zero. Manager linkage to HFR may require external evidence that the filing alone cannot supply.

A six-case, outcome-blind development pack is prepared with full source documents and blank reference worksheets. No completed NLP comparison or accuracy result exists. Guided instruction has begun on the first case, accession 0001104659-20-044387; it is assisted practice, not an independent human reference. Remaining cases require independent answers before model interpretations. Researcher familiarity with 13Ds is still developing, so references cannot be presented as expert ground truth. Evidence-based adjudication and the feasibility of a qualified reviewer should be discussed before validation claims.

Each proposed interpretation must carry its source passage, document identity, uncertainty, and available model/prompt provenance. Missing external or binary evidence remains a gap. Practice/model-assisted answers are kept separate from independent references, and model judgments never become human labels. No paid model APIs are currently authorized. [Evidence E4]

If this pilot is useful and appropriately validated, Phase 2 will be described as structured-feature ML with NLP-assisted data preparation. It will not be described as wholly NLP-free.

### Intent information as Phase 3's incremental contribution

Phase 3 asks whether stated objectives—such as board representation, capital return or a sale—add information beyond the structured inputs. It uses Item 4 and evidence available at that disclosure, with actor/company attribution and uncertainty preserved. A reference to another company's history is not automatically a current objective or position in the subject company.

The principal comparison holds the Phase 2 identity/ownership preparation fixed and adds intent features to the same model families, dates, portfolio rules and tuning budgets. Where feasible, a separate comparison of deterministic-only versus assisted ownership/identity preparation will measure the preparation benefit rather than credit it to intent. Each comparison reports both common-sample performance and coverage changes.

Intent extraction requires human development references, a frozen protocol and a separate extraction-evaluation sample. Report claim/category errors, precision, recall, abstentions and denominators as appropriate. The six difficult development cases cannot establish population accuracy. Pretrained models may contain knowledge of later events; restricting prompts to source text does not eliminate this hindsight risk.

## Evaluation and safeguards

Chronological development folds will fit preprocessing, feature selection and hyperparameters using training data only. With a two-year target, a recent filing cannot become a training example until its return window ends. Purging/embargo rules must address overlapping outcome windows; issuer/manager grouping and sensitivity to dominant managers will assess dependence. Predeclare treatment of unseen managers and unresolved observations.

Much of the existing historical data has already been inspected. The later historical test and the expanded sample cannot be relabeled untouched holdouts. Excluding 2026 from these preparation jobs does not certify it as unexposed. Audit the exposure record and freeze the final evaluation sample before using it; if no credible historical holdout remains, report chronological development results honestly and register prospective evaluation. No prospective collection has begun, and a two-year prospective result may extend beyond the course schedule.

The investment comparison will retain equivalent entry, eligibility, benchmark, capacity, cost, cash and portfolio rules across information sets. Report coverage, events/trades, returns, drawdowns, concentration, turnover, cash exposure and uncertainty. A favorable prediction metric alone does not establish net economic value. Unresolved corporate-action accounting limits affected portfolio claims even if predictive experiments can proceed on a disclosed evaluable subset.

## Data, deliverables and scope control

Sources include the cached SEC archive, 35 supplied quarterly HFR snapshots spanning 2018 Q1–2026 Q3, and available WRDS CRSP/Compustat data. HFR classifications and externally selected recognizable-manager supplements remain candidate mappings with historical-availability and retrospective-selection limitations. The broader HFR manager universe is in scope, with focused activist candidates treated as an overlapping subset. Source availability and joins must be documented; present-day classifications cannot silently become historical signals.

Deliverables are a reproducible baseline, audited feature dictionary/panel, a limited set of supervised-learning comparisons, an evidence-backed extraction pilot and—conditional on validation and time—a matched intent-augmentation experiment. Report unresolved gaps and retain frozen sources, code, software/model identifiers, prompts, outputs and human-reference provenance. Changes to definitions produce new versions.

Work proceeds through ownership/identity review, point-in-time feature assembly, a frozen target/evaluation protocol, structured-model baselines, then conditional intent augmentation. Amendment-driven trading, higher concentration, survival/duration models, disclosure-reform causal analysis and broader 13G/13F/proxy integration remain extensions. No calendar completion promise is made before course dates and validation workload are confirmed.

## Feedback requested

1. Is a strong regularized baseline plus boosted trees sufficient for the course, or is a neural model required?
2. Is the proposed 504-session benchmark-relative target appropriate given the effective sample size and label-maturity constraints?
3. Is the distinction between NLP-assisted preparation and incremental intent features an appropriate research contribution?
4. What level of independent or expert extraction review is feasible and expected?
5. Can the course submission emphasize honest historical development and registered future validation if no untouched historical sample is defensible, and what are the required submission dates and formats?

This revision is a proposal for review, not a new frozen trading or model protocol. It changes no prior returns, investor lists or human answers.

## Evidence register and AI disclosure

E1: PHASE1-FINAL-CONCLUSION-20260924.md and the frozen phase1-long-horizon-v1.md protocol; long-horizon and later historical run archives.

E2: phase2-overnight/20260924-full-v1 — extraction completion, source provenance and selection.

E3: phase2-readiness/20260924-full-v1 — completion and field-coverage diagnostics; PHASE2-DETAILED-PROGRESS-20260925.md.

E4: ownership-identity-pilot-v1.md; six-case pack and 20260925-v1 build/QA records; subsequent guided-practice status recorded September 26. No completed independent labels or validated model comparisons are claimed.

This proposal and research tooling were developed with ChatGPT/Codex assistance. AI-supported extraction and interpretation will be identified separately from source facts and human references. Internal source hashes and evidence paths accompany the review package. No proposal has been sent to the professor by the assistant.
