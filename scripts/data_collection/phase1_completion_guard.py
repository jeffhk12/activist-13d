"""Tier: 1. Record and verify protected research assets during delegated closeout.
Inputs: frozen investor lists, human packets, protected issuers and baseline receipts.
Outputs: immutable SHA manifest; subsequent runs refuse any changed asset.
Identity: neither outcomes nor agent reviews may change protected human/list evidence.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_completion_guard.py
"""

import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

OUT = ROOT / "research/runs/phase1-baseline/20260924-completion-integration-v1"


def main():
    paths = []
    for folder in [
        "review/current",
        "review/drafts/human-first-52",
        "research/runs/hfr-all-managers/20260924-v1",
        "research/runs/investor-identity/20260924-supplemental-v1",
    ]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.name != ".DS_Store")
    for rel in [
        "research/runs/phase1-baseline/20260924-development-v4/human-review-protection.json",
        "research/runs/phase1-baseline/20260924-rebuilt-analysis-v1/provenance.json",
        "research/runs/phase1-baseline/20260924-universe-rebuild-v3/provenance.json",
        "research/protocol/phase1-rebuild-v1.md",
    ]:
        paths.append(ROOT / rel)
    manifest = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    target = OUT / "protected-assets.json"
    if target.exists():
        before = json.loads(target.read_text())
        assert manifest == before, "Protected assets changed during closeout"
        print("Verified unchanged protected assets:", len(manifest))
    else:
        freeze(target, encode(manifest))
        freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
        print("Captured protected assets:", len(manifest))


if __name__ == "__main__":
    main()
