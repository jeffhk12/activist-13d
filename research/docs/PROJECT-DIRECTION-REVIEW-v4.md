# Project direction review — what changed in V4

September 26, 2026 | For Jeff's review alongside the professor proposal

The project still asks whether identifying who is investing—and understanding what they disclose—helps select better investments after an initial 13D. We now have a historical baseline and a large factual dataset. We do not yet have a trained selection model or demonstrated alpha.

## The three investment questions

1. Phase 1: Does simply following eligible initial disclosures work? We established a historical baseline, but the evidence does not establish a reliable investable edge. Favorable longer-horizon averages coexist with negative medians, weak matched comparisons and unresolved portfolio accounting.
2. Phase 2: Can we choose better investments using company characteristics, ownership and investor identity/history? Preparation is complete for 15,813 initial candidates, but historical manager mappings and market features still need work. No predictive model has been trained.
3. Phase 3: Does understanding the investor's stated plans improve selection beyond those structured inputs? This remains the incremental intent-NLP question, conditional on reliable extraction and a fair matched comparison.

## The important refinements

| V3 direction | V4 update | Why it matters |
|---|---|---|
| Establish the simple-following baseline | Historical research synthesized; accounting exceptions disclosed | We cannot describe Phase 1 as proof of alpha or every account as complete |
| Choose horizons before comparative results | Longer-horizon revision followed inspection of earlier results | The two-year thesis is exploratory, not independent confirmation |
| Structured ML followed by NLP | Potential NLP-assisted identity/ownership preparation, then incremental intent NLP | We must isolate two different contributions rather than credit both to intent |
| Human-first extraction review | First case is now assisted practice; other references remain pending | Learning with AI is useful, but it is not independent validation |
| Protected final holdout | Historical exposure must be audited; future validation may be needed | A later date or an unused processing year does not automatically mean unseen data |
| Broad proposed methods | Regularized regression and boosted trees first; neural model conditional | Focus effort on a credible comparison rather than too many techniques |

## What the ownership/identity pilot is trying to solve

Imagine a fund, its manager and a controller each report the same eight-percent position. We need to recognize the relationships without turning eight percent into twenty-four percent or counting three related names as three independent investors. NLP may help read the explanations; it cannot establish a relationship that the source does not support.

The six-case pack is development work. We have started learning how to read the first filing's SEC header. That filing is marked assisted practice for evaluation purposes. No ownership-NLP accuracy claim exists yet. You do not need to pretend to be a 13D expert: uncertain answers stay uncertain, and the proposal asks the professor what independent review standard is appropriate.

## What is proposed, rather than already decided

The proposed first model would predict roughly two-year cumulative return relative to the appropriate historical Russell ETF proxy. We would start with a simple regularized model, then test boosted trees. We would ask whether adding investor information improves selection, then whether adding stated intentions improves it further.

That target is not frozen yet. We must check how many usable training observations remain after requiring two years of outcomes to be known at each training date. The historical sample size is not the same as the usable training sample, and 15,813 filings are not 15,813 independent hedge-fund investments.

We are retaining the existing 5% position targets for comparability. Higher concentration and trades triggered by amendments are separate strategy ideas, not changes already implemented. Missing acquisition settlements also cannot be filled with assumed sale proceeds.

## Recommended next steps

1. Continue the guided ownership/identity example and decide how independent reference review will work.
2. Diagnose field gaps and build dated manager links plus pre-entry market features.
3. Freeze the target, sample, timing, missing-data treatment and evaluation rules before fitting models.
4. Compare simple supervised models with the Phase 1 baseline under the same portfolio rules.
5. Add intent features only after their extraction is sufficiently reliable and the incremental comparison is feasible.

The professor proposal requests feedback on course-method requirements, the two-year target, review standards and a realistic validation/submission scope. V4 does not claim that ML or NLP has already improved returns.

Read PROFESSOR-PROPOSAL-v4.md or the companion HTML for the full academic proposal. Earlier proposal versions, evidence, returns and human worksheets are preserved.
