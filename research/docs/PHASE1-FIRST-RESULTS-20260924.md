# Phase 1: what the first return comparison means

24 September 2026. Status: development evidence, before trading costs; not the
final portfolio backtest. [Open the results report](../runs/phase1-baseline/20260924-development-v4/index.html).

## The investment takeaway

The first calculation does not support buying indiscriminately after every
screened initial 13D. The narrower activist-candidate group looks better, but
the evidence is too uncertain to claim an investment edge. This makes investor
identity worth investigating; it does not yet show that identifying a famous
manager is enough to produce excess returns.

Think of this as comparing a manager's individual investment ideas with the
market over each idea's life. It is not yet the return an allocator would have
earned in a funded portfolio, because capital, cash, costs and simultaneous
holdings still need to be modeled.

## Six-month results

These are event-weighted averages for development entries from 19 March 2018
through 30 December 2022. Every stock is compared with SPY over the same purchase
and exit dates. Six months means 126 trading sessions, including entry day.

| Group | Calculable / scheduled events | Mean stock return | Mean same-window SPY return | Mean difference |
|---|---:|---:|---:|---:|
| All screened initial disclosures | 2,060 / 2,097 | -5.59% | +5.42% | -11.01 percentage points |
| Broad manager candidates | 100 / 101 | +5.70% | +7.34% | -1.65 points |
| Focused activist candidates | 74 / 75 | +11.41% | +7.44% | +3.98 points |
| Other or unresolved managers | 1,960 / 1,996 | -6.17% | +5.32% | -11.49 points |

Differences are calculated before rounding. Focused is inside broad; do not add
the two groups. “Other” is not a certified non-activist control group. The broad
and focused labels remain candidate matches, not verified economic identities.

For the focused subset, the typical middle event beat SPY by about 1.99 points,
and 52.7% of calculable events beat SPY. That is a more modest picture than the
11.41% mean absolute return alone might suggest. The mean excess-return estimate's
95% issuer-resampling interval runs from **-5.76 to +15.35 percentage points**.
It includes both underperformance and outperformance. This uncertainty estimate
accounts for repeated companies, but not shared market shocks or manager effects.

## What we did to make this a useful first test

The rules were recorded before comparative returns were calculated. The user
chose six months as primary, with three and twelve months supporting. All three
appear in the report; we did not select the horizon with the best result.

The purchase occurs at the second trading-session opening after publication,
allowing a full intervening session. Same-company overlapping opportunities are
suppressed before outcomes are examined. Group comparisons use that shared event
schedule; they are not independently simulated manager-subset portfolios.

We excluded 207 issuer identities associated with current human review material
before calculating returns, protecting the labeling work from outcome exposure.
This also makes the sample less representative, which must remain visible in the
interpretation. This run does not evaluate 2024 or later outcomes. A final holdout
will also need to exclude examples already exposed in earlier price previews.

## Data repair and remaining limits

The first pass omitted many observations because the archive had an incomplete
cache pair for 8 February 2023. We preserved that evidence and downloaded the
date into a new raw-data directory. The full response contained 9,483 securities
and exactly matched the union of two disjoint security-ID partitions. Vendor
reported-count inconsistencies remain flagged; this does not certify overall
historical coverage.

The repaired run increased calculable six-month events from 1,905 to 2,077.
The selection ledger and research protocol are byte-identical before and after
the repair. The original result is preserved as development-v2. A subsequent
implementation check found that 17 events did not have a usable closing trade on
the scheduled exit date, as the protocol requires. Development-v4 corrects that
check and is the current result: 2,060 calculable events. Event selections and
the protocol remain unchanged; the manager-subset results are unchanged by the
exit correction. Twenty other scheduled events still have missing or invalid
total returns. All 37 refusals are retained, not treated as zero returns.
The calculation includes 122 events with usable delisting returns.

The corporate-share screen does not finish operating-company or related-party
eligibility review. HFR historical availability is still based on delivery-date
proxies, and the supplemental manager list was chosen retrospectively. SPY does
not control for differences in size, sector or other risk exposures. Entry-day
trading observations support this diagnostic; they are not a validated real-time
liquidity rule or a guarantee of execution.

Returns are gross. Delisting proceeds earn zero after exit in this calculation;
the final portfolio still requires interest-bearing cash, costs, position limits
and capacity checks. Statistical and economic conclusions must wait for those
steps and an untouched evaluation sample.

## Next decisions the work will support

First resolve the 20 return exceptions and 17 exit-trade exceptions, and review company/manager eligibility.
Then determine whether the identity comparison survives comparable company and
period controls, and whether a few managers or companies drive the result.
Build the funded simple-following portfolio before moving to predictive ML.

Verification: 23 focused estimator, refusal, sample-protection and acquisition
tests passed; the saved panel reproduced the run byte-for-byte. Independent
checks reconcile the ledger, protect review issuers and later dates, verify
nonoverlap, recompute mean excess returns and check report links and file hashes.

Evidence: [frozen protocol](../protocol/phase1-development-v1.md),
[exact results](../runs/phase1-baseline/20260924-development-v4/summary.json),
[event ledger](../runs/phase1-baseline/20260924-development-v4/outcomes.json),
[repair receipt](../runs/phase1-baseline/20260924-daily-gap-repair/receipt.json),
and [independent verification](../runs/phase1-baseline/20260924-development-verification-v4/verification.json).
