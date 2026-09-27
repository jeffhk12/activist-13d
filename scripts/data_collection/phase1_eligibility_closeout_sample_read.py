"""Tier: 0. Print bounded exact source contexts from deterministic audit sample.
Input: closeout canonical sample and original eligibility. Output: stdout.
Identity: quote = text[start:end]. Run with project Python, PYTHONPATH=src.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/runs/phase1-baseline"
rows = {
    r["accession"]: r
    for line in (BASE / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
    if (r := json.loads(line))
}
for p in sorted((BASE / "20260924-eligibility-closeout-v1/sample-text").glob("*.txt")):
    r = rows[p.stem]
    t = p.read_text()
    print(
        "\n", p.stem, r["status"], r["campaign_status"], "override", r.get("body_overrides_initial")
    )
    print("COVER", t[:450])
    for s in r["amendment_evidence"] + r["prior_history"]:
        print("EVIDENCE", t[max(0, s["start"] - 180) : s["end"] + 300])
    for m in list(
        re.finditer(
            r"(?i)(?:amends and supplements|this schedule 13d|this statement on schedule 13d|initial schedule 13d)",
            t,
        )
    )[:2]:
        print("CHECK", t[max(0, m.start() - 80) : m.end() + 350])
