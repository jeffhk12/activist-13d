"""Tier: 2. Match every HFR strategy to the local 13D/13D-A archive.

Inputs: 35 frozen HFR snapshots, raw archive hash, SEC SQLite, old ED/supplement sets.
Outputs: dated all-manager observations, name candidates, unique accession unions,
strategy/manager counts and searchable HTML. No returns or NLP labels.
Identity: select latest whole snapshot strictly before filing date; no older
carryforward or later backfill. Count each accession once per cohort. Strategies
describe a manager's HFR offerings, not the purpose of a particular SEC filing.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/screen_all_hfr.py
"""
import html
import json
import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.hfr_all_match import group_managers, index_managers, match_name, prior_index
from activist13d.local_paths import resolve_project_path

SOURCE = ROOT / 'research/runs/hfr-quarterly/20260924-v1'
OUT = ROOT / 'research/runs/hfr-all-managers/20260924-v1'
DB = ROOT / 'research/runs/phase1-overnight/full-20260915/sec.sqlite'
SUP = ROOT / 'research/runs/investor-identity/20260924-supplemental-v1/accession-unions.json'
STYLE = '''body{font:17px/1.6 system-ui;color:#24384a;background:#f4f6f8;margin:0}main{max-width:1250px;margin:30px auto;padding:0 24px}section{background:white;padding:24px;margin:22px 0;border:1px solid #dce3e8}h1{line-height:1.25}h2{font-size:23px}a{color:#155d93}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}.scroll{overflow:auto}th{background:#eaf1f6}input{font:inherit;padding:9px;width:90%}li{margin:8px 0}'''


def page(title, body):
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style></head><body><main><nav><a href="../../../../START-HERE.html">Project home</a> · <a href="index.html">Summary</a> · <a href="managers.html">Managers</a> · <a href="filings.html">Filings</a></nav><h1>{html.escape(title)}</h1>{body}</main></body></html>'


def cells(values):
    return ''.join(f'<td>{html.escape(str(v))}</td>' for v in values)


def main():
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    assert digest(resolve_project_path(manifest['raw_archive'], ROOT)) == manifest['archive_sha256']
    snapshots = sorted(manifest['snapshots'], key=lambda s: s['delivery_date_proxy'])
    dates = [s['delivery_date_proxy'] for s in snapshots]
    assert len(dates) == len(set(dates)) == 35
    managers, by_quarter, indexes, source_hashes = [], {}, {}, {}
    missing_ids, row_total, strategy_rows = 0, 0, Counter()
    for snapshot in snapshots:
        q = snapshot['quarter']
        path = SOURCE / 'snapshots' / f'{q}.json'
        raw = json.loads(path.read_text())
        assert raw['metadata'] == snapshot
        assert len(raw['funds']) == snapshot['all_fund_rows']
        row_total += len(raw['funds'])
        missing_ids += sum(not r['fields'].get('Firm_ID') for r in raw['funds'])
        strategy_rows.update(r['fields'].get('Main_Strategy') or '(missing)' for r in raw['funds'])
        current = group_managers(raw['funds'], q)
        managers.extend(current)
        by_quarter[q] = {m['firm_id']: m for m in current}
        indexes[q] = index_managers(current)
        source_hashes[str(path.relative_to(ROOT))] = digest(path)
    count = Counter()
    forms, candidates = {}, []
    firm_accessions, firm_ciks = defaultdict(set), defaultdict(set)
    strategy_accessions = defaultdict(set)
    cohorts = defaultdict(set)
    with closing(sqlite3.connect(f'file:{DB}?mode=ro', uri=True)) as db:
        for raw, in db.execute('SELECT record_json FROM records ORDER BY accession'):
            record = json.loads(raw)
            if record.get('form') not in {'13D', '13D/A'}:
                continue
            accession, day = record['accession'], record.get('filing_date') or ''
            assert accession not in forms
            forms[accession] = record['form']
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
                count['invalid_filing_date'] += 1
                continue
            i = prior_index(dates, day)
            if i < 0:
                count['no_prior_snapshot'] += 1
                continue
            count['with_prior_snapshot'] += 1
            snapshot = snapshots[i]
            q = snapshot['quarter']
            hits = []
            for filer in record.get('filers', []):
                name = filer.get('name')
                if not name:
                    continue
                for firm, rule in match_name(indexes[q], name).items():
                    manager = by_quarter[q][firm]
                    hits.append(dict(firm_id=firm, hfr_names=manager['names'], filer_name=name,
                        cik=filer.get('cik'), rule=rule, hfr_fund_rows=manager['fund_rows'],
                        strategies=manager['strategies'], substrategies=manager['substrategies'],
                        manager_has_event_driven=manager['event_driven'],
                        manager_has_activist=manager['activist'],
                        manager_fund_of_funds_only=manager['fund_of_funds_only']))
                    firm_accessions[firm].add(accession)
                    if filer.get('cik'):
                        firm_ciks[firm].add(filer['cik'])
                    for strategy in manager['strategies']:
                        strategy_accessions[strategy].add(accession)
            if not hits:
                continue
            cohorts['all_hfr'].add(accession)
            if any(h['manager_has_event_driven'] for h in hits):
                cohorts['manager_has_event_driven'].add(accession)
            else:
                cohorts['no_event_driven_offering_in_matched_managers'].add(accession)
            if any(h['manager_has_activist'] for h in hits):
                cohorts['manager_has_activist'].add(accession)
            if all(h['manager_fund_of_funds_only'] for h in hits):
                cohorts['only_fund_of_funds_managers_matched'].add(accession)
            if len({h['firm_id'] for h in hits}) > 1:
                cohorts['cross_manager_ambiguous'].add(accession)
            accepted = record.get('acceptance_datetime_et')
            timing_flag = bool(accepted and dates[i] >= accepted[:10])
            if timing_flag:
                cohorts['snapshot_not_strictly_before_acceptance_date'].add(accession)
            candidates.append(dict(accession=accession, form=record['form'], filing_date=day,
                acceptance_datetime_et=accepted, quarter=q, delivery_date_proxy=dates[i],
                vendor_datestamp=snapshot['vendor_datestamp'], source_path=record.get('source_path'),
                source_sha256=record.get('source_sha256'), subjects=record.get('subjects'),
                snapshot_not_strictly_before_acceptance_date=timing_flag,
                identity_status='name_candidate_unverified', matches=hits))
    old = json.loads((SOURCE / 'sec-screen/candidates.json').read_text())
    old_ids = {r['accession'] for r in old}
    # Expanding the name universe must retain every previously matched accession.
    assert old_ids <= cohorts['all_hfr']
    supplemental = json.loads(SUP.read_text())
    supplement = set(supplemental['supplement_including_elliott'])
    assert supplement <= forms.keys()
    cohorts['previous_hfr_event_driven_screen'] = old_ids
    cohorts['new_hfr_links_beyond_previous_screen'] = cohorts['all_hfr'] - old_ids
    cohorts['supplement'] = supplement
    cohorts['hfr_supplement_overlap'] = cohorts['all_hfr'] & supplement
    cohorts['all_hfr_plus_supplement'] = cohorts['all_hfr'] | supplement
    previous_combined = set(supplemental['hfr_event_driven_plus_supplement'])
    assert previous_combined <= cohorts['all_hfr_plus_supplement']
    cohorts['new_links_beyond_previous_combined'] = cohorts['all_hfr_plus_supplement'] - previous_combined
    cohorts['other_or_unresolved_after_expansion'] = forms.keys() - cohorts['all_hfr_plus_supplement']
    def totals(ids):
        initials = sum(forms[a] == '13D' for a in ids)
        return dict(filings=len(ids), initials=initials, amendments=len(ids) - initials)
    all_ids = {m['firm_id'] for m in managers}
    latest_ids = set(by_quarter[snapshots[-1]['quarter']])
    manager_summary = []
    histories = defaultdict(list)
    for manager in managers:
        histories[manager['firm_id']].append(manager)
    for firm in sorted(all_ids):
        observations = histories[firm]
        manager_summary.append(dict(firm_id=firm,
            names=sorted({n for m in observations for n in m['names']}),
            strategies_ever_observed=sorted({s for m in observations for s in m['strategies']}),
            snapshots_observed=len(observations), in_latest_snapshot=firm in latest_ids,
            matched_filer_ciks=sorted(firm_ciks[firm]), **totals(firm_accessions[firm])))
    summary = dict(archive_records=len(forms), prior_snapshot_counts=dict(count), snapshot_count=35,
        historical_firm_ids=len(all_ids), latest_firm_ids=len(latest_ids), matched_firm_ids=len([m for m in manager_summary if m['filings']]),
        fund_observations=row_total, observations_missing_firm_id=missing_ids,
        strategy_fund_observations=dict(sorted(strategy_rows.items())),
        cohorts={k: totals(v) for k, v in sorted(cohorts.items())},
        strategy_counts={k: totals(v) for k, v in sorted(strategy_accessions.items())},
        candidate_rate_among_prior_snapshot_records=len(cohorts['all_hfr']) / count['with_prior_snapshot'],
        candidate_rate_among_all_records=len(cohorts['all_hfr']) / len(forms),
        verified_economic_manager_count=None, returns_recalculated=False)
    assert len(forms) == 75631 and len(old_ids) == 1750
    assert len(cohorts['all_hfr_plus_supplement']) + len(cohorts['other_or_unresolved_after_expansion']) == len(forms)
    freeze(OUT / 'manager-observations.json', encode(managers))
    freeze(OUT / 'manager-summary.json', encode(manager_summary))
    freeze(OUT / 'candidates.json', encode(candidates))
    freeze(OUT / 'accession-unions.json', encode({k: sorted(v) for k, v in sorted(cohorts.items())}))
    freeze(OUT / 'summary.json', encode(summary))
    freeze(OUT / 'source-inventory.json', encode(dict(snapshot_hashes=source_hashes,
        manifest_sha256=digest(SOURCE / 'manifest.json'), raw_archive_sha256=manifest['archive_sha256'],
        sec_database_sha256=digest(DB), supplemental_unions_sha256=digest(SUP))))
    report(summary, manager_summary, candidates)
    for path in [Path(__file__), ROOT / 'src/activist13d/hfr_all_match.py', ROOT / 'tests/test_hfr_all_match.py',
                 ROOT / 'scripts/data_collection/run_phase1_development.py', ROOT / 'src/activist13d/local_paths.py']:
        freeze(OUT / 'code' / path.name, path.read_bytes())
    freeze(OUT / 'provenance.json', encode({str(p.relative_to(OUT)): digest(p)
        for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'provenance.json'}))
    print(encode({k: v for k, v in summary.items() if k not in {'strategy_counts', 'strategy_fund_observations'}}))


def report(summary, managers, candidates):
    names = {'previous_hfr_event_driven_screen': 'Previous HFR Event-Driven screen',
             'all_hfr': 'Expanded HFR: all strategies',
             'new_hfr_links_beyond_previous_screen': 'New HFR links beyond the previous screen',
             'all_hfr_plus_supplement': 'All HFR plus the seven supplemental groups',
             'new_links_beyond_previous_combined': 'New links beyond the previous combined universe'}
    rows = ''.join('<tr>' + cells([name, *[summary['cohorts'][key][k] for k in ['filings', 'initials', 'amendments']]]) + '</tr>' for key, name in names.items())
    strategies = ''.join('<tr>' + cells([strategy, s['filings'], s['initials'], s['amendments']]) + '</tr>' for strategy, s in summary['strategy_counts'].items())
    c = summary['cohorts']
    body = f'''<p>24 September 2026 · All 35 supplied HFR snapshots, 2018 Q1–2026 Q3 · Name matches requiring identity review</p>
<section><h2>What changed</h2><p>We now search every HFR strategy category against all {summary['archive_records']:,} local 13D/13D-A records. The historical source contains {summary['historical_firm_ids']:,} distinct HFR manager IDs; {summary['matched_firm_ids']:,} have dated filing-name candidates. Manager IDs are vendor units, not certified unique economic managers.</p><p>The expanded HFR screen links {c['all_hfr']['filings']:,} unique filings, including {c['all_hfr']['initials']:,} initial disclosures. This adds {c['new_hfr_links_beyond_previous_screen']['filings']:,} filings beyond the earlier HFR Event-Driven screen.</p></section>
<section><h2>Filing coverage</h2><div class="scroll"><table><tr><th>Comparison</th><th>Unique filings</th><th>Initial disclosures</th><th>Amendments</th></tr>{rows}</table></div><p>These rows overlap; do not add them. Initials are potential entry observations. Amendments are later updates, not additional independent entry signals. The expanded HFR/supplement union deduplicates {c['hfr_supplement_overlap']['filings']:,} overlapping filings.</p></section>
<section><h2>What this lets us test</h2><p>We can compare following any identified HFR manager with following Event-Driven or activist candidates, and with other/unresolved filers, using the same Russell size benchmark and S&P 500 context. This separates the value of identifying a hedge fund from the narrower value of identifying an activist.</p><p>This run expands identity candidates only. It does not recalculate returns, certify investability, or change the human-labeling packets or protected evaluation outcomes.</p></section>
<section><h2>Coverage by manager strategy offering</h2><div class="scroll"><table><tr><th>HFR main strategy</th><th>Filings</th><th>Initials</th><th>Amendments</th></tr>{strategies}</table></div><p>A manager may offer several strategies, so these rows overlap. A manager offering an activist fund does not make every matched filing an activist investment. Fund-of-funds-only matches are flagged separately ({c.get('only_fund_of_funds_managers_matched', {}).get('filings', 0):,} filings); mixed firms retain all observed strategy categories.</p></section>
<section><h2>How to interpret these matches</h2><p>For each filing we use the latest complete HFR snapshot strictly before its filing date. We do not carry a missing manager forward from an older snapshot or backfill earlier filings using later names. Delivery-folder dates remain unverified historical-availability proxies. {summary['prior_snapshot_counts'].get('no_prior_snapshot', 0):,} records have no earlier supplied snapshot and are outside this dated screen.</p><p>Names match by normalized firm name, firm name without a legal suffix, or normalized fund name. Fuzzy names are not used, and HFR adviser registration numbers are not treated as SEC filer CIKs. {c.get('cross_manager_ambiguous', {}).get('filings', 0):,} filings match more than one HFR manager ID and need review. Missing matches do not prove that a filer is not a hedge fund.</p><p>{summary['observations_missing_firm_id']:,} fund observations have no manager ID and cannot enter the manager-level match. {c.get('snapshot_not_strictly_before_acceptance_date', {}).get('filings', 0):,} candidate filings have a snapshot/acceptance-date timing flag to review before use as investment signals. The seven external manager groups remain a separate retrospectively selected supplement.</p></section>
<section><h2>Review and evidence</h2><p><a href="managers.html">Search the full manager inventory</a> · <a href="filings.html">Search matched filings</a> · <a href="summary.json">Exact counts</a> · <a href="accession-unions.json">Deduplicated cohorts</a> · <a href="candidates.json">Match evidence</a> · <a href="source-inventory.json">Input hashes</a></p></section>'''
    freeze(OUT / 'index.html', page('All HFR managers: expanded filing coverage', body))
    table = []
    for m in sorted(managers, key=lambda r: (-r['filings'], r['firm_id'])):
        table.append('<tr>' + cells([m['firm_id'], '; '.join(m['names']), '; '.join(m['strategies_ever_observed']),
            m['filings'], m['initials'], m['amendments']]) + f'<td><a href="filings.html?firm={html.escape(m["firm_id"], quote=True)}">View candidates</a></td></tr>')
    search = '''<p><input id="search" placeholder="Search names, IDs, strategies or CIKs" aria-label="Search rows"></p><script>document.addEventListener('DOMContentLoaded',()=>{const input=document.getElementById('search');const firm=new URLSearchParams(location.search).get('firm');const filter=()=>{for(const row of document.querySelectorAll('tbody tr'))row.hidden=!(row.textContent.toLowerCase().includes(input.value.toLowerCase())&&(!firm||(row.dataset.firms||'').includes('|'+firm+'|')));};input.addEventListener('input',filter);filter();});</script>'''
    freeze(OUT / 'managers.html', page('HFR manager inventory', '<p>Includes unmatched managers. Names and strategies in this inventory are the historical union for navigation; actual matches use only the selected earlier snapshot.</p>' + search + '<div class="scroll"><table><thead><tr><th>HFR ID</th><th>Names</th><th>Strategies ever observed</th><th>Filings</th><th>Initials</th><th>Amendments</th><th>Evidence</th></tr></thead><tbody>' + ''.join(table) + '</tbody></table></div>'))
    table = []
    for r in candidates:
        firms = sorted({h['firm_id'] for h in r['matches']})
        labels = sorted({f"{h['firm_id']}: {name}" for h in r['matches'] for name in h['hfr_names']})
        filers = sorted({f"{h['filer_name']} ({h['cik']})" for h in r['matches']})
        rules = sorted({h['rule'] for h in r['matches']})
        source = resolve_project_path(r['source_path'], ROOT) if r.get('source_path') else None
        link = f'<a href="{html.escape(str(source), quote=True)}">Source</a>' if source and source.exists() else 'Source unavailable'
        subjects = '; '.join(s.get('name', '') for s in r.get('subjects') or [])
        table.append('<tr data-firms="|' + html.escape('|'.join(firms), quote=True) + '|">' + cells([
            r['filing_date'], r['form'], r['accession'], subjects, '; '.join(labels), '; '.join(filers),
            r['quarter'], '; '.join(rules), 'Multiple manager IDs' if len(firms) > 1 else 'Single manager ID candidate']) + f'<td>{link}</td></tr>')
    freeze(OUT / 'filings.html', page('Matched filing candidates', '<p>Unverified identity candidates. A manager match does not classify investment intent. When opened from a manager link, the list is restricted to that ID; use the Filings navigation link to clear it.</p>' + search + '<div class="scroll"><table><thead><tr><th>Date</th><th>Form</th><th>Accession</th><th>Issuer</th><th>HFR manager</th><th>Reporting person / CIK</th><th>Snapshot</th><th>Match rule</th><th>Ambiguity</th><th>Evidence</th></tr></thead><tbody>' + ''.join(table) + '</tbody></table></div>'))


if __name__ == '__main__':
    main()
