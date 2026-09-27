"""Tier: 2. Verify valuation inputs against frozen receipts, test and replay offline.
Inputs: valuation-resolution-v1 and original provenance; outputs: closeout receipt.
Identity: SHA256(actual input)=SHA256(frozen input); exact repeated output equality.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_valuation_verify.py
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-valuation-resolution-v2"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    checks = 0
    for run in ["20260924-rebuilt-inputs-v2", "20260924-rebuilt-analysis-v1"]:
        path = BASE / run
        provenance = json.loads((path / "provenance.json").read_text())
        for name, sha in provenance["outputs"].items():
            assert digest(path / name) == sha, name
            checks += 1
    env = dict(os.environ, PYTHONPATH="src", PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8")
    commands = [[sys.executable, "-m", "pytest", "-q", "tests/test_phase1_valuation_audit.py", "tests/test_portfolio_accounting.py"],
                [sys.executable, "scripts/data_collection/phase1_valuation_resolution.py"],
                [sys.executable, "-m", "ruff", "check", "src/activist13d/phase1_valuation_audit.py",
                 "tests/test_phase1_valuation_audit.py", "scripts/data_collection/phase1_valuation_resolution.py",
                 "scripts/data_collection/phase1_valuation_verify.py"]]
    results = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        results.append(dict(command=command, returncode=result.returncode, stdout=result.stdout))
    v1 = BASE / "20260924-valuation-resolution-v1"
    original = json.loads((v1 / "provenance.json").read_text())
    snapshot = OUT / "source-v1"
    replay_command = [sys.executable, str(snapshot / "scripts/data_collection/phase1_valuation_resolution.py")]
    replay = subprocess.run(replay_command, cwd=ROOT,
                            env=dict(env, PYTHONPATH=str(snapshot / "src")),
                            check=True, capture_output=True, text=True)
    results.append(dict(command=replay_command, returncode=replay.returncode, stdout=replay.stdout))
    isolated_v1 = snapshot / "research/runs/phase1-baseline/20260924-valuation-resolution-v1"
    assert (isolated_v1 / "provenance.json").read_bytes() == (v1 / "provenance.json").read_bytes()
    for name, sha in original["inputs"].items():
        candidate = snapshot / name
        assert digest(candidate if candidate.exists() else ROOT / name) == sha, name
    for name, sha in original["outputs"].items():
        assert digest(v1 / name) == sha, name
        assert (OUT / name).read_bytes() == (v1 / name).read_bytes(), name
        assert (isolated_v1 / name).read_bytes() == (v1 / name).read_bytes(), name
    supplemental = ROOT / "data/raw/public/phase1-valuation-20260924-v1/supplemental/schwab-endpoint-lead.json"
    receipt = dict(original_frozen_output_hash_checks=checks, commands=results,
                   v1_inputs_verified_against_snapshot=len(original["inputs"]),
                   analytical_outputs_identical_to_v1=len(original["outputs"]),
                   source_snapshot={str(p.relative_to(snapshot)): digest(p)
                                    for p in sorted(snapshot.glob("**/*.py"))},
                   report_sha256=digest(OUT / "phase1_valuation_report.md"),
                   supplemental_source={"path": str(supplemental.relative_to(ROOT)), "sha256": digest(supplemental)},
                   artifacts={str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.glob("*"))
                              if p.is_file() and p.name != "verification-receipt.json"})
    content = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path = OUT / "verification-receipt.json"
    if path.exists():
        assert path.read_text() == content
    else:
        path.write_text(content)
    print(json.dumps(dict(frozen_hash_checks=checks, commands_passed=len(results))))


if __name__ == "__main__":
    main()
