# Phase 1 long-horizon results and handoff

24 September 2026. Revised exploratory analysis executed; primary longer-horizon portfolio incomplete.

## Investment finding

Expanded 2018–2025 history, with 24 months primary and 12/18/36 supporting. Focused first-pair cumulative Russell excess: −0.08 pp at 12 months (65 calculable), −1.81 pp at 18 (60), +8.66 pp at 24 (56), +20.83 pp at 36 (50). Two-year mean stock return +27.82%, assigned ETF +19.15%. Its median excess is −14.91 pp, 41.1% beat the benchmark, and the 95% interval is −17.34 to +40.43 pp. Positive longer-horizon averages do not establish a robust edge.

[Open the revised report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-long-horizon-report-v1/index.html).
Project: `/Users/jefflu/Projects/activist-13d`.

## Scope and evidence

Two-year schedule: 2,107 first-pair events, including 67 focused. Overall 712 benchmark assignments → 694 calculable; focused 58 assignments → 56 calculable. These are events, not manager counts. Fifty focused events are calculable across all four horizons; their cumulative excess means are +7.13/+8.97/+18.24/+20.83 pp. That common-successful-data table is only a coverage sensitivity and never changes the signal selection. Calendar-common schedules and horizon-specific denominators are preserved separately.

At two years, mean individual annualized stock/ETF returns are +4.95%/+8.38%, a −3.43 pp difference. Annualize each event first then average; this is not annualizing the mean or reporting an account CAGR. The sign difference from cumulative means reflects unequal outcomes and the nonlinear transformation. Keep this distinction explicit.

Industry/year/Russell controls yield only 17 two-year focal matches: focused excess −3.07 pp, controls +5.01 pp, difference −8.08 pp, interval −29.87 to +14.03 pp. Do not relax the five-distinct-control rule. Broader HFR-plus-supplement mean excess +26.09 pp across 116/170 observations has a negative median. No winner-driven list revision.

## Account limitation — next dependency

30/48 scenarios complete. All $100k 18/24/36-month variants in both branches stop on 2019-07-18 at Aratana Therapeutics, issuer 0001509190 / PERMNO 13966. Cached row: dlydelflg Y, dlyprevdt 2019-07-17, dlyret −0.011463, dlyretmissflg MV, dlyretdurflg DD, no close/open/volume. The inherited validator requires NA for the return-missing flag and refuses the row despite its numerical return. The code does not prove actual proceeds from that row.

Do not remove Aratana, accept its flagged value, bridge to another ticker, assume cash/stock consideration, or use zero proceeds without source-backed general treatment. Next investigate source definitions and dated corporate-action/settlement evidence; any accounting-policy correction gets a new protocol/code version and parity checks. No other issuer exclusion is authorized by the existing Hill decision. Partial accounts stop after 335 sessions on 2019-07-17 with 17 positions; their 42.14% average cash is a partial prefix and must not be compared with full-period averages.

Completed $100k first-pair 12-month account: +57.41% cumulative, +5.99% annualized, 55.41% average cash, −35.15% max drawdown; 75 buys. Full account window 2018-03-19–2025-12-31. Cash-only +22.87%, SPY +181.73%, IWV +166.93% over that window; differing exposures prevent alpha claims. Larger-capital completed accounts cannot replace the missing primary $100k result.

## Preserve research decisions

This revision is outcome-aware exploratory development requested by the user after shorter-horizon results. It intentionally includes previously examined issuers: 1,902 of 2,107 primary events have an issuer previously selected in the recorded runs. No claim of fresh confirmation. Keep all 207 human-protected issuers excluded, conservative body/header/history eligibility, Company B references as leads, Hill exclusion, fixed investor list and original 5% targets. First observed is archive-relative. Longer horizons and a broader sample changed together; use the common-event diagnostics and avoid attributing all changes to holding duration.

Rebuild issuer nonoverlap schedules at 252/378/504/756 exchange sessions. Entry still counts as session one. Same deterministic entry, liquidity, costs, cash, missing-data and terminal-position rules. No NLP/ML training, new semantic labels, actual trades, prospective launch or concentration sensitivity.

## Artifacts and reproduction

All run folders below are under `research/runs/phase1-baseline/`:

- `20260924-long-horizon-inputs-v1`: frozen selections, exposure tags, environment/code/access record, panel, historical Russell assignments and source inventories. All 1,990 required daily source files exist; row/return validity remains separate. Raw new constituent responses, where required, use `data/raw/wrds/long-horizon-20260924-v1/`; earlier raw caches are preserved.
- `20260924-long-horizon-analysis-v1`: event/group summaries, outcomes/refusals, matched comparisons, common-calendar samples, 48 portfolio ledgers, monthly returns and broad-market context.
- `20260924-long-horizon-qa-v1`: independent schedule reconstruction, 17,990 event-return replays, 160 matched-control arithmetic checks, 48 portfolio replays and 64,800 daily cash/NAV checks including partial prefixes.
- `20260924-long-horizon-diagnostics-v1`: annualization hand pins, all-horizon calculable subset, accounting attribution, ETF identity checks over 1,959 sessions. Individual annualized event statistics are not portfolio CAGR.
- `20260924-long-horizon-report-v1`: user-facing results and provenance.

Protocol: `research/protocol/phase1-long-horizon-v1.md`. Scripts: `prepare_phase1_long_horizon.py`, `run_phase1_long_horizon.py`, `verify_phase1_long_horizon.py`, `diagnose_phase1_long_horizon.py`, `report_phase1_long_horizon.py` under `scripts/data_collection/`. Run using project `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. All input and output hashes must match; use a separate version for changes. Cached panel enables offline analysis replay. Full non-network suite: 180 passed, one deselected; protected guard checks 554 unchanged assets.

Vendor row-count disagreements, sparse benchmark matching, monthly membership timing and revised cash vintages remain limitations. No file-presence check certifies complete market coverage. Preserve earlier development, later historical and long-horizon outputs separately. The revised results support further research into the long-term thesis but do not establish an investable edge or justify changing the list to winners.
