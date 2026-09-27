# Phase 2 offline factual preparation

Run from project root with project Python and PYTHONNOUSERSITE=1,
PYTHONIOENCODING=utf-8. Frozen scope: research/protocol/phase2-factual-staging-v1.md.

Start or resume (same command):

```
PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase2_overnight/launch.py --output research/runs/phase2-overnight/20260924-full-v1
```

The supervisor detaches, holds a global Phase 2 lock, prevents idle sleep, and
records process IDs in launch.json. Keep the Mac powered with its lid open.
Worker progress is in progress.json and index.html; logs in collection.log and
supervisor.log. Eight-hour processing limit; checkpoint after each filing.
A resource-limited job resumes with the same code/input hashes. Failures are explicit
receipts, not silently retried. Fixes require a new version/run; do not modify frozen
code or discard failure records. Completed artifact hashes are checked on resume.

Summary files only are copied to the named OneDrive Personal Project-Transfer
Phase 2 folder every 25 filings and at completion. Cloud upload is not confirmed
by the runner. No raw data or filing-level features are copied to OneDrive.

Run tests with project Python scripts/phase2_overnight/test_staging.py.
Pilot flag: run.py --output NEW_PILOT --pilot 12. Pilots evenly span dates without
looking at outcomes. No paid model APIs or network connections are used.
