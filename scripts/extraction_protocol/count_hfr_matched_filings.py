"""Tier: 1. Count unique accessions in the frozen HFR name-match screen.
Input: 20260923-hfr-event-driven-v1/matches.json; stdout only.
Identity: union accessions across all candidate filer names and managers.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/count_hfr_matched_filings.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
data=json.loads((ROOT/'research/runs/investor-identity/20260923-hfr-event-driven-v1/matches.json').read_text())

def accession_map(managers):
    records={}
    for m in managers:
        for hit in m['matches']:
            for r in hit['filings']:
                if r['accession'] in records:
                    assert records[r['accession']]['form']==r['form']
                records[r['accession']]=r
    return records

fixture=[{'matches':[{'filings':[{'accession':'a','form':'13D'},{'accession':'a','form':'13D'}]}]}]
assert len(accession_map(fixture))==1
assert accession_map([])=={}
all_managers=data['managers']
activists=[m for m in all_managers if 'Activist' in m['substrategies']]
all_records=accession_map(all_managers)
active_records=accession_map(activists)
assert set(active_records)<=set(all_records)
for label,records in [('All Event-Driven',all_records),('Activist subset',active_records)]:
    counts=Counter(r['form'] for r in records.values())
    assert sum(counts.values())==len(records)
    print(json.dumps({'group':label,'unique_accessions':len(records),'form_counts':dict(counts),'share_of_local_archive_pct':100*len(records)/data['summary']['local_13d_records_scanned']}))
for m in activists:
    records=accession_map([m])
    if records:
        print(json.dumps({'manager':m['names'],'unique_accessions':len(records),'form_counts':dict(Counter(r['form'] for r in records.values()))}))
print(json.dumps({'archive_denominator':data['summary']['local_13d_records_scanned'],'all_manager_sum_before_cross_manager_dedup':sum(len(accession_map([m])) for m in all_managers),'activist_manager_sum_before_cross_manager_dedup':sum(len(accession_map([m])) for m in activists)}))
