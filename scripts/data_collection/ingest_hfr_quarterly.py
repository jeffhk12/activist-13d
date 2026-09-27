"""Build dated HFR manager observations from the supplied quarterly archive.

Inputs: nested vendor XLS/XLSX archives and their supplied manifest.
Outputs: immutable raw ZIP, hashed member inventory, per-snapshot identity rows,
manager observations, coverage report. Original workbooks remain inside raw ZIP.
Identity: ED = Main_Strategy exactly Event-Driven; activist = ED and Sub_Strategy
exactly Activist. Manager count = distinct nonblank Firm_ID, never fund-row count.
Dates: delivery-folder date is an UNVERIFIED availability proxy, distinct from
vendor DATESTAMP and actual receipt. No historical availability is certified.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/ingest_hfr_quarterly.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import xlrd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/Users/jefflu/Downloads/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip')
RAW = ROOT / 'data/raw/hfr/2026-09-24-quarterly'
OUT = ROOT / 'research/runs/hfr-quarterly/20260924-v1'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
FIELDS = ['Fund_ID', 'Fund', 'Firm_ID', 'Firm', 'Main_Strategy', 'Sub_Strategy',
          'Firm_SEC_Number', 'Firm_IARD_CRD_Number', 'Fund_Status', 'Principals',
          'Strategy_Code', 'Sub_Strategy_Code', 'Date_Added_to_DB', 'Website']


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def freeze(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode() if isinstance(content, str) else content
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Refusing changed frozen output: {path}')
    else:
        with path.open('xb') as handle:
            handle.write(data)


def column(index):
    value = ''
    while index:
        index, mod = divmod(index - 1, 26)
        value = chr(65 + mod) + value
    return value


def cell_text(value):
    if value is None or value == '':
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def read_funds(data, filename):
    """Read by header name; retain source row/column addresses and missing fields."""
    if filename.endswith('.xls'):
        book = xlrd.open_workbook(file_contents=data, on_demand=True)
        if book.nsheets != 1:
            raise ValueError('Unexpected multiple Fund sheets')
        sheet = book.sheet_by_index(0)
        headers = {column(i + 1): v for i, v in enumerate(sheet.row_values(0))}
        rows = [(i + 1, {headers[column(j + 1)]: cell_text(v)
                        for j, v in enumerate(sheet.row_values(i))})
                for i in range(1, sheet.nrows)]
        sheet_name = sheet.name
        book.release_resources()
    else:
        with ZipFile(io.BytesIO(data)) as book:
            workbook = ET.fromstring(book.read('xl/workbook.xml'))
            sheets = workbook.findall('m:sheets/m:sheet', NS)
            if len(sheets) != 1:
                raise ValueError('Unexpected multiple Fund sheets')
            sheet_name = sheets[0].get('name')
            rid = sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rels = ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))
            target = next(r.get('Target') for r in rels if r.get('Id') == rid)
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            shared = [''.join(s.itertext()) for s in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('m:si', NS)] if 'xl/sharedStrings.xml' in book.namelist() else []
            headers, rows = {}, []
            for _, row in ET.iterparse(book.open(target), events=['end']):
                if row.tag != '{' + NS['m'] + '}row':
                    continue
                values = {}
                for cell in row.findall('m:c', NS):
                    node = cell.find('m:v', NS)
                    raw = node.text if node is not None else None
                    val = shared[int(raw)] if cell.get('t') == 's' and raw else raw
                    if cell.get('t') == 'inlineStr':
                        val = ''.join(cell.find('m:is', NS).itertext())
                    if cell.find('m:f', NS) is not None:
                        raise ValueError('Unexpected formula in vendor Fund source')
                    values[re.sub(r'\d', '', cell.get('r'))] = cell_text(val)
                if not headers:
                    headers = values
                else:
                    rows.append((int(row.get('r')), {headers[c]: v for c, v in values.items()}))
                row.clear()
    required = {'Fund_ID', 'Fund', 'Firm_ID', 'Firm', 'Main_Strategy', 'Sub_Strategy'}
    if not required <= set(headers.values()) or len(set(headers.values())) != len(headers):
        raise ValueError('Missing or duplicate source headers')
    records = [{'excel_row': n, 'fields': {k: row.get(k) for k in FIELDS}}
               for n, row in rows if any(row.values())]
    return sheet_name, headers, records


def summarize(records):
    ed = [r for r in records if r['fields']['Main_Strategy'] == 'Event-Driven']
    activists = [r for r in ed if r['fields']['Sub_Strategy'] == 'Activist']
    def firm_ids(rows):
        return {r['fields']['Firm_ID'] for r in rows if r['fields']['Firm_ID']}
    ids = [r['fields']['Fund_ID'] for r in records]
    return {'all_fund_rows': len(records), 'event_driven_fund_rows': len(ed),
            'event_driven_firm_ids': len(firm_ids(ed)), 'activist_fund_rows': len(activists),
            'activist_firm_ids': len(firm_ids(activists)),
            'missing_firm_id_rows': sum(not r['fields']['Firm_ID'] for r in records),
            'duplicate_fund_id_excess_rows': sum(n - 1 for k, n in Counter(ids).items() if k and n > 1),
            'missing_fund_id_rows': sum(not v for v in ids),
            'event_driven_substrategies': dict(Counter(r['fields']['Sub_Strategy'] for r in ed)),
            'fund_statuses': dict(Counter(r['fields']['Fund_Status'] or '(blank)' for r in records))}


def manager_rows(records, quarter):
    grouped = defaultdict(list)
    for row in records:
        if row['fields']['Main_Strategy'] == 'Event-Driven' and row['fields']['Firm_ID']:
            grouped[row['fields']['Firm_ID']].append(row)
    return [{'quarter': quarter, 'firm_id': firm_id,
             'names': sorted({r['fields']['Firm'] for r in rows if r['fields']['Firm']}),
             'fund_names': sorted({r['fields']['Fund'] for r in rows if r['fields']['Fund']}),
             'fund_rows': [r['excel_row'] for r in rows],
             'substrategies': sorted({r['fields']['Sub_Strategy'] for r in rows if r['fields']['Sub_Strategy']}),
             'crd': sorted({r['fields']['Firm_IARD_CRD_Number'] for r in rows if r['fields']['Firm_IARD_CRD_Number']}),
             'sec': sorted({r['fields']['Firm_SEC_Number'] for r in rows if r['fields']['Firm_SEC_Number']})}
            for firm_id, rows in sorted(grouped.items())]


def build(source, out):
    archive_hash = digest(source)
    frozen = RAW / source.name
    RAW.mkdir(parents=True, exist_ok=True)
    if not frozen.exists():
        with source.open('rb') as src, frozen.open('xb') as dst:
            shutil.copyfileobj(src, dst)
    if digest(frozen) != archive_hash:
        raise ValueError('Raw copy hash mismatch')
    snapshots, all_managers = [], []
    with ZipFile(frozen) as outer:
        supplied = list(csv.DictReader(io.StringIO(outer.read('MANIFEST.csv').decode('utf-8-sig'))))
        names = [r['entry_name'] for r in supplied]
        if len(set(names)) != len(names) or set(names) != {n for n in outer.namelist() if n.endswith('.zip')}:
            raise ValueError('Manifest/archive disagreement')
        expected = [f'{y}Q{q}' for y in range(2018, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)]
        if sorted(r['quarter'] for r in supplied) != expected:
            raise ValueError('Quarter coverage gap or duplicate')
        for item in supplied:
            nested = outer.read(item['entry_name'])
            if len(nested) != int(item['bytes']):
                raise ValueError('Manifest size mismatch')
            delivery = datetime.strptime(item['delivery_folder'], '_%m%d%Y').date().isoformat()
            if item['entry_name'][7:17] != delivery:
                raise ValueError('Filename/delivery-folder disagreement')
            with ZipFile(io.BytesIO(nested)) as inner:
                inventory = []
                for member in inner.infolist():
                    if member.is_dir():
                        continue
                    content = inner.read(member)
                    inventory.append({'member': member.filename, 'bytes': len(content),
                                      'sha256': hashlib.sha256(content).hexdigest()})
                stamp_raw = inner.read('DATESTAMP.txt').decode().strip()
                stamp = datetime.strptime(stamp_raw, '%Y%m%d').date().isoformat()
                candidates = [n for n in inner.namelist() if n in {'Excel_Fund.xls', 'HFR_HFRDB_EXCEL_Fund.xlsx'}]
                if len(candidates) != 1:
                    raise ValueError('Ambiguous/missing Fund workbook')
                member = candidates[0]
                data = inner.read(member)
                sheet, headers, records = read_funds(data, member)
            metadata = {'quarter': item['quarter'], 'vendor_datestamp': stamp,
                        'delivery_date_proxy': delivery, 'availability_verified': False,
                        'actual_historical_receipt': None, 'local_ingest_date': '2026-09-24',
                        'supplied_manifest_row': item, 'archive_member': item['entry_name'],
                        'nested_sha256': hashlib.sha256(nested).hexdigest(),
                        'fund_member': member, 'fund_sha256': hashlib.sha256(data).hexdigest(),
                        'sheet': sheet, 'source_columns': headers,
                        'unavailable_selected_fields': sorted(set(FIELDS) - set(headers.values())),
                        'members': inventory, **summarize(records)}
            freeze(out / 'snapshots' / f'{item["quarter"]}.json', encode({'metadata': metadata, 'funds': records}))
            snapshots.append(metadata)
            all_managers.extend(manager_rows(records, item['quarter']))
            print(item['quarter'], metadata['all_fund_rows'], metadata['event_driven_firm_ids'], metadata['activist_firm_ids'], flush=True)
    ed_ids = {m['firm_id'] for m in all_managers}
    act_ids = {m['firm_id'] for m in all_managers if 'Activist' in m['substrategies']}
    latest_ed = {m['firm_id'] for m in all_managers if m['quarter'] == '2026Q3'}
    latest_act = {m['firm_id'] for m in all_managers if m['quarter'] == '2026Q3' and 'Activist' in m['substrategies']}
    summary = {'snapshot_count': len(snapshots), 'event_driven_firm_ids_union': len(ed_ids),
               'activist_firm_ids_union': len(act_ids),
               'historical_ed_ids_outside_latest_ed': sorted(ed_ids - latest_ed),
               'historical_activist_ids_outside_latest_activist': sorted(act_ids - latest_act),
               'all_fund_observations': sum(s['all_fund_rows'] for s in snapshots)}
    manifest = {'raw_archive': str(frozen), 'archive_sha256': archive_hash,
                'xlrd_version': xlrd.__version__, 'script_sha256': digest(Path(__file__)),
                'summary': summary, 'snapshots': snapshots}
    freeze(out / 'manifest.json', encode(manifest))
    freeze(out / 'managers.json', encode(all_managers))
    rows = ''.join(f'<tr><td>{s["quarter"]}</td><td>{s["vendor_datestamp"]}</td><td>{s["delivery_date_proxy"]}</td><td>{s["all_fund_rows"]}</td><td>{s["event_driven_firm_ids"]}</td><td>{s["activist_firm_ids"]}</td></tr>' for s in snapshots)
    report = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Historical HFR universe</title><style>body{{font:17px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#203448}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;text-align:left;border-bottom:1px solid #ddd}}</style><h1>Historical HFR universe</h1><p>35 supplied quarterly snapshots, 2018 Q1–2026 Q3. {len(ed_ids)} distinct Event-Driven Firm_IDs and {len(act_ids)} Activist Firm_IDs across snapshots.</p><p>{len(ed_ids-latest_ed)} historically observed Event-Driven Firm_IDs are outside the latest Event-Driven set; {len(act_ids-latest_act)} historically observed Activist Firm_IDs are outside the latest Activist set. This can reflect coverage or classification changes; it does not establish liquidation.</p><p>Delivery dates are unverified availability proxies. Vendor datestamps and delivery-folder dates are retained separately. These are within-quarter snapshots, not quarter-end holdings. No 2013–2017 universe is supplied. Counts are HFR IDs, not independently verified legal managers. Share classes remain separate fund rows. No return, performance or investment-intent analysis was performed.</p><table><tr><th>Quarter</th><th>Vendor date</th><th>Delivery proxy</th><th>All fund rows</th><th>ED managers</th><th>Activist managers</th></tr>{rows}</table><p><a href="manifest.json">Hashed source inventory</a> · <a href="managers.json">Dated manager observations</a> · <a href="../../../docs/HFR-QUARTERLY-HANDOFF-20260924.md">Continuation handoff</a> · <a href="../../../../START-HERE.html">Project home</a></p><p>Raw archive SHA-256: {html.escape(archive_hash)}</p></html>'''
    freeze(out / 'index.html', report)
    print(encode(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    build(args.source, args.out)
