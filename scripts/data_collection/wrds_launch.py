"""Launch the authorized WRDS raw-data collector detached with durable logs.

Inputs: local collector and existing frozen cache. Outputs: PID/launch record.
Identity: one exclusive collector lock permits at most one active writer.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/wrds_launch.py
"""

import fcntl
import os
import subprocess
import sys
from pathlib import Path

from wrds_collect import CACHE, OUT, ROOT, utc, write_json

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "worker.lock").open("a+") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("WRDS collector is already running") from None
for path in CACHE.glob("*/*.json.gz"):
    if not path.with_suffix(".meta.json").is_file():
        raise SystemExit(f"Incomplete preserved cache pair; inspect {path}")
for path in CACHE.glob("*/*.json.meta.json"):
    if not path.with_name(path.name.removesuffix(".meta.json") + ".gz").is_file():
        raise SystemExit(f"Incomplete preserved cache pair; inspect {path}")
environment = os.environ.copy()
environment.update(PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY"):
    environment[key] = ""
with (OUT / "collection.log").open("ab") as log:
    child = subprocess.Popen([sys.executable, str(Path(__file__).with_name("wrds_collect.py")), "collect", "--online"],
                             cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=log, start_new_session=True)
write_json(OUT / "launch.json", {"pid": child.pid, "launched_at": utc(), "log": str(OUT / "collection.log"),
                                  "command": "scripts/data_collection/wrds_collect.py collect --online"})
print(f"WRDS collector PID {child.pid}; log {OUT / 'collection.log'}")
