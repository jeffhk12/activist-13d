"""Inspect WRDS schemas or retrieve fixed smoke samples; replay offline by default.

Inputs: CLI mode and online opt-in. Outputs: metadata and sample sizes only.
Identity: n = number of returned rows, not the API's total matching count.
Tier: 1
Run: .venv/bin/python wrds_access/run.py schema --online
"""

import argparse
import json

from client import SCOPES, AccessError, Client

SAMPLES = {
    "crsp.dsf": {"permno": "14593", "date": "2024-01-03"},
    "comp.funda": {"gvkey": "001690", "fyear": "2023"},
    "audit.feed31_shareholder_activism": {"iss_file_date": "2024-01-03"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["schema", "sample"])
    parser.add_argument("--online", action="store_true", help="Allow bounded cache-miss requests")
    args = parser.parse_args()
    client = Client(online=args.online)
    try:
        for table in SCOPES:
            if args.mode == "schema":
                fields, provenance = client.schema(table)
                result = {
                    "columns": len(fields),
                    "filter_fields": [k for k, v in fields.items() if v["filter_field"]],
                }
            else:
                rows, provenance = client.sample(table, SAMPLES[table])
                result = {"n": len(rows), "filters": SAMPLES[table]}
            print(
                json.dumps(
                    {
                        "table": table,
                        **result,
                        "retrieved_at": provenance["retrieved_at"],
                        "sha256": provenance["sha256"],
                    }
                )
            )
    except AccessError as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
