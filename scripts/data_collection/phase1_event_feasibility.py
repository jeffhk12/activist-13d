"""Tier: 1. Audit initial-disclosure identities and entry-price availability.

Inputs: SEC metadata, frozen HFR/supplemental sets, cached CRSP names/index/daily.
Outputs: new event-candidate registry, provenance, attrition and HTML report.
Identity: initial = parsed form 13D and no amendment flag; security candidate =
unique PERMNO matching historical CUSIP within inclusive name dates. Never extend
dates or substitute header/current CUSIP. Opening-date audit proxy = second XNYS
session strictly after acceptance date; conservative full-session delay,
not a frozen execution rule. No future returns or NLP judgments are inspected.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_event_feasibility.py
"""
from __future__ import annotations

import bisect
import gzip
import hashlib
import html
import json
import math
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import exchange_calendars
from ingest_hfr_quarterly import ROOT, digest, encode, freeze
from screen_hfr_quarterly import DB

from activist13d.edgar.deterministic import cusip_check_digit
from activist13d.local_paths import resolve_project_path

RAW = ROOT / 'data/raw/wrds/bulk-v1'
OUT = ROOT / 'research/runs/phase1-baseline/20260924-feasibility-v2'
SUP = ROOT / 'research/runs/investor-identity/20260924-supplemental-v1'
OLD = ROOT / 'research/runs/phase1-overnight/full-20260915/links'
CODE_FIELDS = ['securitytype', 'securitysubtype', 'sharetype', 'issuertype', 'usincflg']


def iso(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        return None


def cusip8(value):
    value = re.sub(r'\s+', '', str(value or '')).upper()
    return value[:8] if re.fullmatch(r'[A-Z0-9]{8}[0-9]?', value) else None


def read_page(path, inventory):
    meta_path = path.with_suffix('.meta.json')
    meta = json.loads(meta_path.read_text())
    raw = gzip.decompress(path.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == meta['sha256'], path
    assert len(raw) == meta['raw_bytes'], path
    assert meta['request']['url'].rstrip('/').endswith('/' + path.parent.name), path
    inventory[str(path.relative_to(ROOT))] = {'sha256_uncompressed': meta['sha256'],
        'sidecar_sha256': digest(meta_path), 'request': meta['request'],
        'retrieved_at': meta.get('retrieved_at')}
    return json.loads(raw), meta


def name_index(inventory):
    index = defaultdict(list)
    for path in sorted((RAW / 'crsp.stocknames_v2').glob('*.json.gz')):
        payload, meta = read_page(path, inventory)
        if meta['request']['method'] != 'GET':
            continue
        for n, row in enumerate(payload.get('results', [])):
            key = cusip8(row.get('cusip'))
            if key:
                index[key].append({'row': row, 'source': str(path.relative_to(ROOT)), 'result_index': n})
    return index


def match_security(cusip, day, index):
    if not cusip8(cusip):
        return {'status': 'missing_or_invalid_cusip', 'permno': None, 'evidence': []}
    if not iso(day):
        return {'status': 'invalid_filing_date', 'permno': None, 'evidence': []}
    candidates = []
    for evidence in index.get(cusip8(cusip), []):
        row = evidence['row']
        start, end = iso(row.get('namedt')), iso(row.get('nameenddt'))
        if not start or not end or not (start <= day <= end):
            continue
        if not str(row.get('permno', '')).isdigit():
            continue
        candidates.append(evidence)
    permnos = sorted({int(x['row']['permno']) for x in candidates})
    return {'status': 'unique_historical_candidate' if len(permnos) == 1 else
            'ambiguous_permno' if permnos else 'no_date_valid_cusip_match',
            'permno': permnos[0] if len(permnos) == 1 else None, 'evidence': candidates}


def security_screen(match):
    if match['permno'] is None:
        return 'unresolved_security'
    codes = {tuple(e['row'].get(k) for k in CODE_FIELDS) for e in match['evidence']}
    if len(codes) != 1:
        return 'conflicting_security_codes'
    typ, sub, share, issuer, us = next(iter(codes))
    if typ == 'FUND':
        return 'fund_vehicle_separate_review'
    if (typ, sub, share) == ('EQTY', 'COM', 'NS') and issuer in {'CORP', 'ACOR'}:
        return 'corporate_common_candidate'
    return 'other_security_separate_review'


def entry_proxy(accepted, sessions):
    try:
        dt = datetime.fromisoformat(accepted)
    except (ValueError, TypeError):
        return None
    i = bisect.bisect_right(sessions, dt.date().isoformat())
    return sessions[i + 1] if i + 1 < len(sessions) else None


def positive(value):
    try:
        number = float(value)
        return math.isfinite(number) and number > 0
    except (TypeError, ValueError):
        return False


def build():
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise RuntimeError('Free disk below project 20 GiB reserve')
    inventory = {}
    index = name_index(inventory)
    sessions = set()
    for path in sorted((RAW / 'crsp.dsi').glob('*.json.gz')):
        payload, meta = read_page(path, inventory)
        if meta['request']['method'] == 'GET':
            sessions.update(r['date'] for r in payload.get('results', []) if iso(r.get('date')))
    cached_sessions = sorted(sessions)
    calendar = exchange_calendars.get_calendar('XNYS', start='2012-01-01', end='2026-10-01')
    sessions = [stamp.date().isoformat() for stamp in calendar.sessions]
    calendar_difference = sorted(set(d for d in cached_sessions if sessions[0] <= d <= cached_sessions[-1])
                                 ^ set(d for d in sessions if d <= cached_sessions[-1]))
    unions = json.loads((SUP / 'accession-unions.json').read_text())
    broad = set(unions['hfr_event_driven_plus_supplement'])
    focused = set(unions['hfr_activist_plus_supplement'])
    supplement = set(unions['supplement_including_elliott'])
    old_summary = json.loads((OLD / 'summary.json').read_text())
    assert digest(OLD / 'candidates.jsonl') == old_summary['candidates_sha256']
    legacy = {r['accession']: r['crsp'] for line in (OLD / 'candidates.jsonl').read_text().splitlines()
              if (r := json.loads(line))['form'] == '13D'}
    records = []
    forms = Counter()
    with closing(sqlite3.connect(f'file:{DB}?mode=ro', uri=True)) as db:
        for raw, in db.execute('SELECT record_json FROM records ORDER BY accession'):
            r = json.loads(raw)
            forms[r.get('form')] += 1
            if r.get('form') != '13D':
                continue
            a = r['accession']
            link = match_security(r.get('cusip'), r.get('filing_date'), index)
            source = resolve_project_path(r['source_path'], ROOT)
            if not source.is_file():
                source_status = 'missing'
            elif source.stat().st_size != r.get('source_bytes') or digest(source) != r.get('source_sha256'):
                source_status = 'hash_or_size_mismatch'
            else:
                source_status = 'hash_and_size_verified'
            accepted = r.get('acceptance_datetime_et')
            proxy = entry_proxy(accepted, sessions)
            parties = sorted({f['cik'] for f in r.get('filers', []) if f.get('cik')})
            issuers = sorted({f['cik'] for f in r.get('subjects', []) if f.get('cik')})
            group = '|'.join(issuers) + '::' + '|'.join(parties) if len(issuers) == 1 and parties else None
            row = {k: r.get(k) for k in ['accession', 'filing_date', 'acceptance_datetime_et', 'cusip',
                    'subjects', 'filers', 'source_path', 'source_sha256', 'source_bytes', 'parser_version', 'flags']}
            normalized = re.sub(r'\s+', '', str(r.get('cusip') or '')).upper()
            check = cusip_check_digit(normalized) if len(normalized) == 9 else None
            row.update(form='13D', amendment_flag_conflict=bool(r.get('is_amendment')),
                       broad_manager_subset=a in broad, focused_activist_subset=a in focused,
                       supplemental_subset=a in supplement,
                       common_hfr_period=bool(r.get('filing_date') and r['filing_date'] > '2018-03-16'),
                       source_status=source_status, cusip_check_digit_valid=check,
                       security_link=link, security_screen=security_screen(link),
                       legacy_permno=legacy.get(a, {}).get('permno'), candidate_group_key=group,
                       issuer_also_filing_party=bool(set(issuers) & set(parties)),
                       entry_date_audit_proxy=proxy, entry_price_status='not_checked',
                       eligibility='not_validated', manager_identity='candidate_only',
                       publication_date_disagrees=bool(accepted and accepted[:10] != r.get('filing_date')))
            records.append(row)
    print(f'Initial registry: {len(records)}; sources and CIZ names checked', flush=True)
    # Candidate group diagnostics are flags, not event merging or eligibility rules.
    group_counts = Counter(r['candidate_group_key'] for r in records if r['candidate_group_key'])
    day_counts = Counter((r['security_link']['permno'], r['filing_date']) for r in records if r['security_link']['permno'])
    requests = defaultdict(list)
    for r in records:
        r['initials_with_same_exact_party_issuer_key'] = group_counts.get(r['candidate_group_key'], 0)
        r['initials_same_security_filing_date'] = day_counts.get((r['security_link']['permno'], r['filing_date']), 0)
        day = r['entry_date_audit_proxy']
        if not day:
            r['entry_price_status'] = 'no_proxy_date_in_entry_calendar'
        elif not r['security_link']['permno']:
            r['entry_price_status'] = 'unresolved_security'
        else:
            requests[day].append(r)
    daily_pages = {}
    for meta_path in sorted((RAW / 'crsp.dsf_v2').glob('*.meta.json')):
        meta = json.loads(meta_path.read_text())
        p = meta.get('request', {}).get('params', {})
        day = p.get('dlycaldt')
        # Production exact-date full slices only; exclude old probes/partitions.
        if day in requests and p == {'dlycaldt': day, 'limit': 50000, 'offset': 0} and meta['request']['method'] == 'GET':
            assert day not in daily_pages, f'Duplicate production date {day}'
            daily_pages[day] = meta_path.with_name(meta_path.name.replace('.meta.json', '.gz'))
    for i, (day, events) in enumerate(sorted(requests.items())):
        path = daily_pages.get(day)
        if not path or not path.exists():
            for r in events:
                r['entry_price_status'] = 'missing_daily_page'
            continue
        payload, meta = read_page(path, inventory)
        rows = payload.get('results', [])
        assert all(row['dlycaldt'] == day for row in rows)
        assert len({row['permno'] for row in rows}) == len(rows)
        assert len(rows) < 50000 and not payload.get('next')
        by_id = {row['permno']: row for row in rows}
        for r in events:
            price = by_id.get(r['security_link']['permno'])
            if price is None:
                r['entry_price_status'] = 'security_absent_on_proxy_date'
                continue
            # Preserve execution-related fields only. Do not inspect future returns.
            r['entry_price_evidence'] = {'source': str(path.relative_to(ROOT)),
                'row': {k: price.get(k) for k in ['permno', 'dlycaldt', 'dlyopen', 'dlyvol',
                     'conditionaltype', 'tradingstatusflg', *CODE_FIELDS]}}
            r['entry_price_status'] = 'positive_open_observed' if positive(price.get('dlyopen')) else 'missing_or_nonpositive_open'
        if i % 100 == 0:
            print(f'Entry-date coverage: {i + 1}/{len(requests)} dates', flush=True)
    def counts(rows):
        n = len(rows)
        matched = sum(r['security_link']['permno'] is not None for r in rows)
        screened = [r for r in rows if r['security_screen'] == 'corporate_common_candidate']
        ready = [r for r in screened if r['source_status'] == 'hash_and_size_verified'
                 and r['entry_price_status'] == 'positive_open_observed'
                 and not r['amendment_flag_conflict'] and not r['publication_date_disagrees']
                 and r['cusip_check_digit_valid'] is not False
                 and r['candidate_group_key'] and not r['issuer_also_filing_party']]
        return {'initial_filings': n, 'source_status': dict(Counter(r['source_status'] for r in rows)),
                'historical_security_candidates': matched, 'match_rate_all_initials': matched/n if n else None,
                'link_status': dict(Counter(r['security_link']['status'] for r in rows)),
                'security_screen': dict(Counter(r['security_screen'] for r in rows)),
                'entry_price_status': dict(Counter(r['entry_price_status'] for r in rows)),
                'corporate_common_with_positive_open': sum(r['entry_price_status'] == 'positive_open_observed' for r in screened),
                'preliminary_data_ready_candidates': len(ready),
                'unique_permnos_in_preliminary_ready': len({r['security_link']['permno'] for r in ready}),
                'legacy_matches': sum(r['legacy_permno'] is not None for r in rows),
                'new_ciz_matches_without_legacy': sum(r['legacy_permno'] is None and r['security_link']['permno'] is not None for r in rows),
                'legacy_ciz_permno_disagreements': sum(r['legacy_permno'] is not None and r['security_link']['permno'] is not None and r['legacy_permno'] != r['security_link']['permno'] for r in rows),
                'bad_cusip_check_digits': sum(r['cusip_check_digit_valid'] is False for r in rows),
                'issuer_is_filing_party': sum(r['issuer_also_filing_party'] for r in rows),
                'repeated_exact_group_initials': sum(r['initials_with_same_exact_party_issuer_key'] > 1 for r in rows)}
    groups = {'all_initials': records,
              'broad_manager_subset': [r for r in records if r['broad_manager_subset']],
              'focused_activist_subset': [r for r in records if r['focused_activist_subset']],
              'other_or_unresolved': [r for r in records if not r['broad_manager_subset']]}
    summary = {'form_counts': dict(forms), 'groups': {k: counts(v) for k, v in groups.items()},
        'by_year': {year: {k: counts([r for r in v if (r['filing_date'] or '')[:4] == year]) for k,v in groups.items()}
                    for year in sorted({(r['filing_date'] or '')[:4] for r in records})},
        'common_hfr_period': {k: counts([r for r in v if r['common_hfr_period']]) for k, v in groups.items()},
        'cached_index_calendar': {'first': cached_sessions[0], 'last': cached_sessions[-1]},
        'entry_calendar': {'name': 'XNYS', 'package': 'exchange-calendars',
            'version': exchange_calendars.__version__, 'first': sessions[0], 'last': sessions[-1],
            'date_differences_against_cached_index_overlap': calendar_difference},
        'entry_dates_checked': len(daily_pages), 'return_values_analyzed': False,
        'final_eligible_event_count': None}
    assert summary['groups']['broad_manager_subset']['initial_filings'] == 404
    assert summary['groups']['focused_activist_subset']['initial_filings'] == 323
    assert len(records) == len({r['accession'] for r in records})
    freeze(OUT / 'event-candidates.jsonl', ''.join(json.dumps(r, sort_keys=True) + '\n' for r in records))
    freeze(OUT / 'summary.json', encode(summary))
    freeze(OUT / 'entry-calendar.json', encode(sessions))
    freeze(OUT / 'source-inventory.json', encode(inventory))
    freeze(OUT / 'provenance.json', encode({'script_sha256': digest(Path(__file__)),
        'sec_database_sha256': digest(DB), 'supplement_union_sha256': digest(SUP / 'accession-unions.json'),
        'legacy_candidates_sha256': digest(OLD / 'candidates.jsonl'),
        'event_candidates_sha256': digest(OUT / 'event-candidates.jsonl'),
        'source_inventory_sha256': digest(OUT / 'source-inventory.json')}))
    table = ''.join(f'<tr><td>{html.escape(k)}</td><td>{v["initial_filings"]:,}</td><td>{v["historical_security_candidates"]:,}</td><td>{v["security_screen"].get("corporate_common_candidate",0):,}</td><td>{v["corporate_common_with_positive_open"]:,}</td><td>{v["preliminary_data_ready_candidates"]:,}</td></tr>' for k,v in summary['groups'].items())
    freeze(OUT / 'index.html', f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 1 event feasibility</title><style>body{{font:17px/1.6 system-ui;max-width:1250px;margin:35px auto;padding:20px;color:#243647}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#145b92}}</style><h1>Phase 1: initial-disclosure feasibility</h1><p>Initial filings only. Identifiers and opening-price coverage; no performance comparison or future return values analyzed.</p><table><tr><th>Discovery group</th><th>Initials</th><th>Historical security links</th><th>Corporate common candidates</th><th>Corporate common + observed open</th><th>Preliminary data-ready candidates</th></tr>{table}</table><p>Groups overlap: focused is within broad; other/unresolved is the complement of broad. Data-ready is a screening count, not validated independent events or confirmed tradability. Identity verification, issuer eligibility, shared/joint filings, re-entry and same-issuer overlaps remain unresolved.</p><p>Corporate-common screen uses EQTY/COM/NS with CORP or ACOR; domestic and foreign flags remain available for review. It does not establish an operating business or exclude every related-party transaction. <a href="https://www.crsp.org/wp-content/uploads/ShareCode.html">CRSP code mapping</a>.</p><p>Entry availability proxy: second XNYS session strictly after acceptance date. XNYS schedule extends through {sessions[-1]}; cached index dates end {cached_sessions[-1]}. No future session is inferred from absent data. This conservative feasibility convention uses exchange-calendars 4.13.2 and awaits the final execution specification. A positive open is not a guarantee of a feasible fill. Daily vendor coverage remains independently unverified.</p><p><a href="summary.json">Detailed counts by year and common period</a> · <a href="event-candidates.jsonl">All candidate evidence</a> · <a href="source-inventory.json">Hash-checked vendor sources</a> · <a href="HANDOFF.md">Findings and next steps</a> · <a href="../../../../START-HERE.html">Project home</a></p></html>''')
    print(encode(summary['groups']))


if __name__ == '__main__':
    build()
