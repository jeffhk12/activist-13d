# Does the activist pattern survive a Russell size comparison?

**Subsequent eligibility finding:** [the disclosure audit](PHASE1-DISCLOSURE-VALIDATION-20260924.md)
found amendment/initial mismatches and prior campaign history for the largest
winner. These preserved results require a full initial-event eligibility revision.

24 September 2026 · Exploratory development results · Six months primary.

**The focused activist pattern survives in the matched sample, but is still
uncertain.** The 66 matched focused events returned 11.98% on average, versus
4.66% for their assigned Russell ETFs: **+7.32 percentage points**. The expanded
HFR-plus-supplement group lagged its assigned benchmarks by 1.78 points.
Recognizing any HFR manager is still not sufficient evidence of an edge.

[Open the full report](../runs/phase1-baseline/20260924-russell-returns-v1/index.html).
Absolute address:
`/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-russell-returns-v1/index.html`.

## Six-month comparison on identical matched events

| Group | Events | Mean stock return | Assigned Russell ETF | Excess over Russell ETF | Excess over SPY |
|---|---:|---:|---:|---:|---:|
| Expanded HFR + supplement | 127 | +2.08% | +3.86% | −1.78 pp | −4.35 pp |
| HFR-listed managers only | 93 | +1.70% | +2.69% | −0.99 pp | −4.19 pp |
| Focused activist candidates | 66 | +11.98% | +4.66% | +7.32 pp | +4.67 pp |
| Other Event-Driven candidates | 15 | −4.36% | +0.52% | −4.88 pp | −8.61 pp |
| Newly recognized other HFR candidates | 46 | −10.03% | +3.79% | −13.82 pp | −15.92 pp |
| Other/unresolved filers | 632 | +0.88% | +2.90% | −2.02 pp | −4.96 pp |
| All matched events | 759 | +1.08% | +3.06% | −1.98 pp | −4.86 pp |

The aggregate rows overlap with the detailed cohorts. Focused, other Event-Driven,
newly recognized HFR and other/unresolved partition the sample. Other/unresolved
is not a verified non-activist or non-hedge-fund comparison group.

Entries are 19 March 2018–30 December 2022; follow-up ends by 29 December 2023.
These are equal-weight gross event averages, not annualized returns or portfolio
performance. ETF expenses and tracking differences are embedded, but trading
costs, portfolio cash and capacity constraints are not included.

## What changed versus SPY?

The focused group's earlier SPY excess was +3.98 points across 74 events. On the
66 events with a usable Russell assignment, SPY excess is +4.67 points. Replacing
SPY with the assigned Russell ETF on those **same 66 events** raises excess to
+7.32 points, a **2.65-point benchmark effect**. The move from +3.98 to +4.67
reflects the change in sample, not a better benchmark.

The focused group's 95% company-resampling interval is **−3.13 to +19.52 points**.
Its median Russell excess is +2.68 points and 53.0% of its 66 events beat their
assigned ETF. The positive average is a research signal, not established alpha;
large winners matter, and the interval still includes underperformance. It does
not capture all common market shocks or manager dependence.

## Historical membership, rather than rough dollar buckets

WRDS access provides monthly FTSE Russell constituents. Use the last month-end
snapshot before the disclosure month, matched through that date's CRSP security
identifier/CUSIP. Midcap members use IWR; remaining Russell 1000 members use IWB;
Russell 2000 members use IWM. Keep the assignment fixed during the event.
The 66 focused events comprise 46 IWM, 18 IWR and two IWB assignments.

This is **lagged monthly membership with ETF returns**, not verified daily
membership, exact index performance or risk-adjusted alpha. It uses no current
market-cap thresholds and no rank approximation. Russell 3000/IWV appears in
the report as broad-market context, not as a microcap category. Stocks without
a reliable supported-segment match remain excluded; we do not assign IWM or IWC
automatically simply because a company appears small.

Membership may change between month end and disclosure. Historical publication
times and retrospective vendor revisions remain unverified. All 58 downloaded
monthly snapshots have vendor total-count discrepancies. Returned dates and
unique identifiers were checked, but overall vendor completeness is not certified.
A missing match does not prove the company was outside the index.

Source definitions: [WRDS FTSE Russell product](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/lseg-mergent/),
[FTSE Russell index family](https://www.lseg.com/en/ftse-russell/indices/russell-us),
[IWB](https://www.ishares.com/us/products/239707/),
[IWR](https://www.ishares.com/us/products/239718/IWR), and
[IWM](https://www.blackrock.com/us/individual/products/239710/ishares-russell-2000-etf).
Historical constituent and price evidence is cached locally; current web-page
returns were not used in this calculation.

## Why the sample gets smaller

Across the original **2,097 scheduled six-month events**, 200 lack historical
security evidence at a required matching date and 1,126 lack a constituent match.
That leaves 771 assigned events. Twelve lack usable original stock returns,
leaving **759 common-sample events**. All 759 have SPY, assigned ETF and IWV returns.

For focused candidates: 75 scheduled, minus one missing historical security and
seven constituent nonmatches, leaves 67 assignments. One unresolved stock return
leaves **66 common events**, compared with 74 calculable events in the original
SPY analysis. For the expanded group: 176 scheduled, minus four missing historical
securities and 43 constituent nonmatches, leaves 129 assignments. Two unresolved
stock returns leave **127 common events**, versus 174 previously calculable.

Only 759 of the original 2,060 calculable stock/SPY events are in the new sample
(36.8%). The 1,301 excluded but previously calculable events averaged −14.60
points versus SPY. Consequently, the matched sample is economically different;
its results cannot be generalized to all filings. Missing outcomes are not zeroes.

## Supporting horizons and next work

| Group | Three-month Russell excess / events | Twelve-month Russell excess / events |
|---|---:|---:|
| Expanded HFR + supplement | −0.53 pp / 133 | +4.38 pp / 125 |
| Focused activist candidates | +4.26 pp / 68 | +17.71 pp / 65 |
| Newly recognized other HFR | −5.09 pp / 49 | −8.57 pp / 45 |
| Other/unresolved | −0.46 pp / 663 | −5.36 pp / 591 |

Six months remains primary. Different overlap exclusions and follow-up windows
produce different counts. These supporting results do not justify choosing the
best horizon after observing performance.

The next useful tests are concentration by manager/company/year, industry
controls, and a funded portfolio with costs and capital constraints. Manager
identity and company eligibility still need validation. The supplemental list
was selected retrospectively. This benchmark refinement followed inspection of
development returns; later outcomes and human-review issuers remain protected.
No predictive ML or NLP was used.

## Calculation and verification

The stock and ETF enter at the open on the second exchange session after public
acceptance and exit at the scheduled close after 126 sessions (63/252 supporting).
Entry-day close/open is compounded with subsequent daily total returns. Original
stock delisting treatment is unchanged: the usable delisting return is included
once, then proceeds earn zero through the scheduled exit. The shared issuer
schedule suppresses overlapping entries before outcomes are calculated.

- [Frozen protocol](../protocol/phase1-russell-v1.md)
- [Group statistics, uncertainty and exclusions](../runs/phase1-baseline/20260924-russell-returns-v1/summary.json)
- [Historical assignments](../runs/phase1-baseline/20260924-russell-inputs-v1/assignments.json)
- [Input/output provenance](../runs/phase1-baseline/20260924-russell-returns-v1/provenance.json)
- [Independent verification](../runs/phase1-baseline/20260924-russell-verification-v1/verification.json)

All 30 relevant tests passed. Offline replay reproduced the result files exactly.
Independent checks verify source/output hashes, historical matching dates and
identifiers, common-sample arithmetic and counts, original stock/SPY parity,
protected-period exclusions and local report links.
