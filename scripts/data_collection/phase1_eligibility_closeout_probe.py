"""Tier: 0. Inspect frozen evidence and schema for independent closeout.
Inputs: frozen eligibility/canonical audit and development pre-event inputs.
Outputs: stdout; no outcomes. Identity: exact accession joins.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_eligibility_closeout_probe.py
"""

import gzip
import json
import sqlite3
from pathlib import Path

from activist13d.local_paths import resolve_project_path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/runs/phase1-baseline"
rows = [
    json.loads(x)
    for x in (BASE / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
]
db = sqlite3.connect(f"file:{BASE / '20260924-universe-rebuild-v1/audit.sqlite'}?mode=ro", uri=True)
for r in rows:
    if r["status"].startswith("unresolved"):
        text = gzip.decompress(
            db.execute(
                "select canonical_gzip from audit where accession=?", (r["accession"],)
            ).fetchone()[0]
        ).decode()
        p = resolve_project_path(r["source_path"], ROOT)
        print(
            json.dumps(
                {
                    k: r.get(k)
                    for k in [
                        "accession",
                        "metadata_form",
                        "status",
                        "reason",
                        "source_bytes",
                        "manager_keys",
                    ]
                }
            ),
            "exists",
            p.exists(),
            "START",
            text[:700],
        )
for fname in ["selection", "assignments"]:
    x = json.loads((BASE / f"20260924-rebuilt-inputs-v2/{fname}.json").read_text())
    print(fname, list(x)[:8])
    if fname == "selection":
        print("selected", x["selected"]["first_observed"][0])
        print(
            "plan", {k: v for k, v in x["plans"]["first_observed"]["126"][0].items() if k != "days"}
        )
        print("excluded", x["exclusions"]["first_observed"]["schedule"]["126"][:2])
    else:
        print(next(iter(x.values())))
