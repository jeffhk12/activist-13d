"""Freeze ten selected Bloomberg rows for filing-date/publication-date review.

Inputs: original XLSX caches, ten-case manifest, requests and event metadata.
Outputs: new dated snapshot/receipt. Identity: unique exact row_id joins and
unchanged source SHA before/after inspection. Tier: 1; no refresh or XLSX edits.
Run: project Python scripts/ml_experiment/prepare_bloomberg_timing.py [--verify].
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_ranking_scope import unique_index, workbook_caches  # noqa: E402

RUN = ROOT/'research/runs/bloomberg-timing/20261026-v1'
WORKBOOK = Path('/Users/jefflu/Downloads/13D_Bloomberg_9_Field_Extraction.xlsx')
MANIFEST = ROOT/'research/runs/ranking-llm-pilot/20261025-v2/financial-checks/manifest.json'
REQUESTS = ROOT/'research/runs/bloomberg-extraction-handoff/20261017-v2/event_requests.csv'
METADATA = ROOT/'research/runs/ml-feature-preview/20261012-v1/row-metadata.jsonl'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    manifest=json.loads(MANIFEST.read_text())
    expected=manifest['workbook_sha256']
    assert sha(WORKBOOK)==expected
    with REQUESTS.open(newline='') as stream:
        requests=unique_index(list(csv.DictReader(stream)), 'row_id')
    metadata=unique_index([json.loads(line) for line in METADATA.read_text().splitlines()], 'row_id')
    workbook=workbook_caches(WORKBOOK)
    rows=[]
    for case, key in enumerate(manifest['event_ids'], 1):
        request, meta=requests[key], metadata[key]
        assert request['accession']==meta['accession']
        assert request['accepted_et']==meta['accepted_et']
        assert request['issuer_cik']==meta['issuer']
        assert int(request['permno'])==meta['permno']
        views={}
        for sheet, width in [('Live Fundamentals',17),('BQL Raw Nine',14)]:
            cells=workbook[sheet]['cells']
            rownums=[c[1:] for c,v in cells.items() if c.startswith('A') and c[1:].isdigit() and v==key]
            assert len(rownums)==1
            rownum=rownums[0]
            headers={chr(65+i):cells[f'{chr(65+i)}1'] for i in range(width)}
            views[sheet]={'excel_row':int(rownum),
                          'range':f'A{rownum}:{chr(64+width)}{rownum}',
                          'values':{h:cells.get(f'{c}{rownum}') for c,h in headers.items()},
                          'formulas':{f'{c}{rownum}':workbook[sheet]['formulas'].get(f'{c}{rownum}') for c in headers}}
        raw=views['BQL Raw Nine']['values']
        live=views['Live Fundamentals']['values']
        for field in ['event_as_of','reviewed_bbg_ID','candidate_FY']:
            assert raw[field]==live[field]
        assert raw['event_as_of']==request['as_of_date']
        assert request['as_of_date']<meta['accepted_et'][:10]<meta['entry']
        rows.append({'case_id':f'F{case:02d}', 'row_id':key, 'company':request['issuer_name_sec'],
                     'accession':meta['accession'], 'issuer_cik':meta['issuer'],
                     'filing_accepted_et':meta['accepted_et'], 'filing_date':meta['accepted_et'][:10],
                     'entry_date':meta['entry'], 'financial_cutoff_date':request['as_of_date'],
                     'candidate_fiscal_year':int(raw['candidate_FY']), 'historical_identity':request,
                     'workbook_views':views})
    assert len(rows)==len({r['row_id'] for r in rows})==10
    assert sha(WORKBOOK)==expected
    receipt={'workbook_sha256':expected, 'selected_events':10, 'selected_field_slots':90,
             'source_sha256':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p)
                              for p in [WORKBOOK,MANIFEST,REQUESTS,METADATA,Path(__file__)]},
             'workbook_mutated':False,'formula_recalculation':False,
             'scope':'Existing ten-event financial-check pilot: known-conflict BHE control plus nine discovery-related events. No reserved text or numerical outcomes read.'}
    return {'selected-workbook-rows.json':rows,'input-receipt.json':receipt}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    artifacts=build()
    RUN.mkdir(parents=True,exist_ok=True)
    for name,data in artifacts.items():
        payload=(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
        path=RUN/name
        if args.verify or path.exists():
            assert path.read_bytes()==payload,name
        else:
            path.write_bytes(payload)
    print(json.dumps({'events':len(artifacts['selected-workbook-rows.json']),
                      'snapshot':str(RUN/'selected-workbook-rows.json'),'original_workbook':'unchanged'},indent=2))


if __name__=='__main__':
    main()
