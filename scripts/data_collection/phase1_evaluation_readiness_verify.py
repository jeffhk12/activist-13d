"""Tier: 2. Independently reconcile readiness counts and metadata input coverage.
Inputs: frozen readiness manifest, source inventory and calendar; no returns.
Outputs: receipts/verification.json. Formula: input=merged+scheduled+excluded.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_evaluation_readiness_verify.py
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/phase1-baseline/20260924-evaluation-readiness-v1'
BASE = ROOT / 'research/runs/phase1-baseline'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for path, receipt in manifest['inputs'].items():
        assert digest(ROOT / path) == receipt['sha256'], path
    for path, sha in manifest['outputs'].items():
        assert digest(OUT / path) == sha, path
    selection = json.loads((OUT / 'candidate-selection.json').read_text())
    protected = set(json.loads((BASE / '20260924-development-v4/human-review-protection.json').read_text())['issuers'])
    assert len(selection['selected']) + len(selection['exclusions']) == 17795
    reconciliations = {}
    for branch, horizons in selection['plans'].items():
        for horizon, plan in horizons.items():
            events = plan['events']
            merged = sum(len(e['accessions']) - 1 for e in events)
            assert plan['counts']['before_schedule'] == len(events) + merged + len(plan['exclusions'])
            assert all(e['issuer'] not in protected and e['exit'] <= '2026-09-23' for e in events)
            assert all(len(e['days']) == int(horizon) and e['exit'] == e['days'][-1] for e in events)
            reconciliations[branch + '/' + horizon] = dict(input_filings=plan['counts']['before_schedule'],
                scheduled_events=len(events), simultaneous_filings_merged=merged,
                excluded_filings=len(plan['exclusions']))
    registry_path = BASE / '20260924-feasibility-v2/event-candidates.jsonl'
    registry = [json.loads(line) for line in registry_path.read_text().splitlines()]
    eligible_path = BASE / '20260924-universe-rebuild-v3/eligibility.jsonl'
    eligibility = [json.loads(line) for line in eligible_path.read_text().splitlines()]
    inventory_path = BASE / '20260924-feasibility-v2/source-inventory.json'
    inventory = json.loads(inventory_path.read_text())
    request_dates = sorted({v['request']['params']['dlycaldt'] for k, v in inventory.items()
                            if '/crsp.dsf_v2/' in k and 'dlycaldt' in v['request']['params']})
    membership_path = BASE / '20260924-russell-inputs-v1/membership-receipt.json'
    membership = json.loads(membership_path.read_text())
    daily_missing = {}
    for b, horizons in selection['plans'].items():
        for h, p in horizons.items():
            required = {d for e in p['events'] for d in e['days']}
            absent = sorted(required - set(request_dates))
            daily_missing[b + '/' + h] = {'required_event_session_dates': len(required),
                'absent_from_frozen_feasibility_source_inventory': len(absent),
                'first_absent': min(absent, default=None), 'last_absent': max(absent, default=None)}
    focus_ids = {e['accession'] for e in selection['selected'] if e['focused']}
    selected_focused = [r for r in registry if r['accession'] in focus_ids]
    focused_exclusions = Counter(r['reason'] for r in selection['exclusions']
                                if next((x['focused_activist_subset'] for x in registry if x['accession'] == r['accession']), False))
    receipt = {
        'all_frozen_input_and_output_hashes_match': True,
        'input_count_reconciles': True, 'schedule_reconciliations': reconciliations,
        'parsed_filing_date_min': min(r['filing_date'] for r in eligibility),
        'parsed_filing_date_max': max(r['filing_date'] for r in eligibility),
        'registry_filing_date_max': max(r['filing_date'] for r in registry),
        'candidate_entry_min': min(r['entry'] for r in selection['selected']),
        'candidate_entry_max': max(r['entry'] for r in selection['selected']),
        'registry_by_filing_year': dict(Counter(r['filing_date'][:4] for r in registry)),
        'focused_registry_filings': sum(r['focused_activist_subset'] for r in registry),
        'focused_selected_filings': len(selected_focused),
        'focused_sequential_exclusions': dict(focused_exclusions),
        'source_inventory_daily_request_first': min(request_dates),
        'source_inventory_daily_request_last': max(request_dates),
        'daily_input_inventory_check': daily_missing,
        'daily_inventory_caveat': 'Request-date presence is not security-row coverage, raw integrity, usable marks, completeness or lack of exposure. No new return rows opened.',
        'historical_membership_snapshot_n': len(membership),
        'historical_membership_first': min(r['date'] for r in membership),
        'historical_membership_last': max(r['date'] for r in membership),
        'historical_membership_count_discrepancies': sum(r['count_discrepancy'] for r in membership),
        'inputs': {str(p.relative_to(ROOT)): digest(p) for p in [inventory_path, membership_path, Path(__file__)]},
    }
    path = OUT / 'receipts/verification.json'
    path.parent.mkdir(exist_ok=True)
    raw = json.dumps(receipt, sort_keys=True, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == raw
    else:
        path.write_text(raw)
    print(raw)


if __name__ == '__main__':
    main()
