"""Tier: 2. Audit cached daily-request metadata without reading return payloads.
Inputs: WRDS *.meta.json, frozen schedules and feasibility source inventory.
Outputs: supplemental metadata-only cache receipt. Identity: gap=found+absent.
A full-date request has only its exact date and pagination filters; this proves
neither complete pagination nor rows/usable returns. Payload existence is checked
with stat only. Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
.venv/bin/python scripts/data_collection/phase1_evaluation_readiness_cache_metadata.py
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from activist13d.local_paths import resolve_project_path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/phase1-baseline/20260924-evaluation-readiness-v1'


def full_date_request(request):
    table = request.get('url', '').rstrip('/').split('/')[-1]
    date_key = {'crsp.dsf': 'date', 'crsp.dsf_v2': 'dlycaldt'}.get(table)
    params = request.get('params', {})
    if (date_key is None or request.get('method') != 'GET'
            or set(params) - {date_key, 'limit', 'offset'}):
        return None
    date = params.get(date_key)
    if not isinstance(date, str) or len(date) != 10:
        return None
    return table, date


def main():
    # Hand pins: security-specific, range, non-daily and non-GET requests refuse.
    base = {'url': 'https://example.test/crsp.dsf_v2/', 'method': 'GET',
            'params': {'dlycaldt': '2024-01-16', 'limit': 50000, 'offset': 0}}
    assert full_date_request(base) == ('crsp.dsf_v2', '2024-01-16')
    assert full_date_request({**base, 'params': {**base['params'], 'permno': 1}}) is None
    assert full_date_request({**base, 'params': {'dlycaldt__gte': '2024-01-16'}}) is None
    assert full_date_request({**base, 'method': 'POST'}) is None
    assert full_date_request({**base, 'url': 'https://example.test/crsp.stocknames/'}) is None
    assert full_date_request({'url': 'https://example.test/crsp.dsf/', 'method': 'GET',
                              'params': {'date': '2024-01-16', 'offset': 3000}}) == ('crsp.dsf', '2024-01-16')
    selection_path = OUT / 'candidate-selection.json'
    inventory_path = ROOT / 'research/runs/phase1-baseline/20260924-feasibility-v2/source-inventory.json'
    plans = json.loads(selection_path.read_text())['plans']
    inventory = json.loads(inventory_path.read_text())
    present = {v['request']['params']['dlycaldt'] for k, v in inventory.items()
               if '/crsp.dsf_v2/' in k and 'dlycaldt' in v['request']['params']}
    required = {d for e in plans['first_observed']['126']['events'] for d in e['days']}
    gaps = required - present
    assert len(required) == 624 and len(gaps) == 174
    index = defaultdict(list)
    malformed = []
    scanned = []
    for path in sorted((ROOT / 'data/raw/wrds').rglob('*.meta.json')):
        raw = path.read_bytes()
        scanned.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()})
        try:
            meta = json.loads(raw)
        except (ValueError, UnicodeError):
            malformed.append(str(path.relative_to(ROOT)))
            continue
        hit = full_date_request(meta.get('request', {}))
        if hit is None:
            continue
        table, date = hit
        if date not in gaps:
            continue
        cached = meta.get('cache_path')
        if cached:
            payload = resolve_project_path(cached, ROOT)
        else:
            payload = path.with_name(path.name.replace('.meta.json', '.gz'))
        index[date].append({'table': table, 'metadata_path': str(path.relative_to(ROOT)),
            'metadata_sha256': hashlib.sha256(raw).hexdigest(),
            'payload_exists': payload.is_file(), 'payload_bytes_on_disk': payload.stat().st_size if payload.is_file() else None,
            'reported_payload_hash_not_verified': meta.get('sha256'),
            'retrieved_at': meta.get('retrieved_at'),
            'pagination': {k: meta['request']['params'].get(k) for k in ('limit', 'offset')}})
    details = []
    for day in sorted(gaps):
        pages = index[day]
        v2 = any(p['table'] == 'crsp.dsf_v2' and p['payload_exists'] for p in pages)
        any_daily = any(p['payload_exists'] for p in pages)
        details.append({'date': day, 'cached_v2_full_date_request': v2,
                        'cached_any_daily_full_date_request': any_daily, 'metadata': pages})
    found_v2 = sum(r['cached_v2_full_date_request'] for r in details)
    found_any = sum(r['cached_any_daily_full_date_request'] for r in details)
    assert len(details) == found_any + sum(not r['cached_any_daily_full_date_request'] for r in details)
    receipt = {
        'scope': 'All *.meta.json under data/raw/wrds, full-date GET requests for crsp.dsf and crsp.dsf_v2; payloads not opened.',
        'required_primary_event_session_dates': len(required), 'absent_from_feasibility_inventory': len(gaps),
        'gap_dates_with_cached_v2_full_date_request': found_v2,
        'gap_dates_with_cached_any_daily_full_date_request': found_any,
        'gap_dates_with_no_cached_full_date_request': len(gaps) - found_any,
        'no_cached_full_date_request_dates': [r['date'] for r in details if not r['cached_any_daily_full_date_request']],
        'metadata_sidecars_scanned': len(scanned), 'malformed_metadata': malformed,
        'dates': details, 'scanned_metadata_hashes': scanned,
        'inputs': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [selection_path, inventory_path, Path(__file__)]},
        'limits': 'Request metadata and payload existence only. No row, raw integrity, pagination completeness, security coverage, execution marks, or absence of prior exposure certified. Legacy daily requests are not substitutes for the frozen v2 estimator without validation.',
        'checks': {'six_hand_pins': True, 'gap_count_pin': True, 'partition_reconciles': True},
    }
    output = OUT / 'receipts/cache-metadata-supplement.json'
    raw = json.dumps(receipt, sort_keys=True, indent=2) + '\n'
    if output.exists():
        assert output.read_text() == raw
    else:
        output.write_text(raw)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('dates', 'scanned_metadata_hashes')}, indent=2))


if __name__ == '__main__':
    main()
