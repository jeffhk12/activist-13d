"""Tier 0: Inspect the already exposed ten-file pilot for an explanatory report.
Inputs: frozen pilot JSONL and canonical bundles. Output: compact source inventory.
Checks all source hashes; does not access the human-first 32, 52 or 200 cases.
Run with the local project .venv/bin/python.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
records = [json.loads(x) for x in (ROOT/'data/interim/pilot/filings.jsonl').read_text().splitlines()]
bundles = json.loads((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text())
rows = []
for record in records:
    raw = ROOT/record['source_path']
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == record['source_sha256']
    bundle = next(x for x in bundles if x['accession'] == record['accession'])
    for d in bundle['documents']:
        if d.get('text') is not None:
            assert hashlib.sha256(d['text'].encode()).hexdigest() == d['text_sha256']
    rows.append({k: record.get(k) for k in ['accession','filing_date','acceptance_datetime_et','filers','subjects','cusip','event_date','item4_status','ownership_status','reporting_persons_xml','source_url','source_sha256']}
        | {'filing_date': record['index_filing_date'], 'item4': record['item4_text'], 'documents': [{k:d.get(k) for k in ['document_id','filename','type','status']} for d in bundle['documents']]})
(OUT/'pilot-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
    print(json.dumps({k:v for k,v in row.items() if k not in ['item4','reporting_persons_xml','source_sha256','source_url']},ensure_ascii=False))
