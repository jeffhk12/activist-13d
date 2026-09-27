"""Tier: 1. Recover the single missing 2023-02-08 CRSP daily source slice.

Inputs: existing WRDS entitlement, exact date, frozen acquisition client.
Outputs: frozen raw page(s), partition-equality acquisition receipt.
Identity: full-date rows equal the disjoint union below/above PERMNO 50000;
vendor reported total remains separately flagged. No return calculation.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/repair_phase1_daily_gap.py
"""
import json
from pathlib import Path

from wrds_collect import FrozenClient, Refusal
from wrds_daily import archive_daily

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/phase1-baseline/20260924-daily-gap-repair'


def main():
    client = FrozenClient(online=True, cache=ROOT / 'data/raw/wrds/phase1-gap-20260924')
    try:
        receipt = archive_daily(client, 'crsp.dsf_v2', {'dlycaldt': '2023-02-08'},
                                50000, lambda _: None, partition_check=True)
    except Refusal as error:
        print(str(error))
        raise SystemExit(1) from None
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'receipt.json'
    if not path.exists():
        path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': receipt['n'], 'partition_check_passed': receipt['partition_check_passed'],
                      'network_calls': client.network_calls,
                      'vendor_count_discrepancy': receipt['reported_count_discrepancy']}))


if __name__ == '__main__':
    main()
