"""Descriptive EDA from audited candidate records, coverage, and benchmark files.

Inputs: SEC SQLite, WRDS/link reports, frozen HFR/public manifests. Outputs:
Markdown/HTML report, PNG charts and JSON calculation tables with source hashes.
Identity: rates = observed count / explicitly named denominator; quantiles use
nearest-rank ceil(p*n)-1. Candidate groups and parser spans are unvalidated.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/eda.py RUN_DIRECTORY
"""
import argparse
import base64
import hashlib
import html
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {'n': 0}
    return {'n': len(ordered), 'min': ordered[0], 'p25': ordered[max(0, math.ceil(.25 * len(ordered)) - 1)],
            'median': ordered[math.ceil(.5 * len(ordered)) - 1], 'p75': ordered[math.ceil(.75 * len(ordered)) - 1],
            'p95': ordered[math.ceil(.95 * len(ordered)) - 1], 'max': ordered[-1]}


def scan(db):
    years = defaultdict(Counter)
    flags, forms, parsers, subjects, filers, hours = (Counter() for _ in range(6))
    lengths, delays, bytes_ = [], [], []
    missing_subject = missing_filer = n = negative = 0
    for (value,) in db.execute('SELECT record_json FROM records ORDER BY accession'):
        r = json.loads(value)
        n += 1
        year = r['filing_date'][:4]
        years[year]['parsed'] += 1
        years[year][r['form']] += 1
        forms[r['form']] += 1
        parsers[r.get('parser_source', 'unknown')] += 1
        flags.update(set(r.get('flags', [])))
        for field in ('cusip', 'item4_text', 'event_date'):
            if r.get(field):
                years[year][field + '_present'] += 1
        issuer_ids = {str(x['cik']).lstrip('0') or '0' for x in r.get('subjects', []) if x.get('cik')}
        filer_ids = {str(x['cik']).lstrip('0') or '0' for x in r.get('filers', []) if x.get('cik')}
        subjects.update(issuer_ids)
        filers.update(filer_ids)
        missing_subject += not bool(issuer_ids)
        missing_filer += not bool(filer_ids)
        if r.get('item4_text'):
            lengths.append(len(r['item4_text']))
        if r.get('source_bytes') is not None:
            bytes_.append(r['source_bytes'])
        if r.get('acceptance_datetime_et'):
            hours[r['acceptance_datetime_et'][11:13]] += 1
        if r.get('event_date'):
            difference = (date.fromisoformat(r['filing_date']) - date.fromisoformat(r['event_date'])).days
            delays.append(difference)
            negative += difference < 0
    failed_years = Counter()
    failure_types = Counter()
    for error, source in db.execute('SELECT error, source_json FROM failures'):
        failed_years[json.loads(source)['filing_date'][:4]] += 1
        failure_types[error.split('\n')[0][:160]] += 1
    for year, number in failed_years.items():
        years[year]['failed'] = number
    return {'parsed_n': n, 'failures_n': sum(failed_years.values()), 'years': dict(sorted(years.items())),
            'forms': dict(forms), 'flags': dict(flags), 'parser_sources': dict(parsers),
            'unique_subject_ciks': len(subjects), 'unique_filer_ciks': len(filers),
            'missing_subject_cik_n': missing_subject, 'missing_filer_cik_n': missing_filer,
            'top_subject_ciks_by_filing_mentions': subjects.most_common(20),
            'top_filer_ciks_by_filing_mentions': filers.most_common(20),
            'acceptance_hour_et': dict(sorted(hours.items())), 'item4_characters': distribution(lengths),
            'source_bytes': distribution(bytes_), 'filing_minus_event_calendar_days': distribution(delays),
            'negative_event_delay_n': negative, 'failure_types': dict(failure_types)}


class Report:
    def __init__(self):
        self.md, self.web = [], []

    def heading(self, title, level=2):
        self.md.append('#' * level + ' ' + title)
        self.web.append(f'<h{level}>{html.escape(title)}</h{level}>')

    def para(self, text):
        self.md.append(text)
        self.web.append('<p>' + html.escape(text) + '</p>')

    def table(self, headers, rows):
        rows = [[str(x) for x in row] for row in rows]
        self.md.append('\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(x.replace('|', '/') for x in row) + ' |' for row in rows]))
        self.web.append('<table><thead><tr>' + ''.join('<th>' + html.escape(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + html.escape(x) + '</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table>')

    def figure(self, filename, caption):
        self.md.append(f'![{caption}]({filename})')
        self.web.append(f'<figure><img src="{filename}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>')


def run(run_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output = run_dir / 'eda'
    output.mkdir(exist_ok=True)
    dbpath = run_dir / 'sec.sqlite'
    with sqlite3.connect(f'file:{dbpath}?mode=ro', uri=True) as db:
        values = scan(db)
        with (output / 'review_queue.jsonl').open('w') as queue:
            for accession, error, source in db.execute('SELECT accession,error,source_json FROM failures ORDER BY accession'):
                queue.write(json.dumps({'accession': accession, 'review_type': 'source_or_parser_failure', 'error': error, 'source': json.loads(source)}) + '\n')
            for accession, raw in db.execute('SELECT accession,record_json FROM records ORDER BY accession'):
                record = json.loads(raw)
                if record.get('flags'):
                    queue.write(json.dumps({'accession': accession, 'review_type': 'mechanical_evidence_flags', 'flags': record['flags'], 'source_path': record['source_path'], 'source_sha256': record['source_sha256']}) + '\n')
    files = [dbpath, run_dir / 'provenance.json']
    report = Report()
    report.heading('Activist 13D — data feasibility and exploratory analysis', 1)
    report.para('This report describes the downloaded research universe and mechanical candidate extraction. It does not establish corporate eligibility, activist intent, distinct economic campaigns, investability, or strategy performance. The 2026 SEC period is a partial-year snapshot. Counts describe this frozen download, not all possible historical activism.')
    report.heading('Scope, integrity, and processing attrition')
    total = values['parsed_n'] + values['failures_n']
    report.table(['Measure', 'Count'], [('SEC manifest records processed', total), ('Parsed candidates', values['parsed_n']), ('Parser/integrity failures retained for review', values['failures_n']), ('Distinct subject CIKs in parsed records', values['unique_subject_ciks']), ('Distinct filer CIKs in parsed records', values['unique_filer_ciks'])])
    report.para('Parsed plus failed equals processed. Failed filings remain in sec.sqlite/failures and are not silently discarded. Unique party counts are filing-header identifiers, not verified companies or activist managers. One filing can name multiple parties. Original blank review packets are protected by hash comparison; all job outputs use separate paths.')
    index_path = run_dir / 'index-audit.json'
    if index_path.exists():
        files.append(index_path)
        index_audit = json.loads(index_path.read_text())
        report.para(f'Quarterly index snapshots verified against manifest hashes and sidecars: {len(index_audit)}. These consistency checks are not independent cryptographic authentication of the vendor.')
    report.heading('Filing trends and extraction availability')
    headers = ['Year', 'Parsed', 'Failed', 'Initial 13D', 'Amendment', 'CUSIP present', 'Item 4 present', 'Event date present']
    report.table(headers, [[year] + [counts.get(k, 0) for k in ('parsed', 'failed', '13D', '13D/A', 'cusip_present', 'item4_text_present', 'event_date_present')] for year, counts in values['years'].items()])
    years = list(values['years'])
    fig, ax = plt.subplots(figsize=(11, 5))
    initial = [values['years'][y].get('13D', 0) for y in years]
    amendment = [values['years'][y].get('13D/A', 0) for y in years]
    ax.bar(years, initial, label='Initial 13D')
    ax.bar(years, amendment, bottom=initial, label='Amendments')
    ax.set(ylabel='Parsed filings', title='Parsed filings by year — 2026 is partial')
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / 'filings_by_year.png', dpi=150)
    plt.close(fig)
    report.figure('filings_by_year.png', 'Counts from parsed records; failures appear separately in the table.')
    report.heading('Missing evidence and parser limitations')
    report.table(['Flag (overlapping)', 'Filings', '% of parsed filings'], [(k, v, f'{100*v/values["parsed_n"]:.2f}%' if values['parsed_n'] else 'N/A') for k, v in sorted(values['flags'].items(), key=lambda x: -x[1])])
    if values['flags']:
        fig, ax = plt.subplots(figsize=(11, 6))
        keys = sorted(values['flags'], key=values['flags'].get)
        ax.barh(keys, [values['flags'][k] for k in keys])
        ax.set(xlabel='Parsed filings flagged (overlap allowed)', title='Mechanical evidence review queue')
        fig.tight_layout()
        fig.savefig(output / 'evidence_gaps.png', dpi=150)
        plt.close(fig)
        report.figure('evidence_gaps.png', 'Flags identify review needs; no flag does not certify complete evidence.')
    report.table(['Parser source', 'Filings'], sorted(values['parser_sources'].items()))
    report.para('CUSIP presence is syntactic extraction, not a validated security match. Item 4 text is a candidate span, not an intent label. Referenced external filings/exhibits and binary documents may still require retrieval or manual inspection. Parser failures include bounded resource refusals and remain visible.')
    report.table(['Failure category / first error line', 'Count'], sorted(values['failure_types'].items(), key=lambda x: -x[1]))
    report.heading('Concentration and disclosure timing')
    report.table(['Subject CIK', 'Filing mentions'], values['top_subject_ciks_by_filing_mentions'])
    report.table(['Filer CIK', 'Filing mentions'], values['top_filer_ciks_by_filing_mentions'])
    report.para('Rankings count each CIK once per parsed filing. They measure disclosure activity, not capital, trading activity, campaign success, or independent observations. Filer headers do not necessarily capture every reporting person.')
    report.table(['Distribution', 'n', 'Min', 'P25', 'Median', 'P75', 'P95', 'Max'], [[key] + [values[key].get(k, 'N/A') for k in ('n','min','p25','median','p75','p95','max')] for key in ('item4_characters','source_bytes','filing_minus_event_calendar_days')])
    report.para(f"Event-to-filing differences use calendar days only and unvalidated extracted dates; they are not a legal deadline/compliance measure. Negative differences requiring review: {values['negative_event_delay_n']}. Quantiles use nearest rank.")
    report.table(['Acceptance hour (Eastern, source convention)', 'Filings'], sorted(values['acceptance_hour_et'].items()))
    report.heading('Candidate grouping and historical CRSP matching')
    report.para('Exact party-set groupings are candidate chains. Party changes can split one campaign; repeated campaigns can share the same parties. No grouping is a final campaign label. Historical security matching must be unique and valid on the filing date; ambiguous matches stay unresolved.')
    report.heading('WRDS coverage and market-data readiness')
    report.para('The WRDS daily API reported inconsistent counts. Local audits can identify duplicates, empty slices, gaps, and missing fields, but cannot independently certify vendor completeness. A weekday with zero rows may be an exchange holiday, an unavailable date, or a coverage gap; it is not a zero return.')
    for stage in ('links', 'wrds'):
        folder = run_dir / stage
        report.heading(stage.upper() + ' detailed audit outputs', 3)
        if folder.exists():
            for p in sorted(folder.glob('*.json')):
                if p.name not in ('audit.json', 'summary.json'):
                    continue
                files.append(p)
                data = json.loads(p.read_text())
                values[stage + '_' + p.stem] = data
                report.table(['Measure', 'Observed value'], [(k, v) for k, v in data.items() if isinstance(v, (int, float, str)) or v is None])
                if stage == 'links':
                    report.table(['Match status', 'Filings'], sorted(data.get('crsp_status', {}).items()))
                    report.table(['Year', 'Parsed', 'CUSIP/date available', 'Matched', 'Conditional match rate'],
                                 [[year, v.get('n'), v.get('eligible_cusip'), v.get('matched'), v.get('match_rate')] for year, v in sorted(data.get('match_rates_by_year', {}).items())])
                    report.para('The conditional match-rate denominator excludes missing CUSIPs/dates. Overall availability also depends on parser failures and missing identifiers; these are shown in earlier attrition tables.')
                    groups_path = folder / 'groups.jsonl'
                    if groups_path.exists():
                        files.append(groups_path)
                        group_sizes = []
                        initial_counts = Counter()
                        for line in groups_path.open():
                            group = json.loads(line)
                            group_sizes.append(group['n_records'])
                            initial_counts['no_initial' if group['n_initials'] == 0 else 'one_initial' if group['n_initials'] == 1 else 'multiple_initials'] += 1
                        values['candidate_group_size'] = distribution(group_sizes)
                        values['candidate_group_initial_counts'] = dict(initial_counts)
                        report.table(['Candidate group characteristic', 'Count'], sorted(initial_counts.items()))
                        report.table(['Group-size statistic', 'Filings per group'], list(values['candidate_group_size'].items()))
                else:
                    daily = data.get('daily', {})
                    report.table(['Daily coverage measure', 'Observed value'], [(k, v) for k, v in daily.items() if isinstance(v, (int, float, str))])
                    report.table(['Year', 'Daily rows'], sorted(daily.get('rows_by_year', {}).items()))
                    report.table(['Opening-price field', 'Non-null daily rows'], sorted(daily.get('opening_price_fields_nonnull', {}).items()))
                    report.table(['File audit status', 'Files'], sorted(data.get('file_status_counts', {}).items()))
                    tables = data.get('tables', {})
                    if isinstance(tables, dict):
                        report.table(['WRDS table', 'Rows', 'Files'], [[k, v.get('rows'), v.get('files')] for k, v in sorted(tables.items())])
                    report.para('Full missing/unexpected date lists, observed field counts and per-date row counts are in calculations.json and the WRDS audit JSON.')
                    by_date = daily.get('rows_by_date', {})
                    if by_date:
                        fig, ax = plt.subplots(figsize=(11, 5))
                        dates = sorted(by_date)
                        ax.plot([date.fromisoformat(d) for d in dates], [by_date[d] for d in dates], linewidth=.7)
                        ax.set(ylabel='Rows per observed date', title='CRSP daily rows in archived responses')
                        fig.tight_layout()
                        fig.savefig(output / 'wrds_rows_by_date.png', dpi=150)
                        plt.close(fig)
                        report.figure('wrds_rows_by_date.png', 'Observed rows only; gaps do not imply zero returns.')
            for p in sorted(folder.glob('*.md')):
                report.md.append(f'[Detailed {stage} report](../{stage}/{p.name})')
                report.web.append(f'<p><a href="../{stage}/{p.name}">Detailed {stage} report</a></p>')
    report.heading('HFRI Event-Driven benchmark and public series')
    hfrpath = ROOT / 'data/interim/hfr/hfr_manifest.json'
    hfr = json.loads(hfrpath.read_text())
    series_path = ROOT / 'data/interim/hfr/hfri_event_driven_2703_monthly.jsonl'
    if sha(series_path) != hfr['hfri_event_driven_2703']['extract_sha256']:
        raise ValueError('HFR extracted series hash mismatch')
    for entry in hfr['files']:
        if sha(Path(entry['frozen_path'])) != entry['sha256']:
            raise ValueError('Frozen HFR source hash mismatch')
    series = [json.loads(line) for line in series_path.read_text().splitlines() if line.strip()]
    hfr_info = hfr['hfri_event_driven_2703']
    files.extend([hfrpath, series_path])
    report.table(['Benchmark field', 'Observed value'], [('Index', '2703 — HFRI Event-Driven (Total) Index'), ('Monthly observations', len(series)), ('First month', min(r['Date'] for r in series)), ('Last month', max(r['Date'] for r in series)), ('Missing source ROR', sum(r.get('ROR') in (None,'') for r in series)), ('Currency / fee source labels', 'USD / Net of All Fees')])
    report.para('ROR values and NAV remain as supplied. Return-unit convention and methodology documentation remain unresolved; no compounded benchmark returns, annualized Sharpe, or strategy comparisons are presented. Monthly HFR returns will not be interpolated to daily.')
    values['hfr_inventory'] = hfr_info
    public = ROOT / 'output/data-collection/public-series-20260914T010236Z-corrected-v2/manifest.json'
    files.append(public)
    values['public_series_inventory'] = json.loads(public.read_text())
    report.para('Public-series inventory: archived FRED DTB3 cash-rate proxy and Fama–French daily/monthly factors. Pull dates, coverage and missing-value conventions are preserved in the public-series manifest and calculation JSON. Cash-accrual conversion and final benchmark specification are not frozen.')
    report.heading('Prioritized decisions before modeling')
    report.table(['Priority', 'Work required'], [('1', 'Resolve source/hash failures and missing evidence; inspect parser refusal queue.'), ('2', 'Independently reconcile WRDS daily coverage and opening-price/corporate-action/delisting availability.'), ('3', 'Review historical match conflicts and corporate eligibility; report resulting campaign attrition.'), ('4', 'Freeze human labeling codebook and reference-label protocol before AI intent evaluation.'), ('5', 'Choose campaign horizons and chronological splits from feasibility evidence, without optimizing on final-test returns.')])
    report.para('This run makes no provider calls and no AI eligibility or intent judgments. No backtest or final sample count is implied. Every descriptive statistic is traceable to the SQLite candidates/failures, stage reports, and frozen input manifests.')
    values['sources'] = {str(p.relative_to(ROOT)): sha(p) for p in files}
    (output / 'calculations.json').write_text(json.dumps(values, indent=2))
    (output / 'REPORT.md').write_text('\n\n'.join(report.md) + '\n')
    body = '\n'.join(report.web)
    for chart in output.glob('*.png'):
        body = body.replace('src="' + chart.name + '"', 'src="data:image/png;base64,' + base64.b64encode(chart.read_bytes()).decode('ascii') + '"')
    (output / 'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Activist 13D EDA</title><style>body{max-width:1150px;margin:40px auto;padding:0 24px;font:16px/1.55 system-ui;color:#182334}h1,h2{color:#173d65}table{border-collapse:collapse;width:100%;margin:20px 0;font-size:14px}th,td{border-bottom:1px solid #ccd5df;text-align:left;padding:8px}th{background:#edf2f7}img{max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px;font-size:12px}figcaption{color:#526174}</style><body>' + body + '</body></html>')
    return {'report': str(output / 'REPORT.html'), 'parsed_n': values['parsed_n'], 'failures_n': values['failures_n']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    print(json.dumps(run(parser.parse_args().run_dir.resolve())))
