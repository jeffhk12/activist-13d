"""Tier: 2. Coarse industry/year/Russell-segment matched event comparison.
Inputs: eligible branch event outcomes with historical SIC and assigned ETF.
Outputs: focal/control counts, means and differences; no causal claim.
Identity: control mean equally weights issuer-specific mean excess returns.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_matched_controls.py
"""

import statistics
from collections import defaultdict


def match_events(rows, min_issuers=5):
    controls = defaultdict(list)
    for r in rows:
        if not r["focused"] and r["excess"] is not None and r.get("industry"):
            controls[(r["entry"][:4], r["industry"], r["assigned_etf"])].append(r)
    results = []
    for r in rows:
        if not r["focused"]:
            continue
        result = dict(
            accession=r["accession"],
            issuer=r["issuer"],
            entry=r["entry"],
            focused_excess=r["excess"],
            status="unresolved_focal",
        )
        if r["excess"] is not None and r.get("industry"):
            peers = [
                p
                for p in controls.get((r["entry"][:4], r["industry"], r["assigned_etf"]), [])
                if p["issuer"] != r["issuer"]
            ]
            issuers = defaultdict(list)
            for p in peers:
                issuers[p["issuer"]].append(p["excess"])
            result.update(control_events=len(peers), control_issuers=len(issuers))
            if len(issuers) < min_issuers:
                result["status"] = "fewer_than_five_control_issuers"
            else:
                mean = statistics.mean(statistics.mean(v) for v in issuers.values())
                result.update(
                    status="matched",
                    control_mean=mean,
                    difference=r["excess"] - mean,
                    control_accessions=sorted(p["accession"] for p in peers),
                )
        results.append(result)
    return results
