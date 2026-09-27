"""Launch and supervise the offline Phase 2 job with idle-sleep prevention.

Inputs: explicit isolated output directory. Outputs: durable log and process IDs.
Identity: one global supervisor lock prevents concurrent full overnight jobs.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase2_overnight/launch.py --output research/runs/phase2-overnight/RUN
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supervise", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "MOONSHOT_API_KEY",
        "KIMI_API_KEY",
    ):
        env[key] = ""
    if not args.supervise:
        with (output / "supervisor.log").open("ab") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--supervise",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        print("Supervisor PID", child.pid, "output", output)
        return
    (ROOT / "research/runs/phase2-overnight").mkdir(parents=True, exist_ok=True)
    with (ROOT / "research/runs/phase2-overnight/supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (output / "collection.log").open("ab") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).with_name("run.py")),
                    "--output",
                    str(output),
                    "--sync",
                ],
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
            )
            awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
            status = {
                "status": "running",
                "supervisor_pid": os.getpid(),
                "worker_pid": child.pid,
                "caffeinate_pid": awake.pid,
            }
            (output / "launch.json").write_text(json.dumps(status, indent=2))
            try:
                code = child.wait()
            finally:
                awake.terminate()
                awake.wait()
            status.update(status="exited", exit_code=code)
            (output / "launch.json").write_text(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
