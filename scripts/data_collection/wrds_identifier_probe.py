"""Tiny alternative-query diagnostic for CRSP daily identifier/year slices.

Inputs: a known smoke PERMNO and declared calendar years. Outputs: page parity.
Identity: every row must match identifier and lie within the calendar year.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/wrds_identifier_probe.py
"""

import json

from wrds_collect import OUT, FrozenClient, write_json

client = FrozenClient(online=True)
report = []
for year in (2012, 2024, 2025):
    params = {"permno": "14593", "dlycaldt__gte": f"{year}-01-01", "dlycaldt__lte": f"{year}-12-31", "limit": 1000, "offset": 0}
    payload, meta = client.request("crsp.dsf_v2", "GET", params)
    rows = payload.get("results", [])
    result = {"year": year, "n": len(rows), "count": payload.get("count"), "next": payload.get("next"),
              "dates_match": all(f"{year}-01-01" <= row["dlycaldt"] <= f"{year}-12-31" and row["permno"] == 14593 for row in rows),
              "source": meta}
    report.append(result)
    print(json.dumps({k: v for k, v in result.items() if k != "source"}), flush=True)
write_json(OUT / "identifier-probe.json", report)
