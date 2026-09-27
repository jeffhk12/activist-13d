# Does following the broader HFR universe improve returns?

**Subsequent comparison:** [Russell segment ETF results are now available](PHASE1-RUSSELL-RESULTS-20260924.md).
The SPY-only result and its calculation-stage limitations below remain preserved.

24 September 2026 · Exploratory development results · Six months primary.

**The expanded manager group outperformed other/unresolved filers, but still
lagged SPY.** Across 174 calculable events, stocks returned 2.39% on average,
versus 6.61% for SPY over the same dates. The focused activist candidates retained
their positive 3.98 percentage-point SPY-relative average. Recognizing a manager
in HFR alone does not establish an investment edge in this sample.

[Open the full report](../runs/phase1-baseline/20260924-expanded-hfr-returns-v1/index.html).
Absolute address:
`/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-expanded-hfr-returns-v1/index.html`.

## Six-month evidence

These are equally weighted gross event returns, not annualized returns or a
funded portfolio. Entries run from 19 March 2018 through 30 December 2022;
follow-up ends by 29 December 2023. All manager identities remain candidates.

| Group | Calculable / scheduled events | Mean stock return | Same-window SPY | Difference |
|---|---:|---:|---:|---:|
| All HFR + seven supplemental groups | 174 / 176 | +2.39% | +6.61% | −4.22 pp |
| HFR-listed managers only | 137 / 139 | +2.08% | +6.24% | −4.16 pp |
| Focused activist candidates | 74 / 75 | +11.41% | +7.44% | +3.98 pp |
| Other Event-Driven candidates | 26 / 26 | −10.56% | +7.09% | −17.64 pp |
| Newly recognized other HFR candidates | 74 / 75 | −2.09% | +5.61% | −7.70 pp |
| Other or unresolved filers | 1,886 / 1,921 | −6.33% | +5.31% | −11.64 pp |
| All screened initial disclosures | 2,060 / 2,097 | −5.59% | +5.42% | −11.01 pp |

The first two rows overlap with the detailed groups; do not add all rows.
Focused, other Event-Driven, newly recognized other HFR, and other/unresolved
form the four mutually exclusive groups. “Other/unresolved” is not a verified
non-hedge-fund or non-activist control group. Different event dates explain the
different SPY averages. “pp” means percentage points.

The expanded group's 95% company-resampling interval is −11.41 to +3.49 points;
the focused group's is −5.76 to +15.35 points. Both include underperformance and
outperformance. These intervals do not account for all shared market or manager
effects. The observed differences between groups are not a causal comparison.

## What changed

The previous Event-Driven-plus-supplement group had 100 calculable six-month
events and averaged −1.65 points versus SPY. The expansion adds 74 calculable
events averaging −7.70 points, bringing the combined average to −4.22 points.
Those added events already existed in the all-filings sample under
other/unresolved. Their returns and the focused group's membership are unchanged.
The saved prices were recalculated and reproduced the prior event returns exactly.

Across all dates, the expanded matching screen identifies 688 initial filings;
389 pass the preliminary data checks. Those are coverage counts, not the backtest
sample. Applying the original development entry screens to the 688 leaves 196
initial filings: 345 are excluded by dates, 27 by protected review issuers, and
120 by preliminary readiness, in the screen's recorded exclusion order.
Merging simultaneous events and suppressing overlapping company entries leaves
176 six-month events. Two have unresolved returns, leaving 174 calculable events.
Missing outcomes are not assumed to earn zero.

## Supporting holding periods

| Group | Three-month excess / calculable events | Twelve-month excess / calculable events |
|---|---:|---:|
| Expanded HFR + supplement | −1.38 pp / 182 | +1.36 pp / 167 |
| Focused activist candidates | +3.26 pp / 76 | +14.09 pp / 72 |
| Newly recognized other HFR | −1.20 pp / 78 | −2.09 pp / 71 |
| Other or unresolved | −3.86 pp / 1,962 | −19.56 pp / 1,780 |

Six months remains the primary holding period. Counts differ because the
holding period changes overlapping-entry exclusions and follow-up requirements.
The report includes all strategy views; those overlap because a manager can
offer several strategies.

## Interpretation and next step

The focused pattern remains worth testing, but **these figures are SPY-relative,
not Russell size-adjusted**. Stock size, industry, event timing and manager
selection could explain part of the difference. The next comparison is to assign
historically appropriate Russell size benchmarks and report them beside SPY on
the same matched events. Historical membership and return coverage remain pending.

The study still needs verified manager/company eligibility, historical HFR
availability, trading costs, capacity and portfolio accounting. The seven
supplemental groups were selected retrospectively; HFR name matches and strategy
offerings do not prove that a particular filing vehicle is a hedge fund or that
its investment is activist. This expansion followed inspection of development
results and is not an untouched confirmation test. Later outcomes and protected
human-review companies remain excluded. No ML or NLP was used.

## Methods and reproducibility

Entry is at the open on the second exchange session after the acceptance date;
the primary exit is the scheduled close after 126 sessions (63/252 supporting).
The original common issuer schedule suppresses overlapping entries. Entry-day
close/open is compounded with subsequent total returns; valid delisting returns
are included once, then proceeds earn zero through the scheduled exit. Gross
event averages do not include costs, capital constraints or portfolio cash drag.

- [Frozen rules](../protocol/phase1-expanded-hfr-v1.md)
- [Exact statistics](../runs/phase1-baseline/20260924-expanded-hfr-returns-v1/summary.json)
- [Sample bridge](../runs/phase1-baseline/20260924-expanded-hfr-returns-v1/bridge.json)
- [Source and output hashes](../runs/phase1-baseline/20260924-expanded-hfr-returns-v1/provenance.json)
- [Independent verification](../runs/phase1-baseline/20260924-expanded-hfr-verification-v1/verification.json)

The calculation replay reproduced the saved outputs. Independent checks reconcile
group counts and arithmetic means, preserve original event results, verify input
and output hashes, and check report links. Estimator, timing, refusal, cohort and
replay tests are in the project's test suite.
