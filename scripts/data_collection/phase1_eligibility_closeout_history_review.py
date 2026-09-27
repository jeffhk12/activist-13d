"""Tier: 1. Exact contexts for all 24 development text-history exclusions.
Inputs: immutable eligibility and canonical audit. Outputs: JSON evidence inventory.
Identity: quote = canonical[start:end]; no inference or outcomes. Run with project Python.
"""

import gzip
import json
import sqlite3
from pathlib import Path

from run_phase1_development import encode, freeze

R = Path(__file__).resolve().parents[2]
B = R / "research/runs/phase1-baseline"
CLOSEOUT = B / "20260924-eligibility-closeout-v1"
selection = json.loads((B / "20260924-rebuilt-inputs-v2/selection.json").read_text())
wanted = {
    r["accession"]
    for r in selection["exclusions"]["first_observed"]["eligibility"]
    if r["reason"] == "prior_history_in_document"
}
rows = {
    r["accession"]: r
    for line in (B / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
    if (r := json.loads(line))
}
db = sqlite3.connect(f"file:{B / '20260924-universe-rebuild-v1/audit.sqlite'}?mode=ro", uri=True)
records = []
for a in sorted(wanted):
    r = rows[a]
    t = gzip.decompress(
        db.execute("select canonical_gzip from audit where accession=?", (a,)).fetchone()[0]
    ).decode()
    spans = []
    for s in r["prior_history"]:
        assert t[s["start"] : s["end"]] == s["quote"]
        start = max(0, s["start"] - 250)
        end = min(len(t), s["end"] + 350)
        spans.append(dict(start=start, end=end, quote=t[start:end]))
    records.append(
        dict(
            accession=a,
            canonical_sha256=r["canonical_sha256"],
            source_path=r["source_path"],
            cover=t[:350],
            contexts=spans,
        )
    )
    print(a, t[:180])
    print("\n".join(s["quote"] for s in spans[:2]))
assert len(records) == 24
freeze(CLOSEOUT / "development-history-contexts.json", encode(records))
