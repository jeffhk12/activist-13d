"""Smoke-test WRDS audit on three existing production pages without raw edits.

Inputs: frozen task paths. Outputs: symlinks in pilot folder and pilot audit.
Identity: pilot coverage is not full-universe coverage.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/pilot_wrds.py
"""
import json
from pathlib import Path

from wrds_audit import DEFAULT_RAW, _production_cache_paths, run

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    pilot = ROOT / 'research/runs/phase1-overnight/pilot-20260915'
    raw = pilot / 'wrds-pilot-sources'
    paths = _production_cache_paths(DEFAULT_RAW)
    for table in ('crsp.dsf_v2', 'crsp.stocknames', 'comp.funda'):
        relative = next(p for p in sorted(paths) if p.startswith(table + '/'))
        source = DEFAULT_RAW / relative
        target = raw / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.symlink_to(source)
            target.with_suffix('.meta.json').symlink_to(source.with_suffix('.meta.json'))
    first = run(pilot / 'wrds', raw)
    second = run(pilot / 'wrds', raw)
    assert first['files_verified'] == 3
    assert first['daily'] == second['daily']
    print(json.dumps({'files_verified': first['files_verified'], 'daily_rows': first['daily']['rows'], 'duplicate_rows': first['daily']['duplicate_security_date_rows'], 'resume_equal': True}))
