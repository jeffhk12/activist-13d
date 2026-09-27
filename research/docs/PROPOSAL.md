---
title: Predicting Activist Campaign Duration and Outcome from Disclosed Intent
subtitle: Machine learning on Schedule 13D filings, 2013–2026
kicker: PROJECT PROPOSAL
course: Advanced Machine Learning in Finance · Fall 2026
author: Jeff Lu · solo project
date: 8 September 2026
---

> [!NOTE] SCOPE
> This is the submission-shaped proposal. Full design detail — the alternatives considered and
> rejected, the extraction and labelling protocol, the decisions register and the complete reading
> list — is in `DESIGN-RECORD.md` in this folder.

# 1 · Research question

Schedule 13D discloses two things a Form 13F cannot: that an investor has taken a stake of 5% or
more, and — in Item 4, *Purpose of Transaction* — what they say they intend to do about it. Since
5 February 2024 it must be filed within five business days rather than ten calendar days, with
amendments within two.

The project asks whether that stated intent, extracted at scale by a language model, predicts how a
campaign unfolds and whether an outside investor can act on it.

| | Question | Method |
|---|---|---|
| **Q1** | Does extracted campaign intent predict campaign duration and terminal outcome? | LLM extraction → competing-risks survival |
| **Q2** | Did the February 2024 acceleration change the premium available to an outsider? | Difference-in-differences around 5 Feb 2024 |
| **Q3** | Does conditioning position size and holding period on predicted duration beat naive following? | Decision-focused sizing layer |

Q3 is the deliverable; Q1 and Q2 are inputs to it. The output is a sizing and holding-period rule,
not a return forecast.

# 2 · Motivation

Institutional holdings data is a poor basis for outside investors because of its reporting lag. A
13F position is up to four months stale on publication, which is why naive replication of hedge fund
holdings does not work and why the machine-learning literature on holdings prediction is largely
predicting portfolio inertia.

Schedule 13D does not have that problem. The filing arrives within a week, it states a thesis, and
it describes a campaign whose natural horizon is one to three years. The reporting frequency finally
matches the horizon of the strategy.

Two features make this a live question rather than a settled one. First, the 2024 acceleration is a
clean structural break with roughly two and a half years of post-change data and no settled
empirical answer. Second, the demand type in Item 4 — board representation, sale of the company,
operating change, capital return, management removal — is the primary conditioning variable for
everything downstream, and it exists only as legal prose thick with boilerplate. Keyword and
dictionary methods fail on it.

# 3 · Related work and the gap

The base event study is settled and this project does not attempt it. Brav, Jiang and co-authors
document an announcement abnormal return of roughly 7% with no reversal over the following year,
decaying from 15.9% in 2001 to 3.4% in 2006, with campaigns achieving success or partial success in
about two-thirds of cases. Bebchuk, Brav and Jiang find positive long-horizon effects; DeHaan,
Larcker and McClure dispute them. That debate is the backdrop, not the contribution.

The gap sits in three places:

1. **Intent has never been extracted at scale with modern models.** Existing classifications are
   hand-coded by commercial vendors over a subset of campaigns.
2. **Competing-risks survival has been applied to hedge fund lifetimes but not to activist campaign
   durations.** Haghani's dependent competing-risks framework with latent exit types is the
   methodological precedent; the application is open.
3. **The machine-learning literature on institutional holdings predicts holdings and never prices
   the prediction.** The 2026 dynamic-graph benchmark on 13F reaches NDCG 0.9127 against a
   persistent-forecast baseline of 0.8891 and evaluates no returns at all.

This project does the join: modern extraction, a survival model that respects competing risks, and
an economic evaluation against a persistence baseline with transaction costs.

# 4 · Data

All primary data is public. Fund-initiated Schedule 13D and 13D/A filings, 2013–2026, restricted to
a curated set of activist managers — an estimated 3,000–4,000 campaigns, of which roughly 600 fall
after February 2024.

| Source | Role |
|---|---|
| EDGAR quarterly index `form.idx` | Enumerate every `SC 13D` and `SC 13D/A`. The spine |
| EDGAR archives, whole accessions | Filing text, cover page, and all exhibits |
| WRDS → CRSP | Returns, delisting codes, shares outstanding |
| WRDS → Compustat | Target fundamentals, payout, operating performance |
| WRDS → Audit Analytics (to confirm) | Human-coded activism classifications — the validation set |

Two facts shape the pipeline. The 18 December 2024 XML mandate splits the sample into a structured
and an unstructured half, so each row carries a flag for which parser produced it. And Item 4
frequently points at an exhibit, so whole accessions are pulled rather than primary documents alone.

# 5 · Method

**Stage 0 — Panel.** Enumerate filings, resolve filers to managers, join targets to CRSP and
Compustat. The panel is keyed on **filing date, not event date**. Amendments chain to their initial
13D to form the campaign record.

**Stage 1 — Extraction.** A language model reads Item 4 and the exhibits and returns categorical and
ordinal fields only — demand type (multi-label), escalation stage, demand specificity, tone. All
numeric quantities come from structured sources. Extraction runs across multiple providers with
repeated sampling; the aggregate is a vote distribution, which becomes a soft label downstream. The
model is asked for stated intent only, never for an outcome or a return.

**Stage 2 — Duration and outcome.** Competing-risks survival where the terminal states are mutually
exclusive: settlement, proxy win, proxy loss, target acquired, quiet exit. Live campaigns are
right-censored. **DeepHit** is the primary specification, with random survival forests,
gradient-boosted Cox and Cox proportional hazards as baselines built first. Evaluation on
time-dependent AUC, Uno's C and the integrated Brier score.

**Stage 3 — Heterogeneous effects.** Causal forests and double machine learning estimate which
campaign types produce results on which kinds of target, controlling for high-dimensional firm
characteristics. The quantity of interest is the conditional effect, not the average one.

**Stage 4 — Sizing.** A sizing function trained on a portfolio objective — Sharpe or CVaR — rather
than on prediction accuracy, benchmarked against equal weight, stake-proportional weight and
buy-and-hold-to-exit.

**Stretch.** Neural temporal point processes over 13D/A amendment chains, added only if Stages 1–4
land by mid-November.

**Explicitly cut:** dynamic graph neural networks. With ~3,000 campaigns the manager × target graph
is far too sparse for temporal graph learning. Choosing a model class to fit the effective sample
size, and documenting why, is part of the work rather than a concession.

# 6 · Validation

| Check | What it buys |
|---|---|
| Purged and embargoed splits on filing date | Leakage control — the usable timestamp is publication, never the event date |
| Persistence and naive baselines, always reported | A predictive number without its baseline is not a result |
| Vendor-coded or blind hand-labelled ground truth, with measured κ | Label validity, and a reliability estimate rather than an assumption |
| Label-noise propagation — unanimous, all, and perturbed label sets | Robustness to the labelling problem |
| Cross-extractor conclusion stability | Robustness to the choice of extraction model |
| Cost-aware evaluation in return space | Economic meaning, rather than NDCG or concordance alone |

**Reproducibility.** Every raw model response is cached to disk, so downstream analysis re-runs
deterministically even if endpoints change. Prompts and schemas are versioned files, hashed, with
the hash recorded on each response alongside model string, provider and timestamp. Source filings
are archived rather than re-fetched.

# 7 · Deliverables

1. Technical report — question, data, method, results, limitations.
2. Reproducibility bundle — code, cached model responses, codebook, versioned prompts and schemas,
   environment lockfile, archived filings.
3. Presentation, including an explicit account of what did not survive validation.

# 8 · Timeline

| Weeks | Dates | Work |
|---|---|---|
| 1–2 | 8–21 Sep | Confirm data access. Build the EDGAR pipeline; produce the campaign event list |
| 3–4 | 22 Sep – 5 Oct | Codebook and category definitions. Hand-label the validation set. Extraction prompt v1 |
| 5–6 | 6–19 Oct | Extraction at scale. Measure extraction error against ground truth |
| 7–9 | 20 Oct – 9 Nov | Competing-risks survival: baselines first, then DeepHit |
| 10–11 | 10–23 Nov | Causal forests. Sizing layer |
| 12–13 | 24 Nov – 7 Dec | Robustness, label-noise sensitivity, cost-aware evaluation, write-up |
| 14 | 8–14 Dec | Presentation |

Baselines precede the neural model at every stage. If the schedule slips, the stretch goal is cut
first, then Stage 3.

# 9 · Risks

| Risk | Mitigation |
|---|---|
| Vendor-coded activism database unavailable | Hand-label a stratified sample with active learning — roughly 8 hours. Decided in week 1 |
| Sample size (~3,000 campaigns, ~600 post-2024) | Model class chosen to fit the effective sample, with the reasoning documented |
| Pre-2024 parsing quality | Parser-source flag per row; extraction quality reported either side of the December 2024 break |
| Provider drift mid-semester | Cached raw responses; pinned model version strings recorded per call |
| Null result on Q2 | A null on the disclosure break is informative. This is a comparison design and cannot fail to produce a result |

# 10 · Key references

Full annotated reading list in `DESIGN-RECORD.md` § 10.

- Brav & Jiang, *Hedge Fund Activism: A Review*
- Brav, Jiang, Partnoy & Thomas (2008, *JF*), *Hedge Fund Activism, Corporate Governance, and Firm Performance*
- Bebchuk, Brav & Jiang (2015), *The Long-Term Effects of Hedge Fund Activism*, NBER w21227
- DeHaan, Larcker & McClure (2018) — the rebuttal
- Cremers & Pareek (2016, *JFE*), *Patient Capital Outperformance*
- Griffin & Xu (2009, *RFS*), *How Smart Are the Smart Guys?*
- *Institutional Equity Holdings Prediction Using Node Affinities of Dynamic Graphs*, arXiv 2607.12067 (2026)
- Lee, Zame, Yoon & van der Schaar (2018, *AAAI*), *DeepHit*
- Haghani (2014, *J. Empirical Finance*), *Modeling Hedge Fund Lifetimes*
- Wager & Athey (2018, *JASA*), *Heterogeneous Treatment Effects using Random Forests*
- Chernozhukov et al. (2018), *Double/Debiased Machine Learning*
- Hansen & Kazinnik (2023), *Can ChatGPT Decipher Fedspeak?*
- López de Prado (2018), *Advances in Financial Machine Learning*, ch. 7 and 12
- SEC Release 33-11030 — Modernization of Beneficial Ownership Reporting

# 11 · Open items

1. Does the university's WRDS subscription include Audit Analytics? Determines whether the
   validation set is a download or a three-week build.
2. Does a ~3,000-event survival and event-study project satisfy the course's deep-learning emphasis,
   or is a larger-data application expected?
3. Course project specification not yet received — deliverable format and deadline unconfirmed.

# 12 · Scope note

All data used is public SEC filings plus the university's own CRSP, Compustat and Audit Analytics
entitlements. No licensed or proprietary data from any employer is used at any point.
