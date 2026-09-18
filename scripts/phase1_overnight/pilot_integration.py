"""Exercise report/link integration using the existing 50-filing pilot.

Inputs: frozen pilot SQLite. Outputs: isolated pilot linkage and EDA outputs.
Identity: pilot outputs never establish population-wide feasibility.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/pilot_integration.py
"""
from pathlib import Path

from eda import run as eda
from link_candidates import run as link

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    output = ROOT / 'output/phase1-overnight/pilot-20260915'
    result = link(output / 'sec.sqlite', output / 'links')
    print({k: result[k] for k in ('n_records', 'matched', 'conflicts')})
    print(eda(output))
