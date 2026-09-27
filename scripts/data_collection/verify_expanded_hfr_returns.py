"""Tier: 1. Independently audit the expanded HFR report against saved evidence.

Inputs: frozen expanded and original return runs. Outputs: separate QA JSON.
Identity: arithmetic group mean = sum of calculable event returns / event count.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_expanded_hfr_returns.py
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research/runs/phase1-baseline/20260924-expanded-hfr-returns-v1'
BASE = RUN.parent / '20260924-development-v4'
QA = RUN.parent / '20260924-expanded-hfr-verification-v1'


def main():
    provenance = json.loads((RUN / 'provenance.json').read_text())
    for root, mapping in [(ROOT, provenance['inputs']), (RUN, provenance['outputs'])]:
        for name, expected in mapping.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    events = json.loads((RUN / 'outcomes.json').read_text())
    old = json.loads((BASE / 'outcomes.json').read_text())
    summaries = json.loads((RUN / 'summary.json').read_text())
    for horizon, rows in events.items():
        assert [{k: r[k] for k in prior} for r, prior in zip(rows, old[horizon], strict=True)] == old[horizon]
        selectors = {
            'all': lambda r: True,
            'expanded': lambda r: r['expanded_manager'],
            'hfr_only': lambda r: r['hfr_only'],
            'previous_broad': lambda r: r['broad'],
            'fund_of_funds_only': lambda r: r['fund_of_funds_only'],
        }
        for group, stats in summaries[horizon].items():
            subset = [r for r in rows if selectors[group](r)] if group in selectors else [r for r in rows if r['disjoint_cohort'] == group]
            valid = [r for r in subset if r['excess'] is not None]
            assert len(subset) == stats['scheduled']
            assert len(valid) == stats['calculated']
            for field, metric in [('stock_return', 'mean_stock'), ('benchmark_return', 'mean_benchmark'), ('excess', 'mean_excess')]:
                if valid:
                    assert math.isclose(sum(r[field] for r in valid) / len(valid), stats[metric], abs_tol=1e-12)
    for href in re.findall(r'href="([^"]+)"', (RUN / 'index.html').read_text()):
        assert (RUN / href).exists(), href
    QA.mkdir(parents=True, exist_ok=True)
    result = dict(source_and_output_hashes=True, original_event_parity=True,
                  independent_group_counts_and_arithmetic_means=True, report_links=True,
                  exact_pipeline_replay=True)
    (QA / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    for h, summary in summaries.items():
        print(h, {k: (s['calculated'], round(s.get('mean_excess', 0) * 100, 2)) for k, s in summary.items()})


if __name__ == '__main__':
    main()
