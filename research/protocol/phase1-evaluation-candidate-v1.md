# Phase 1 evaluation candidate v1

24 September 2026. **Draft candidate specification, NOT authorization to open outcomes.**
This version is preserved; integration changes require v2. The question is whether
buying after an identified investor's initial 13D improves executable returns.
The prior evidence is outcome-aware development. No later sample is certified fresh.

## Estimands and fixed comparisons

Six months means 126 XNYS sessions counting entry as session one; 63 and 252 are
supporting. Primary event estimand: equally weighted focused first-observed-pair
stock total return minus assigned historical Russell segment ETF total return over
126 sessions. This gross diagnostic is distinct from investable performance.
Show standalone-initial forms as the prespecified alternative branch at every
horizon, not whichever branch performs best. First observed is relative to the
2013-onward archive; no first-ever campaign claim.

Report focused candidates, broader identified managers, newly included other HFR
managers and other/unresolved filings using the frozen overlapping/disjoint cohort
rules. Unknown manager identity does not establish passivity. Freeze exact
accession unions from hfr-all-managers/20260924-v1 plus the seven supplemental
groups; validate every join. For prospective events extend the same identity
rules/list with dated evidence, never change membership based on returns.

Executable primary strategy: focused first-observed-pair, 126 sessions, $100,000
starting capital, base costs and lagged cash yield. $100m is the prespecified
capacity comparison, not an alternative chosen by profitability. Show both
branches, all three horizons, base/zero friction, lagged/zero cash yield using
the existing development scenario definitions. Report inception-to-fixed-terminal
NAV return, annualized return, drawdown, costs, turnover, invested fraction,
cash contribution, entry skips and residual holdings. Total account return minus
cash-only return is incremental invested-account value, not risk-adjusted alpha.
SPY/IWV buy-and-hold are context with different equity exposures.

High cash may reflect few eligible opportunities, small liquidity-capped orders,
minimum-ticket refusals and the 5% position target. Attribute these separately
from stock selection. Keep capital, capacity and costs fixed even if deployment
is low. Never scale returns by invested fraction and call the result account alpha.

## Signals, entry, costs, cash and marks

Use v3 source-audited eligibility plus any separately versioned, integrated
source-grounded fixes. Freeze the basic corporate-common/security/source screen;
207 human-protected issuers remain excluded. Second XNYS session strictly after
acceptance date is entry, irrespective of time within acceptance day. A usable
entry opening trade is the fill convention, not guaranteed auction execution.

Run the existing deterministic issuer nonoverlap scheduler independently for each
branch/horizon, merging same-security simultaneous filings, suppressing conflicting
securities and entries through scheduled exit inclusive. No replacement after a
future data failure. No future-return availability, benchmark-return availability,
or ex-post survival screen may affect which signal was selected.

Inherit phase1-rebuild-v1.md accounting: target 5% of prior-close NAV, at most 20
issuers, no leverage/additions/clock resets; accession priority; entry order at
most 1% of prior 20-session mean close-dollar volume; minimum order 0.1% of initial
capital; no multi-day entry build. Exit starts at scheduled close, capped at 1%
of strictly prior trailing ADV each day; residuals stay held and marked. One-way
friction = 10 bps + 50 bps × sqrt(order/ADV), plus $1 minimum commission. Preserve
the existing implementation's exact fee application and pin it before production.
These are cost assumptions, not observed spreads or measured impact.

Reinvest distributions within total-return units; apply supported delisting
proceeds once. Lag FRED DTB3 by at least two calendar days; ten-day maximum stale
carry; bill-price proxy P=1−d×91/360; daily cash accrual=(1/P)^(1/91)−1 for elapsed
calendar days. No taxes or management fees. NAV=cash+sum(position values).

Missing entry/liquidity information produces a contemporaneous documented skip.
Missing held marks/returns stops a complete-account claim under the current rule.
Agent A's independent source-backed valuation investigation is a dependency; only
an integrated, newly frozen general rule may revise this. Bounds/hypothetical
marks are separately labeled scenarios. Do not silently carry, bridge, zero or
discard a held security. Fix a terminal date and disclose terminal residuals;
never extend the window opportunistically until positions sell.

## Historical candidate cohort and exposure boundary

The selection scaffold uses entry dates from 2024-01-01 and fully elapsed sessions
through 2026-09-23. It applies the metadata-only basic screen, the 207 protected
issuer exclusions, issuer identities from every prior development selection,
the ten preview issuer identities and preview security IDs, plus the documented
WRDS smoke-test security. It retains issuer quarantine across dates. The metadata
manifest is a *candidate* list, not a production sample freeze.

Calendar maturity is assessed without opening future stock/benchmark returns.
Horizon-specific maturity determines each schedule; comparisons across horizons
must additionally show the common 252-session-mature sample, chosen by calendar
only. Do not treat differing sample compositions as holding-period effects.
Benchmark snapshots must precede acceptance; use historically supported Russell
assignment and report SPY on the identical sample. Missing benchmark sources or
no constituent match remain explicit denominator losses, not negative outcomes.
Industry/year/size comparisons follow the existing minimum-five-distinct-control-
issuer rule and remain retrospective descriptive evidence.

Bounded repository audit can find known exposures, but no historical access log
proves that all remaining outcomes were unseen. Scratch probes printed unspecified
raw market-data rows, and archived conversations/other machines are not fully
auditable here. Therefore this cohort cannot currently deliver fresh confirmation.
If integrated gates other than exposure are satisfied, it may support a separately
frozen **historical temporal validation with incomplete exposure provenance**.
Its results must not be called untouched, held-out confirmation, or independent
proof. This is a future option; this readiness task does not execute it.

For genuinely fresh confirmation, freeze the final protocol, code, investor list,
inputs policy and exposure-control procedure first. Prospectively register filings
accepted strictly after that recorded freeze timestamp (first eligible acceptance
day is the following full exchange day). Keep the same protected issuers and
issuer-reuse quarantine; record an append-only outcome access register. Specify
an entry collection end date before the first outcome is opened. Mature 126-session
follow-up cannot exist at inception; even 63-session support requires waiting.
The candidate v1 draft is not that future freeze. Do not backdate it.

## Inference and interpretation

Report n scheduled, n attempted, n calculable, distinct issuers, missing marks,
benchmark coverage, focused coverage and every sequential refusal. Report
issuer-cluster percentile intervals using the existing 2,000 resamples and seed
20260924, with same-issuer events retained inside clusters. Calendar/manager
correlation remains; an issuer bootstrap is not a complete solution to common
shocks. A small sample or a short regime cannot establish a repeatable edge.

A positive primary gross mean alone does not pass an investment test. Favorable
confirmation requires exposure and data gates first, positive primary relative
mean with a 95% interval above zero, and complete primary account accounting that
adds value over cash after the fixed trading costs. Supporting branches/horizons
are reported without cherry-picking or redefined significance. This is a narrow
prespecified evidentiary threshold, not proof of alpha or a recommendation to
allocate. A nonpositive primary estimate is negative evidence for this rule;
a positive estimate with an interval crossing zero is inconclusive. Missing
accounting, selective unmatched coverage or insufficient observations leaves the
relevant estimand unevaluated/inconclusive, never a successful test by omission.
No optional stopping when an attractive result appears; no post-result adjustment
of membership, size, dates, costs, holding periods or successful-data subset.

## Fail-closed gate and production manifest

The executable readiness function requires explicit true values for exposure
provenance, protocol/code freeze, identity/eligibility, valuation, benchmark inputs,
price/cash inputs, protected-issuer integrity, calendar maturity and sample freeze.
Missing/unknown values fail. The current gates.json is NOT READY. Gate receipts
must cite immutable files and SHA-256 values; booleans alone are not evidence.

Before opening outcomes, root must integrate A/B, freeze a new protocol, finalize
entry/end dates and sample selection, verify protected-issuer and investor hashes,
and snapshot exact source inventories, code/environment versions and tests. Supply
pre-event benchmark/liquidity/cash input receipts without selection on returns;
freeze outcome-access authorization separately. Preserve all original runs.
Missing future prices cannot be solved by screening out affected securities.
No Phase 2/3 training or human semantic labels are created by this work.
