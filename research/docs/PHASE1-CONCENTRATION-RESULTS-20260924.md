# Activist outperformance is promising, but concentrated

**Subsequent eligibility finding:** [the disclosure audit](PHASE1-DISCLOSURE-VALIDATION-20260924.md)
identified two amendments classified as initials and prior campaign history for
the largest winner. The preserved figures below are not an eligibility-corrected baseline.

24 September 2026 · Exploratory development diagnostic.

**The twelve-month result survives removing any single manager, company or entry
year, but most of the average outperformance comes from a handful of winners.**
This supports further investigation of activist identification; it does not yet
support a broad, repeatable activist-following edge.

[Open the detailed report](../runs/phase1-baseline/20260924-concentration-v1/index.html).
Absolute address:
`/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-concentration-v1/index.html`.

## How much depends on the largest winners?

| Stress check | Twelve-month events remaining | Mean Russell ETF excess | Six-month events remaining | Mean Russell ETF excess |
|---|---:|---:|---:|---:|
| Original matched focused sample | 65 | +17.71 pp | 66 | +7.32 pp |
| Remove the largest positive event | 64 | +10.49 pp | 65 | +1.97 pp |
| Remove the top three positive events | 62 | +4.09 pp | 63 | −1.11 pp |
| Remove the top five positive events | 60 | +0.25 pp | 61 | −3.62 pp |

These removals deliberately use realized returns to diagnose concentration. They
are not investable selection rules. Their remaining positive means do not establish
statistical significance. Six months remains the original primary test; twelve
months remains supporting.

The twelve-month median excess is **+4.26 points**, well below the +17.71 mean;
**55.4% of 65 events** beat the assigned ETF. The top five events account for
56.1% of gross positive excess before losing events offset those gains.
This pattern is consistent with a strategy whose success depends on capturing
large winners, but we have not demonstrated that those winners can be identified
in advance or held through an executable portfolio process.

The five largest twelve-month excess returns were Bed Bath & Beyond
(entry 6 April 2020), CymaBay Therapeutics (16 December 2019), Vertiv
(24 October 2022), Chefs' Warehouse (1 April 2020) and Tenneco (7 April 2020).
Their respective excess returns were +479.57, +228.26, +189.76, +121.78 and
+116.43 points over the assigned Russell ETFs. These refer only to the specified
historical holding windows, not each company's subsequent performance.

## Is it just one manager or company?

The twelve-month sample spans **62 companies and 13 candidate manager IDs/groups**.
Nine manager groups have positive average excess, although several have only
one to three events and cannot support a manager ranking.

Legion is the largest contributor: its ten candidate-linked events contribute
**9.54 points of the total +17.71-point event average**. Removing all Legion-linked
events leaves **55 events averaging +9.65 points**. Across all single-manager
removals, remaining averages range from +9.65 to +19.83 points.

Giving each company equal weight, rather than each event, yields **+15.05 points**.
Removing the top three contributing companies leaves +4.95 points; removing the
top five leaves +1.57 points. Repeated observations of the same company alone do
not explain the result, but strong company-level concentration remains.

The six-month result is more fragile: excluding Legion leaves +1.54 points,
and excluding the top three event winners turns the mean negative.

Manager identities remain candidates, with HFR Firm_IDs and external supplemental
groups treated separately. These are associations, not proof that a manager caused
the performance. Co-managed events may appear in multiple manager rows; additive
contributions split those events equally, while removing a manager removes all
its associated events. No winning-manager list has been fitted to these results.

## Does it depend on one market period?

| Entry year | Twelve-month events | Mean excess over Russell ETF |
|---|---:|---:|
| 2018 | 18 | −10.62 pp |
| 2019 | 14 | +23.36 pp |
| 2020 | 17 | +50.17 pp |
| 2021 | 7 | +1.00 pp |
| 2022 | 9 | +17.27 pp |

Four of five entry years are positive, but 2020 is particularly influential.
Excluding all 17 entries from 2020 leaves **48 events averaging +6.21 points**.
Several major winners entered around the early-2020 market dislocation. Size
matching alone does not remove sector, distress, valuation or rebound exposure;
we cannot attribute this pattern solely to activist skill.

These are entry-year cohorts with overlapping holding windows, not independent
calendar-year portfolio returns. The 2018 entry sample begins in March.

## Does twelve months still look better on identical events?

Yes. For the **same 65 disclosures, securities and purchase dates** available
at all three horizons:

| Holding period | Mean excess over assigned Russell ETF |
|---|---:|
| Three months | +3.84 pp |
| Six months | +7.25 pp |
| Twelve months | +17.71 pp |

The longer-period pattern therefore is not merely a change in sample composition.
It still reflects different lengths of market exposure and correlated outcomes,
and does not demonstrate that activism needs twelve months to work.

## What this means for our direction

Keep the activist-identification hypothesis, but frame it more precisely:
**can we identify qualifying activist disclosures before investment, and does
following them capture enough large winners to outperform after costs?** The
current average should not be interpreted as a typical expected investment return.

Next, validate the high-contribution manager/disclosure relationships and inspect
industry and entry-period exposure. Then freeze the eligibility, holding-period
and portfolio rules for fresh-data evaluation. Do not choose managers or change
the primary horizon simply because they performed best in these tables.

This work uses only the existing development results: entries March 2018–December
2022, follow-up through 2023. Human-review issuers and later evaluation outcomes
remain excluded. No NLP or ML was used. Historical Russell matches are selective,
monthly membership is lagged, vendor snapshot count discrepancies remain, and
HFR availability and supplemental-manager selection retain their earlier limitations.

## Methods and evidence

Gross equal-event stock-minus-ETF returns use identical opening purchase and
closing sale dates: second exchange session after acceptance, held for
63/126/252 sessions. Original delisting, overlap and refusal conventions are
unchanged. ETF expenses are embedded; strategy costs, portfolio cash and capacity
are not modeled. Removing winners is an after-the-fact stress test, not a new
strategy or independent confirmation of the earlier confidence interval.

- [Frozen diagnostic definitions](../protocol/phase1-concentration-v1.md)
- [Exact diagnostics and all removal results](../runs/phase1-baseline/20260924-concentration-v1/diagnostics.json)
- [Event and manager evidence](../runs/phase1-baseline/20260924-concentration-v1/events.json)
- [Same-event horizon comparison](../runs/phase1-baseline/20260924-concentration-v1/paired-horizons.json)
- [Provenance](../runs/phase1-baseline/20260924-concentration-v1/provenance.json)
- [Independent verification](../runs/phase1-baseline/20260924-concentration-verification-v1/verification.json)

All 33 relevant tests passed; offline replay reproduced the frozen outputs.
Independent checks reconcile original event values, group contributions,
leave-one-out results, winner removals, source/output hashes and report links.
