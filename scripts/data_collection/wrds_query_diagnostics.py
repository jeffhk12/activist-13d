"""Bounded WRDS exact/range-filter diagnostic; no analysis output.

Inputs: three tiny fixed diagnostic requests. Outputs: redacted shape/date evidence.
Identity: each returned date must satisfy the declared diagnostic scope.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/wrds_query_diagnostics.py
"""

import json

from wrds_collect import OUT, FrozenClient, utc, write_json

client = FrozenClient(online=True)
requests = [
    {"permno": "14593", "date": "2024-01-03", "limit": 10, "offset": 0},
    {"permno": "14593", "date__gte": "2012-01-01", "date__lte": "2026-09-13", "limit": 10, "offset": 0},
    {"date": "2024-01-03", "permno__gt": "90000", "limit": 10, "offset": 0},
    {"date": "2024-01-03", "permno__lt": "50000", "limit": 10000, "offset": 0},
    {"date": "2024-01-03", "permno__gte": "50000", "limit": 10000, "offset": 0},
]
results = []
for params in requests:
    payload, meta = client.request("crsp.dsf", "GET", params)
    rows = payload.get("results", [])
    result = {"request": params, "count": payload.get("count"), "n": len(rows),
              "dates": sorted({str(r.get("date")) for r in rows}),
              "permno_min": min((r.get("permno") for r in rows), default=None),
              "permno_max": max((r.get("permno") for r in rows), default=None), "source": meta}
    results.append(result)
    print(json.dumps({k: v for k, v in result.items() if k != "source"}), flush=True)
write_json(OUT / "query-diagnostics.json", {"at": utc(), "results": results})
