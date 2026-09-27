"""Tier 0: Inspect schema for bounded grouped-review preparation; read only."""
import sqlite3,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with sqlite3.connect(f'file:{root}/research/runs/phase1-overnight/full-20260915/sec.sqlite?mode=ro',uri=True) as db:
    print(db.execute('SELECT sql FROM sqlite_master WHERE type="table"').fetchall())
    r=json.loads(db.execute('SELECT record_json FROM records LIMIT 1').fetchone()[0])
    print(json.dumps({k:v for k,v in r.items() if k not in ['item4_text','documents','xml_fields']},indent=2)[:6500])
    print('KEYS',list(r))
