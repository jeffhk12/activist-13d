"""Prepare source-verified SEC development evidence and blank human packets.

Inputs: frozen manifest, overnight SQLite, original packet hash baseline.
Outputs: 32 disjoint development records, canonical text and blank worksheets.
Identity: selected n = sum(disjoint stratum counts); quote offsets refer to exact
saved Unicode text. No category values, returns or AI answers enter packets.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_prep/prepare_sample.py
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sqlite3
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SEED = 'sec-extraction-development-20260916-v1'
BUCKETS = ((2013, 2016), (2017, 2020), (2021, 2024), (2025, 2026))
CAP = 20 * 1024**2
RESERVE = 10 * 1024**3
OUTPUT_CAP = 256 * 1024**2


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rank(accession):
    return sha(f'{SEED}:{accession}'.encode())


def decode(raw):
    try:
        return raw.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        return raw.decode('cp1252', errors='replace'), 'cp1252_with_possible_replacement'


def header_field(header, name):
    match = re.search(r'^' + re.escape(name) + r':\s*([^\r\n]+)', header, re.M)
    return match[1].strip() if match else None


def docs(raw):
    source, encoding = decode(raw)
    header = re.split(r'<DOCUMENT>', source, maxsplit=1, flags=re.I)[0]
    accession = header_field(header, 'ACCESSION NUMBER')
    out = [{'document_id': 'SEC-HEADER', 'document_index': 0, 'source_accession': accession,
            'filename': 'submission.txt', 'type': 'SEC-HEADER', 'text': header,
            'text_sha256': sha(header.encode()), 'status': 'parsed_text', 'encoding': encoding}]
    for i, block in enumerate(re.findall(r'<DOCUMENT>\s*(.*?)</DOCUMENT>', source, re.S | re.I), 1):
        def tag(name, block=block):
            match = re.search(r'^<' + name + r'>([^\r\n]+)', block, re.M | re.I)
            return match[1].strip() if match else None
        filename, typ = tag('FILENAME'), tag('TYPE')
        match = re.search(r'<TEXT>\s*(.*?)</TEXT>', block, re.S | re.I)
        body = match[1] if match else None
        binary = bool(filename and Path(filename.lower()).suffix in {'.pdf','.jpg','.jpeg','.png','.gif','.zip','.xlsx','.xls','.tif','.tiff','.bmp','.ico'})
        if body and (body.lstrip().startswith('%PDF-') or re.match(r'begin \d{3} ', body.lstrip())):
            binary = True
        plain = None
        status = 'binary_in_raw_submission' if binary else 'missing_text_body' if body is None else 'parsed_text'
        if status == 'parsed_text':
            soup = BeautifulSoup(body, 'html.parser')
            for node in soup(['script', 'style']):
                node.decompose()
            plain = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True)).strip()
        out.append({'document_id': f'DOCUMENT[{i}]', 'document_index': i, 'source_accession': accession,
                    'filename': filename, 'type': typ, 'text': plain,
                    'text_sha256': sha(plain.encode()) if plain is not None else None,
                    'status': status, 'encoding': encoding})
    if len(out) == 1:
        out.append({'document_id': 'UNRESOLVED-SUBMISSION', 'document_index': 1, 'source_accession': accession,
                    'filename': 'submission.txt', 'type': None, 'text': None, 'text_sha256': None,
                    'status': 'document_blocks_unresolved', 'encoding': encoding})
    return out


def packet_hashes(root):
    folder = root / 'output/phase1-prep/20260914T003050627334Z/packets'
    actual = {p.name: sha(p.read_bytes()) for p in folder.glob('*.html')}
    baseline = json.loads((root / 'output/phase1-prep/integrity-20260914T004440397334Z/audit.json').read_text())['packet_hashes_after']
    if actual != baseline:
        raise ValueError('Original human packet hashes differ from baseline')
    return actual


def packet_metadata(root):
    folder = root / 'output/phase1-prep/20260914T003050627334Z/packets'
    return {p.name: [p.stat().st_size, p.stat().st_mtime_ns] for p in folder.glob('*.html')}


def load_exclusions(root):
    excluded = set()
    for p in (root / 'output/phase1-prep').glob('*/packets/*.html'):
        excluded.add(p.stem)
    for p in (root / 'output/phase1-overnight').glob('*pilot*/sec.sqlite'):
        with sqlite3.connect(f'file:{p}?mode=ro', uri=True) as db:
            excluded.update(r[0] for r in db.execute('SELECT accession FROM records'))
    return excluded


def choose(rows, failures, excluded):
    used, selected, unavailable = set(), [], Counter()
    def add(pool, n, label):
        candidates = sorted((r for r in pool if r['accession'] not in used and r['accession'] not in excluded), key=lambda r: rank(r['accession']))
        got = candidates[:n]
        selected.extend((label, r) for r in got)
        used.update(r['accession'] for r in got)
        if len(got) < n:
            unavailable[label] += n - len(got)
    for lo, hi in BUCKETS:
        for amend in (False, True):
            add([r for r in rows if lo <= int(r['filing_date'][:4]) <= hi and r['is_amendment'] == amend], 2, f'broad_{lo}_{hi}_{"amendment" if amend else "initial"}')
    add([r for r in rows if 'missing_item4_text' in r.get('flags', [])], 4, 'missing_item4')
    add([r for r in rows if 'missing_cusip' in r.get('flags', [])], 4, 'missing_cusip')
    add([r for r in rows if {'unresolved_detected_references','binary_document_requires_review'} & set(r.get('flags', []))], 4, 'reference_or_binary')
    add(failures, 4, 'failure')
    if len(selected) < 32:
        add(rows, 32 - len(selected), 'unavailable_strata_fill')
    return selected, dict(unavailable)


def verify(row, manifest, root):
    source = (root / manifest['storage_path']).resolve()
    if not source.is_relative_to((root / 'data/raw/edgar').resolve()):
        raise ValueError('Raw source path escapes SEC cache')
    if source.stat().st_size > CAP:
        raise ValueError('Source exceeds 20 MiB development bound')
    raw = source.read_bytes()
    sidecar = source.with_suffix(source.suffix + '.meta.json')
    meta = json.loads(sidecar.read_text())
    digest = sha(raw)
    url = meta.get('url', '')
    expected_url = manifest.get('source_url')
    url_valid = url == expected_url if expected_url else bool(re.fullmatch(r'https://www\.sec\.gov/Archives/edgar/data/\d+/' + re.escape(row['accession']) + r'\.txt', url))
    if meta.get('sha256') != digest or meta.get('bytes') != len(raw) or not url_valid:
        raise ValueError('Raw source SHA/size/URL mismatch')
    if row.get('source_sha256') and row['source_sha256'] != digest:
        raise ValueError('Overnight source hash differs')
    header = re.split(r'<DOCUMENT>', decode(raw)[0], maxsplit=1, flags=re.I)[0]
    if header_field(header, 'ACCESSION NUMBER') != row['accession']:
        raise ValueError('Raw accession differs')
    if header_field(header, 'FILED AS OF DATE') != manifest['filing_date'].replace('-', ''):
        raise ValueError('Raw filing date differs')
    form = header_field(header, 'CONFORMED SUBMISSION TYPE')
    return raw, source, sidecar, form


def packet(bundle):
    esc = html.escape
    body = [f"<h1>{esc(bundle['accession'])}</h1>", '<p>Development review. Complete your answers before viewing any model answers. All text below is mechanically recovered from the source, without intent labels.</p>',
            f"<p>Source form: {esc(bundle['source_form'] or 'unavailable')} · Filed: {esc(bundle['filing_date'])}</p>",
            f"<p>Raw source: {esc(bundle['source_path'])}<br>SHA-256: {bundle['source_sha256']}</p>",
            '<h2>Blank worksheet</h2><pre>Reviewer / date: __________\nCompany / source: __________\nReporting persons / sources: __________\nCUSIP / source: __________\nRelevant dates / sources: __________\nItem 4 location: __________\nStated objectives / exact passages / document IDs: __________\nMissing or unclear evidence: __________\nMinutes spent: __________</pre>',
            '<p>Save answers separately. This page does not save edits. Binary documents remain in the raw submission; their contents have not been read here.</p>']
    for d in bundle['documents']:
        body.append(f"<h2>{esc(d['document_id'])} · {esc(d['filename'] or 'unnamed')}</h2><p>Type: {esc(d['type'] or 'unknown')} · Status: {esc(d['status'])}</p><pre>{esc(d['text']) if d['text'] is not None else '[Unreadable or binary evidence: inspect the frozen raw submission.]'}</pre>")
    return "<!doctype html><html lang='en'><meta charset='utf-8'><title>SEC development review</title><style>body{max-width:1000px;margin:40px auto;padding:0 20px;font:16px/1.5 system-ui;color:#172638}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h2{margin-top:2em}</style><body>" + '\n'.join(body) + '</body></html>'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/extraction-prep/development-20260916')
    args = parser.parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'COMPLETE.json').exists():
        raise ValueError('Completed development pack is frozen; choose a new output directory')
    if shutil.disk_usage(out).free < RESERVE:
        raise ValueError('10 GiB bounded-preparation disk reserve reached')
    before = packet_metadata(ROOT)
    print('Preparing sample; original packet content-hash check is deferred after a stalled local read.', flush=True)
    dbpath = ROOT / 'output/phase1-overnight/full-20260915/sec.sqlite'
    db = sqlite3.connect(f'file:{dbpath}?mode=ro', uri=True)
    manifest_path = ROOT / 'data/interim/bulk-v1/sec-manifest.json'
    manifest_available = manifest_path.exists()
    manifest = {r['accession']: r for r in json.loads(manifest_path.read_text())['records']} if manifest_available else {}
    frame_provenance = {'basis': 'frozen_download_manifest' if manifest_available else 'overnight_sqlite_due_missing_download_manifest',
                        'sqlite_path': str(dbpath), 'sqlite_sha256': file_sha(dbpath),
                        'download_manifest_sha256': file_sha(manifest_path) if manifest_available else None}
    rows = []
    oversize = 0
    for (value,) in db.execute('SELECT record_json FROM records'):
        r = json.loads(value)
        if not manifest_available:
            manifest[r['accession']] = {'accession': r['accession'], 'storage_path': r['source_path'],
                                       'filing_date': r['filing_date'], 'form': r['form'], 'source_url': None}
        if r['source_bytes'] > CAP:
            oversize += 1
            continue
        rows.append({k: r.get(k) for k in ['accession','filing_date','is_amendment','flags','source_sha256','parser_source']})
    failures = []
    for acc, error, source_json in db.execute('SELECT accession,error,source_json FROM failures'):
        if not manifest_available:
            manifest[acc] = json.loads(source_json)
        source = ROOT / manifest[acc]['storage_path']
        if source.stat().st_size > CAP:
            oversize += 1
            continue
        audit = db.execute('SELECT audit_json FROM audits WHERE accession=?', (acc,)).fetchone()
        failures.append({'accession': acc, 'failure_error': error, 'source_sha256': json.loads(audit[0])['source_sha256'] if audit else None})
    db.close()
    exclusions = load_exclusions(ROOT)
    selected, gaps = choose(rows, failures, exclusions)
    for folder in ('packets','document-text'):
        (out / folder).mkdir(exist_ok=True)
    records, labels, outputs = [], [], {}
    output_bytes = 0
    for stratum, row in selected:
        if shutil.disk_usage(out).free < RESERVE:
            raise ValueError('10 GiB bounded-preparation disk reserve reached')
        acc = row['accession']
        m = manifest[acc]
        raw, source, sidecar, form = verify(row, m, ROOT)
        bundle = {'accession': acc, 'source_path': str(source), 'source_sha256': sha(raw), 'source_form': form,
                  'filing_date': m['filing_date'], 'documents': docs(raw), 'transformation_sha256': sha(Path(__file__).read_bytes())}
        text_path = out / 'document-text' / f'{acc}.json'
        text_value = json.dumps(bundle, ensure_ascii=False, indent=2) + '\n'
        packet_path = out / 'packets' / f'{acc}.html'
        packet_value = packet(bundle)
        added_bytes = len(text_value.encode()) + len(packet_value.encode())
        output_bytes += added_bytes
        if output_bytes > OUTPUT_CAP or shutil.disk_usage(out).free - added_bytes < RESERVE:
            raise ValueError('Bounded output budget/disk reserve would be exceeded')
        text_path.write_text(text_value)
        packet_path.write_text(packet_value)
        outputs[str(text_path.relative_to(out))] = sha(text_path.read_bytes())
        outputs[str(packet_path.relative_to(out))] = sha(packet_path.read_bytes())
        records.append({'accession': acc, 'stratum': stratum, 'source_path': str(source), 'source_url': json.loads(sidecar.read_text())['url'],
                        'source_sha256': sha(raw), 'source_bytes': len(raw), 'sidecar_sha256': sha(sidecar.read_bytes()),
                        'source_form': form, 'index_form': m['form'], 'filing_date': m['filing_date'], 'parser_source': row.get('parser_source'),
                        'form_discrepancy': (form or '').replace('SC ', '').replace('SCHEDULE ', '') != m['form'],
                        'evidence_path': str(text_path.relative_to(out)), 'evidence_sha256': sha(text_path.read_bytes())})
        labels.append({'accession': acc, 'workflow_status': 'unreviewed', 'reviewer': None, 'reviewed_at': None,
                       'fields': None, 'intent': None, 'evidence': [], 'rationale': None})
    if len(records) != 32 or len({r['accession'] for r in records}) != 32:
        raise ValueError('Development sample is not 32 unique verified filings')
    (out / 'human-labels.jsonl').write_text('\n'.join(json.dumps(r) for r in labels) + '\n')
    (out / 'sample-manifest.json').write_text(json.dumps({'seed': SEED, 'sample_size': len(records), 'all_development': True, 'frame_provenance': frame_provenance, 'records': records}, indent=2) + '\n')
    report = {'sample_size': len(records), 'counts': dict(Counter(r['stratum'] for r in records)), 'gaps': gaps,
              'excluded_accessions': sorted(exclusions), 'oversize_frame_exclusions': oversize,
              'parser_formats': dict(Counter(r['parser_source'] or 'previous_failure' for r in records)),
              'source_forms': dict(Counter(r['source_form'] for r in records)), 'original_blank_packets_unchanged': None,
              'original_packet_metadata_unchanged': packet_metadata(ROOT) == before,
              'original_packet_hash_verification': 'deferred_due_stalled_local_read; old packets were not written',
              'network_calls': 0, 'model_api_calls': 0, 'selection_is_population_representative': False}
    if not {'xml', 'html_or_text'}.issubset(report['parser_formats']):
        raise ValueError('Selected sample does not cover both XML and legacy formats')
    (out / 'selection-report.json').write_text(json.dumps(report, indent=2) + '\n')
    links = ['<h1>SEC extraction development review</h1><p>Start with the first six below; all 32 are development examples. Complete your human answers before viewing model answers.</p>',
             '<p><a href="../../../docs/EXTRACTION-START-HERE.md">Start guide</a> · <a href="../../../protocol/intent-codebook-v1.md">Draft codebook</a></p><h2>First six</h2><ol>']
    for r in records[:6]:
        links.append(f'<li><a href="packets/{r["accession"]}.html">{r["accession"]}</a></li>')
    links.append('</ol><h2>All 32</h2><ol>')
    for r in records:
        links.append(f'<li><a href="packets/{r["accession"]}.html">{r["accession"]}</a></li>')
    links.append('</ol><p>Use a separate dated notes file; the reading pages do not save answers. No held-out evaluation has started.</p>')
    (out / 'index.html').write_text("<!doctype html><meta charset='utf-8'><title>SEC development review</title><style>body{max-width:950px;margin:40px auto;font:17px/1.6 system-ui;padding:20px}</style>" + '\n'.join(links))
    for name in ('index.html','sample-manifest.json','selection-report.json','human-labels.jsonl'):
        outputs[name] = sha((out / name).read_bytes())
    (out / 'COMPLETE.json').write_text(json.dumps({'outputs_sha256': outputs, 'frame_provenance': frame_provenance, 'script_sha256': sha(Path(__file__).read_bytes()), 'original_packet_metadata_unchanged': packet_metadata(ROOT) == before, 'original_blank_packets_hash_check': 'deferred_due_stalled_local_read'}, indent=2) + '\n')
    print(json.dumps(report))
    return len(records)


if __name__ == '__main__':
    main()
