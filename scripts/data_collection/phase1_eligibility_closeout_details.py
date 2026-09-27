"""Tier: 0. Bounded detail inspection. No outcomes. Inputs frozen closeout JSON.
Outputs stdout. Identity exact accession joins. Run with project Python.
"""

import json
from pathlib import Path

R = Path(__file__).resolve().parents[2]
B = R / "research/runs/phase1-baseline"
CLOSEOUT = B / "20260924-eligibility-closeout-v1"
sample = json.loads((CLOSEOUT / "source-sample.json").read_text())["records"]
for r in sample:
    t = (CLOSEOUT / "sample-text" / f"{r['accession']}.txt").read_text()
    print(
        r["accession"], r["status"], r["campaign_status"], "override", r["body_overrides_initial"]
    )
    spans = r["prior_history"][:1] or r["amendment_evidence"][:1]
    for s in spans:
        print(t[max(0, s["start"] - 80) : s["end"] + 200])
    if not spans:
        print(t[:200])
rows = [
    json.loads(s)
    for s in (B / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
]
lookup = {r["accession"]: r for r in rows}
print("MANAGER ONLY INITIAL")
for r in rows:
    if (
        r["status"] == "standalone_initial_candidate"
        and r["campaign_status"] == "previously_observed_pair"
        and not any(
            set(r["reporter_ciks"]) & set(lookup[a]["reporter_ciks"]) for a in r["prior_accessions"]
        )
    ):
        print(r["accession"], r["prior_accessions"], r["manager_keys"])
for r in json.loads((R / "research/runs/hfr-all-managers/20260924-v1/candidates.json").read_text()):
    if r["snapshot_not_strictly_before_acceptance_date"]:
        print("HFR NOT PRIOR", r["accession"], r["filing_date"], r["delivery_date_proxy"])
c = json.loads((CLOSEOUT / "pre-event-coverage.json").read_text())["tables"]["first_observed"]["126"]
print("YEAR AND SIZE", [x for x in c if x["dimension"] in ["year", "size"]])
print("FOCUSED INDUSTRIES", [x for x in c if x["dimension"] == "industry" and x["focused_n"]])
print("FUNNEL", json.loads((CLOSEOUT / "development-funnel.json").read_text()))
