# Phase 2 feature-readiness audit

This is a second offline preparation pass. It does not fit models or read returns.
Frozen specification: research/protocol/phase2-readiness-audit-v1.md.

Launch/resume from project root:

```
PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase2_readiness/launch.py --output research/runs/phase2-readiness/20260924-full-v1
```

Inspect launch.json for supervisor/worker status, progress.json for counts,
collection.log and supervisor.log for diagnostics. The worker saves per-filing
receipts, verifies original input/code hashes, and refuses changed inputs on resume.
Eight-hour limit; 90 seconds per filing; 20 GiB free-disk floor. A limit stop can
resume using the same command; failed receipts remain explicit and fixes need a
new version/run. Caffeinate prevents idle sleep while the supervisor lives.
Keep the Mac powered and lid open.

Outputs: field-coverage.json (by year/field, both row opportunities and filing
coverage), per-filing receipts (including exceptions), progress and morning report.
Read these as diagnostics; exact citation matches do not establish extraction
accuracy. No source files, old outputs, human packets or investor lists are changed.

Summary files only copy to OneDrive Personal / Project-Transfer / Activist-13D /
2026-09-24-Phase-2-Readiness. Remote upload is not confirmed by the worker.

Tests: project Python scripts/phase2_readiness/test_readiness.py.
Pilot: run.py --output NEW_DIRECTORY --pilot 12 (spaced across chronology).
