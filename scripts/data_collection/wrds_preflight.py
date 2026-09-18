"""Verify bulk daily-price pagination at three fixed coverage dates.

Inputs: authorized raw DSF pages for 2012-01-03, 2024-01-03, 2026-09-10.
Outputs: count-reconciled task manifests; shared frozen pages reused by bulk job.
Identity: task n equals sum(page n) with exact date and duplicate checks.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/wrds_preflight.py
"""

import argparse
import json

from wrds_collect import OUT, FrozenClient, Refusal, collect_task, utc, write_json
from wrds_daily import archive_daily, enumerate_daily

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=10000)
parser.add_argument("--offline", action="store_true")
parser.add_argument("--explicit-offsets", action="store_true")
parser.add_argument("--table", choices=["crsp.dsf", "crsp.dsf_v2"], default="crsp.dsf")
parser.add_argument("--single-slice", action="store_true")
args = parser.parse_args()
client = FrozenClient(online=not args.offline)
report = {"started_at": utc(), "checks": [], "model_api_calls": 0}
for value in ("2012-01-03", "2024-01-03", "2025-12-31", "2026-06-30", "2026-09-10"):
    try:
        field = "date" if args.table == "crsp.dsf" else "dlycaldt"
        if args.single_slice:
            result = archive_daily(client, args.table, {field: value}, args.limit, lambda _: None, partition_check=True)
        else:
            result = enumerate_daily(client, {field: value}, args.limit, lambda _: None) if args.explicit_offsets else collect_task(client, args.table, {field: value}, args.limit, lambda _: None)
        report["checks"].append(result)
        print(json.dumps({"date": value, "n": result["n"], "pages": len(result["pages"])}), flush=True)
    except Refusal as error:
        report["checks"].append({"date": value, "status": "refused", "error": str(error)})
        print(str(error), flush=True)
    write_json(OUT / f"daily-preflight-{args.table}-{args.limit}-{'slice' if args.single_slice else 'offsets' if args.explicit_offsets else 'strict'}.json", report)
report.update(completed_at=utc(), network_calls=client.network_calls)
write_json(OUT / f"daily-preflight-{args.table}-{args.limit}-{'slice' if args.single_slice else 'offsets' if args.explicit_offsets else 'strict'}.json", report)
