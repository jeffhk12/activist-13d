# Phase 1 eligibility, matched comparisons and portfolio rebuild v1

Frozen 24 September 2026 before rebuilt results. Outcome-aware development
revision; no investor-list tuning, human-reference labels, NLP categories or fresh
outcome evaluation. All 75,631 existing parsed filings are audited mechanically;
return analysis remains March 2018–December 2022 entries, follow-up through 2023.
Preserve earlier runs and protected issuer exclusions.

## Eligibility and history

Verify original raw bytes, hashes, source URLs and header accession/date. Extract
one primary Schedule 13D document using lxml and whitespace-normalize into a new,
explicitly versioned canonical representation. Save hashes and exact evidence
spans. Any header/document/index amendment form or explicit positive cover
amendment number excludes an initial signal. Conflicting initial metadata is
resolved conservatively to amendment when affirmative amendment evidence exists;
missing, unreadable or ambiguous evidence is refused. XML amendment numbers and
self-referential numbered amendments are also checked. Absence of a detected
amendment is not proof of first campaign. Do not infer intent.

Keep all reporting CIKs and issuer CIKs as historical anchors. Retain the existing
HFR Firm_ID matches and seven supplemental groups unchanged. Process chronologically,
using only prior filings for each event. Any earlier same manager-ID/issuer or
reporting-CIK/issuer occurrence (including amendments or failed body audits) makes
that pair previously observed. Retain actor-level proxy histories for unmatched
managers; do not claim they are verified economic entities. Group changes do not
reset history when any reporter/manager overlap exists. Affirmative textual prior
Schedule 13D/group-dissolution references flag unresolved prior history. First
observed means first in the supplied 2013-onward archive, never first ever.
Same-acceptance batches share pre-batch history. No future CIK back-propagation.

Rebuild two branches from the original basic data/security screen: (1) eligible
standalone initial forms; (2) no previously observed current manager/reporting-party
pair and no detected prior-history reference. Use the original common issuer
nonoverlap scheduler afresh after exclusions for 63/126/252 sessions. Report all
exclusions, newly released entries, unresolved identities and left censoring.
Reclassified metadata amendments are not automatically promoted to initials.

## Benchmarks and controls

Use the same gross return estimator, historical monthly Russell membership and
ETF proxies. New scheduled entries obtain historical inputs from cached raw pages;
missing snapshots are acquired only for the required pre-disclosure dates. Never
choose a benchmark from subsequent returns. SPY remains market context.

Industry/time comparison: for each focused event, controls are non-focused eligible
initial events in the same branch and horizon, same pre-disclosure two-digit SIC,
same assigned Russell ETF and entry calendar year. Exclude the focal issuer;
require at least five distinct control issuers. Average each control issuer's
excess first, then equally weight issuers. Difference = focal stock-minus-Russell
excess minus that control mean. Report coverage and focused excess on exactly the
matched sample; show missing/undersized groups. This is a coarse retrospective
comparison, not a tradable signal, causal estimator or independently verified
non-activist control. No optimization of matching dimensions or thresholds.

## Portfolio accounting conventions

Core development portfolio: focused candidate signals in each eligibility branch,
126 sessions primary, 63/252 supporting; identical signals at $100k and $100m.
Buy at the delayed entry open; target 5% of prior-close NAV per new issuer, maximum
20 open issuers, no leverage/additions/exit-clock resets, deterministic accession
priority for simultaneous entries. Opening-price fills are a modeling convention,
not certified opening-auction capacity. Orders capped at 1% of prior 20-session
mean close-price dollar volume, all inputs strictly before entry; minimum order
0.1% of initial capital. Residual cash stays cash. Missing pre-entry liquidity
inputs cause a documented contemporaneous skip, not an outcome-based exclusion.

Base one-way friction = 10 bps + 50 bps * sqrt(order/prior ADV), plus $1 minimum
commission per execution. These are explicit assumptions, not measured spreads or
impact. Show zero-cost sensitivity; do not tune to results. Exit from the scheduled
close onward, capped at 1% of trailing ADV per day; retain and mark residual until
sold. No multi-day entry accumulation. If a usable delisting occurs, receive its
value once in cash. Reinvest distributions within total-return positions (synthetic
fractional total-return units); no double-counted dividends or splits.

Cash uses the cached FRED DTB3 discount yield, with at least two calendar days of
observation lag and a maximum ten-day stale carry. Approximate 91-day bill price
P=1-d*91/360; daily accrual=(1/P)^(1/91)-1, compounded for elapsed calendar days.
This is a cash accrual proxy, not actual bill trading or verified historical release
vintages. Include a zero-interest sensitivity. No taxes or management fees.

At every close NAV=cash+sum(position values); record orders, costs, cash, exposure,
turnover, drawdown, daily/monthly returns and terminal positions. No screening out
trades for future return availability. Missing held-position returns explicitly
stop/refuse a complete portfolio result; disclose affected scenarios and available
prefix rather than fabricating marks. Do not declare a partial run a full-period
backtest. End date 2023-12-29; residual unsold positions are reported marked, not
silently liquidated beyond the boundary. Buy-and-hold SPY/IWV and cash are context,
not risk-matched alpha; event Russell comparisons stay distinct.

Freeze code/input hashes, seeds and environment. Test body/header conflicts,
footnote false positives, historical grouping without future leakage, matched
sample arithmetic, cash conservation, duplicate-issuer refusal, liquidity/cost
limits, delisting, missing-data refusal and deterministic replay. Do not begin
fresh-data evaluation until eligibility/data limitations are resolved.
