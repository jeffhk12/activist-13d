# Phase 1 development calculation — v1

Recorded 24 September 2026 before comparative returns are calculated. This is a
development diagnostic, not the final investable-universe or portfolio protocol.
The user selected six months primary, with three and twelve months supporting.
Use 126, 63 and 252 exchange sessions respectively, counting the entry session as
session one. These are trading-session approximations, not calendar anniversaries.

## Sample and information boundaries

Use the preserved feasibility-v2 registry. Require its basic readiness checks,
one identified issuer CIK, and normal active trading with positive opening price
and volume at entry. Corporate-share eligibility and manager identity remain
provisional. Do not describe resulting observations as validated campaigns.
Only entry dates 2018-03-19 through 2022-12-30 enter development; follow-up may
extend through 2023-12-29. Reserve 2024 onward from this calculation. This proposed
evaluation boundary does not certify that every later record is globally unseen:
the earlier 2025 price-preview examples must be excluded from a final holdout.

Protect human development material before return calculation: collect accession
identifiers appearing in filenames under review/current and review/drafts, and
exclude all initial filings of their issuer CIKs from this development study.
This deliberately conservative issuer-level rule protects other filings about
the same company. Do not write outcomes into any human review material.

For each horizon independently, sort eligible events by entry date and accession.
Suppress simultaneous multiple-security choices for the same issuer. Combine
same-issuer/same-security/same-entry disclosures, preserving accessions and taking
the union of their manager subset flags. Accept the earliest remaining event per
issuer and suppress new entries through its scheduled exit, inclusive. Do this
before observing outcomes; a later data failure must not trigger a replacement
trade. Re-entry after that scheduled exit is allowed. This is an event sampling
rule, not capital allocation or certified campaign construction.

## Entry, benchmark and return

Entry is the second XNYS trading session strictly after the SEC acceptance date,
preserving the feasibility convention and a full intervening session. Use the
recorded opening trade price. Exit at the scheduled session's closing trade price.
Benchmark each event against SPY (CRSP security 84398, historical CUSIP 78462F10)
over the identical interval, verifying the historical name interval. SPY is a
broad large-cap opportunity-cost comparison, not a size/sector/risk-matched control.

Gross wealth multiplier = entry-day close/open times the product of (1 + daily
total return) on subsequent sessions. Entry-day distributions are not credited
to an investor purchasing on their ex-date. Subsequent total returns incorporate
CRSP's distribution adjustments; do not additionally apply split factors or add
legacy delisting returns to CIZ returns. Use dlyclose, not absolute dlyprc, for
entry-day trade-price valuation. Positive observed prices do not guarantee fills.

Refuse missing pages, missing stock observations, invalid prices/returns, returns
below -100%, return durations that do not link to the preceding session, and
unresolved terminal values. A delisting row with an available return and matching
previous date is included once; its remaining proceeds are held at zero return
to the scheduled exit for this diagnostic. This is a simplifying assumption,
not the interest-bearing cash convention of the final portfolio. Stop interpreting
post-delisting stock rows. A valid -100% return gives zero terminal wealth.
Each refusal is retained; never fill missing returns with zero.

## Reporting and limits

Calculate equally weighted event mean and median stock returns, same-window SPY
returns, mean/median stock-minus-SPY differences and fraction beating SPY. Report
all scheduled and calculable event counts and refusal reasons. Report broad
manager candidates, focused candidates within broad, and the broad complement.
These are overlapping research comparisons, not distinct portfolios.

Use an issuer-cluster percentile bootstrap (2,000 resamples, seed 20260924) for
the mean stock-minus-SPY difference. This captures repeated-issuer dependence,
not calendar shocks or manager dependence. Intervals are descriptive and cannot
establish alpha or causal effects. Three horizons are predeclared; do not select
the best-performing horizon after observing returns.

Report gross event results only. Costs, capacity, position caps, cash drag,
matched controls and manager verification remain gates before an executable
portfolio conclusion. Selection from incomplete return histories can bias the
diagnostic. No predictive model or NLP processing is authorized by this protocol.
Preserve source hashes, page requests, code, environment and excluded-event logs.
Protocol changes require a new version; do not retune this version using results.

Official field references: [CRSP CIZ database guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)
and [CRSP daily delisting convention mapping](https://www.crsp.org/wp-content/uploads/appendix/FlagType_MU.html).
