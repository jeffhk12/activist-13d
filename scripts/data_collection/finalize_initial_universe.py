"""Tier: 2. Final form/history reconciliation from verified universe canonical text.
Inputs: v1 source audit SQLite and candidate identities. Outputs: v2 eligibility.
Identity: tightened literal matching excludes 13G checkbox/contract boilerplate.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/finalize_initial_universe.py
"""

import gzip
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.initial_eligibility_v2 import classify, mark_history
from activist13d.local_paths import resolve_project_path

OLD = ROOT / "research/runs/phase1-baseline/20260924-universe-rebuild-v1"
OUT = OLD.parent / "20260924-universe-rebuild-v2"


def main():
    old = [json.loads(s) for s in (OLD / "eligibility.jsonl").read_text().splitlines()]
    db = sqlite3.connect(f"file:{OLD / 'audit.sqlite'}?mode=ro", uri=True)
    rows = []
    differences = []
    for r in old:
        r = dict(r)
        r.pop("campaign_status")
        r.pop("prior_accessions")
        if r["status"] != "unresolved_source_or_primary":
            text = gzip.decompress(
                db.execute(
                    "select canonical_gzip from audit where accession=?", (r["accession"],)
                ).fetchone()[0]
            ).decode()
            assert hashlib.sha256(text.encode()).hexdigest() == r["canonical_sha256"]
            xml = None
            if r.get("body_overrides_initial") and not r["amendment_evidence"]:
                raw = resolve_project_path(r["source_path"], ROOT).read_text(errors="replace")
                m = re.search(r"<(?:\w+:)?(?:amendmentNo|amendmentNumber)>\s*(\d+)", raw, re.I)
                xml = m[1] if m else None
            revised = classify(
                text, [r["metadata_form"], r["header_form"], r["document_form"]], xml
            )
            if revised["status"] != r["status"] or revised["prior_history"] != r["prior_history"]:
                differences.append(
                    dict(
                        accession=r["accession"],
                        old_status=r["status"],
                        new_status=revised["status"],
                        old_history_spans=len(r["prior_history"]),
                        new_history_spans=len(revised["prior_history"]),
                    )
                )
            r.update(revised)
        rows.append(r)
    result = mark_history(rows)
    freeze(OUT / "eligibility.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in result))
    freeze(OUT / "lexical-corrections.json", encode(differences))
    summary = dict(
        records=len(result),
        forms=dict(Counter(r["status"] for r in result)),
        campaigns=dict(Counter(r["campaign_status"] for r in result)),
        initial_body_overrides=sum(r.get("body_overrides_initial", False) for r in result),
        initial_campaigns=dict(
            Counter(
                r["campaign_status"]
                for r in result
                if r["status"] == "standalone_initial_candidate"
            )
        ),
    )
    freeze(OUT / "summary.json", encode(summary))
    for p in [
        Path(__file__),
        ROOT / "src/activist13d/initial_eligibility_v2.py",
        ROOT / "tests/test_initial_eligibility_v2.py",
        ROOT / "research/protocol/phase1-rebuild-v1.md",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [
                        OLD / "eligibility.jsonl",
                        OLD / "audit.sqlite",
                        OLD / "provenance.json",
                    ]
                },
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    print(encode(summary))


if __name__ == "__main__":
    main()
