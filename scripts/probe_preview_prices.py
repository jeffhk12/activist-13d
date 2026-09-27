"""Tier 0 scratch: inspect cached market data shapes; no changes or network.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/probe_preview_prices.py
"""
import gzip,json
from pathlib import Path
import importlib.util
root=Path(__file__).resolve().parents[1]
for table in ['crsp.dsf','crsp.stocknames']:
    p=next((root/'data/raw/wrds/bulk-v1'/table).glob('*.json.gz'))
    obj=json.loads(gzip.decompress(p.read_bytes()))
    print(table,p.name,str(obj)[:1800])
for m in ['matplotlib','pandas','requests','exchange_calendars']:
    print(m,bool(importlib.util.find_spec(m)))
