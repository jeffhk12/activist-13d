# Phase 1 rebuild handoff — 24 September 2026

The first-observed-pair result is substantially weaker than the original initial-form result: +0.28 points versus Russell at six months and +7.08 at twelve months, each on 54 focused events. Neither range rules out zero. Matched results use only 19 events. Large-capital portfolios remain largely cash; small-capital six-/twelve-month portfolios cannot be fully valued because of Hill International's missing vendor return on 14 August 2018. This is exploratory development evidence, not an established edge.

Current HTML: [rebuilt report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-rebuild-report-v2/index.html).

- Final eligibility: `research/runs/phase1-baseline/20260924-universe-rebuild-v3`. v1 contains verified raw/canonical SQLite evidence; v2 is preserved diagnostic classification history. v3 fixes cover numbering/13G conversion and standard-checkbox false positives without using returns or case-specific exclusions.
- Complete inputs: `20260924-rebuilt-inputs-v2`. v1 stopped at the end-date assertion before source panel processing; no result came from it. v2 constrains the scheduler calendar to 2023-12-29, matching the original protocol.
- Outcomes: `20260924-rebuilt-analysis-v1`, including event, control membership, trade, skip, daily NAV, monthly return and cash-factor ledgers.
- QA: `20260924-rebuilt-qa-v1`; 12,107 event replays, 123 matched comparisons, 36 portfolio replays, 36,204 daily reconciliations, 53 targeted tests.
- Current report: `20260924-rebuild-report-v2`; v1 had a prose count typo for conversion overlaps (six instead of two), corrected in v2. Quantitative artifacts are unchanged.
- Protocol: `research/protocol/phase1-rebuild-v1.md`.

All run identifiers above are under `research/runs/phase1-baseline/`. Scripts: `rebuild_initial_universe.py`, `finalize_initial_universe_v3.py`, `prepare_rebuilt_development.py`, `run_rebuilt_analysis.py`, `verify_rebuilt_analysis.py`, `report_rebuilt_analysis.py`, in `scripts/data_collection/`. Use the project virtual environment and `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. Runs refuse changed frozen bytes.

Scope boundaries: all 75,631 parsed filings were mechanically audited, but only 2018–2022 development entries with follow-up through 2023 were evaluated. Retain the unchanged investor list, 207 protected issuers and clean human worksheets. No outcome-aware review becomes a human label. Do not move to fresh evaluation until valuation, source/identity limitations and evaluation exposure are addressed under frozen choices. First observed is archive-relative, not a verified first-ever campaign.
