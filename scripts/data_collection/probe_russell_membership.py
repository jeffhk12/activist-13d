"""Tier: 0. Inspect historical Russell membership schema under existing WRDS entitlement.
Inputs: named API metadata endpoints. Outputs: frozen schema responses, no returns.
Identity: direct vendor schema, no estimation.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/probe_russell_membership.py
"""
import json
import wrds_collect
from wrds_collect import FrozenClient, ROOT, Refusal

if __name__ == '__main__':
    wrds_collect.TABLES = (*wrds_collect.TABLES, 'ftse.idx_holdings_us')
    client = FrozenClient(online=True, cache=ROOT / 'data/raw/wrds/russell-membership-20260924')
    try:
        payload, meta = client.request('ftse.idx_holdings_us')
        print(json.dumps(payload, indent=2))
    except Refusal as error:
        print(str(error))
