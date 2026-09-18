"""Record a user-requested pause after collection processes have exited.

Inputs: released worker locks, current progress and frozen cache pairs.
Outputs: dated pause checkpoint and paused progress markers; no raw mutations.
Identity: every cached payload has a corresponding provenance sidecar.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/record_pause.py
"""

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/data-collection"
stamp = datetime.now(timezone.utc).isoformat()
locks = []
for relative in ("sec/collector.lock", "wrds/worker.lock"):
    handle = (OUT / relative).open("a+")
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    locks.append(handle)
problems = []
for payload in (ROOT / "data/raw/edgar/bulk-v1/filings").glob("*/submission.txt"):
    if not payload.with_suffix(".txt.meta.json").is_file():
        problems.append(str(payload.relative_to(ROOT)))
for payload in (ROOT / "data/raw/wrds/bulk-v1").glob("*/*.json.gz"):
    if not payload.with_suffix(".meta.json").is_file():
        problems.append(str(payload.relative_to(ROOT)))
partials = [str(p.relative_to(ROOT)) for p in (ROOT / "data/raw/edgar/bulk-v1").rglob("*.part")]
checkpoint = {"paused_at_utc": stamp, "reason": "User requested pausing downloads",
              "incomplete_cache_pairs": problems, "partial_files": partials, "progress_before_pause": {}}
for job in ("sec", "wrds"):
    path = OUT / job / "progress.json"
    state = json.loads(path.read_text())
    checkpoint["progress_before_pause"][job] = state.copy()
    state.update(status="paused_by_user", paused_at_utc=stamp,
                 pause_note="Worker exited. Existing counters are checkpoints; verified cache replay resumes without discarding completed downloads.")
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, indent=2) + "\n")
    temp.replace(path)
path = OUT / ("pause-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
path.write_text(json.dumps(checkpoint, indent=2) + "\n")
for handle in locks:
    handle.close()
print(json.dumps({"checkpoint": str(path), "incomplete_cache_pairs": problems, "partial_files": partials}))
