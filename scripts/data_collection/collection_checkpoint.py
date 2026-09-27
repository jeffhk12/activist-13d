"""Capture a dated read-only collection checkpoint and code snapshot.

Inputs: current progress, HFR manifest, original blank-packet hashes and scripts.
Outputs: isolated status JSON and reproducibility source copies.
Identity: each original packet's current hash must equal its prior audit hash.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/collection_checkpoint.py
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = ROOT / "research/runs/data-collection" / ("checkpoint-" + stamp)
out.mkdir()
code = out / "code"
code.mkdir()
files = sorted((ROOT / "scripts/data_collection").glob("*.py")) + [ROOT / "tests/test_sec_bulk.py", ROOT / "requirements-pilot-lock.txt", ROOT / "pyproject.toml"]
sources = {}
for path in files:
    target = code / path.name
    shutil.copy2(path, target)
    sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
baseline = json.loads((ROOT / "research/runs/phase1-prep/integrity-20260914T004440397334Z/audit.json").read_text())["packet_hashes_after"]
packets = ROOT / "research/runs/phase1-prep/20260914T003050627334Z/packets"
if {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in packets.glob("*.html")} != baseline:
    raise RuntimeError("Original packet hashes changed")
result = {"captured_at": stamp, "source_hashes": sources, "original_blank_packets_unchanged": True,
          "model_api_calls": 0}
for key, path in {
    "sec": ROOT / "research/runs/data-collection/sec/progress.json",
    "wrds": ROOT / "research/runs/data-collection/wrds/progress.json",
    "hfr": ROOT / "data/interim/hfr/hfr_manifest.json",
    "public_series": ROOT / "research/runs/data-collection/public-series-20260914T010236Z-corrected-v2/manifest.json",
}.items():
    result[key] = json.loads(path.read_text())
(out / "status.json").write_text(json.dumps(result, indent=2) + "\n")
print(out)
