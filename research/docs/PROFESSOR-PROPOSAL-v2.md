# Activist Intent and Investment Selection

Project Proposal V2

Jeff Lu | QFGB 890H Advanced Machine Learning | Fall 2026

For Professor Dmitry Udler | September 13 2026

## Research objective

I propose to test whether intent extracted from initial Schedule 13D disclosures improves a medium- to long-term investment strategy focused on corporate activism. Item 4 and referenced exhibits describe demands such as board representation, capital return, or a company sale. The question is whether these disclosures help select investments beyond simple activist-following and conventional company characteristics.

The core deliverable is a long-only research backtest. It will compare a strategy that buys every eligible campaign, selection using structured information, and the same selection model with validated natural-language processing (NLP) features added. This comparison isolates the incremental contribution of NLP. Research success means a credible out-of-sample evaluation after trading costs; a finding of no improvement remains a valid result.

## Data and feasibility

The proposed historical scope is 2013-2026, subject to coverage and adequate follow-up. SEC filings supply text, reporting parties, ownership disclosures, and exhibits. The current discovery collection contains 100 parsed filings and an index inventory spanning 55 quarters, with the final quarter partial. These are not yet 100 verified activist campaigns.

Read access is confirmed for CRSP daily stock data, Compustat annual fundamentals, and Audit Analytics shareholder activism data. Schema inspection and small sample queries are complete; a linked investment panel remains to be built. Audit Analytics definitions will be assessed before its classifications are used as validation evidence. I will provide monthly HFR event-driven index returns for comparison.

The first feasibility gate will count distinct eligible corporate campaigns with usable historical identifiers and return coverage, including delisting treatment. Every exclusion and failed link will be reported. If observations are insufficient, I will investigate coverage gaps and simplify the models before considering a separate investment universe.

## NLP extraction and reproducibility

Pretrained language models will extract multiple stated-intent categories from information available at the initial filing. Every positive label must include a supporting passage and source location. Missing, ambiguous, or incomplete evidence will remain explicitly uncertain. The language model will extract disclosures rather than forecast investment outcomes.

Original filings, exact inputs, category definitions, prompts, model identifiers and settings, raw responses, timestamps, and hashes will be archived. Cached responses will reproduce the research dataset offline; fresh reruns will assess model stability separately. This design also preserves the disclosures needed to audit possible hindsight contamination.

I will label development examples before seeing model answers or subsequent returns, then evaluate the frozen extraction protocol on a separate held-out sample. Precision, recall, abstentions, and sample sizes will be reported by category. Unsupported categories will be excluded. DeepSeek and Kimi are candidate bulk-processing providers, to be compared within a $50 total API budget. Provider agreement will supplement, not replace, source-based human review.

<!-- PAGEBREAK -->

## Machine learning methods and course alignment

The investment models will learn from structured company characteristics and validated intent features. Regression versus classification, the outcome benchmark, and candidate holding horizons will be settled after feasibility checks and before final testing.

**Regularized baseline.** Elastic-net regression or regularized logistic regression will provide a constrained, interpretable starting point, depending on the chosen target. Each model will be evaluated with structured features alone and with NLP features added.

**Gradient-boosted trees.** Boosted decision trees will test nonlinear relationships and interactions between company characteristics and activist demands. This connects directly to the syllabus coverage of decision trees and boosting. Tuning and learned preprocessing will occur within chronological development splits.

**Neural extension.** A small feedforward neural network will use the same inputs and evaluation framework, connecting to the course coverage of artificial neural networks and financial predictive analytics. Complexity will be constrained by sample size. If campaign-ending labels are feasible, conventional survival models and DeepHit may later investigate duration-informed exits; this is a separate extension, not a prerequisite for the core backtest.

The syllabus excludes LLM topics. Accordingly, language-model extraction is the feature-construction component; supervised selection and the neural extension demonstrate the course methods.

## Portfolio design and evaluation

Portfolios will use capped, equal-sized allocations, one position per issuer, and interest-bearing cash for unused capital. Entry will occur at the first regular-session opening at least one full trading session after publication, subject to price-data feasibility. Announcement-jump filters and stop-losses will be tested against unfiltered and no-stop baselines. Thresholds and holding horizons will be frozen before final evaluation.

Identical investment rules will be simulated at $100,000 and $100 million, with size-dependent costs and execution constraints. Oversized orders will be reduced, with residual capital in cash. Results will report trade counts, concentration, cash exposure, turnover, drawdowns, returns, and uncertainty. FRED will supply a documented cash-rate proxy. Core returns will include trading costs but exclude taxes and management fees.

Expanding-window development will precede a protected chronological holdout; only matured outcomes available at each training date may enter training. Rolling-window and disclosure-period comparisons will assess robustness without causal claims. Monthly HFR and broad-equity comparisons, including market-beta and alpha estimates, will provide investment context. Exact benchmark series remain to be agreed.

## Work plan and requested feedback

The phases are data feasibility, NLP validation, strategy specification, model development, and final evaluation. Deliverables are a technical report, presentation, and reproducibility bundle. I will work solo for 5-10 hours weekly, initially reserving two hours weekly for three weeks of manual validation. I request feedback on scope, whether the neural extension should be required, and submission dates and formats.

**AI use disclosure.** This proposal was developed and drafted with ChatGPT and Codex assistance. Research outputs will identify AI-assisted components and preserve prompts and available model/software versions for attribution and verification, consistent with the course policy.
