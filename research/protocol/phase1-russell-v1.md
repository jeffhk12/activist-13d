# Phase 1: historical Russell segment ETF comparison, v1

Frozen 24 September 2026 before calculating new benchmark returns. Development
refinement after inspecting SPY results; not a fresh confirmation test.

Reuse expanded-HFR-v1 event membership and development-v4 schedules/outcomes.
Six months (126 sessions) primary; 63 and 252 supporting. Keep the original
protected companies, entry dates and outcome cutoff. No rescheduling on failure.

Use FTSE Russell `ftse.idx_holdings_us` monthly constituent records via WRDS.
Select the last exchange session of the calendar month strictly preceding the
earliest merged disclosure's acceptance date. This is lagged monthly membership,
not verified daily membership at disclosure. The snapshot must precede disclosure
and be no more than 35 calendar days old. No subsequent snapshot backfill.
Historical publication timestamps are unverified; retrospective vendor data can
contain revisions. This is an explicit residual availability limitation.

At that snapshot date, map the event's CRSP PERMNO to its historical daily CUSIP8,
then exact-match the first eight characters of the Russell CUSIP9. Require one
record, valid identifier lengths, and consistent membership flags/positive
weights. Do not use ticker, name, present-day identifiers or company-cap guesses.
Positive Russell 1000 and 2000 membership together is a refusal. Midcap requires
Russell 1000. Each selected segment's membership flag must be Y and weight >0.

Assignment precedence: Midcap -> IWR; other Russell 1000 -> IWB; Russell 2000 ->
IWM. Thus larger companies outside Midcap use the broad Russell 1000 reference,
not Top 200. Freeze the selected ETF for the entire event. Russell 3000/IWV is
additional broad-market context, never a microcap bucket. No forced assignment
for missing/nonmember stocks, foreign listings or companies below index size
coverage. No rank approximation is blended into these results.

Verify historical ETF identifiers and use CRSP daily total returns with the same
opening entry and closing exit convention as the stock. Apply the existing
return estimator and refusal rules unchanged. ETF expenses/tracking differences
are embedded; these are ETF-relative returns, not exact index returns or alpha.
No stock return re-estimation or changes to the original event weights.

Require stock, SPY, assigned ETF and IWV calculable for the common comparison.
Show full-sample SPY separately from common-sample SPY so selection effects are
visible. Report sequential assignment/return exclusions and original-event SPY
performance of excluded observations. Report disjoint cohorts plus overlapping
expanded/HFR-only totals, benchmark composition, means/medians/win rates and the
existing issuer-bootstrap interval (2,000 draws, seed 20260924). The interval
does not capture shared market shocks or manager dependence.

Preserve hashes and raw monthly pages, date/unique-key checks and vendor reported
count discrepancies. A nonmatch means unavailable in the downloaded snapshot,
not proven nonmembership. Monthly rows contain other vendor fields, but only
identifiers and membership flags/weights may feed assignment; vendor constituent
return fields are not used. Do not expose protected-company or later outcomes.

Replay saved inputs offline. Verify assignment boundaries/refusals, estimator
pins, matched-sample identity, unchanged stock/SPY returns and all sample counts.
