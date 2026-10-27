"""Audit existing evidence for the October 25 ranking/LLM project scope.

Inputs: frozen 667-row panel, SEC receipts/bundles/raw files, horizon outcomes,
assignments, saved model evaluation, and the original Bloomberg XLSX caches.
Outputs: new dated audit JSON/CSV/source hashes; reports are written separately.
Identity: coverage=finite present values / rows; eligible horizon joins require
exact event identity and one accession, never a first-match or horizon substitution.
Tier: 1. No fitting, network, workbook refresh, source writes, or semantic labels.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/audit_ranking_scope.py --output NEW_RUN [--verify]
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from activist13d.edgar.deterministic import verify_citations  # noqa: E402
from activist13d.local_paths import resolve_project_path  # noqa: E402

FEATURE = 'research/runs/ml-feature-preview/20261012-v1'
FACT = 'research/runs/phase2-overnight/20260924-full-v1'
MARKET = 'research/runs/phase1-baseline/20260924-long-horizon-inputs-v1'
OUTCOME = 'research/runs/phase1-baseline/20260924-long-horizon-analysis-v1'
BBG = Path('/Users/jefflu/Downloads/13D_Bloomberg_9_Field_Extraction.xlsx')
HANDOFF = Path('/Users/jefflu/Downloads/13D_Codex_Handoff_2026-10-25.md')
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def unique_index(rows, key):
    index = {r[key]: r for r in rows}
    if len(index) != len(rows):
        raise ValueError(f'Duplicate {key}; a first-match join is refused')
    return index


def coverage(values):
    values = list(values)
    n = len(values)
    present = sum(finite(v) for v in values)
    return {'rows': n, 'finite': present, 'missing_or_nonnumeric': n - present,
            'coverage_pct': 100 * present / n if n else None,
            'zero': sum(finite(v) and v == 0 for v in values),
            'negative': sum(finite(v) and v < 0 for v in values),
            'nonnumeric_values': dict(Counter(str(v) for v in values if v is not None and not finite(v)))}


def valid_label(row):
    return row.get('status') == 'calculated_common_sample' and finite(row.get('excess'))


def join_horizon(metadata, rows):
    # Exact source identity. Each schedule was independently formed by horizon.
    indexed = defaultdict(list)
    for row in rows:
        indexed[row['input_key']].append(row)
    joined = {}
    statuses = Counter()
    for m in metadata:
        candidates = [r for r in indexed[m['row_id']]
                      if r['accessions'] == [m['accession']]
                      and r['issuer'] == m['issuer'] and r['permno'] == m['permno']
                      and r['entry'] == m['entry']]
        if len(candidates) > 1:
            raise ValueError('Ambiguous exact horizon identity')
        if not candidates:
            statuses['no_exact_single_event_in_this_horizon_schedule'] += 1
        elif not valid_label(candidates[0]):
            statuses[candidates[0]['status']] += 1
        else:
            joined[m['row_id']] = candidates[0]
            statuses['valid_exact_single_event'] += 1
    return joined, dict(statuses)


def cell_value(cell, strings):
    kind = cell.get('t')
    value = cell.find('s:v', NS)
    if kind == 'inlineStr':
        return ''.join(cell.itertext())
    if value is None or value.text is None:
        return None
    if kind == 's':
        return strings[int(value.text)]
    if kind in ('str', 'e'):
        return value.text
    if kind == 'b':
        return value.text == '1'
    try:
        return float(value.text)
    except ValueError:
        return value.text


def workbook_caches(path):
    """Read OOXML caches verbatim; never evaluate formulas or save the workbook."""
    result = {}
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS):
            rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = rels[rid]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            cells = {}
            formulas = {}
            for c in ET.fromstring(z.read(member)).findall('.//s:sheetData/s:row/s:c', NS):
                cells[c.get('r')] = cell_value(c, strings)
                f = c.find('s:f', NS)
                if f is not None:
                    formulas[c.get('r')] = f.text
            result[sheet.get('name')] = {'cells': cells, 'formulas': formulas}
    return result


def checks():
    # Four inputs: two finite (including zero), one absent, one vendor error.
    assert coverage([0, -2, None, '#N/A'])['coverage_pct'] == 50
    assert coverage([0, -2, None, '#N/A'])['negative'] == 1
    assert not finite(True) and not finite(float('nan'))
    try:
        unique_index([{'id': 'a'}, {'id': 'a'}], 'id')
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate join must be refused')
    m = {'row_id': 'a', 'accession': 'a', 'issuer': 'i', 'permno': 1, 'entry': '2018-01-01'}
    r = {'input_key': 'a', 'accessions': ['a'], 'issuer': 'i', 'permno': 1,
         'entry': '2018-01-01', 'excess': 0, 'status': 'calculated_common_sample'}
    assert len(join_horizon([m], [r])[0]) == 1  # Zero is a valid target.
    assert not join_horizon([m], [dict(r, accessions=['a', 'b'])])[0]
    c = ET.fromstring('<c xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" t="e"><v>#N/A</v></c>')
    assert cell_value(c, []) == '#N/A'  # Vendor error remains missing, never zero.


def audit():
    inputs = {}

    def track(path):
        path = path if isinstance(path, Path) else ROOT / path
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        sha = digest(path)
        inputs[key] = {'sha256': sha, 'bytes': path.stat().st_size}
        return path, sha

    def load(path):
        p, _ = track(path)
        return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_text())

    def jsonl(path):
        p, _ = track(path)
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]

    track(Path(__file__))
    track(HANDOFF)
    metadata = jsonl(f'{FEATURE}/row-metadata.jsonl')
    features = jsonl(f'{FEATURE}/features.jsonl')
    targets = jsonl(f'{FEATURE}/targets.jsonl')
    mi, fi, ti = (unique_index(rows, 'row_id') for rows in [metadata, features, targets])
    if set(mi) != set(fi) or set(mi) != set(ti):
        raise ValueError('Panel row identities differ')
    n = len(mi)
    assert n == 667
    load(f'{FEATURE}/provenance.json')
    feature_columns = list(features[0]['features'])
    selection = load(f'{FACT}/selection.json')
    selected = unique_index(selection, 'accession')
    assignments = load(f'{MARKET}/assignments.json')
    outcome = load(f'{OUTCOME}/outcomes.json')
    op = load(f'{OUTCOME}/provenance.json')
    assert digest(ROOT / OUTCOME / 'outcomes.json') == op['outputs']['outcomes.json']
    previous_bbg = load('research/runs/bloomberg-return-audit/20261018-v1/audit.json')
    previous_bhe = load('research/runs/bloomberg-return-audit/20261018-v1/bhe_example.json')
    availability = load('research/runs/bloomberg-return-audit/20261018-v1/availability_source.json')
    evaluation = load('research/runs/ml-nonlinear/20261019-windows-v1/evaluation.json')
    for p in ['research/protocol/ml-baselines-v1.json', 'research/protocol/ml-nonlinear-v1.json',
              'research/protocol/phase1-long-horizon-v1.md', 'research/protocol/phase1-rebuild-v1.md',
              'research/protocol/extraction-workflow-v1.md', 'research/protocol/categories-v1.yaml',
              'research/protocol/ownership-identity-pilot-v1.md']:
        track(p)
    # Input references, not a second daily-return or vendor-completeness audit.
    track(ROOT / MARKET / 'panel.json')
    for p in ['research/runs/ml-nonlinear/20261019-windows-v1/predictions.jsonl',
              'research/runs/ml-nonlinear/20261019-windows-v1/scored-events.csv',
              'research/runs/ml-baselines/20261015-v1/predictions.jsonl']:
        if (ROOT / p).exists():
            track(p)
    field_coverage = {}
    for name in feature_columns:
        def present(m, name=name):
            value = fi[m['row_id']]['features'][name]
            return value is not None if name == 'pre_disclosure_industry_sic2' else finite(value)
        vals = [fi[m['row_id']]['features'][name] for m in metadata]
        numeric = [v for v in vals if finite(v)]
        if name == 'pre_disclosure_industry_sic2':
            invalid = sum(v is not None and not re.fullmatch(r'[0-9]{2}', str(v)) for v in vals)
        else:
            invalid = sum(v is not None and not finite(v) for v in vals)
            invalid += sum(v < 0 for v in numeric)
            if name == 'snapshot_security_market_cap_usd':
                invalid += sum(v == 0 for v in numeric)
            if name == 'ownership_pct_valid_fraction':
                invalid += sum(v > 1 for v in numeric)
            if name == 'reported_ownership_pct_max':
                invalid += sum(v > 100 for v in numeric)
        field_coverage[name] = {'present': sum(present(m) for m in metadata), 'rows': n,
                                'mechanical_range_or_type_flags': invalid,
                                'finite_min': min(numeric) if numeric else None,
                                'finite_max': max(numeric) if numeric else None,
                                'coverage_pct': 100 * sum(present(m) for m in metadata) / n,
                                'by_year': {}, 'by_industry': {}}
        for grouping, getter in [('by_year', lambda m: m['entry'][:4]),
                                 ('by_industry', lambda m: str(fi[m['row_id']]['features']['pre_disclosure_industry_sic2']))]:
            for group in sorted({getter(m) for m in metadata}):
                subset = [m for m in metadata if getter(m) == group]
                field_coverage[name][grouping][group] = {'rows': len(subset), 'present': sum(present(m) for m in subset)}
    sources = []
    for m in metadata:
        a = m['accession']
        receipt = load(f'{FACT}/receipts/{a}.json')
        bundle = load(f'{FACT}/bundles/{a}.json.gz')
        facts = load(f'{FACT}/facts/{a}.json.gz')
        assert digest(ROOT / FACT / 'bundles' / f'{a}.json.gz') == receipt['bundle_sha256']
        assert digest(ROOT / FACT / 'facts' / f'{a}.json.gz') == receipt['facts_sha256']
        source, sha = track(resolve_project_path(bundle['source_path'], ROOT))
        assert sha == bundle['source_sha256'] == receipt['source_sha256'] == selected[a]['source_sha256']
        assert bundle['accession'] == facts['accession'] == a and receipt['status'] == 'processed'
        verify_citations(facts, bundle)
        documents = bundle['documents']
        for doc in documents:
            if doc.get('text') is not None:
                assert hashlib.sha256(doc['text'].encode()).hexdigest() == doc['text_sha256']
        f = facts['filings'][0]
        form = f.get('source_form', {}).get('value')
        acceptance = f.get('acceptance_datetime_et', {}).get('value')
        assert acceptance == m['accepted_et']
        section_counts = {item: sum(s.get('section') == item and s.get('field', {}).get('status') == 'present'
                                  for s in facts['sections']) for item in ['ITEM 3', 'ITEM 4', 'ITEM 5']}
        docs = [d for d in documents if d.get('type') != 'SEC-HEADER']
        ass = assignments.get(m['row_id'], {})
        sources.append({'row_id': m['row_id'], 'accession': a, 'issuer': m['issuer'],
                        'permno': m['permno'], 'entry': m['entry'], 'accepted_et': acceptance,
                        'source_form': form, 'source_path': str(source.relative_to(ROOT)),
                        'source_url': bundle.get('source_url'), 'source_sha256': sha,
                        'canonical_documents': len(docs), 'canonical_text_chars': sum(len(d.get('text') or '') for d in docs),
                        'documents_without_text': sum(not d.get('text') for d in docs),
                        'document_types': sorted({str(d.get('type')) for d in docs}),
                        'item3_spans': section_counts['ITEM 3'], 'item4_spans': section_counts['ITEM 4'],
                        'item5_spans': section_counts['ITEM 5'],
                        'unresolved_references': sum(r.get('resolution_status') == 'referenced_unresolved' for r in facts['references']),
                        'assignment_status': ass.get('status'), 'assigned_etf': ass.get('etf'),
                        'assignment_permno_agrees': ass.get('permno') == m['permno'],
                        'ownership_security_status': m['ownership_security_status'],
                        'all_source_and_citation_hashes_pass': True})
    wbpath, wbhash = track(BBG)
    requests_path, _ = track(ROOT / 'research/runs/bloomberg-extraction-handoff/20261017-v2/event_requests.csv')
    with requests_path.open(newline='') as stream:
        requests = unique_index(list(csv.DictReader(stream)), 'row_id')
    assert set(requests) == set(mi)
    wb = workbook_caches(wbpath)
    raw = wb['BQL Raw Nine']['cells']
    headers = [raw.get(f'{chr(65+c)}1') for c in range(14)]
    rows = []
    for cell, event_id in raw.items():
        if re.fullmatch(r'A[0-9]+', cell) and isinstance(event_id, str) and event_id in mi:
            excel_row = int(cell[1:])
            rows.append({'row_id': event_id, 'excel_row': excel_row,
                         **{str(headers[c]): raw.get(f'{chr(65+c)}{excel_row}') for c in range(1, 14)}})
    bindex = unique_index(rows, 'row_id')
    assert set(bindex) == set(mi)
    raw_event_ids = [v for c, v in raw.items() if re.fullmatch(r'A[0-9]+', c)
                     and isinstance(v, str) and '|' in v]
    unknown_raw_ids = sorted(set(raw_event_ids) - set(mi))
    cutoff_mismatches = [r['row_id'] for r in rows if r['event_as_of'] != requests[r['row_id']]['as_of_date']]
    seed_mismatches = [r['row_id'] for r in rows if r['ticker_seed_ONLY'] != requests[r['row_id']]['bloomberg_ticker_seed_unverified']]
    raw_fields = headers[5:14]
    counts = Counter(sum(finite(r[f]) for f in raw_fields) for r in rows)
    bfields = {}
    for field in raw_fields:
        bfields[field] = coverage(r[field] for r in rows)
        for label, getter in [('by_entry_year', lambda m: m['entry'][:4]),
                              ('by_industry', lambda m: str(fi[m['row_id']]['features']['pre_disclosure_industry_sic2']))]:
            bfields[field][label] = {g: coverage(bindex[m['row_id']][field] for m in metadata if getter(m) == g)
                                     for g in sorted({getter(m) for m in metadata})}
    live = wb['Live Fundamentals']['cells']
    live_index = unique_index([{'row_id': v, 'excel_row': int(c[1:])} for c, v in live.items()
                               if re.fullmatch(r'A[0-9]+', c) and isinstance(v, str) and v in mi], 'row_id')
    assert set(live_index) == set(mi)
    scale = wb['Extraction Controls']['cells'].get('B2')
    arithmetic_bad = []
    for r in rows:
        if finite(r['bs_tot_asset']) and finite(r['TOT_DEBT_TO_TOT_ASSET']) and finite(scale) and scale != 0:
            observed = live.get(f'I{live_index[r["row_id"]]["excel_row"]}')
            expected = r['bs_tot_asset'] * r['TOT_DEBT_TO_TOT_ASSET'] / scale
            if not finite(observed) or not math.isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-5):
                arithmetic_bad.append(r['row_id'])
    assert wbhash == digest(BBG)
    complete = {r['row_id'] for r in rows if all(finite(r[f]) for f in raw_fields)}
    joined = {}
    horizons = {}
    for h in ['252', '504', '756']:
        all_rows = outcome['first_observed'][h]['russell']
        mapped, status = join_horizon(metadata, all_rows)
        joined[h] = mapped
        horizon = {'horizon_sessions': int(h), 'months_approx': int(h) // 21,
                   'all_scheduled_first_observed_events': len(all_rows),
                   'all_calculable_common_labels': sum(valid_label(r) for r in all_rows),
                   'all_valid_single_filing_labels': sum(valid_label(r) and len(r['accessions']) == 1 for r in all_rows),
                   'scheduled_status_counts': dict(Counter(r['status'] for r in all_rows)),
                   'exact_valid_labels_within_667': len(mapped), 'within_667_join_status': status,
                   'with_nine_numeric_bbg_fields_unverified': len(set(mapped) & complete),
                   'known_point_in_time_financial_eligibility': 'not_established', 'annual_folds': []}
        for year in range(2019, 2025):
            cutoff = f'{year}-01-01'
            train = [r for r in mapped.values() if r['entry'] < cutoff and r['exit'] < cutoff]
            later = [r for r in mapped.values() if cutoff <= r['entry'] < f'{year+1}-01-01']
            horizon['annual_folds'].append({'prediction_year': year, 'completed_training_events': len(train),
                                             'later_entries': len(later),
                                             'shared_issuers': len({r['issuer'] for r in train} & {r['issuer'] for r in later})})
        horizons[h] = horizon
    # Verify existing 24-month y bytes correspond to the inherited event return.
    assert len(joined['504']) == n
    for key, target in ti.items():
        assert target['target_russell_excess_504'] == joined['504'][key]['excess']
    common12_24 = set(joined['252']) & set(joined['504'])
    common_all = common12_24 & set(joined['756'])
    rankings = {str(year): {model: values.get('spearman') for model, values in models.items()}
                for year, models in evaluation['by_prediction_year'].items()}
    structure = {'rows': n, 'unique_row_ids': len(mi), 'duplicate_rows': n-len(mi),
                 'distinct_accessions': len({m['accession'] for m in metadata}),
                 'distinct_issuers': len({m['issuer'] for m in metadata}),
                 'distinct_securities_permno': len({m['permno'] for m in metadata}),
                 'entry_year_counts': dict(sorted(Counter(m['entry'][:4] for m in metadata).items())),
                 'industry_counts': dict(sorted(Counter(str(fi[m['row_id']]['features']['pre_disclosure_industry_sic2']) for m in metadata).items())),
                 'header_form_counts': dict(Counter(r['source_form'] for r in sources)),
                 'raw_and_canonical_hashes_and_citations_passed': len(sources),
                 'item4_candidate_span_events': sum(r['item4_spans'] > 0 for r in sources),
                 'item3_candidate_span_events': sum(r['item3_spans'] > 0 for r in sources),
                 'item5_candidate_span_events': sum(r['item5_spans'] > 0 for r in sources),
                 'events_with_unresolved_references': sum(r['unresolved_references'] > 0 for r in sources),
                 'source_urls_present': sum(bool(r['source_url']) for r in sources),
                 'acceptance_after_1600_et': sum(m['accepted_et'][11:] > '16:00:00' for m in metadata),
                 'acceptance_not_before_entry': sum(m['accepted_et'][:10] >= m['entry'] for m in metadata),
                 'assignment_permno_disagreements': sum(not r['assignment_permno_agrees'] for r in sources),
                 'benchmark_etf_counts': dict(Counter(str(r['assigned_etf']) for r in sources)),
                 'ownership_security_status_counts': dict(Counter(r['ownership_security_status'] for r in sources))}
    audit_result = {'decision_date': '2026-10-25', 'status': 'offline_audit_complete_with_unresolved_eligibility',
                    'scope': 'existing_667_panel_and_preserved_horizon_schedules_not_full_archive_reaudit',
                    'panel': structure, 'structured_field_coverage': field_coverage,
                    'bloomberg': {'path': str(BBG), 'source_sha256': wbhash,
                                  'same_bytes_as_oct18_audit': wbhash == previous_bbg['source']['sha256'],
                                  'sheets': list(wb), 'event_rows': len(rows), 'numeric_field_histogram': dict(counts),
                                  'unknown_raw_event_ids': unknown_raw_ids,
                                  'raw_event_id_duplicate_count': len(raw_event_ids) - len(set(raw_event_ids)),
                                  'request_cutoff_mismatches': cutoff_mismatches,
                                  'request_ticker_seed_mismatches': seed_mismatches,
                                  'field_coverage': bfields, 'debt_ratio_divisor_saved_assumption': scale,
                                  'debt_arithmetic_disagreements_under_saved_assumption': arithmetic_bad,
                                  'controls': previous_bbg['controls'], 'field_notes': previous_bbg['field_code_notes'],
                                  'release_date_verified_event_count': None,
                                  'release_date_status': 'no_event_level_publication_vintage_evidence_established',
                                  'historical_id_status': 'seed_agreement_is_not_independent_security_validation',
                                  'availability_conflict_example': previous_bhe, 'availability_source_record': availability,
                                  'source_unchanged': True},
                    'horizons': horizons,
                    'common_samples': {'12_24_exact_event_rows': len(common12_24),
                                       '12_24_36_exact_event_rows': len(common_all),
                                       '12_24_with_nine_numeric_bbg_unverified': len(common12_24 & complete),
                                       'all_horizons_with_nine_numeric_bbg_unverified': len(common_all & complete),
                                       'llm_validated_feature_eligibility': 'not_established',
                                       'model_ready_A_B_C_common_sample': 'not_established'},
                    'prior_within_year_spearman_verified_from_saved_file': rankings,
                    'reconciliation': ['Ranking was already evaluated in 2021-2023; it is not an untested metric.',
                                       'Existing predictors omit the Bloomberg financial fields and validated LLM information.',
                                       'All prior outcomes remain exposed development evidence; this audit cannot create an untouched test.'],
                    'limits': ['Header initial form is not independent confirmation of first activist involvement.',
                               'Item section spans are parser candidates, not semantic or exhibit-completeness certification.',
                               'Annual fold counts establish availability only, not independence or sufficient inner validation.',
                               'Daily stock/corporate-action accounting is inherited, not recomputed or fully reaudited.',
                               'The current 667-panel coverage is not the final universe for new horizon-specific samples.']}
    ledger = []
    for m in metadata:
        b = bindex[m['row_id']]
        ledger.append({'row_id': m['row_id'], 'accession': m['accession'], 'issuer': m['issuer'],
                       'permno': m['permno'], 'entry': m['entry'], 'industry': fi[m['row_id']]['features']['pre_disclosure_industry_sic2'],
                       'raw_bbg_numeric_fields': sum(finite(b[f]) for f in raw_fields),
                       **{f'exact_valid_{h}_label': m['row_id'] in joined[h] for h in joined}})
    return audit_result, sources, ledger, inputs


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    checks()
    result, sources, ledger, inputs = audit()
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=list(ledger[0]))
    writer.writeheader()
    writer.writerows(ledger)
    outputs = {'audit.json': encode(result), 'filing-source-audit.json': encode(sources),
               'event-coverage.csv': buf.getvalue().encode(), 'source-manifest.json': encode(inputs)}
    if args.verify:
        for name, data in outputs.items():
            if (args.output / name).read_bytes() != data:
                raise ValueError(f'Exact audit replay differs: {name}')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in outputs.items():
            (args.output / name).write_bytes(data)
    print(json.dumps({'output': str(args.output), 'replay': args.verify,
                      'panel': result['panel'], 'common_samples': result['common_samples'],
                      'horizon_labels': {h: v['exact_valid_labels_within_667'] for h, v in result['horizons'].items()},
                      'bloomberg_numeric_histogram': result['bloomberg']['numeric_field_histogram']}, indent=2))


if __name__ == '__main__':
    main()
