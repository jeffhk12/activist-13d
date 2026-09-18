"""Launch one bounded Terra CLI worker and save process state for morning review.

Inputs: dated task file, local Codex login; outputs: logs, PID and final status.
Identity: elapsed wall-clock runtime <= six hours plus termination grace.
Tier: 0
Run: .venv/bin/python scripts/launch_overnight.py [--supervise]
"""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/overnight"


def now():
    return datetime.now(timezone.utc).isoformat()


def supervise():
    with (OUTPUT / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("An overnight supervisor already holds the lock") from None
        command = [
            str(Path.home() / ".local/bin/codex"), "exec",
            "--model", "gpt-5.6-terra", "-c", 'model_reasoning_effort="medium"',
            "--approve-for-me",
            "-c", "sandbox_workspace_write.network_access=true",
            "--skip-git-repo-check", "--cd", str(ROOT), "--color", "never",
            "--output-last-message", str(OUTPUT / "WORKER-FINAL.md"), "-",
        ]
        env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
        # External model extraction is outside this run's scope.
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
                    "GEMINI_API_KEY", "GOOGLE_API_KEY", "MISTRAL_API_KEY"):
            env.pop(key, None)
        task = ROOT / "docs/OVERNIGHT-TASK-2026-09-09.txt"
        with task.open("rb") as source, (OUTPUT / "worker.log").open("ab") as log:
            worker = subprocess.Popen(command, stdin=source, stdout=log, stderr=log,
                                      cwd=ROOT, env=env, start_new_session=True)
            state = {"status": "running", "started_at": now(), "supervisor_pid": os.getpid(),
                     "worker_pid": worker.pid, "model": "gpt-5.6-terra", "reasoning": "medium",
                     "maximum_seconds": 21600}
            (OUTPUT / "run-status.json").write_text(json.dumps(state, indent=2) + "\n")
            awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
            try:
                code = worker.wait(timeout=21600)
                state.update(status="exited", exit_code=code)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGTERM)
                try:
                    worker.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid, signal.SIGKILL)
                    worker.wait()
                state.update(status="time_limit_reached", exit_code=worker.returncode)
            finally:
                awake.terminate()
                awake.wait()
                state["finished_at"] = now()
                (OUTPUT / "run-status.json").write_text(json.dumps(state, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervise", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.supervise:
        supervise()
        return
    # Check the same lock before launching; the supervisor also checks it.
    with (OUTPUT / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Overnight job is already running") from None
    with (OUTPUT / "supervisor.log").open("ab") as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--supervise"],
                                   cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   start_new_session=True)
    print(f"Supervisor launched: PID {process.pid}; status: {OUTPUT / 'run-status.json'}")


if __name__ == "__main__":
    main()
