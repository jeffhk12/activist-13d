"""Tier: 0. Point mutable project navigation at the verified rebuild report.
Inputs: current home/plan; outputs: navigation plus dated handoff.
Identity: preserve earlier findings as historical; leave human packets unchanged.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/publish_rebuilt_navigation.py
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'START-HERE.html';s=p.read_text()
section='''<section><h2>Current: rebuilt initial events, matched peers and portfolio accounting</h2><p>First observed manager–issuer pairs average +0.28 percentage points versus Russell at six months and +7.08 at twelve months (54 focused events each). Both uncertainty ranges include zero. Industry/year matching gives positive six- and twelve-month differences, but only 19 focused events qualify.</p><p>The $100k six-/twelve-month portfolios stop on an unresolved held-stock return. The $100m runs complete but remain mostly cash under the fixed liquidity limits. These development results do not establish an investable edge. Investor membership and human labels are unchanged; fresh evaluation has not started.</p><a class="button" href="research/runs/phase1-baseline/20260924-rebuild-report-v2/index.html">Open the rebuilt results</a><a href="research/docs/PHASE1-REBUILT-RESULTS-20260924-v2.md">Plain-English findings and next steps</a></section>
<p class="secondary">Earlier reports below are preserved research history. Use the rebuilt results above for the current Phase 1 baseline.</p>
'''
if '20260924-rebuild-report-v2' not in s:s=s.replace('<section>',section+'<section>',1)
s=s.replace('Latest audit: initial-disclosure eligibility needs correction','Prior audit: why initial-disclosure eligibility was rebuilt')
p.write_text(s)
p=ROOT/'research/docs/PROJECT-PLAN.md';s=p.read_text()
new='''**Current rebuilt baseline:** [eligibility, matched comparisons and portfolio results](PHASE1-REBUILT-RESULTS-20260924-v2.md) now supersede the provisional estimates below. The full parsed universe has 17,420 standalone initial-form candidates; 16,278 are first observed pairs within the archive. First-pair focused excess is +0.28/+7.08 points at six/twelve months (54 events each), with both uncertainty ranges including zero. Industry/year/size matching has only 19 qualifying focal events. Portfolio accounting completed 24 of 36 scenarios; 12 stop because Hill International lacks a held-position return on 14 August 2018. Large-capital cases hold very high cash. No investor-list tuning, human-label changes or fresh-data evaluation occurred.

**Next gate:** resolve held-security valuation from source evidence under a new frozen rule; validate remaining form/entity ambiguity and benchmark coverage; then freeze all research choices and establish an exposure-clean fresh evaluation sample. Keep six months primary, twelve supporting. Outcome-aware reviews remain separate from human reference labels.

### Preserved earlier development findings

'''
marker='## Current direction — September 24, 2026\n\n'
if 'Current rebuilt baseline' not in s:s=s.replace(marker,marker+new)
p.write_text(s)
p=ROOT/'research/docs/PHASE1-REBUILD-HANDOFF-20260924.md'
if not p.exists():p.write_text('''# Phase 1 rebuild handoff — 24 September 2026

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
''')
