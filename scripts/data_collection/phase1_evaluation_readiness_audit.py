"""Outcome-blind Phase 1 exposure inventory and mature candidate readiness audit.

Inputs: existing metadata/selection/protection/preview manifests; path inventory.
Outputs: hashes, metadata-only schedules, sequential refusals, NOT READY gates.
Identity: input filings = selected filings + sequentially excluded filings.
Tier: 2. Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
.venv/bin/python scripts/data_collection/phase1_evaluation_readiness_audit.py
No raw return panels, future candidate outcomes, network, or human labels opened.
"""
import hashlib
import json
import platform
import re
from collections import Counter
from pathlib import Path

from activist13d.phase1_evaluation_readiness_selection import candidates, readiness

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/phase1-baseline/20260924-evaluation-readiness-v1'
BASE = Path('research/runs/phase1-baseline')
INPUTS = {}


def read(path, lines=False):
    path = ROOT / path
    raw = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)


def write(name, obj):
    raw = (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    path = OUT / name
    if path.exists() and path.read_bytes() != raw:
        raise ValueError(f'Frozen result differs: {path}; use a new version')
    path.write_bytes(raw)


def walk_events(obj):
    if isinstance(obj, dict):
        if {'issuer', 'entry', 'accession'} <= obj.keys():
            yield obj
        for value in obj.values():
            yield from walk_events(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_events(value)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    registry = read(BASE / '20260924-feasibility-v2/event-candidates.jsonl', lines=True)
    eligibility = {r['accession']: r for r in read(BASE / '20260924-universe-rebuild-v3/eligibility.jsonl', lines=True)}
    sessions = read(BASE / '20260924-feasibility-v2/entry-calendar.json')
    protection = read(BASE / '20260924-development-v4/human-review-protection.json')
    protected = set(protection['issuers'])
    assert len(protected) == 207
    exposed = set()
    dev_sources = []
    for path in sorted((ROOT / BASE).glob('*/selection.json')):
        if any(token in path.parent.name for token in ('development-v', 'rebuilt-inputs-v')):
            events = list(walk_events(read(path)))
            issuers = {e['issuer'] for e in events}
            exposed |= issuers
            dev_sources.append({'path': str(path.relative_to(ROOT)), 'issuer_count': len(issuers),
                                'min_entry': min((e['entry'] for e in events), default=None),
                                'max_entry': max((e['entry'] for e in events), default=None),
                                'basis': 'conservative selected/excluded-event identity union, not outcome values'})
    development_issuers = set(exposed)

    preview_manifest = read('review/archive/13d-price-preview-20260922/manifest.json')
    preview_records = read('review/archive/13d-structured-review-20260922/review-inputs.json')
    preview_accessions = {r['accession'] for r in preview_records}
    assert len(preview_accessions) == preview_manifest['n_filings'] == 10
    preview_issuers = {i for a in preview_accessions for i in eligibility[a]['issuers']}
    exposed |= preview_issuers
    preview_identifiers = read('review/archive/13d-price-preview-20260922/identifier-candidates.json')
    exposed_permnos = {r['permno'] for r in preview_identifiers}
    # Previously printed WRDS development smoke observation, documented in README.
    exposed_permnos.add(14593)
    unions = read('research/runs/hfr-all-managers/20260924-v1/accession-unions.json')
    focus = set(unions['manager_has_activist']) | set(unions['supplement'])
    broad = set(unions['previous_hfr_event_driven_screen']) | set(unions['supplement'])
    assert all(r['focused_activist_subset'] == (r['accession'] in focus) for r in registry)
    assert all(r['broad_manager_subset'] == (r['accession'] in broad) for r in registry)
    result = candidates(registry, eligibility, sessions, protected, exposed, exposed_permnos)
    write('candidate-selection.json', result)
    temporal = candidates(registry, eligibility, sessions, protected, set(), set())

    # Inventory every research/review output path, but do not open arbitrary outcomes.
    # Freeze the first inventory; newly written parallel-agent files are outside this snapshot.
    inventory_path = OUT / 'path-inventory.json'
    if inventory_path.exists():
        inventory = json.loads(inventory_path.read_text())
    else:
        inventory = []
        for folder in ('research', 'review', 'maintenance'):
            for path in sorted((ROOT / folder).rglob('*')):
                if not path.is_file() or OUT in path.parents:
                    continue
                rel = str(path.relative_to(ROOT))
                category = ('human_material_not_opened' if rel.startswith(('review/current/', 'review/drafts/human-first-52/'))
                            else 'possible_outcome_or_preview_path' if re.search(r'price|return|outcome|portfolio|preview', rel, re.I)
                            else 'other_research_path')
                inventory.append({'path': rel, 'bytes': path.stat().st_size, 'category': category})
        write('path-inventory.json', inventory)
    summary = {
        'status': 'NOT READY', 'asof_completed_session': '2026-09-23',
        'candidate_entry_start': '2024-01-01', 'input_filings': len(registry),
        'eligibility_records': len(eligibility), 'eligibility_joined': sum(r['accession'] in eligibility for r in registry),
        'protected_issuers': len(protected), 'prior_selection_issuer_union': len(development_issuers),
        'preview_issuers': sorted(preview_issuers), 'preview_accessions': sorted(preview_accessions),
        'preview_filing_dates': sorted(eligibility[a]['filing_date'] for a in preview_accessions),
        'preview_issuers_already_protected': len(preview_issuers & protected),
        'conservative_exposed_issuer_union': len(exposed), 'quarantined_permnos': sorted(exposed_permnos),
        "date_only_protected_screen_plans": {b: {h: p["counts"] for h, p in hs.items()} for b, hs in temporal["plans"].items()},
        "date_only_protected_screen_base_filings": len(temporal["selected"]),

        'base_selected_filings': len(result['selected']), 'base_exclusions': result['exclusion_counts'],
        'plans': {b: {h: p['counts'] for h, p in hs.items()} for b, hs in result['plans'].items()},
        'by_entry_year': dict(Counter(e['entry'][:4] for e in result['selected'])),
        'mature_entry_cutoffs': {str(h): [s for s in sessions if s <= '2026-09-23'][-h] for h in (63,126,252)},
        'inventory_counts': dict(Counter(r['category'] for r in inventory)),
        'development_sources': dev_sources,
        'outcomes_opened': False, 'certified_fresh_samples': 0,
        'interpretation': 'Calendar-mature historical candidates, not a certified untouched evaluation sample. No result on investment merit.',
    }
    write('summary.json', summary)
    gates = {
        'exposure_provenance': False, 'protocol_and_code_frozen': False,
        'identity_eligibility': False, 'valuation_policy': False,
        'benchmark_inputs': False, 'price_cash_inputs': False,
        'protected_issuer_integrity': True, 'calendar_maturity': True, 'selection_frozen': False,
    }
    write('gates.json', {'gates': gates, **readiness(gates),
                         'reason': 'Metadata candidate manifest is not a production freeze or authorization to open outcomes.'})
    for path in [Path(__file__), ROOT / 'src/activist13d/phase1_evaluation_readiness_selection.py',
                 ROOT / 'tests/test_phase1_evaluation_readiness_selection.py',
                 ROOT / 'research/protocol/phase1-evaluation-candidate-v1.md']:
        raw = path.read_bytes()
        INPUTS[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    write('manifest.json', {'inputs': INPUTS, 'python': platform.python_version(),
                            'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(OUT.glob('*.json')) if p.name != 'manifest.json'},
                            'access_boundary': 'Explicit allowlist metadata only; candidate future returns never loaded.'})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
