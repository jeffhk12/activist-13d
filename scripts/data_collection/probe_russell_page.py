"""Tier: 0. Check dated Russell constituent access; preserve vendor response.
Inputs: exact 2018-02-28 date. Outputs: cached page and bounded coverage log.
Identity: returned date must equal requested date; no outcomes.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/probe_russell_page.py
"""
import json
import wrds_collect
from wrds_collect import FrozenClient, ROOT, Refusal, validate_page
if __name__ == '__main__':
    wrds_collect.TABLES = (*wrds_collect.TABLES, 'ftse.idx_holdings_us')
    client = FrozenClient(online=True, cache=ROOT / 'data/raw/wrds/russell-membership-20260924')
    try:
        payload, meta = client.request('ftse.idx_holdings_us','GET', {'date':'2018-02-28','limit':10000,'offset':0})
        rows=validate_page(payload, {'date':'2018-02-28'},10000)
        print(json.dumps({'rows':len(rows),'count':payload.get('count'),'next':payload.get('next'),'first':rows[:1]},indent=2))
    except Refusal as error:
        print(str(error))
