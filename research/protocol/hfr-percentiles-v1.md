# HFR historical percentile scorecards v1

September 30, 2026. Exploratory preparation for reopened Phase 1; no selected-manager investment backtest or predictive claim.

## Scope and dates

Use all 35 supplied snapshots, 2018Q1–2026Q3. Reopen each snapshot's Fund, return and asset workbooks independently; never replace older return observations or classifications with a newer snapshot. Verify source archive/member hashes against the existing ingestion manifest. Only Event-Driven fund rows enter the panel; Activist is its overlapping subset.

Snapshot labels are delivery labels, not actual quarter ends. Effective cutoff is the last completed calendar month before the earlier of the vendor DATESTAMP and delivery-folder date. The delivery-folder date is an unverified availability proxy. Rankings are not certified point-in-time signals. Values through 2026 are descriptive rankings only; existing 13D backtests end in 2025. Repeated return histories, backfill and revisions remain separated by snapshot. Include prior histories as known in that snapshot, while flagging observations before database addition. Active historical snapshots are not a complete dead-fund database.

## Normalization and eligibility

HFR Performance/ROR is a percentage: divide by 100. Dates are Excel serial dates or explicit dates; source datemode must be honored. Keep original values, member, sheet and row. Asset figures are millions of the fund's stated asset currency; no FX conversion and no summation of related vehicles. Refuse conflicting fund-month values; collapse exact duplicates only, preserving all source locations. Returns below −100%, nonfinite values and non-month-end observations are unavailable, not zero. Preserve zero and −100% returns. Calculations require complete consecutive monthly observations to the common cutoff. Do not forward-fill returns. A reporting field explicitly identifying non-monthly frequency disqualifies rankings; where absent, contiguous month-end rows are observed monthly coverage, not independent reporting-frequency certification.

All ED funds remain in coverage and source tables. Ranking eligibility requires Fund_Status Active, Returns_Denomination USD, Reporting_Style Net of All Fees, a nonblank Firm_ID, and valid monthly data. No restriction to managers with SEC matches or strong historical 13D returns.

## Statistics

For n=12,36,60 months: cumulative return = product(1+r)−1; annualized return = product(1+r)^(12/n)−1. Volatility = sample standard deviation(r) × sqrt(12). Zero-hurdle return/volatility = mean(r)/sample standard deviation(r) × sqrt(12). This is not a cash-adjusted Sharpe ratio. Zero volatility yields unavailable ratio. Downside deviation = sqrt(mean(min(r,0)^2)) × sqrt(12), a zero minimum-acceptable-return convention. Max drawdown = min(wealth/running peak−1), including initial wealth 1; monthly observations omit intramonth drawdowns. Positive-month fraction uses r>0. No alpha claims. No pooled composite score.

Latest assets at/before cutoff, their date and age are reported. Asset growth over 12 months requires exact aligned endpoints in the same stated currency. Approximate monthly flow = A_t−A_(t−1)*(1+r_t), only for adjacent month ends and matching asset/return currencies. It is an estimate affected by valuation, reporting and fund-structure changes, not verified subscriptions/redemptions. No fee adjustments are added to net reported returns.

## Fund-to-manager rule and peer groups

Retain all products and their metrics. For each snapshot and peer group, choose one eligible product per Firm_ID using: longest uninterrupted valid history ending at cutoff; then largest positive same-currency USD assets dated no more than three months before cutoff; then ascending numeric Fund_ID (lexical fallback). Neither return magnitude nor a performance percentile enters selection. Select before requiring a particular metric horizon; do not substitute another product to rescue a missing metric. This is a representative-product proxy, not a consolidated firm return, guaranteed flagship, or verified economic-manager identity. Family_ID is retained where present, never backfilled. One representative per Firm_ID prevents duplicate products from multiplying manager weight; distinct firm IDs may still refer to related organizations.

Peer groups: all Event-Driven, Activist, and each other ED sub-strategy. A manager may have different representatives in different groups. Never add overlapping group counts. Rank fund products separately within the same groups as a supplementary view; these product ranks can overweight share classes and are not manager ranks.

For each metric/horizon/group/snapshot with at least eight eligible observations: percentile = 100*(average ascending rank−1)/(N−1), orienting higher return/ratio and lower risk/drawdown magnitude as better. Ties receive average rank. Top quartile means percentile >=75; ties and discrete samples may change its count. N<8 is unranked with an explicit reason. Primary manager selection score is 36-month annualized-return percentile; risk metrics and 12/60-month returns are separate diagnostics, not alternatives optimized on outcomes. These are calculated research percentiles, not official HFR ratings.

Persistence is descriptive: record prior eligible snapshot count and prior top-quartile share for the primary score, excluding the current snapshot. Also report representative changes. Overlapping windows and changing peer membership mean snapshot ranks are not independent trials. No forward performance test is implied.

## Deliverables and validation

Source-normalized dated return/asset panels with row provenance, fund metrics and exclusions, one-representative manager scorecards, peer denominators, persistence, coverage, searchable local HTML and CSV downloads. Publish a new dated directory. Preserve previous runs, source data and human review. No paid endpoints, labels, model fitting or investment backtest.

Tests pin compound return, volatility, drawdown, percentile ties, minimum peer size, selection without return magnitude, missing months, future dates, duplicate conflicts, zero/−100% values, historical snapshot separation and deterministic replay. Full run checks reconcile identity counts with the old manifest, assert all observation dates precede the snapshot cutoff, and independently recalculate saved metrics/ranks. Record code, protocol, input and output hashes and environment. The existing CI discovers the added tests; remote CI is not claimed without a run.

Field definitions: https://www.hfr.com/database/hfr-database/dead-funds-database-field-definitions/ (accessed September 30, 2026). Field units and names are corroborated against the supplied active-fund workbooks. Definition page does not establish complete coverage or historical availability.
