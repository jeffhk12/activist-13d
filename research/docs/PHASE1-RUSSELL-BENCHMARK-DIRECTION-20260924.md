# Phase 1: Russell size benchmarks plus S&P 500 context

**Subsequent update:** [the lagged historical-membership ETF comparison is now
complete](PHASE1-RUSSELL-RESULTS-20260924.md). The planning-stage status below is
preserved as history; this first implementation uses recorded monthly membership,
not a market-cap approximation.

24 September 2026. User-directed refinement of the benchmark revision.
Status: index structure and local ETF identities checked; stock assignments and
Russell-relative returns not yet calculated.

## The comparison we want

For each investment, ask two questions: did it beat comparable-sized US stocks,
and did it beat the S&P 500 over the same holding period? Use the appropriate
Russell size segment for the first question and retain S&P 500/SPY for the second.
Industry-matched comparisons remain a subsequent robustness check rather than
a prerequisite to the next size-benchmark calculation.

| Role | Russell benchmark to examine | Meaning | Potential ETF proxy |
|---|---|---|---|
| Largest companies, optional refinement | Russell Top 200 | Largest-company segment | IWL |
| Larger companies | Russell 1000 | Approximately the largest 1,000 eligible US companies | IWB |
| Mid-sized companies | Russell Midcap | Approximately the smaller 800 within Russell 1000 | IWR |
| Smaller companies | Russell 2000 | Approximately the smaller 2,000 within Russell 3000 | IWM |
| Microcap cases, separate coverage check | Russell Microcap | Microcap segment; not simply the remainder of Russell 3000 | IWC |
| Broad US market comparison | Russell 3000 | Broad large-, mid- and small-cap coverage | IWV |
| High-level comparison for every matched event | S&P 500 | Familiar large-cap opportunity-cost benchmark | SPY |

These are overlapping index families, not successive dollar-cap buckets. Russell
3000 is broad-market coverage, not a microcap benchmark. Russell Top 100 can also
be investigated if historical series and definitions cover our study period;
we have not verified that coverage. “100–3000” should not imply that an index
exists at every rank cutoff or that all series were historically available.

Definitions: [FTSE Russell US index family](https://www.lseg.com/en/ftse-russell/indices/russell-us),
[Russell 1000](https://www.lseg.com/en/ftse-russell/indices/russell-us/russell-1000),
[Russell 2000 and 3000](https://www.lseg.com/en/ftse-russell/indices/russell-2000-index),
and [FTSE Russell's segment description](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/other/russell-indexes-quarterly-ipo-update.pdf).
These establish the family structure; they do not establish historical membership
for a particular company in 2018–2022.

## Assignment and return conventions

Prefer membership effective before the disclosure, including historical
reconstitution dates and additions/removals. Do not use today's constituents or
market-cap cutoffs. Resolve index overlap with a documented assignment rule:
midcap members can use Midcap as their primary size reference, while Russell
1000 remains their broader large/mid-cap cross-check. Optional Top 200 and Microcap
refinements require explicit historical coverage checks.

If historical membership is unavailable, construct a pre-disclosure size/rank
approximation and label it as such. The earlier $2bn/$10bn descriptive bands do
not reconstruct Russell membership. Company capitalization across share classes,
US eligibility and the historical reconstitution rules must be addressed. Do not
force foreign or unresolved companies into a US size benchmark without disclosure.

Assign the benchmark before inspecting subsequent returns and hold that assignment
fixed for the event's holding period. Do not switch a stock's benchmark because
its subsequent performance changes its size. The selected index or ETF can still
reconstitute its own holdings normally during the period.

Use total returns and identical opening-entry/closing-exit dates. A direct index
close-to-close series is not automatically comparable with our open-to-close
stock return. ETF proxies may align more readily with the existing execution
convention, but include fund expenses and tracking differences; label results
as ETF-relative when proxies are used. Do not call proxy returns exact index returns.

Keep six months primary and three/twelve months supporting. Show stock return,
assigned Russell benchmark return, stock-minus-Russell, S&P 500 proxy return and
stock-minus-SPY. Compare benchmarks on the same successfully matched events and
show exclusions. Do not report the best result from several alternative benchmarks
as though it were the preselected primary test.

## Available evidence and next work

Cached CRSP stocknames_v2 records have ETF identity intervals covering the
development period for IWB (88221), IWM (88222), IWV (88223), IWR (89059),
IWL (93024) and IWC (90834). These are persistent security identifiers, not
verified price coverage or stock-to-index membership assignments. The original
SPY identity and return calculation remain preserved.

The [historical characteristics audit](../runs/phase1-baseline/20260924-benchmark-inputs-v1/index.html)
provides size and industry fields for all 75 scheduled focused-group events.
We have not yet verified a historical Russell constituent dataset or completed
an approximation rule. Next, establish assignment coverage and benchmark return
coverage, record a new calculation protocol, and run the common-sample comparison.

The focused group's existing +3.98-point mean excess return is against SPY across
74 calculable events. It must not be relabeled as Russell-relative or risk-adjusted
alpha. This benchmark refinement follows inspection of development results; the
later evaluation period remains reserved.
