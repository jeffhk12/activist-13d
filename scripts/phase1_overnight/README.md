# Offline Phase 1 overnight processing

The authorized run audits and parses the frozen SEC universe, audits WRDS coverage, makes mechanical candidate groups and historical CUSIP matches, and renders a descriptive EDA report. It uses local Python, no model APIs and no network requests. Raw evidence and existing human-review packets are not modified.

Run from the project root:

```sh
PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/launch.py --output research/runs/phase1-overnight/full-20260915
```

The launcher records the worker and supervisor PIDs in `launch.json`; `progress.json` records stages and counts. `collection.log` contains progress and failures. The process continues after the interactive turn ends. `caffeinate` prevents idle system sleep while the supervisor runs; keep the laptop plugged in and the lid open.

To pause, send SIGTERM to the recorded **worker PID**. SEC stops after its current filing (parser subprocess timeout 90 seconds); WRDS checks for stop between files. Linking/report rendering finish their current stage. Resume using the same command and directory. Code/environment/manifest provenance must match; otherwise use a new directory. Parsed source hashes are reverified on resume. Explicit parser failures are retained for review, not silently retried with changed code.

Outputs:

- `sec.sqlite`: compact source-backed parser candidates, audits and explicit failures; full documents remain in raw files.
- `index-audit.json`: quarterly index consistency checks.
- `wrds/`: resumable source and coverage audit. Empty weekdays are not automatically missing trading days.
- `links/candidates.jsonl`, `links/groups.jsonl`: candidate groups, historical matches, ambiguity and unmatched records.
- `eda/REPORT.html`: readable report with embedded charts.
- `eda/REPORT.md`, `eda/calculations.json`: report text and supporting calculations/provenance.
- `eda/review_queue.jsonl`: parser/source failures followed by overlapping mechanical evidence flags.
- `provenance.json`, `code/`: input hashes and source/environment snapshot.

Resource guards: 20 GiB minimum free space; one SEC source per parser subprocess; 20 MiB input cap; 90-second parser timeout; 32 MiB regular-file stdout/stderr cap. Large/problematic filings go to the explicit failure queue. No document text is duplicated beyond candidate Item 4 text and metadata.

The first evenly spaced 50-filing pilot parsed 50/50 in 9.66 seconds and produced a 258,048-byte SQLite file. This suggests roughly four hours for SEC parsing, before WRDS audit and reporting, but is not a guaranteed completion time. The pilot is not a random or validated research sample. All full-run findings must be read from the final report.

Limits: candidate groups are not verified campaigns; party changes can split chains and repeated campaigns can share party sets. CUSIP matches are historical candidate security links, not corporate-eligibility decisions. The incomplete reference detector does not certify complete evidence. WRDS vendor completeness remains independently unverified. HFR return units/methodology must be documented before performance comparisons. No eligibility/intent labels, trading signals, holdout selection, or backtests are generated.
