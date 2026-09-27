"""Tier: 1. Screen SEC names against strictly earlier HFR delivery proxies.

Inputs: frozen quarterly manager observations, local read-only SEC SQLite records.
Outputs: candidate evidence and counts in a new dated run; no verified CIK links.
Identity: choose max(snapshot delivery proxy < filing date), then match names
only within that entire snapshot. Never carry a missing manager from an older
snapshot, never backfill a later classification, never sum duplicate accessions.
Delivery dates are unverified historical-availability proxies, not public times.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/screen_hfr_quarterly.py
"""
from __future__ import annotations

import bisect
import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing

from ingest_hfr_quarterly import OUT, ROOT, digest, encode, freeze

DB = ROOT / 'research/runs/phase1-overnight/full-20260915/sec.sqlite'
RESULT = OUT / 'sec-screen'


def norm(name):
    name = re.sub(r'\bL\s*\.\s*L\s*\.\s*C\b', ' LLC', name, flags=re.I)
    name = re.sub(r'\bL\s*\.\s*P\b', ' LP', name, flags=re.I)
    return ' '.join(re.findall(r'[a-z0-9]+', name.lower()))


def base(name):
    words = norm(name).split()
    while words and words[-1] in {'llc', 'lp', 'ltd', 'limited', 'inc', 'incorporated', 'corp', 'corporation', 'llp'}:
        words.pop()
    return ' '.join(words)


def prior_index(dates, filing_date):
    return bisect.bisect_left(dates, filing_date) - 1


def index_managers(managers):
    indexes = [defaultdict(set) for _ in range(3)]
    for m in managers:
        for name in m['names']:
            if norm(name):
                indexes[0][norm(name)].add(m['firm_id'])
            if base(name):
                indexes[1][base(name)].add(m['firm_id'])
        for name in m['fund_names']:
            if norm(name):
                indexes[2][norm(name)].add(m['firm_id'])
    return indexes


def match_name(indexes, name):
    # First matching rule PER MANAGER; preserve cross-manager ambiguity.
    hits = {}
    for index, key, rule in zip(indexes, [norm(name), base(name), norm(name)],
                              ['normalized_firm', 'firm_without_legal_suffix', 'normalized_fund'], strict=True):
        for firm in sorted(index.get(key, set())):
            hits.setdefault(firm, rule)
    return hits


def build():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    managers = json.loads((OUT / 'managers.json').read_text())
    snapshots = sorted(manifest['snapshots'], key=lambda s: s['delivery_date_proxy'])
    dates = [s['delivery_date_proxy'] for s in snapshots]
    if len(set(dates)) != len(dates):
        raise ValueError('Ambiguous duplicate snapshot date')
    by_quarter = {s['quarter']: {m['firm_id']: m for m in managers if m['quarter'] == s['quarter']}
                  for s in snapshots}
    indexes = {q: index_managers(list(ms.values())) for q, ms in by_quarter.items()}
    count = Counter()
    matched, manager_accessions, manager_activist = [], defaultdict(set), defaultdict(set)
    quarter_counts = defaultdict(Counter)
    with closing(sqlite3.connect(f'file:{DB}?mode=ro', uri=True)) as db:
        for (raw,) in db.execute('SELECT record_json FROM records ORDER BY accession'):
            r = json.loads(raw)
            if r.get('form') not in {'13D', '13D/A'}:
                continue
            count['local_13d_records'] += 1
            date = r.get('filing_date') or ''
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
                count['invalid_or_missing_filing_date'] += 1
                continue
            i = prior_index(dates, date)
            if i < 0:
                count['no_strictly_prior_snapshot'] += 1
                continue
            count['records_with_prior_snapshot_proxy'] += 1
            snapshot = snapshots[i]
            q = snapshot['quarter']
            quarter_counts[q]['records_with_prior_snapshot_proxy'] += 1
            hits = []
            for filer in r.get('filers', []):
                name = filer.get('name')
                if not name:
                    continue
                for firm, rule in match_name(indexes[q], name).items():
                    manager = by_quarter[q][firm]
                    activist = 'Activist' in manager['substrategies']
                    hits.append({'firm_id': firm, 'hfr_names': manager['names'],
                                 'filer_name': name, 'cik': filer.get('cik'), 'rule': rule,
                                 'activist_in_selected_snapshot': activist,
                                 'hfr_fund_rows': manager['fund_rows']})
                    manager_accessions[firm].add(r['accession'])
                    if activist:
                        manager_activist[firm].add(r['accession'])
            if not hits:
                continue
            activist = any(h['activist_in_selected_snapshot'] for h in hits)
            count['candidate_accessions'] += 1
            count['candidate_initials' if r['form'] == '13D' else 'candidate_amendments'] += 1
            quarter_counts[q]['candidate_accessions'] += 1
            if activist:
                count['activist_candidate_accessions'] += 1
                count['activist_initials' if r['form'] == '13D' else 'activist_amendments'] += 1
            if len({h['firm_id'] for h in hits}) > 1:
                count['cross_manager_ambiguous_accessions'] += 1
            matched.append({'accession': r['accession'], 'filing_date': date, 'form': r['form'],
                            'subjects': r.get('subjects'), 'source_path': r.get('source_path'),
                            'source_sha256': r.get('source_sha256'), 'quarter': q,
                            'delivery_date_proxy': snapshot['delivery_date_proxy'],
                            'vendor_datestamp': snapshot['vendor_datestamp'],
                            'status': 'name_candidate_unverified_identity_and_availability',
                            'matches': hits})
    count['candidate_firm_ids'] = len(manager_accessions)
    count['activist_candidate_firm_ids'] = len(manager_activist)
    count['verified_identifier_links'] = 0
    summary = dict(count)
    summary['candidate_rate_among_records_with_prior_proxy'] = count['candidate_accessions'] / count['records_with_prior_snapshot_proxy']
    summary['quarter_counts'] = dict(quarter_counts)
    summary['manager_counts'] = [{'firm_id': firm, 'names_across_snapshots': sorted({n for m in managers if m['firm_id'] == firm for n in m['names']}),
                                 'unique_candidate_accessions': len(ids),
                                 'activist_candidate_accessions': len(manager_activist[firm])}
                                for firm, ids in sorted(manager_accessions.items())]
    summary['source_hashes'] = {'sec_database': digest(DB), 'manifest': digest(OUT / 'manifest.json'),
                               'managers': digest(OUT / 'managers.json')}
    freeze(RESULT / 'summary.json', encode(summary))
    freeze(RESULT / 'candidates.json', encode(matched))
    print(encode({k: v for k, v in summary.items() if k not in {'quarter_counts', 'manager_counts'}}))


if __name__ == '__main__':
    build()
