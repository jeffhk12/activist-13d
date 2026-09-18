"""Summarize cached WRDS probes; no network or credentials.

Inputs: frozen inspection cache. Outputs: filter metadata and scope fields.
Identity: no transformations. Tier: 0
Run: .venv/bin/python wrds_access/summarize_probe.py
"""

import json
from pathlib import Path

for path in sorted(
    (Path(__file__).resolve().parents[1] / "data/raw/wrds").glob("inspect-*/*.response")
):
    try:
        payload = json.loads(path.read_bytes())
    except ValueError:
        continue
    if "fields" in payload:
        print(
            path.parent.name,
            path.name,
            "columns",
            len(payload["fields"]),
            "filters",
            {k: v for k, v in payload["fields"].items() if v["filter_field"]},
        )
    if "results" in payload:
        print(
            path.parent.name,
            path.name,
            "scope",
            [
                {
                    k: v
                    for k, v in row.items()
                    if k in {"gvkey", "datadate", "permno", "date", "iss_file_date", "company_fkey"}
                }
                for row in payload["results"]
            ],
        )
