"""Tier: 1. Add authorized supplemental activists and count accession unions.

Inputs: local SEC metadata and frozen dated HFR candidate screen.
Outputs: supplemental universe, matched metadata, exclusions, union counts, HTML.
Identity: each filing counted once by accession; explicit reporting-entity CIK/name
pairs replace broad token discovery. CIKs observed in metadata are not independent
proof of historical manager/fund relationships. No issuer/body-name matches.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/include_supplemental_activists.py
"""
import html
import json
import sqlite3
from collections import defaultdict
from contextlib import closing

from ingest_hfr_quarterly import OUT as HFR
from ingest_hfr_quarterly import ROOT, digest, encode, freeze
from screen_hfr_quarterly import DB, norm

OUT = ROOT / 'research/runs/investor-identity/20260924-supplemental-v1'
# User-selected supplement, 2026-09-24. Reporting entities observed locally.
UNIVERSE = {
    'Starboard Value': [('0001517137', 'Starboard Value LP')],
    'Pershing Square': [('0001336528', 'Pershing Square Capital Management, L.P.'),
                        ('0002026053', 'PERSHING SQUARE INC.')],
    'Sachem Head': [('0001582090', 'Sachem Head Capital Management LP')],
    'TCI': [('0001647251', 'TCI Fund Management Ltd')],
    'ValueAct': [('0001464912', 'ValueAct Capital Master Fund, L.P.')],
    'Icahn-related entities': [('0000921669', 'ICAHN CARL C'),
                               ('0001412093', 'ICAHN CAPITAL LP'),
                               ('0001034563', 'ICAHN ENTERPRISES HOLDINGS L.P.')],
    'Elliott': [('0000904495', 'ELLIOTT ASSOCIATES, L.P.'),
                ('0000937611', 'ELLIOTT INTERNATIONAL, L.P.'),
                ('0001791786', 'Elliott Investment Management L.P.')],
}
TOKENS = ['starboard', 'pershing square', 'valueact', 'tci fund', 'sachem head', 'icahn', 'elliott']


def count(ids, records, denominator):
    initials = sum(records[a]['form'] == '13D' for a in ids)
    amendments = sum(records[a]['form'] == '13D/A' for a in ids)
    assert initials + amendments == len(ids)
    return {'initials': initials, 'amendments': amendments, 'unique_filings': len(ids),
            'percent_of_local_13d_records': 100 * len(ids) / denominator}


def build():
    # Hand-computed union/count pins: A is shared; A/B/C are three, not four.
    demo = {'A': {'form': '13D'}, 'B': {'form': '13D/A'}, 'C': {'form': '13D/A'}}
    assert len({'A', 'B'} | {'A', 'C'}) == 3
    assert count(set(demo), demo, 6)['percent_of_local_13d_records'] == 50
    assert count(set(demo), demo, 6)['initials'] == 1
    index = {(cik, norm(name)): manager for manager, pairs in UNIVERSE.items() for cik, name in pairs}
    by_manager = defaultdict(set)
    records, evidence, exclusions = {}, [], []
    with closing(sqlite3.connect(f'file:{DB}?mode=ro', uri=True)) as db:
        for raw, in db.execute('SELECT record_json FROM records ORDER BY accession'):
            r = json.loads(raw)
            if r.get('form') not in {'13D', '13D/A'}:
                continue
            accession = r['accession']
            assert accession not in records, 'Duplicate accession in source database'
            records[accession] = r
            matches = []
            for f in r.get('filers', []):
                name = f.get('name') or ''
                manager = index.get((f.get('cik'), norm(name)))
                if manager:
                    by_manager[manager].add(accession)
                    matches.append({'manager': manager, 'reporting_entity': f})
                elif any(t in name.lower() for t in TOKENS):
                    exclusions.append({'accession': accession, 'reporting_entity': f,
                                       'reason': 'Outside explicit supplemental entity set; token alone insufficient'})
            if matches:
                evidence.append({**{k: r.get(k) for k in ['accession', 'form', 'filing_date', 'subjects', 'source_path', 'source_sha256']},
                                 'matches': matches, 'status': 'metadata_entity_candidate_relationship_verification_pending'})
    denominator = len(records)
    supplement = set().union(*by_manager.values())
    six = set().union(*(ids for name, ids in by_manager.items() if name != 'Elliott'))
    hfr = json.loads((HFR / 'sec-screen/candidates.json').read_text())
    ed = {r['accession'] for r in hfr}
    activist = {r['accession'] for r in hfr if any(m['activist_in_selected_snapshot'] for m in r['matches'])}
    assert activist <= ed <= records.keys()
    sets = {'six_new_managers': six, 'supplement_including_elliott': supplement,
            'hfr_dated_event_driven': ed, 'hfr_dated_activist': activist,
            'hfr_event_driven_plus_supplement': ed | supplement,
            'hfr_activist_plus_supplement': activist | supplement,
            'overlap_hfr_event_driven_supplement': ed & supplement,
            'overlap_hfr_activist_supplement': activist & supplement}
    summary = {'denominator': denominator,
               'by_manager': {name: count(by_manager[name], records, denominator) for name in UNIVERSE},
               'unions': {name: count(ids, records, denominator) for name, ids in sets.items()},
               'cross_supplement_manager_overlap_excess': sum(map(len, by_manager.values())) - len(supplement),
               'excluded_token_candidate_accessions': len({r['accession'] for r in exclusions}),
               'source_hashes': {'sec_database': digest(DB), 'hfr_candidates': digest(HFR / 'sec-screen/candidates.json'),
                                 'script': digest(__import__('pathlib').Path(__file__))}}
    freeze(OUT / 'universe.json', encode({'selection': 'User-authorized external supplement, 2026-09-24',
          'historical_hfr_membership_implied': False, 'entities': UNIVERSE,
          'status': 'Explicit metadata entities; manager relationships and history pending verification'}))
    freeze(OUT / 'summary.json', encode(summary))
    freeze(OUT / 'candidates.json', encode(evidence))
    freeze(OUT / 'excluded-token-hits.json', encode(exclusions))
    freeze(OUT / 'accession-unions.json', encode({name: sorted(ids) for name, ids in sets.items()}))
    rows = ''.join(f'<tr><td>{html.escape(name)}</td><td>{v["initials"]}</td><td>{v["amendments"]}</td><td>{v["unique_filings"]}</td></tr>' for name, v in summary['by_manager'].items())
    totals = ''.join(f'<li>{html.escape(name)}: {v["unique_filings"]:,} unique filings ({v["percent_of_local_13d_records"]:.2f}%)</li>' for name, v in summary['unions'].items())
    freeze(OUT / 'index.html', f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Supplemental activist universe</title><style>body{{font:17px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#203448}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}table{{border-collapse:collapse;width:100%}}</style><h1>Supplemental activist universe</h1><p>User-selected external supplement, 24 September 2026. Denominator: {denominator:,} local 13D/13D-A records. Counts deduplicate accession IDs.</p><table><tr><th>Manager group</th><th>Initials</th><th>Amendments</th><th>Total</th></tr>{rows}</table><ul>{totals}</ul><p>These are metadata entity candidates, not verified campaigns or complete manager histories. Explicit reporting-entity CIK/name pairs exclude incidental names such as Icahn School of Medicine and Starboard Enterprises. Icahn and Elliott include multiple related-entity candidates; relationships require dated evidence. Supplemental selection is external and retrospective, not historical HFR membership. HFR counts use earlier delivery-date proxies and start in 2018; the supplement searches all available local filing dates. Combined counts are discovery coverage, not a time-consistent backtest universe.</p><p><a href="universe.json">Selected entities</a> · <a href="candidates.json">Filing evidence</a> · <a href="summary.json">Count calculations</a> · <a href="accession-unions.json">Deduplicated accession lists</a> · <a href="excluded-token-hits.json">Excluded broad-name hits</a> · <a href="../../../../START-HERE.html">Project home</a></p></html>''')
    print(encode(summary))


if __name__ == '__main__':
    build()
