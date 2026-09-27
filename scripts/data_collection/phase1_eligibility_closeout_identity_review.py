"""Tier: 1. Audit exact flagged identity receipt dates and development joins.
Input fixed candidates and eligibility. Output JSON; no returns.
Identity proxy must precede acceptance date. Run with project Python.
"""

import json
from pathlib import Path

from run_phase1_development import encode, freeze

R = Path(__file__).resolve().parents[2]
B = R / "research/runs/phase1-baseline"
CLOSEOUT = B / "20260924-eligibility-closeout-v1"
rows = [
    json.loads(s)
    for s in (B / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
]
lookup = {r["accession"]: r for r in rows}
s = json.loads((B / "20260924-rebuilt-inputs-v2/selection.json").read_text())
out = []
for r in json.loads((R / "research/runs/hfr-all-managers/20260924-v1/candidates.json").read_text()):
    if r["snapshot_not_strictly_before_acceptance_date"]:
        a = r["accession"]
        d = dict(r)
        d["eligibility"] = lookup[a]
        d["selected_branches"] = [
            b for b, rr in s["selected"].items() if any(x["accession"] == a for x in rr)
        ]
        d["history_dependents"] = [x["accession"] for x in rows if a in x["prior_accessions"]]
        out.append(d)
        print(json.dumps(d, indent=2))
freeze(CLOSEOUT / "identity-timing-review.json", encode(out))
