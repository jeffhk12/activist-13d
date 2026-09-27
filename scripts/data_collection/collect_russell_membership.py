"""Tier: 1. Archive pre-disclosure monthly Russell membership snapshots.
Inputs: frozen development event dates and calendar; existing WRDS entitlement.
Outputs: immutable raw date pages and membership-only receipt; no return analysis.
Identity: one unique CUSIP per requested date; vendor count discrepancy disclosed.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/collect_russell_membership.py
"""
import bisect
import json
from collections import Counter
from datetime import date, timedelta
import wrds_collect
from wrds_collect import FrozenClient, ROOT, Refusal
from run_phase1_development import INPUT, freeze, encode

OUT=ROOT/'research/runs/phase1-baseline/20260924-russell-inputs-v1'
BASE=ROOT/'research/runs/phase1-baseline/20260924-development-v4'


def snapshot_date(public_day, sessions):
    first=date.fromisoformat(public_day).replace(day=1)
    last=(first-timedelta(days=1)).isoformat()
    index=bisect.bisect_right(sessions,last)-1
    if index < 0:
        raise ValueError('No historical month-end session')
    return sessions[index]


def main():
    wrds_collect.TABLES=(*wrds_collect.TABLES,'ftse.idx_holdings_us')
    client=FrozenClient(online=True,cache=ROOT/'data/raw/wrds/russell-membership-20260924')
    sessions=json.loads((INPUT/'entry-calendar.json').read_text())
    registry={r['accession']:r for line in (INPUT/'event-candidates.jsonl').read_text().splitlines() if (r:=json.loads(line))}
    plans=json.loads((BASE/'selection.json').read_text())['plans']
    days=sorted({snapshot_date(min(registry[a]['acceptance_datetime_et'][:10] for a in e['accessions']),sessions) for events in plans.values() for e in events})
    receipt=[]
    for day in days:
        payload,meta=client.request('ftse.idx_holdings_us','GET',{'date':day,'limit':10000,'offset':0})
        rows=payload.get('results')
        if not isinstance(rows, list) or not rows or len(rows)>=10000 or payload.get('next'):
            raise Refusal('Missing or possibly truncated membership snapshot')
        if any(r.get('date') != day for r in rows):
            raise Refusal('Requested membership date ignored')
        counts=Counter(r['cusip'] for r in rows)
        if any(n>1 for n in counts.values()):
            raise Refusal('Ambiguous membership snapshot keys')
        receipt.append(dict(date=day,rows=len(rows),reported_count=payload['count'],count_discrepancy=len(rows)!=payload['count'],source=meta['cache_path']))
        print(day,len(rows),payload['count'],flush=True)
    freeze(OUT/'membership-receipt.json',encode(receipt))


if __name__=='__main__':
    main()
