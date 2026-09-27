"""Tier: 0. Inspect candidate schema and required source dates without outcomes.
Inputs: frozen candidate metadata. Outputs: counts and schema only.
Run: PYTHONPATH=src .venv/bin/python scripts/data_collection/probe_item3_requirements.py
"""
import json
from pathlib import Path
p=Path('research/runs/phase1-baseline/20260924-evaluation-readiness-v1/candidate-selection.json')
r=json.loads(p.read_text());print(list(r));print(list(r['plans']['first_observed']['126']));e=r['plans']['first_observed']['126']['events'][0];print({k:v for k,v in e.items() if k!='days'})
print('distinct entry events',len({(e['accession'],e['entry']) for b in r['plans'].values() for h in b.values() for e in h['events']}))
