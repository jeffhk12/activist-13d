---
title: Predicting Activist Campaign Duration and Outcome from Disclosed Intent
subtitle: Machine learning on Schedule 13D filings, 2013–2026
kicker: COURSE PROJECT — DESIGN RECORD
course: Advanced Machine Learning in Finance · Fall 2026
author: Jeff Lu · solo project
date: Drafted 8 September 2026
---

> [!NOTE] PURPOSE
> This document consolidates the full design conversation behind the project: the research question,
> the alternatives considered and rejected, the method architecture, the extraction and labelling
> protocol, the validation and reproducibility design, the reading list, and the open items that
> still gate the work. It is a working record, not a submission.

# 1 · Executive summary

Schedule 13D tells you two things a 13F cannot: that an activist has taken a stake of 5% or more,
and — in Item 4, *Purpose of Transaction* — what they say they intend to do about it. Since
February 2024 it tells you within five business days rather than ten calendar days.

The project asks whether that stated intent, extracted at scale by a language model, predicts how a
campaign unfolds, and whether an outsider can act on it.

| | Question | Method |
|---|---|---|
| **Q1** | Does extracted campaign intent predict campaign duration and terminal outcome? | LLM extraction → competing-risks survival |
| **Q2** | Did the February 2024 acceleration change the premium available to an outsider? | Difference-in-differences around 5 Feb 2024 |
| **Q3** | Does conditioning size and holding period on predicted duration beat naive following? | Decision-focused sizing layer |

**Q3 is the deliverable.** Q1 and Q2 are inputs to it. The output of the project is a sizing and
holding-period rule, not a return forecast. Held loosely, this becomes a stock-picking project; held
firmly, it is portfolio construction.

## The three methods to point at

| Method | What it does | Why it is advanced |
|---|---|---|
| **DeepHit** — neural competing-risks survival | Predicts campaign duration and which of five mutually exclusive endings occurs (settlement, proxy win, proxy loss, target acquired, quiet exit), with live campaigns right-censored | A neural network with a custom loss — multi-task softmax over time × cause plus a ranking term. Competing risks is the hard part; a plain hazard model is simply wrong here |
| **Causal forests / GRF** with double-ML orthogonalisation | Heterogeneous treatment effects — which campaign type works on which kind of target | Built for modest samples with high-dimensional confounders. Yields a defensible causal claim rather than a correlation |
| **LLM extraction + conformal prediction** | Turns Item 4 prose into the categorical labels everything downstream conditions on, with calibrated abstention and label noise propagated forward | A semi-supervised pipeline with a real uncertainty story. Treating LLM output as noisy rather than as truth is the part almost nobody does |

**Supporting cast.** Random survival forests, gradient-boosted Cox and Cox proportional hazards as
baselines · learning-to-rank with a listwise objective for campaign selection · decision-focused
learning for the sizing layer, trained on Sharpe or CVaR rather than prediction accuracy ·
hierarchical shrinkage for thin campaign-type cells.

**Stretch goal.** Neural temporal point processes over 13D/A amendment chains — an asynchronous,
self-exciting marked event stream, which is a structural match rather than a method bolted on. Added
only if the core lands by mid-November.

> [!NOTE] THE ONE-LINER
> *A neural competing-risks survival model over LLM-extracted campaign intent, with causal forests
> for treatment heterogeneity and a decision-focused sizing layer — model classes chosen to fit a
> 3,000-event sample rather than scaled down from big-data methods.*

# 2 · How the project was chosen

Three candidate projects were worked through in sequence. Each pivot solved a specific defect in the
one before it, and the reasoning is recorded here so it is not re-litigated.

| Step | Candidate | Why it moved on |
|---|---|---|
| 1 | **Virtue of complexity, multi-asset timing** — replicate Kelly–Malamud–Zhou on a multi-asset sleeve universe, extend with LLM-read FOMC features | Cheap, cutting-edge, closed-form, and the only candidate that was genuinely multi-asset portfolio construction. Set aside by preference for 13F, not by defect |
| 2 | **Generic 13F hedge fund holdings** — replicate or learn from quarterly institutional holdings | Fatally exposed to the 45-day reporting lag. Naive cloning is a solved negative (Griffin & Xu), the commercial products have a poor live record, and the ML literature shows holdings prediction is dominated by inertia |
| 3 | **Activist Schedule 13D** — the selected project | Fixes the lag defect outright, and the horizon of the strategy matches the frequency of the data |

## Why activist 13D fixes the defect

| Filing | Deadline | What it tells you |
|---|---|---|
| 13F | 45 days after quarter end | A position existed at some point in the last four months |
| **13D** | **5 business days** | A stake of 5%+ **and the stated thesis** |
| **13D/A** | **2 business days** | Escalation, in near-real time |
| 13G / 13G/A | 45 days after quarter end (from 30 Sep 2024) | The passive counterpart — your control group |

You get the position and the intent within a week, on a strategy whose natural horizon is one to
three years. The 45-day lag stops being the binding constraint, and quarterly grain becomes adequate
rather than crippling.

## What this costs, and what it buys

The project is single-name US equity, event-driven. It is **not** multi-asset construction. Combined
with the MSQF capstone (manager selection) and the GBS industry project (earnings-call signal
extraction), the December portfolio becomes three equity projects rather than a spread across the
allocation stack.

That trade-off is accepted deliberately. It pays off specifically for hedge fund solutions and
event-driven seats, where understanding activist manager behaviour is directly on point, and it is
weaker than the multi-asset alternative for a core allocation seat.

# 3 · What is already known

The base event study is settled and the project does not attempt it.

| Established finding | Source |
|---|---|
| Announcement abnormal return of roughly **7%**, with no reversal over the following year | Brav & Jiang review; Brav, Jiang, Partnoy & Thomas (2008) |
| Decay from **15.9% in 2001 to 3.4% in 2006** as activism became common | Brav & Jiang review |
| Campaigns achieve success or partial success in about **two-thirds** of cases | Brav & Jiang review |
| Long-horizon effects positive — no evidence for the short-termism critique | Bebchuk, Brav & Jiang (2015) |
| Contested: pre- to post-activism returns insignificantly different from zero | DeHaan, Larcker & McClure (2018) |
| Alpha decays fully within roughly **12 months** from trade date | Di Mascio, Lines & Naik |

> [!WARN] CONSTRAINT
> Brav and Jiang have owned this literature for eighteen years. The novelty available here is the
> 2024 disclosure break, the LLM intent taxonomy, escalation-sequence modelling, and the sizing
> layer — **not** whether 13D filings produce announcement returns.

## The three gaps

1. **Intent has never been extracted at scale with modern models.** Existing classifications are
   hand-coded by commercial vendors over a subset of campaigns.
2. **Competing-risks survival has been applied to hedge fund lifetimes but not to activist campaign
   durations.** Haghani's dependent competing-risks framework with latent exit types is the
   methodological precedent; the application to campaigns is open.
3. **The ML literature on institutional holdings predicts holdings and never prices the
   prediction.** The 2026 dynamic-graph benchmark reaches NDCG 0.9127 against a persistent-forecast
   baseline of 0.8891, and evaluates no returns at all.

> [!WARN] THE NUMBER THAT DEFINES THE PROJECT
> State-of-the-art temporal graph learning beats *assume nothing changed* by about 2.6 points.
> Institutional portfolios are overwhelmingly inertial, so high prediction accuracy on holdings is
> nearly free and carries little information. Predict the thing that is not inertia — duration and
> changes in sizing — and always report the persistence baseline.

The project does the join: modern extraction, a survival model that respects competing risks, and an
economic evaluation with a persistence baseline and transaction costs.

# 4 · Method architecture

## Stage 0 — Panel construction

Enumerate filings, resolve filers to managers, join targets to CRSP and Compustat, and build the
campaign panel keyed on **filing date, not event date**. Amendments chain to their initial 13D to
form the campaign record. Filings are archived locally so the pipeline never depends on re-fetching.

## Stage 1 — Extraction

A language model reads Item 4 and the exhibits and returns **categorical and ordinal fields only**.
Everything numeric comes from structured sources.

| Field | Type | Source |
|---|---|---|
| Campaign demands | Categorical, **multi-label** | LLM |
| Escalation stage | Ordinal, 1 (discussions) → 5 (proxy contest / litigation) | LLM |
| Demand specificity | Ordinal: vague / specific / with deadline | LLM |
| Tone | Categorical: friendly / neutral / hostile | LLM |
| Stake %, share counts | Numeric | XML fields post-Dec 2024; cover page before; CRSP |
| Filing dates, campaign duration | Numeric | EDGAR metadata — derived, never extracted |
| Returns, market cap, fundamentals | Numeric | CRSP / Compustat |

> [!WARN] WHY CATEGORICAL
> Numbers in legal prose arrive wrapped in units, as-of dates and cross-references. A model will
> return a figure that genuinely appears in the document and answers a different question — and
> unlike a wrong category, a wrong number fails silently. Averaging five hallucinated numbers
> produces a confident wrong answer; five split votes on a category visibly flags the ambiguity.

**Multi-label, not single-label.** A single 13D often demands several things at once — board seats
and a capital return and a strategic review. Forcing one mutually exclusive class discards that and
manufactures disagreement between coders who each picked a valid answer. Use independent binary
flags per demand type; agreement is then measured per label or by Jaccard.

## Stage 2 — Duration and outcome

Competing-risks survival on campaign duration, where the terminal states are mutually exclusive:
settlement, proxy win, proxy loss, target acquired, quiet exit. Live campaigns are right-censored.

- **DeepHit** as the primary model — the neural competing-risks specification and the deep-learning
  component of the project.
- **Random survival forests, gradient-boosted Cox, and Cox proportional hazards** as baselines,
  built first.
- Evaluation on **time-dependent AUC, Uno's C, and integrated Brier score** — never accuracy.

## Stage 3 — Heterogeneous effects

Causal forests and double machine learning estimate which campaign types produce results on which
kinds of target, controlling for high-dimensional firm characteristics. The interesting quantity is
the conditional effect, not the average one.

## Stage 4 — Sizing

A sizing function trained on a **portfolio objective** — Sharpe or CVaR — rather than on prediction
accuracy, benchmarked against equal weight, stake-proportional weight, and buy-and-hold-to-exit.
This is the deliverable.

## Explicitly cut

| Dropped | Why |
|---|---|
| **Dynamic graph neural networks** on the manager × stock bipartite graph | Roughly 3,000–4,000 campaigns total and ~600 post-February 2024. Far too sparse for temporal graph learning. The reasoning is documented rather than hidden — choosing a model class to fit the effective sample size is itself the graded skill |
| **Deep learning trained from scratch on large data** | The sample does not support it. Causal identification, competing risks, calibrated uncertainty and learning under a decision loss are the harder methods here, not the softer ones |

# 5 · Extraction and labelling protocol

## Multi-provider design

| Step | Model tier | Purpose |
|---|---|---|
| Bulk pass | Cheap tier, **N = 5 samples** per filing | Primary extraction |
| Escalation | Frontier tier, split votes only | Resolve disagreement on ~15–25% of filings |
| Cross-provider audit | Second and third vendor, random 500 | Detect systematic bias |
| Optional fourth vote | Local open-weights model | Free at any sample count; version fully controlled |

**Why multiple providers, not multiple samples from one.** Sampling one model N times measures that
model's internal variance. Models from the same vendor share training data, post-training pipeline
and often tokeniser, so their errors are correlated and agreement between them overstates
confidence. Cross-provider agreement is a genuinely independent check — and where vendors diverge,
you have located text that is actually ambiguous. Route that divergence straight into the *cannot
determine* category and the abstention rule.

### Design rules

- **Vote distribution, not mean.** Labels are categorical; the aggregate is a distribution and a
  modal share, which becomes the soft label downstream.
- **Stated intent only.** The model is never asked for an outcome or a return. It has memorised what
  happened to these firms; asking it to forecast injects lookahead through the back door.
- **Instruction text byte-identical across providers.** Only schema binding and transport differ, or
  the comparison measures prompt differences rather than model differences.
- **Verify the model exposes a temperature parameter at all.** Several current frontier models have
  removed sampling controls and reject the parameter outright; the N-sample design depends on that
  knob.
- **Batch/async tier and prompt caching** on the fixed schema prefix. Total extraction spend lands
  in the low hundreds of dollars even at five samples plus audits.

## Ground truth

**First choice: a vendor-coded activism database** — human-coded classifications built from the same
filings. If the university's WRDS subscription includes Audit Analytics, the validation set is a
download rather than a three-week build.

**Fallback — hand-labelling, done properly.** A codebook written *before* labelling, with explicit
inclusion and exclusion rules, worked examples per category, and a **cannot determine** option.
Forcing a label onto genuinely ambiguous text is where single-annotator noise originates. Stratified
sampling plus active learning reaches a defensible set in roughly eight hours rather than forty.

> [!WARN] ANCHORING
> **Label blind to model output.** Reviewing and correcting LLM extractions inherits the model's
> framing and inflates every agreement statistic — you end up measuring how well a model agrees with
> a version of itself. This is the single largest threat to the validation and it is free to avoid.

### Trusting a single annotator

You cannot fully, and treating one person's labels as truth is the error. They are a **second
measurement with their own error rate**, and the fix is to measure that rate:

- **Test–retest.** Relabel 100 filings two weeks later, blind to the first pass, and report Cohen's
  κ against yourself.
- **A second coder** on 100 filings if one can be found, for a proper inter-annotator κ.
- **One codebook, two renderings.** The human codebook and the extraction prompt are generated from
  a single source of category definitions. If they diverge, human and model labels measure different
  constructs and the agreement statistic is noise.

### What is not ground truth

**Analyst ratings and sell-side reports.** Different construct — they describe a third party's view
of the stock, not the activist's stated intent — and they are usually written after the 13D, so
using them to label intent injects hindsight into a feature that must be point-in-time. Both belong
downstream as outcome data and firm-level controls, never as labels. Both are also licensed for
internal academic use and are not republishable.

# 6 · Validation and reproducibility

The validation design carries the most weight in this project, and it is deliberate about what each
check buys.

| Check | What it buys |
|---|---|
| **Purged and embargoed splits on filing date** | Leakage control. The usable timestamp is when the filing became public, never the event date |
| **Persistence and naive baselines, always reported** | Interpretability of every predictive claim. A number without its baseline is not a result |
| **Vendor-coded or hand-labelled ground truth** | Validity — are the labels actually right |
| **Label-noise propagation** | Robustness to the labelling problem. Run the model on unanimous labels, all labels, and labels perturbed at the measured error rate |
| **Cross-extractor conclusion stability** | Robustness to the choice of extraction model. Re-run the full pipeline on each provider's labels and compare *conclusions*, not label agreement rates |
| **Cost-aware evaluation in return space** | Economic meaning. Transaction costs, turnover limits, capacity and decay — never NDCG or concordance alone |

> [!WARN] A DISTINCTION WORTH KEEPING
> Cross-model consistency buys **robustness**, not reproducibility — and multi-provider working
> actually lowers reproducibility, because three endpoints can each change under you mid-semester.
> The two are graded separately and conflating them invites a hard question in the presentation.

## What actually makes it reproducible

1. **Cache every raw model response to disk.** Roughly 60,000 JSON documents, a few hundred
   megabytes. Downstream analysis then re-runs deterministically even if every endpoint changes or
   the models are retired, any label can be audited back to the exact text the model saw, and you
   never re-pay for extraction while iterating.
2. **Version the prompt and schema as files**, hashed, with the hash recorded on every response
   alongside model string, provider, timestamp and sample index. Never edit a prompt in place — a
   change means a new version, because labels produced under v1 and v2 are not comparable.
3. **Archive the source filings** rather than re-fetching them.
4. **Pin the environment** with a lockfile, and record seeds where the provider exposes them.

An agent instruction file (`CLAUDE.md`, `AGENTS.md`) governs how a coding assistant writes the code.
It is worth keeping in the repository as honest disclosure of how the code was produced — but it
reproduces nothing about the labels, and should not be counted toward that.

> [!NOTE] COURSE ALIGNMENT
> L1A claim #6 — *generalization is a property of the whole procedure ℛ(A), not of the final fitted
> equation.* The choice of extraction model is part of A. Varying it and showing the conclusion
> survives is literally estimating procedure risk over that dimension.

# 7 · Data and access

All primary data is public. No licensed or proprietary data from any employer is used at any point
in this project.

| Source | Role | Access |
|---|---|---|
| `full-index/{year}/QTR{n}/form.idx` | Enumerate every `SC 13D` and `SC 13D/A`, 2013–2026. **The spine** | Free, stable |
| EDGAR archives, whole accessions | Filing text, cover page, and **all exhibits** | Free |
| `data.sec.gov/submissions/CIK…json` | Per-filer history | Free, documented |
| `efts.sec.gov` full-text search | Targeted lookups only | Free but **undocumented** — no schema or stability commitment |
| WRDS → CRSP | Returns, delisting codes, shares outstanding | University entitlement |
| WRDS → Compustat | Target fundamentals, payout, operating performance | University entitlement |
| WRDS → Audit Analytics | Human-coded activism classifications — the validation set | **To confirm** |
| Bloomberg | Campaign outcomes, spot-checks. Inputs only, not republished | University terminal |

## Universe

Fund-initiated Schedule 13D filings, 2013–2026, restricted to a curated set of activist managers
rather than all filers — a 13F or 13D does not declare that its filer is a hedge fund, and
hand-curating 50–150 known managers is far cheaper than classifying 8,000 CIKs. Estimated
3,000–4,000 campaigns, of which roughly 600 fall after February 2024.

## Three facts that shape the pipeline

- **The 18 December 2024 XML mandate** splits the sample into a structured half and an unstructured
  half. Each row carries a flag for which parser produced it, because extraction quality almost
  certainly differs across the break — and the break sits inside the sample.
- **Item 4 frequently points at an exhibit** — the letter to the board, the presentation deck. Pull
  whole accessions. Parsing only the primary document would systematically under-capture intent on
  exactly the richest campaigns.
- **Access discipline.** SEC requires a declared `User-Agent` with a contact address and enforces
  roughly 10 requests per second across `www.sec.gov` and `efts.sec.gov`. Requests without a
  User-Agent are blocked.

## Compute

DeepHit on 3,000 events trains in seconds on CPU; causal forests are CPU-bound; API extraction
removes any need for local inference. **A discrete GPU is essentially irrelevant to this project**,
other than as an optional local ensemble member and for the neural point-process stretch goal. Total
API spend lands around **$100–150**. Cost is not the constraint here; label quality is.

## Measured universe (2026-09-08)

Counted directly from the EDGAR quarterly indices, 2013 Q1 to 2026 Q3, by
`scripts/count_universe.py`. These are all parties, before any curation to
activist managers.

| | |
|---|---|
| Initial 13D filings, 2013-2026 | **17,791** |
| Amendments 13D/A | 57,969 |
| Distinct filings | 75,760 (from 150,739 index rows) |
| **Initial filings on/after 5 Feb 2024** | **2,864** |
| Top 150 CIKs appear on | **3,267 initial filings (18.4%)** |
| Distinct CIKs, either role | 22,126 |

Run rate is stable at 1,100-1,557 initial filings a year across thirteen years,
with a mild dip in 2019-20 and no trend.

**The scoping assumption holds.** Section 4 assumed ~3,000-4,000 fund-initiated
campaigns and ~600 post-rule-change; a top-150 curation gives 3,267 before
filtering to activists, and the raw post-2024 window is 2,864. Nothing in the
method stack needs revisiting on sample-size grounds.

### Three things the count discovered

**The form-type string was renamed** from `SC 13D` to `SCHEDULE 13D` at the
18 December 2024 structured-data mandate. 2024 Q4 is the transition quarter and
carries both. Filtering on the old spelling alone returns 7 filings for the
whole of 2025 instead of ~1,100 -- it silently deletes the entire post-rule-change
sample, which is exactly the period Q2 measures. This is now a **third** thing
that changes at the December 2024 boundary, alongside the XML mandate and the
extraction-quality break.

**`form.idx` is not reliably fixed-width.** Column starts drift across the
archive, and a colspec measured on one year parses another year's dates as NaT.
Rows are matched on a regex anchored to the genuine invariants -- numeric CIK,
ISO date, `edgar/` path.

**Every 13D is indexed twice**, under the filer and under the subject company,
sharing one accession. Counting index rows overstates the universe by 2x, and
`form.idx` does not say which party is which -- that needs the submission
header (`FILED BY` / `SUBJECT COMPANY`).

### Open scoping decision: closed-end-fund versus corporate activism

The filing-frequency ranking proposed as the vendor-free curation method
surfaces **closed-end-fund discount activists**, not corporate activists:

| CEF / discount activists | | Corporate activists | |
|---|---|---|---|
| GAMCO Investors | 231 | Starboard Value | 59 |
| Saba Capital | 158 | Icahn | 40 |
| Brooklyn Capital | 66 | Elliott Associates | 34 |
| Karpus Management | 52 | VA Partners (ValueAct) | 31 |
| Stilwell Joseph | 31 | Ancora Advisors | 37 |

These are different phenomena. A CEF discount campaign has a different horizon,
a different demand taxonomy (tender offers, board declassification, open-ending)
and a different terminal-state distribution from a corporate campaign seeking a
board seat or a sale. Pooling them without a control would mix two data-generating
processes in a sample already thin enough to constrain the model class.

Three options, to be decided **before the codebook is written**, because the
campaign-type categories differ between them:

1. **Corporate only.** Cleanest comparison to Brav and Jiang, smallest sample.
2. **Both, with a fund-type indicator** and heterogeneous effects estimated
   across it. Largest sample; the causal-forest layer is already the right tool
   for exactly this split.
3. **CEF only.** Under-studied, cleaner outcome coding (open-ending and tender
   offers are observable events), but a niche result.

Option 2 is the working assumption. Identifying CEF targets is mechanical --
the subject company is a registered investment company, observable from its
SEC filer type.

# 8 · Decisions register

Every material choice, what was rejected, and why. Recorded so it is not reopened without new
information.

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Project topic | Activist Schedule 13D | Generic 13F replication — killed by the 45-day lag and a solved negative literature. Virtue-of-complexity multi-asset — better career fit, set aside by preference |
| Headline model | DeepHit competing-risks survival | Dynamic GNN — sample far too sparse. Deep RL — reproducibility-hostile and undefendable out-of-sample in one semester |
| Language | Python | MATLAB — the course environment, but the survival, causal-ML and conformal ecosystems are all Python. Confirm the course permits it |
| Extraction output | Categorical and ordinal only | Numeric extraction from prose — fails silently, and no clean agreement metric |
| Label structure | Multi-label binary flags | Single mutually exclusive class — discards genuine multi-demand campaigns and manufactures coder disagreement |
| Aggregation | Vote distribution and modal share | Mean — meaningless on categorical labels, and averaging hallucinations yields a confident wrong answer |
| Provider strategy | Multi-provider ensemble with cascade escalation | Single vendor — correlated errors across a shared training pipeline overstate confidence |
| Ground truth | Vendor-coded database, else blind hand-labelling with measured κ | Analyst ratings and sell-side reports — wrong construct and hindsight-contaminated |
| Reproducibility | Cached raw responses, versioned hashed prompts, archived filings | Cross-model consistency alone — that is robustness, a different property |
| Evaluation | Return space with costs, against a persistence baseline | NDCG or concordance alone — the graph literature's mistake |
| Universe: CEF vs corporate | **OPEN** — working assumption is both, with a fund-type indicator | Corporate-only (cleanest, smallest); CEF-only (niche). Decide before the codebook |
| Filing enumeration | Regex anchored on CIK / ISO date / `edgar/` path | Fixed-width colspecs — not stable across the archive, parses dates as NaT |
| Filing count grain | Distinct accession | Index rows — every 13D is indexed under both filer and subject, a 2x overcount |

# 9 · Timeline, risks and open items

| Weeks | Dates | Work |
|---|---|---|
| 1–2 | 8–21 Sep | Confirm Audit Analytics and CRSP access. Build the EDGAR pipeline; produce the campaign event list |
| 3–4 | 22 Sep – 5 Oct | Codebook and category definitions. Hand-label the validation set. Extraction prompt v1 |
| 5–6 | 6–19 Oct | Extraction at scale, multi-provider. Measure extraction error against ground truth |
| 7–9 | 20 Oct – 9 Nov | Competing-risks survival: baselines first, then DeepHit |
| 10–11 | 10–23 Nov | Causal forests. Sizing layer |
| 12–13 | 24 Nov – 7 Dec | Robustness, label-noise sensitivity, cost-aware evaluation, write-up |
| 14 | 8–14 Dec | Presentation |

Baselines are built before the neural model at every stage. If the schedule slips, the stretch goal
is cut first, then Stage 3.

## Risks

| Risk | Mitigation |
|---|---|
| Vendor-coded activism database unavailable | Hand-label a stratified sample with active learning — roughly 8 hours, not 40. Decided in week 1 |
| Sample size (~3,000 campaigns, ~600 post-2024) | Model class chosen to fit the effective sample. Graph learning ruled out on these grounds, with the reasoning documented rather than hidden |
| Pre-2024 parsing quality | Parser-source flag on every row; extraction quality reported separately either side of the December 2024 break |
| Provider drift mid-semester | Cached raw responses; pinned model version strings recorded per call |
| Null result on Q2 | A null on the disclosure break is informative and publishable. This is a comparison design and cannot fail to produce a result |
| Deep-learning emphasis of the course | DeepHit is a neural model and is the primary specification. If a larger-data application is expected, this must be settled before the pipeline is built |

## Open items

> [!WARN] ACTION REQUIRED
> Both blocking items belong to other people. Neither should wait on week-1 work.

1. **Does the university's WRDS subscription include Audit Analytics?** Determines whether the
   validation set is a download or a three-week build. Resolve in week 1.
2. **Does a ~3,000-event survival and event-study project satisfy the course's deep-learning
   emphasis**, or is a larger-data deep-learning application expected? This decides the shape of the
   project and should be settled before the data pipeline is built.
3. **Decide the CEF-versus-corporate universe split** (see Measured universe above).
   Blocks the codebook, because the campaign-type categories differ.
4. Assign filer-versus-subject roles per accession from the submission header.
   Not available in `form.idx`; blocks any filer league table or manager curation.
5. Confirm nothing has published on the post-February-2024 window since this draft.
6. Course syllabus and project specification not yet received — deliverable format, deadline and
   solo permission all unconfirmed.

# 10 · Reading list

Priority: **[1]** read before writing code · **[2]** read during the relevant stage · **[3]** cite,
skim as needed. Every citation should be pulled and verified before it enters the report; several
below are recorded from memory rather than from a fetched source.

## A · Hedge fund activism — the foundation

| Ref | Why |
|---|---|
| **[1]** Brav & Jiang, *Hedge Fund Activism: A Review* | The best entry point. Establishes the ~7% announcement return, the decay from 15.9% to 3.4%, and the two-thirds success rate — everything you may not claim as novel |
| **[1]** Brav, Jiang, Partnoy & Thomas (2008, *JF*), *Hedge Fund Activism, Corporate Governance, and Firm Performance* | The canonical event study. Your benchmark layer replicates this |
| **[1]** Bebchuk, Brav & Jiang (2015), *The Long-Term Effects of Hedge Fund Activism* (NBER w21227) | The long-horizon case |
| **[1]** DeHaan, Larcker & McClure (2018) | The rebuttal — insignificant pre-to-post returns. The live dispute is what makes your question defensible |
| **[2]** Becht, Franks, Grant & Wagner (2017, *RFS*), *Returns to Hedge Fund Activism: An International Study* | Cross-country evidence; useful for framing generalisability limits |

## B · The 2024 disclosure change

| Ref | Why |
|---|---|
| **[1]** SEC Release 33-11030, press release 2023-219, and the SEC fact sheet | The primary source. Read the rule itself — dates, scope and the XML mandate all bear on the design |
| **[1]** *Journal of Financial Regulation and Compliance* (2024), on shortening the 13D window | Predicts the shortened window compresses activists' delay profits, regardless of target size, profitability or stated reason. **This is the paper Q2 tests empirically.** Verify exact author and title |
| **[3]** Law-firm memoranda — Skadden, Sidley, Paul Weiss, Olshan | Fast, accurate summaries of the compliance detail. Useful for the institutional section; not citable as research |

## C · Holding duration and patient capital

| Ref | Why |
|---|---|
| **[1]** Cremers & Pareek (2016, *JFE*), *Patient Capital Outperformance* | The empirical basis for the whole longer-horizon premise — high active share plus duration over two years outperforms by roughly 2% per year |
| **[2]** Cremers & Pareek (2015); Cremers, Pareek & Sautner (2014) | Where the fund-duration measure is constructed. Read if you build your own |
| **[2]** Di Mascio, Lines & Naik, *Alpha Decay* | Alpha decays fully within roughly 12 months from trade date. Sets the clock Q2 measures against |

## D · Institutional holdings and machine learning

| Ref | Why |
|---|---|
| **[1]** *Institutional Equity Holdings Prediction Using Node Affinities of Dynamic Graphs* (arXiv 2607.12067, 2026) | The closest prior work and the paper that defines your gap: NDCG 0.9127 against a 0.8891 persistence baseline, and no return evaluation whatsoever |
| **[2]** Griffin & Xu (2009, *RFS*), *How Smart Are the Smart Guys?* | Why naive holdings-based skill inference fails. Read to know what not to build |
| **[2]** Agarwal, Jiang, Tang & Yang (2013, *JF*), *Uncovering Hedge Fund Skill from the Portfolio Holdings They Hide* | Confidential holdings outperform — the disclosure-selection problem at its sharpest |
| **[3]** Fleiss, Stoikov, Cui & DiPietro (2020, *JFDS*), *Constructing Equity Portfolios from SEC 13F Data* | An ML-on-13F portfolio construction precedent |
| **[3]** Angelini, Iqbal & Jivraj (2019), *Systematic 13F Hedge Fund Alpha* | The edge survives only when managers are pre-selected for long-term views — direct support for the universe choice |

## E · Survival analysis and competing risks

| Ref | Why |
|---|---|
| **[1]** Lee, Zame, Yoon & van der Schaar (2018, *AAAI*), *DeepHit* | The primary model. Read the loss construction carefully — a multi-task softmax over (time × cause) with a ranking term |
| **[1]** Haghani, *Modeling Hedge Fund Lifetimes: A Dependent Competing Risks Framework with Latent Exit Types* (*J. Empirical Finance*, 2014) | The finance precedent for competing risks — applied to fund lifetimes, not campaigns. Your gap, stated by someone else's scope |
| **[2]** Ishwaran, Kogalur, Blackstone & Lauer (2008), *Random Survival Forests* | The tree baseline |
| **[2]** Fine & Gray (1999) | Subdistribution hazards — the classical competing-risks estimator |
| **[2]** Uno et al. on time-dependent C-statistics; Graf et al. on the integrated Brier score | The evaluation metrics. Do not report accuracy on survival output |

## F · Causal machine learning

| Ref | Why |
|---|---|
| **[1]** Wager & Athey (2018, *JASA*), *Estimation and Inference of Heterogeneous Treatment Effects using Random Forests* | Stage 3's method |
| **[2]** Athey, Tibshirani & Wager (2019, *Annals of Statistics*), *Generalized Random Forests* | The general framework; read if you extend beyond the basic causal forest |
| **[2]** Chernozhukov et al. (2018, *Econometrics Journal*), *Double/Debiased Machine Learning* | The orthogonalisation argument. Essential for defending Stage 3 |

## G · Language models and text in finance

| Ref | Why |
|---|---|
| **[1]** Hansen & Kazinnik (2023), *Can ChatGPT Decipher Fedspeak?* | The closest methodological precedent for LLM extraction from institutional financial prose |
| **[2]** Loughran & McDonald (2011, *JF*) and their subsequent survey work | The foundation of textual analysis in finance and the standard critique of dictionary methods. Cite when justifying why keywords fail on Item 4 |
| **[2]** Lopez-Lira & Tang (2023), *Can ChatGPT Forecast Stock Price Movements?* | Read specifically for the contamination critique — the reason the design extracts intent rather than predictions |
| **[2]** Chen, Kelly & Xiu, *Expected Returns and Large Language Models*; Bybee, *The Ghost in the Machine* | LLM-as-feature-extractor framing in asset pricing |
| **[3]** *A Survey of Large Language Models in Finance* (arXiv 2402.02315); *LLMs for Financial Applications* (arXiv 2406.11903) | Orientation surveys. Skim for coverage, cite sparingly |

## H · Validation, uncertainty and backtest discipline

| Ref | Why |
|---|---|
| **[1]** López de Prado (2018), *Advances in Financial Machine Learning*, ch. 7 and 12 | A course textbook. Purging, embargo, combinatorial purged CV. Implement these yourself — `mlfinlab` went commercial, and the implementation is itself a graded modelling decision |
| **[1]** Bailey & López de Prado (2014), *The Deflated Sharpe Ratio* | Charging yourself for the specifications you tried |
| **[2]** Bergmeir, Hyndman & Koo (2018, *CSDA*) | Cited in L1A — cross-validation validity for time-dependent data |
| **[2]** Cawley & Talbot (2010, *JMLR*) | Cited in L1A — overfitting in model selection; the argument for nested CV |
| **[2]** Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction* | The calibrated-abstention machinery for the extraction labels |
| **[3]** Dixon, Halperin & Bilokon, *Machine Learning in Finance* | Course textbook; general reference |

## Reading order

Start with **A** and **B** — the contribution cannot be scoped until you know what Brav and Jiang
already own and exactly what the 2024 rule changed. Then **D**'s first entry, which defines the gap.
**E** and **F** during Stages 2 and 3. **G** before writing the extraction prompt. **H** throughout,
and before any number leaves the notebook.

# 11 · Scope note

Techniques and general methodology from professional work carry over freely. Data, code and
documents from any employer do not, and none are used here. The entire empirical basis of this
project is public SEC filings plus the university's own CRSP, Compustat and Audit Analytics
entitlements.
