# Investor Identity, Disclosed Intent, and Returns Following Initial 13D Filings

Project Proposal V3 — Direction review draft

Jeff Lu | QFGB 890H Advanced Machine Learning | Fall 2026

For Professor Dmitry Udler | September 24, 2026

## Research objective

I propose to test whether an outside investor can improve investment returns by following initial Schedule 13D disclosures, whether identifying the investor helps select investments, and whether stated intent adds information beyond structured data. The core deliverable is a long-only research backtest with realistic disclosure timing, execution constraints and trading costs.

The research has three sequential comparisons. First, establish the performance of simple disclosure-following rules without machine learning. Second, test whether supervised learning using investor identity and structured company and filing information improves selection. Third, add validated natural-language processing (NLP) features from Item 4 and available referenced exhibits to the same models. NLP is the incremental contribution, measured against structured-data ML rather than against an otherwise weaker strategy.

Research success is a credible out-of-sample comparison. Neither profitable simple following nor an improvement from ML or NLP is assumed. A negative or inconclusive result remains a valid outcome.

## Phase 1: initial-disclosure baseline

Construct eligible initial manager–issuer disclosure events and compare simple, capped equal-allocation strategies following: all eligible initial 13Ds; the identified Event-Driven manager subset; and the narrower identified Activist subset. Compare subset events with other eligible initial disclosures over common periods and against appropriate equity benchmarks. Other or unresolved filers will not automatically be classified as non-activists.

The starting setting is operating-company common equity. Closed-end funds, other investment vehicles, related-party/control transactions and different security classes require explicit eligibility decisions or separate analysis. Amendments are subsequent information, not independent baseline entries. Re-entry, joint-filer and overlapping-issuer rules will be fixed before performance evaluation.

Entry retains the V2 baseline: the first regular-session opening at least one full trading session after public disclosure, subject to historical price feasibility. The exact acceptance-timestamp and exchange-calendar implementation will be specified before testing. This distinguishes returns an outsider could earn from announcement returns already realized before entry. Primary holding horizon and benchmark will be selected after coverage checks and before inspecting comparative performance. Secondary horizons will be declared in advance.

## Phase 2: structured-data machine learning

Test investment selection using only information available at the decision time: investor identity or manager group, disclosed ownership stake, company characteristics, liquidity and prior price behavior. Historical fundamentals must respect their release dates. Any manager track-record feature may use only outcomes already observable at that training date; the treatment of previously unseen managers will be explicit.

Begin with elastic-net regression or regularized logistic regression, depending on the frozen return target. Gradient-boosted trees will test nonlinear relationships. A small feedforward neural network remains a sample-size-dependent extension, subject to course requirements. Within the same eligible universe, compare structured company/filing features with and without investor information to isolate identity's contribution. Preprocessing, tuning and model selection occur within chronological development folds.

## Phase 3: incremental contribution of NLP

Add validated stated-intent features from the initial filing's Item 4 and contemporaneously available referenced exhibits, such as board representation, capital return or a company sale. Keep the model families, structured inputs, evaluation dates, portfolio rules and tuning procedures comparable to Phase 2. Report both predictive and net investment-performance differences. Compare matched samples and report NLP-related exclusions so changes in sample composition do not masquerade as an NLP benefit.

Language models construct features; they do not supply investment outcomes or return forecasts. Human development labels precede model answers and subsequent-return inspection. A frozen extraction protocol will be evaluated on a separate held-out sample, reporting category precision, recall, abstentions and sample sizes. Positive labels require exact supporting passages. Missing evidence is distinct from absence of intent, and unreliable categories will be excluded. Pretrained-model hindsight contamination remains a limitation to assess, not something prompting alone eliminates.

## Data and current feasibility

The proposed SEC scope is 2013–2026, subject to coverage and matured outcomes. The local archive currently contains 75,631 parsed 13D/13D-A metadata records. A 200-filing review pack and a deterministic 52-filing development extraction exist; these do not constitute a completed, validated intent dataset.

Thirty-five supplied HFR snapshots cover 2018 Q1–2026 Q3. Historical Event-Driven and Activist classifications support dated universe construction. A separately flagged, externally selected supplement includes Elliott, Starboard, Pershing Square, Sachem Head, TCI, ValueAct and Icahn-related entities. Historical delivery dates remain unverified availability proxies, and present-day selection of recognizable managers introduces retrospective selection concerns.

The combined broad discovery screen contains 71 candidate manager units and 3,125 unique filings, including 404 initials. The focused screen contains 22 candidate units and 2,636 filings, including 323 initials. These are neither verified unique economic managers nor independent eligible campaigns. The supplement and HFR screen currently have different temporal coverage; comparable historical samples must be established before testing. No 3,000–4,000-campaign sample is presumed.

WRDS access is confirmed for CRSP, Compustat and Audit Analytics, and raw-data acquisition work exists. Price coverage, historical identifier joins, vendor-count inconsistencies and return/delisting conventions still require reconciliation. Audit Analytics will be assessed as reference evidence rather than assumed to be ground truth. HFR fund/manager snapshots are distinct from the proposed monthly HFR benchmark series, whose exact definition remains open.

The first gate is a documented count of usable events, identities, price links and follow-up by period, with every exclusion reported. The return panel, investment models and performance findings are not yet complete.

## Portfolio evaluation and validity

Retain capped equal-sized allocations, one position per issuer, interest-bearing cash and a documented FRED cash-rate proxy. Test identical signals at $100,000 and $100 million with size-dependent costs and feasible participation limits. Reduce oversized orders and retain residual cash. Core accounting includes trading costs and excludes taxes and management fees. Announcement-jump filters and stop-losses remain secondary comparisons against unfiltered and no-stop baselines, with gap-aware execution.

Use expanding-window development followed by a protected chronological holdout. Only outcomes matured by each training date may enter training; overlapping event horizons require purging and an appropriate embargo. Keep information from later amendments, later ownership disclosures and revised manager classifications out of initial signals. Freeze selection and execution rules before final evaluation, including the treatment of external-manager selection.

Report trade counts, event attrition, concentration, cash exposure, turnover, drawdowns, net returns and benchmark-adjusted performance with uncertainty. Examine manager and issuer dependence and sensitivity to dominant managers. Fixed-horizon event comparisons and executable portfolio returns will be reported separately. Differences are predictive associations, not proof that activism or disclosure causes returns. Rolling-window and disclosure-period analyses provide robustness without a core causal claim.

## Scope, sequence and requested feedback

Proceed through event/price feasibility, specification and simple-following baselines, structured-data ML, validated NLP augmentation, and final evaluation. Protect the final holdout throughout all stages. Human-first NLP development may proceed separately from return analysis; review packets will not expose future outcomes.

Survival models, DeepHit, duration-informed sizing, causal analysis of disclosure reforms and other-investor participation remain extensions after the core comparison. Complementary 13G, proxy/8-K, 13F and insider disclosures are staged work, not prerequisites for the first baseline.

Deliver a technical report, presentation, trade ledger and reproducibility bundle. Preserve source files, evidence spans, codebooks, prompts, model/software identifiers, raw responses, timestamps and hashes. Paid model APIs remain off during current preparation; V2's proposed $50 ceiling does not itself authorize processing. Provider choice and any later processing run require a validated bounded pilot and the applicable project authorization.

The project remains solo work with a planned 5–10 hours weekly. Supervised regularization, boosting and the potential neural extension supply the course-method contribution; LLM extraction is feature construction, consistent with the course framing recorded in V2. Feedback is requested on scope, whether a neural model is required, and submission dates and format.

**AI use disclosure.** This proposal was developed and drafted with ChatGPT and Codex assistance. Research outputs will identify AI-assisted components and retain available prompts, model/software versions and verification records.
