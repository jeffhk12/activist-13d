"""Build a self-contained Bloomberg extraction handoff from the frozen ML sample.

Inputs: 667 feature-preview metadata/evidence rows, SEC facts, cached CRSP dsenames,
and the handoff prose template. Outputs: Markdown, six CSVs, evidence and a ZIP.
Identity: retain every row_id; name interval contains the prior-session cutoff;
use dated ncusip, never the cache's potentially later cusip as the historical ID.
Tier: 1, transfer preparation; no price estimates, new labels or model fitting.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
scripts/ml_experiment/build_bloomberg_handoff.py --output NEW_DIRECTORY
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / 'research/runs/ml-feature-preview/20261012-v1'
TEMPLATE = Path(__file__).with_name('bloomberg_handoff_template.md')
CORE = [
    ('total_assets', 'Total assets', 'Latest reported balance sheet available at cutoff', 'Asset base; consolidated company; preserve fiscal period end'),
    ('common_book_equity', 'Common shareholders book equity', 'Latest reported balance sheet available at cutoff', 'Exclude preferred equity/noncontrolling interests where identifiable; preserve negative values'),
    ('total_debt', 'Total interest-bearing debt', 'Latest reported balance sheet available at cutoff', 'Short plus long term; explicitly record whether lease liabilities are included'),
    ('cash_equivalents', 'Cash and cash equivalents', 'Latest reported balance sheet available at cutoff', 'Record treatment of restricted cash and short-term investments; no silent broader substitution'),
    ('revenue_ttm', 'Revenue, actual trailing 12 months', 'Latest fully reported actual TTM available at cutoff', 'Actuals only; return period start/end and component periods if TTM is reconstructed'),
    ('revenue_ttm_prior_year', 'Comparable prior-year revenue TTM', 'One fiscal year earlier than revenue_ttm, same historical information cutoff', 'Comparable fiscal basis and currency; not a new query as of today'),
    ('net_income_ttm', 'Net income attributable to common, actual TTM', 'Latest fully reported actual TTM available at cutoff', 'Record attribution basis; do not silently substitute EPS or analyst estimates'),
    ('operating_cash_flow_ttm', 'Net cash from operating activities, actual TTM', 'Latest fully reported actual TTM available at cutoff', 'Distinguish annual, YTD and quarterly flows; do not sum overlapping YTD values'),
    ('company_market_cap', 'Company common-equity market capitalization', 'Historical close on as_of_date', 'Company equity scope compatible with book equity, all common classes; record ADR/share-class treatment'),
]
OPTIONAL = [
    ('total_assets_prior_year', 'Total assets one fiscal year earlier', 'Comparable prior-year balance sheet, same historical cutoff', 'Allows average-assets profitability measures'),
    ('ebitda_ttm', 'EBITDA actual TTM', 'Latest fully reported actual TTM available at cutoff', 'Separate reported and adjusted EBITDA; retain definition and missing values'),
]


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + '\n'


def csv_text(rows, columns):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n', extrasaction='raise')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def field_value(field):
    return field.get('value') if field.get('status') == 'present' else None


def joined_values(rows, key):
    return ';'.join(sorted({r[key] for r in rows if r[key]}))


def dated_projection(row):
    return tuple(str(row.get(k) or '') for k in ('ticker', 'tsymbol', 'comnam', 'ncusip', 'shrcls', 'permco'))


def select_name(records, cutoff):
    matches = [r for r in records if r.get('namedt') and r.get('nameendt')
               and r['namedt'] <= cutoff <= r['nameendt']]
    distinct = {dated_projection(r) for r in matches}
    if len(distinct) != 1:
        raise ValueError(f'Historical name match is missing or ambiguous at {cutoff}')
    return sorted(matches, key=lambda r: (r['namedt'], r['nameendt'], json.dumps(r, sort_keys=True)))[0]


def self_checks():
    original = {'namedt': '2018-01-01', 'nameendt': '2018-12-31', 'ticker': 'OLD',
                'tsymbol': 'OLD', 'comnam': 'ORIGINAL CO', 'ncusip': '12345678',
                'cusip': '87654321', 'permco': 1}
    assert select_name([original], '2018-01-01')['ncusip'] == '12345678'
    assert select_name([original], '2018-12-31')['ticker'] == 'OLD'
    assert select_name([original, dict(original)], '2018-06-30')['ticker'] == 'OLD'
    for records, cutoff in [([original], '2019-01-01'),
                            ([original, {**original, 'ticker': 'OTHER'}], '2018-06-30')]:
        try:
            select_name(records, cutoff)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing/conflicting dated identities must be refused')
    assert list(csv.DictReader(io.StringIO(csv_text([{'cik': '0000814453', 'cusip': '00165C10'}], ['cik', 'cusip']))))[0]['cik'] == '0000814453'


def build(out):
    self_checks()
    if out.exists():
        raise ValueError('Use a new output directory; prior handoffs are preserved')
    source_hashes = {}

    def read(path):
        payload = path.read_bytes()
        source_hashes[str(path.relative_to(ROOT))] = sha(payload)
        return payload

    metadata = [json.loads(line) for line in read(PREVIEW / 'row-metadata.jsonl').decode().splitlines()]
    evidence = {r['row_id']: r for line in read(PREVIEW / 'field-evidence.jsonl').decode().splitlines() if (r := json.loads(line))}
    assert len(metadata) == len(evidence) == len({r['row_id'] for r in metadata}) == 667
    assert len({r['permno'] for r in metadata}) == 639
    assert len({r['issuer'] for r in metadata}) == 641
    assert {r['row_id'] for r in metadata} == set(evidence)
    needed = {r['permno'] for r in metadata}
    histories = defaultdict(list)
    history_sources = defaultdict(set)
    skipped_schema_files = []
    for path in sorted((ROOT / 'data/raw/wrds/bulk-v1/crsp.dsenames').glob('*.json.gz')):
        payload = read(path)
        envelope = json.loads(gzip.decompress(payload))
        if 'results' not in envelope:
            assert 'fields' in envelope, 'Unexpected cache envelope'
            skipped_schema_files.append(str(path.relative_to(ROOT)))
            continue
        for record in envelope['results']:
            if record['permno'] in needed:
                histories[record['permno']].append(record)
                history_sources[json.dumps(record, sort_keys=True)].add(str(path.relative_to(ROOT)))
    events, lineage = [], []
    for row in sorted(metadata, key=lambda r: (r['accepted_et'], r['row_id'])):
        ev = evidence[row['row_id']]
        assignment = ev['market_assignment']
        cutoff = assignment['pre']
        assert cutoff == row['industry_as_of'] < row['accepted_et'][:10]
        assert assignment['permno'] == row['permno']
        name = select_name(histories[row['permno']], cutoff)
        assert name['permno'] == row['permno']
        ncusip = name.get('ncusip') or ''
        if not re.fullmatch('[A-Z0-9*@#]{8}', ncusip):
            raise ValueError('Dated CUSIP8 unavailable')
        fact_path = ROOT / ev['facts_path']
        fact = json.loads(gzip.decompress(read(fact_path)))
        assert fact['accession'] == row['accession']
        issuers = [r for r in fact['issuers'] if field_value(r['cik']) == row['issuer']]
        assert len(issuers) == 1
        filing_candidates = sorted({str(v) for r in fact['securities'] if (v := field_value(r['cusip']))})
        matching = [r for r in fact['securities'] if (v := field_value(r['cusip']))
                    and len(str(v)) == 9 and str(v)[:8] == ncusip
                    and field_value(r.get('cusip_check_digit_valid', {})) is True]
        usable = matching[0] if len(matching) == 1 else None
        notes = []
        if not usable:
            notes.append('filing_cusip9_not_uniquely_confirmed_against_dated_ncusip')
        if name.get('shrcls'):
            notes.append('confirm_share_class_and_Bloomberg_ticker_format')
        if assignment['historical_security']['cusip'] != ncusip:
            notes.append('dated_ncusip_differs_from_prior_month_snapshot_cusip')
        raw_symbol = name.get('tsymbol') or name.get('ticker') or ''
        event = {
            'row_id': row['row_id'], 'accession': row['accession'],
            'accepted_et': row['accepted_et'], 'as_of_date': cutoff,
            'cutoff_timezone': 'America/New_York', 'issuer_cik': row['issuer'],
            'issuer_name_sec': field_value(issuers[0]['name']) or '',
            'permno': str(row['permno']), 'permco': str(name.get('permco') or ''),
            'historical_company_name': name.get('comnam') or '',
            'historical_ticker': name.get('ticker') or '', 'historical_trading_symbol': raw_symbol,
            'historical_share_class': name.get('shrcls') or '',
            'historical_cusip8': ncusip,
            'filing_cusip9_candidate': field_value(usable['cusip']) if usable else '',
            'filing_cusip_candidates': ';'.join(filing_candidates),
            'historical_name_start': name['namedt'], 'historical_name_end': name['nameendt'],
            'bloomberg_ticker_seed_unverified': raw_symbol + ' US Equity' if raw_symbol else '',
            'bloomberg_identifier_verified': '', 'mapping_status': 'unverified',
            'review_notes': ';'.join(notes),
        }
        events.append(event)
        lineage.append({'row_id': row['row_id'], 'facts_path': ev['facts_path'],
                        'historical_name_row': name,
                        'historical_name_sources': sorted(history_sources[json.dumps(name, sort_keys=True)]),
                        'month_snapshot_cusip8': assignment['historical_security']['cusip'],
                        'decision': 'Dated ncusip used; generic cusip is not used as historical identity',
                        'filing_cusip9_rule': 'One explicitly extracted, check-digit-valid CUSIP9 matching dated ncusip; otherwise blank'})
    assert events[0]['historical_ticker'] == 'NWL'
    assert events[0]['historical_cusip8'] == '65122910'
    assert events[0]['filing_cusip9_candidate'] == '651229106'
    grouped = defaultdict(list)
    for row in events:
        grouped[row['permno']].append(row)
    securities = []
    for permno, group in sorted(grouped.items(), key=lambda item: int(item[0])):
        first = group[0]
        securities.append({'permno': permno, 'event_count': len(group),
            'first_as_of_date': group[0]['as_of_date'], 'last_as_of_date': group[-1]['as_of_date'],
            'historical_company_names': joined_values(group, 'historical_company_name'),
            'issuer_names_sec': joined_values(group, 'issuer_name_sec'), 'issuer_ciks': joined_values(group, 'issuer_cik'),
            'historical_tickers': joined_values(group, 'historical_ticker'),
            'historical_trading_symbols': joined_values(group, 'historical_trading_symbol'),
            'historical_cusip8_values': joined_values(group, 'historical_cusip8'),
            'filing_cusip9_candidates': joined_values(group, 'filing_cusip9_candidate'),
            'bloomberg_ticker_seed_unverified': first['bloomberg_ticker_seed_unverified'],
            'bloomberg_identifier_verified': '', 'bloomberg_company_identifier': '',
            'returned_cusip': '', 'returned_name': '', 'returned_share_class': '',
            'mapping_status': 'unverified',
            'mapping_evidence': '', 'mapping_notes': 'Multiple issuer CIKs: review entity relationship' if len({r['issuer_cik'] for r in group}) > 1 else ''})
    pilot = []

    def choose(rows, reason):
        for row in rows:
            if row['row_id'] not in {r['row_id'] for r in pilot}:
                pilot.append({**row, 'pilot_reason': reason})
                return

    for year in range(2018, 2024):
        choose([r for r in events if r['accepted_et'].startswith(str(year))], f'Calendar coverage: {year}')
    choose([r for r in events if r['historical_share_class']], 'Share-class mapping review')
    choose([r for r in events if not r['filing_cusip9_candidate']], 'CUSIP9 not uniquely confirmed: test abstention')
    choose([r for r in events if len(grouped[r['permno']]) > 1], 'Repeated security at separate event cutoffs')
    repeated = pilot[-1]['permno']
    choose(grouped[repeated], 'Second cutoff for the repeated pilot security')
    if len(pilot) < 10:
        choose(list(reversed(events)), 'Latest event cutoff')
    for row in events:
        if len(pilot) >= 10:
            break
        choose([row], 'Chronological fill; no outcomes consulted')
    assert len(pilot) == 10
    assert any(count > 1 for count in Counter(r['permno'] for r in pilot).values())
    fields = [{'logical_field_id': code, 'priority': 'core' if index < len(CORE) else 'optional',
               'requested_measure': title, 'period_rule': period, 'definition_notes': note,
               'bloomberg_field_or_bql_item': '', 'validated_asof_syntax': '',
               'validation_status': 'unverified', 'help_reference': ''}
              for index, (code, title, period, note) in enumerate(CORE + OPTIONAL)]
    requests = [{'request_id': row['row_id'] + '::' + code, 'row_id': row['row_id'],
                 'permno': row['permno'], 'as_of_date': row['as_of_date'],
                 'historical_cusip8': row['historical_cusip8'],
                 'bloomberg_identifier_verified': '', 'logical_field_id': code,
                 'status': 'not_requested'} for row in events for code, *_ in CORE]
    assert len(requests) == len({r['request_id'] for r in requests}) == 6003
    result_columns = ['request_id', 'row_id', 'logical_field_id', 'as_of_date',
        'bloomberg_security_id', 'bloomberg_company_id', 'returned_security_name', 'returned_cusip',
        'value', 'raw_value', 'currency', 'unit', 'scale_multiplier',
        'period_start', 'period_end', 'period_basis', 'publication_datetime',
        'vendor_available_datetime', 'revision_vintage', 'point_in_time_status',
        'query_text', 'query_version', 'extracted_at_utc', 'batch_id',
        'status', 'raw_error', 'source_reference', 'notes']
    files = {
        'event_requests.csv': csv_text(events, list(events[0])),
        'security_lookup.csv': csv_text(securities, list(securities[0])),
        'pilot_events.csv': csv_text(pilot, list(pilot[0])),
        'field_dictionary.csv': csv_text(fields, list(fields[0])),
        'event_field_requests.csv': csv_text(requests, list(requests[0])),
        'result_schema.csv': csv_text([], result_columns),
    }
    context = {'events': len(events), 'securities': len(securities),
        'issuer_ciks': len({r['issuer_cik'] for r in events}),
        'first_accepted_et': events[0]['accepted_et'], 'last_accepted_et': events[-1]['accepted_et'],
        'first_as_of_date': min(r['as_of_date'] for r in events),
        'last_as_of_date': max(r['as_of_date'] for r in events),
        'events_with_filing_cusip9_candidate': sum(bool(r['filing_cusip9_candidate']) for r in events),
        'events_requiring_filing_cusip9_review': sum(not r['filing_cusip9_candidate'] for r in events),
        'events_with_share_class': sum(bool(r['historical_share_class']) for r in events),
        'month_snapshot_cusip_disagreements': sum('dated_ncusip_differs' in r['review_notes'] for r in events),
        'unique_dated_name_matches': len(events), 'core_fields': len(CORE),
        'core_requests': len(requests), 'pilot_events': len(pilot),
        'disclosure_year_counts': dict(sorted(Counter(r['accepted_et'][:4] for r in events).items()))}
    prose = read(TEMPLATE).decode()
    prompt = prose.split('<!-- CHATGPT_PROMPT_START -->\n', 1)[1].split('\n<!-- CHATGPT_PROMPT_END -->', 1)[0]
    replacements = {'{{EVENT_CSV}}': files['event_requests.csv'].rstrip(),
                    '{{SUMMARY_JSON}}': dumps(context).rstrip(),
                    '{{SECURITY_TABLE}}': '\n'.join('| ' + ' | '.join(str(s[k]).replace('|','/') for k in ('permno','historical_tickers','historical_company_names','historical_cusip8_values','event_count')) + ' |' for s in securities)}
    for old, new in replacements.items():
        prose = prose.replace(old, new)
    assert '{{' not in prose
    files['handoff.md'] = prose
    files['chatgpt_prompt.txt'] = prompt + '\n'
    files['scope_summary.json'] = dumps(context)
    files['source_evidence.json'] = dumps({'source_sha256': source_hashes,
        'builder': str(Path(__file__).relative_to(ROOT)), 'builder_sha256': sha(Path(__file__).read_bytes()),
        'schema_cache_files_skipped_as_data': skipped_schema_files, 'events': lineage,
        'limits': 'Dated CRSP name matches are lookup aids, not Bloomberg validation or certified vendor knowledge-time history. SEC semantic extraction remains subject to review. No return targets or investor strategy labels exported.'})
    out.mkdir(parents=True)
    for name, contents in files.items():
        (out / name).write_text(contents, encoding='utf-8', newline='')
    for name in ('event_requests.csv', 'security_lookup.csv', 'pilot_events.csv', 'field_dictionary.csv', 'event_field_requests.csv'):
        loaded = list(csv.DictReader(io.StringIO((out / name).read_text())))
        assert len(loaded) == {'event_requests.csv':667,'security_lookup.csv':639,'pilot_events.csv':10,'field_dictionary.csv':11,'event_field_requests.csv':6003}[name]
    embedded = prose.split('<!-- EVENT_CSV_START -->\n```csv\n', 1)[1].split('\n```\n<!-- EVENT_CSV_END -->', 1)[0]
    assert embedded + '\n' == files['event_requests.csv']
    assert list(csv.DictReader(io.StringIO(embedded))) == events
    assert all(not r['bloomberg_identifier_verified'] and r['mapping_status'] == 'unverified' for r in events)
    assert all(date.fromisoformat(r['as_of_date']) < date.fromisoformat(r['accepted_et'][:10]) for r in events)
    assert not any(key in events[0] for key in ('target', 'excess', 'label_end', 'cohort_for_diagnostics_only'))
    for path, digest in source_hashes.items():
        assert sha((ROOT / path).read_bytes()) == digest
    manifest = {'schema': 1, 'date': '2026-10-17', 'scope': context,
        'status': 'Prepared transfer instructions and lookup aids; no Bloomberg identifiers/fields/PIT queries validated',
        'checks': ['667 unique events retained', '639 securities and 641 issuer CIKs reconciled',
                   '667 unambiguous dated CRSP identity matches', 'CUSIP9 candidates from source only',
                   'all cutoffs precede public disclosure', '6003 unique core request IDs',
                   'CSV roundtrip preserves leading zeros', 'embedded CSV equals companion CSV',
                   'all source bytes unchanged', 'no return targets/cohort labels exported'],
        'files': {name: {'sha256': sha((out / name).read_bytes()), 'bytes': (out / name).stat().st_size} for name in files}}
    (out / 'package_manifest.json').write_text(dumps(manifest))
    archive = out / '13D_Bloomberg_Handoff_20261017.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as package:
        for name in sorted([*files, 'package_manifest.json']):
            package.write(out / name, name)
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            assert package.read(name) == (out / name).read_bytes()
    print(dumps({'output': str(out), 'scope': context, 'zip_bytes': archive.stat().st_size,
                 'verification': 'passed; ZIP members read back byte-for-byte'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output.resolve())
