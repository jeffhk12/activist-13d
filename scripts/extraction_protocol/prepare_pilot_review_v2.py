"""Prepare a reproducible review snapshot of the ten already-exposed pilot filings.

Inputs: cached raw submissions, pilot JSONL, original ledger and v1 categories.
Outputs: canonical document bundles and review inputs in a new dated directory.
Identity: SHA256(raw) must match the pilot; each citation is text[start:end].
Tier: 1. No network, model API, training, or changes to existing research/protocol/labels.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/prepare_pilot_review_v2.py
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'review/archive/13d-structured-review-20260922'


def build():
    spec = importlib.util.spec_from_file_location('canonical', ROOT/'scripts/extraction_prep/prepare_sample.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ledger = (ROOT/'research/docs/PILOT-TRIAGE-2026-09-09.md').read_text()
    pilot = [json.loads(line) for line in (ROOT/'data/interim/pilot/filings.jsonl').read_text().splitlines()]
    print('PILOT KEYS',list(pilot[0]))
    records = []
    for line in ledger.splitlines():
        if not line.startswith('| [000'):
            continue
        cells = [x.strip() for x in line.split('|')[1:-1]]
        accession = re.search(r'\[(.*?)\]',cells[0])[1]
        sheet = (ROOT/f'research/runs/pilot-filings/{accession}.md').read_text()
        source = ROOT/f'data/raw/edgar/pilot/filings/{accession}/submission.txt'
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == re.search(r'Source SHA-256: `(.*?)`',sheet)[1]
        documents = module.docs(raw)
        for document in documents:
            if document['text'] is not None:
                assert hashlib.sha256(document['text'].encode()).hexdigest()==document['text_sha256']
        record = {'accession':accession,'source_sha256':digest,'documents':documents,'pilot':next(x for x in pilot if x.get('accession')==accession),'ledger_evidence':cells[1],'ledger_judgment':cells[2],'sheet':sheet}
        records.append(record)
    assert len(records)==10 and len({r['accession'] for r in records})==10
    OUT.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(records,ensure_ascii=False,indent=2)+'\n'
    target=OUT/'review-inputs.json'
    if target.exists():
        assert target.read_text()==payload,'Refuse changed evidence snapshot'
    else:
        target.write_text(payload)
    print('OUTPUT',target)
    for r in records:
        print(r['accession'],[(d['document_id'],d['filename'],len(d['text'] or '')) for d in r['documents']])
    print('FIRST RECORD',json.dumps(records[0]['pilot'],ensure_ascii=False)[:8000])


if __name__=='__main__':build()
