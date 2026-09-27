# Phase 1 historical validation — findings and continuation

24 September 2026. Status: authorized historical evaluation completed; no fresh confirmation.

## Investment finding

The later sample does not confirm a focused-activist edge. Five six-month first-observed events average -6.18 pp versus assigned Russell ETFs (mean stock -1.00%, benchmark +5.18%). The issuer-resampling 95% interval is -25.93 pp to +10.59 pp. This is negative observed evidence with substantial uncertainty, not proof that all activist investing fails.

The $100,000 primary account earns +8.73% cumulatively (+4.26% annualized) over 2 January 2024–31 December 2025, versus +9.72% cash-only. Mean cash weight is 94.22%. Five buys; one prior-liquidity skip; no terminal positions. Gain $8,730.84 = cash interest $9,014.89 + gross stock P&L $-220.13 − costs $63.92. Full-period account returns differ from six-month event averages.

[Open the full report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-historical-validation-report-v1/index.html).
Project: `/Users/jefflu/Projects/activist-13d`.

## Samples and comparisons

Frozen primary schedule: 503 events, including six focused. Fifty have missing historical identity evidence and 315 no constituent match, leaving 138 assignments; one return-validation failure leaves 137 common benchmark observations. Stock-only: 492 calculable, seven invalid/missing total returns, four unusable exits. All six focused stock histories calculate; five have Russell assignments. Coverage is selective. No missing event was replaced.

First-pair focused Russell excess: three months −7.85 pp (6 calculable / 7 scheduled), six months −6.18 pp (5/6), twelve months −29.39 pp (3/4). On the same three common companies, respective means are −10.12/−14.39/−29.39 pp. Six months remains primary. All-horizon/branch tables, SPY on identical samples and common-calendar selection keys are in the report and run.

No focused event qualifies for the frozen industry/year/Russell comparison requiring five distinct control issuers. This analysis is unavailable, not estimated as zero and not relaxed after results. Broader HFR-plus-supplement six-month excess is +16.24 pp across 14 calculable of 22 scheduled events, with an interval spanning zero. Newly recognized other HFR has eight calculable events and a positive descriptive mean. Do not tune the investor list to these winners.

## Rules preserved

First-observed pairs are archive-relative candidates, not first-ever campaigns. Preserve standalone initial forms separately; fixed six-month primary and three/twelve-month supporting horizons; $100k primary and $100m capacity accounts; existing 5% targets, 20-issuer limit, liquidity/fee/cash rules. Missing marks refuse a complete account; delisting settlement uses supported CIZ total-return flags once. Hill remains excluded under the retrospective user decision. Company B references remain unconfirmed research leads for later NLP. Human labels and all investor memberships are unchanged.

## Source and implementation record

- Decision freeze: `20260924-historical-decision-freeze-v1`, governed by `research/protocol/phase1-historical-validation-v1.md`.
- Input access/preparation: `20260924-historical-execution-inputs-v1` records code/environment and first numerical access before reading numeric fields. It verifies 522 cached date sources. Required-key and raw-source inventories are retained.
- Corrected execution inputs: `20260924-historical-execution-inputs-v2`. Restore inherited SIC rule 100 <= code < 9999: 32 specifications with 9999 and five with 0 were initially given a false industry category. Correction sets them to missing. Original panel, selection and access receipt preserved exactly.
- Current analysis: `20260924-historical-validation-v2`; original v1 retained. Seven analytical artifacts, including summaries, matched comparisons and portfolio results, are byte-identical across versions. Event records differ only in corrected industry metadata.
- Independent QA: `20260924-historical-validation-qa-v2`: 2,911 event-return replays, 36 exact portfolio replays and 18,072 cash/NAV checks. All 36 portfolio scenarios complete; zero qualifying matched estimates.
- Diagnostics: `20260924-historical-diagnostics-v1`, including independent cash/P&L identity, industry-range contract and correction parity.
- Current report: `20260924-historical-validation-report-v1`.

All run names above are below `research/runs/phase1-baseline/`. Full non-network suite: 180 passed, one deselected. Protected guard: 554 unchanged assets. Source count disagreements, monthly membership publication timing and cash revision-vintage limitations remain. This is a limited historical validation with incomplete exposure provenance. These outcomes are now examined and must never be represented as an untouched final test.

## Reproduce

From project root, use `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. Scripts under `scripts/data_collection/`:

1. `prepare_phase1_historical_execution.py` — original cached numerical source preparation and access receipt; no new network calls.
2. `repair_phase1_historical_industry.py` — separate v2 input correction, no selection or price changes.
3. `run_phase1_historical_validation_v2.py` — current event, matched and portfolio execution.
4. `verify_phase1_historical_validation.py` — independent joins, return arithmetic and accounting replay.
5. `summarize_phase1_historical_validation.py` — correction parity and investment diagnostics.
6. `report_phase1_historical_validation.py` — report and this handoff.

Frozen artifacts refuse changed bytes. New implementation changes require a new version with reason and appropriate parity checks. The copied first-access receipt in v2 is provenance from original v1, not a claim that v2 was the first access.

## Position-sizing discussion after results

User asked whether sparse opportunities explain high cash and whether concentration should rise. Five purchases at 5% target weights with roughly six-month holdings across a two-year account explain the approximately 6% average exposure. This reflects few qualifying focused signals, not absence of the broader 503-event universe. The 20-position maximum is capacity, not a requirement to hold 20 names.

Recommendation: preserve the 5% baseline and consider 10%/20% targets on exactly the same signals, dates and liquidity rules as a separately labeled exploratory sensitivity. Larger positions raise company risk and may still hit capacity limits. Purchased stocks collectively lost money before costs here; more exposure is not evidence of a better signal. No concentration sensitivity has been executed or adopted in this run. Any later execution must disclose that this sizing question was raised after seeing outcomes.

## Next work

Review the unfavorable later result without changing the fixed investor list. Phase 1 now has a completed simple-following historical baseline and a later-period test, but no demonstrated investable edge and no fresh confirmation. Industry/time robustness remains coverage-limited.

Prepare the actual prospective registration and operating collection controls using the separate prospective plan; collection has not been launched. Freeze dates and any general implementation changes before prospective signals arrive. A twelve-month collection window is still a planning recommendation, not an activated schedule. Keep append-only signal and outcome-access records and preserve quarantine rules.

Structured-data ML may next investigate whether investor/company/filing attributes improve the baseline. NLP must demonstrate additional value beyond that model. The now-examined historical period may be diagnostic/development evidence with explicit disclosure, but cannot be recycled as independent final evaluation. No ML/NLP training or human-label changes have occurred in this task.
