"""Run one restartable SEC collector while preventing macOS idle sleep.

Inputs: local SEC contact, the bounded collection script, and cached evidence.
Outputs: collector log and status; exactly one collector process at a time.
Identity: flock(collector.lock) permits at most one live collector.
Tier: 1
Run: .venv/bin/python scripts/launch_collection_overnight.py
     .venv/bin/python scripts/launch_collection_overnight.py --supervise
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "research/runs/overnight"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(**details: object) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "collection-run-status.json").write_text(
        json.dumps(details, indent=2) + "\n", encoding="utf-8"
    )


def supervise() -> None:
    """Hold the lock through the collector lifetime and persist its exit state."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "collector.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Collector already running; see collection-run-status.json") from None
        collector = [sys.executable, str(ROOT / "scripts/collect_overnight.py")]
        environment = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
        log_path = OUTPUT / "collection.log"
        with log_path.open("ab") as log:
            process = subprocess.Popen(collector, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
            write_status(status="running", started_at=timestamp(), supervisor_pid=os.getpid(),
                         collector_pid=process.pid, log_path=str(log_path.relative_to(ROOT)))
            awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
            try:
                exit_code = process.wait()
            finally:
                awake.terminate()
                awake.wait()
            write_status(status="exited", started_at=timestamp(), supervisor_pid=os.getpid(),
                         collector_pid=process.pid, exit_code=exit_code, finished_at=timestamp(),
                         log_path=str(log_path.relative_to(ROOT)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervise", action="store_true")
    args = parser.parse_args()
    if args.supervise:
        supervise()
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "collection-supervisor.log").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--supervise"], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
        )
    print(f"Collection supervisor launched: PID {process.pid}")
    print(f"Status: {OUTPUT / 'collection-run-status.json'}")


if __name__ == "__main__":
    main()
