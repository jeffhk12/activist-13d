"""Tier: 1. Restore inherited missing-SIC treatment in historical input adapter.
Inputs: frozen v1 panel/assignments and v2 runner. Outputs: new v2 input receipt.
Identity: SIC must satisfy 100 <= SIC < 9999; 9999 is not a matchable industry.
No selection, price, return or investor changes; preserve original run evidence.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/repair_phase1_historical_industry.py
"""

import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OLD = BASE / "20260924-historical-execution-inputs-v1"
OUT = BASE / "20260924-historical-execution-inputs-v2"


def main():
    prov = json.loads((OLD / "provenance.json").read_text())
    for rel, sha in prov["outputs"].items():
        assert digest(OLD / rel) == sha, rel
    assignments = json.loads((OLD / "assignments.json").read_text())
    changes = []
    for key, a in assignments.items():
        sic = a["siccd"]
        industry = (
            str(int(sic)).zfill(4)[:2] if sic is not None and 100 <= int(sic) < 9999 else None
        )
        if industry != a["industry"]:
            changes.append(dict(input_key=key, siccd=sic, old=a["industry"], new=industry))
        a["industry"] = industry
    assert len(changes) == 37 and all(r["siccd"] in {0, 9999} and r["new"] is None for r in changes)
    for name in [
        "panel.json",
        "selection.json",
        "source-inventory.json",
        "required-keys.json",
        "missing-keys.json",
        "environment.json",
        "outcome-access-0001.json",
    ]:
        freeze(OUT / name, (OLD / name).read_bytes())
        assert digest(OUT / name) == digest(OLD / name)
    freeze(OUT / "assignments.json", encode(assignments))
    freeze(
        OUT / "correction.json",
        encode(
            {
                "reason": "Restore existing protocol: unknown SIC 9999 must not become matching industry 99",
                "changes": changes,
                "selection_price_investor_changes": False,
                "original_run_preserved": True,
                "prior_access_receipt_inherited": True,
            }
        ),
    )
    code = (
        [Path(__file__), ROOT / "scripts/data_collection/run_phase1_historical_validation_v2.py"]
        + sorted((ROOT / "src/activist13d").glob("*.py"))
        + [ROOT / "scripts/data_collection/run_phase1_development.py"]
    )
    for p in code:
        freeze(OUT / "code" / p.relative_to(ROOT), p.read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {
                    str(p.relative_to(ROOT)): digest(p) for p in [OLD / "provenance.json"] + code
                },
                "outputs": {
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            }
        ),
    )
    print("Restored 37 unknown SIC assignments to unmatchable; sample and panel identical.")


if __name__ == "__main__":
    main()
