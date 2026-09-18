"""Launch the resumable SEC bulk collector in a detached supervised process.

Inputs: bulk collector and local SEC contact. Outputs: PID/status/log records.
Identity: one supervisor owns one collector; collector itself holds an exclusive lock.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/sec_launch.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/data-collection/sec"


def supervise() -> None:
    log_path = OUTPUT / "collection.log"
    environment = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
    with log_path.open("ab") as log:
        collector = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/data_collection/sec_bulk.py")],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
        )
        status = {"status": "running", "supervisor_pid": os.getpid(), "collector_pid": collector.pid,
                  "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "log_path": str(log_path.relative_to(ROOT))}
        (OUTPUT / "run-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
        try:
            code = collector.wait()
        finally:
            awake.terminate()
            awake.wait()
        status.update(status="exited", exit_code=code, finished_at_utc=datetime.now(timezone.utc).isoformat())
        (OUTPUT / "run-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervise", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.supervise:
        supervise()
        return
    with (OUTPUT / "supervisor.log").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--supervise"], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
        )
    print(f"SEC supervisor launched: PID {process.pid}")


if __name__ == "__main__":
    main()
