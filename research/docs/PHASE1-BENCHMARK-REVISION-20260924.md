# Phase 1: benchmark each investment against comparable stocks

24 September 2026. User-directed development revision after reviewing the SPY
comparison. Status: historical inputs audited; revised benchmark returns pending.

Latest refinement: [Russell size segments plus S&P 500 context](PHASE1-RUSSELL-BENCHMARK-DIRECTION-20260924.md)
now define the next comparison. Industry matching remains a subsequent robustness
check. The earlier hierarchy below is retained as the development history.

## The investment meaning

The user is right that SPY is too narrow a reference for answering whether these
investments have an edge. We need to separate the return earned by choosing the
stock from the return available in similar investments during the same period.

The focused activist candidates did show positive excess returns **against SPY
in this development sample**: about 3.98 percentage points on average over six
months across 74 calculable events. That is a real description of the calculation.
It is not yet an estimate of excess returns against an appropriate stock-specific
benchmark, nor proof of reliable alpha. Its issuer-resampling interval was -5.76
to +15.35 percentage points; the sample is small and the interval is wide.

For example, if a smaller industrial company returns 12% while comparable stocks
return 5%, its relative return is +7 points. If those peers return 15%, the same
investment trails by 3 points. Its return relative to SPY cannot settle which
interpretation applies. These example figures are illustrative, not project results.

## The size audit supports the benchmark concern

We examined characteristics at the last trading session strictly before the
earliest associated disclosure date, rather than using current company sizes.
These counts cover scheduled events, including events with unresolved returns.

| Group | Scheduled events | Below $2bn | $2bn–$10bn | $10bn or more | Size missing |
|---|---:|---:|---:|---:|---:|
| All screened events | 2,097 | 1,762 | 276 | 54 | 5 |
| Broad manager candidates | 101 | 64 | 30 | 7 | 0 |
| Focused activist candidates | 75 | 43 | 26 | 6 | 0 |

The focused group is within the broad group. About 84% of all scheduled events
fall below $2bn, while 69 of 75 focused events fall below $10bn. The audit has
size and industry fields for 2,092 of 2,097 total events and all 75 focused events.
This supports further matching; it does not mean a suitable benchmark has already
been successfully assigned to every event.

Size here is the historical security-level market capitalization in CRSP. It
may not equal whole-company capitalization for multiple share classes. The dollar
bands are descriptive, not historical Russell/S&P index membership. Industry is
a two-digit SIC grouping, not a completed economic-peer or GICS-sector match.

## Revised benchmark hierarchy

1. **Primary research comparison: similar size and industry.** Assign a benchmark
   or peer basket based on characteristics observable before disclosure. Account
   for geography where a US benchmark would be inappropriate. Resolve company
   versus share-class size, peer counts, weighting, and missing-data rules before
   calculating the new comparison. Do not select peers using their later returns.
2. **Investable reference: an appropriate size segment.** Small-, mid- and large-cap
   index funds provide interpretable opportunity-cost comparisons. They are a
   useful cross-check but do not by themselves remove sector or style effects.
   For illustration, IJR tracks S&P SmallCap 600 and IJH tracks S&P MidCap 400;
   neither should be assigned solely by claiming that our descriptive dollar
   bands reproduce historical constituent membership.
3. **SPY: retain as broad-market context.** Preserve the original result so the
   effect of changing the benchmark remains visible. It is no longer sufficient
   as the primary evidence for a stock-selection edge.

Compare the old and revised benchmark on **the same matched events**, using
identical purchase/exit dates and return conventions. Report full-sample SPY
results separately from matched-sample SPY results, so sample attrition is not
mistaken for a benchmark effect. Show benchmark coverage, characteristics and
matching quality alongside the return differences.

Size/industry adjustment still does not isolate manager skill completely. Later
robustness should examine value/growth, momentum, beta and common market-period
effects, followed by costs and executable portfolio performance. No predictive
machine learning is required to construct or evaluate these baseline comparisons.

## What changes and what stays fixed

This changes the main benchmark question, not the user-selected six-month primary
horizon, three-/twelve-month supporting horizons, disclosure delay or reserved
later evaluation period. Prior frozen research protocols and numerical runs are
preserved. The exact new calculation will have a new protocol version.

We have already seen development results, so this refinement must be disclosed
as a development-stage revision. We cannot describe it as independently specified
before all results were observed. Rules will be fixed before computing the new
comparison and kept unchanged for later evaluation.

The next deliverable is a documented stock-to-benchmark mapping and a comparison
on common matched events. **No revised benchmark excess-return estimate has yet
been calculated.** The appropriate conclusion today is a promising in-sample
SPY-relative pattern that needs a fairer benchmark test.

## Evidence

- [Historical size/industry audit](../runs/phase1-baseline/20260924-benchmark-inputs-v1/index.html)
- [Exact coverage counts](../runs/phase1-baseline/20260924-benchmark-inputs-v1/summary.json)
- [Pre-disclosure characteristics and sources](../runs/phase1-baseline/20260924-benchmark-inputs-v1/observations.json)
- [Preserved SPY results](../runs/phase1-baseline/20260924-development-v4/summary.json)
- [CRSP field definitions](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/): daily capitalization is reported in thousands; the audit converts the units consistently.
- [IJR official factsheet](https://www.ishares.com/us/literature/fact-sheet/ijr-ishares-core-s-p-small-cap-etf-fund-fact-sheet-en-us.pdf) and [IJH official product page](https://www.ishares.com/us/products/239763/ishares-core-sp-midcap-etf): examples of size-segment benchmarks, not a completed assignment rule.
