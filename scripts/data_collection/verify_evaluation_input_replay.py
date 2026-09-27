"""Tier: 1. Verify source-only replay repair and frozen input-preparation outputs.
Inputs: initial/new run receipts, raw-cache and ETF metadata. Outputs: parity proof.
Identity: every analytical JSON hash agrees; source metadata is not performance.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_evaluation_input_replay.py
"""

import gzip
import hashlib
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OLD = BASE / "20260924-evaluation-inputs-v1"
NEW = BASE / "20260924-evaluation-inputs-v2"
OUT = BASE / "20260924-evaluation-inputs-replay-v1"


def main():
    compared = []
    for p in sorted(OLD.glob("*.json")):
        if p.name == "provenance.json":
            continue
        assert digest(p) == digest(NEW / p.name), p.name
        compared.append(p.name)
    for folder in [
        OLD,
        NEW,
        BASE / "20260924-evaluation-inputs-qa-v1",
        BASE / "20260924-evaluation-inputs-etf-v1",
        BASE / "20260924-evaluation-calendar-support-v1",
    ]:
        prov = json.loads((folder / "provenance.json").read_text())
        for p, sha in prov["outputs"].items():
            assert digest(folder / p) == sha, (folder, p)
        for p, sha in prov["inputs"].items():
            assert digest(ROOT / p) == sha, p
    rawchecks = []
    receipts = json.loads((NEW / "membership-receipt.json").read_text()) + json.loads(
        (BASE / "20260924-evaluation-inputs-etf-v1/identity-coverage.json").read_text()
    )
    for rec in receipts:
        if "source" not in rec:
            continue
        path = ROOT / rec["source"]
        meta = json.loads(path.with_suffix(".meta.json").read_text())
        raw = gzip.decompress(path.read_bytes())
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"] and len(raw) == meta["raw_bytes"]
        assert meta["sha256"] == rec.get("sha256", rec.get("source_sha256"))
        rawchecks.append(str(path.relative_to(ROOT)))
    dependencies = [
        "scripts/data_collection/run_phase1_development.py",
        "scripts/data_collection/collect_russell_membership.py",
        "scripts/data_collection/wrds_collect.py",
        "scripts/data_collection/wrds_daily.py",
        "src/activist13d/phase1_baseline.py",
        "wrds_access/client.py",
    ]
    for rel in dependencies:
        freeze(OUT / "code" / rel, (ROOT / rel).read_bytes())
    receipt = dict(
        status="passed",
        analytical_json_equal=compared,
        analytical_json_count=len(compared),
        membership_and_etf_raw_hash_checks=len(rawchecks),
        raw_sources=rawchecks,
        reason_for_v2="Preserve initial acquisition receipt after cache warm-up; original output remains frozen. No analytical change.",
        replay="Use prepare_phase1_evaluation_inputs_v2.py for repeated offline-cache processing; v1 captures original acquisition history and its source snapshot.",
        dependency_hashes={rel: digest(ROOT / rel) for rel in dependencies},
        inputs={
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                OLD / "provenance.json",
                NEW / "provenance.json",
                BASE / "20260924-evaluation-inputs-qa-v1/provenance.json",
                BASE / "20260924-evaluation-inputs-etf-v1/provenance.json",
            ]
        },
    )
    freeze(OUT / "receipt.json", encode(receipt))
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    print(
        encode(
            {
                k: v
                for k, v in receipt.items()
                if k in ["status", "analytical_json_count", "membership_and_etf_raw_hash_checks"]
            }
        )
    )


if __name__ == "__main__":
    main()
