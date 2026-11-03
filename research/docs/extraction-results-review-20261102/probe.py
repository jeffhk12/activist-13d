"""Inspect report dependencies and frozen extraction shapes without model calls.
Inputs: local Python libraries and selected completed record/schema metadata.
Outputs: bounded console metadata only. Identity: key names are read unchanged.
Tier: 0. Run project Python research/docs/extraction-results-review-20261102/probe.py.
"""
import importlib.util
import json
from pathlib import Path
ROOT = Path('/Users/jefflu/Projects/activist-13d')
BASE = ROOT / 'research/runs/extraction-batches/20261028-v1'
print('libraries', {name: bool(importlib.util.find_spec(name)) for name in ['reportlab','pypdf','pdfplumber','PIL','matplotlib']})
for role in ['extractor', 'blind', 'critic']:
    record = json.loads((BASE / f'batch-001/jobs/{role}_b001_01/record.json').read_bytes())
    print(role, {key: (list(value) if isinstance(value,dict) else f'list:{len(value)}' if isinstance(value,list) else value)
                 for key,value in record.items() if key not in ['intent','ownership','transactions','reviews','funding','evidence_gaps','run_metadata','review_delivery']})
    print(role, 'metadata', record.get('run_metadata',{}))
    if role == 'extractor':
        print('ownership', type(record['ownership']).__name__, str(record['ownership'])[:800])
        print('transaction_facts', type(record['transaction_facts']).__name__, str(record['transaction_facts'])[:900])
queue=json.loads((BASE/'queue.json').read_bytes())
print('queue_keys',list(queue))
print('queue_meta',{k:v for k,v in queue.items() if k not in ['queue','excluded']})
print('first_queue_keys',list(queue['queue'][0]))
schema=json.loads((ROOT/'research/protocol/extraction-schema-v3.json').read_bytes())
print('schema_keys',list(schema))
print('schema_enums', str(schema)[:300])
