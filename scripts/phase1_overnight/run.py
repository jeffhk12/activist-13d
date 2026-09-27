"""Resumable offline SEC audit, parsing, and Phase 1 feasibility orchestration.

Inputs: frozen SEC manifest/submissions and WRDS cache. Outputs: isolated SQLite
candidate records, failures, provenance, coverage and link reports; no labels.
Identity: manifest n = parsed candidates + explicitly failed records + pending.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/run.py --output research/runs/phase1-overnight/RUN
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from activist13d.local_paths import resolve_project_path
MANIFEST = ROOT / 'data/interim/bulk-v1/sec-manifest.json'
STOP = False
RESERVE = 20 * 1024**3


def offline(*args, **kwargs):
    raise RuntimeError('Network disabled for offline Phase 1 run')


socket.socket.connect = offline
socket.create_connection = offline


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def check_space(path):
    if shutil.disk_usage(path).free < RESERVE:
        raise RuntimeError('disk_guard: less than 20 GiB free')


def packet_hashes():
    folder = ROOT / 'research/runs/phase1-prep/20260914T003050627334Z/packets'
    actual = {p.name: digest(p) for p in folder.glob('*.html')}
    baseline = json.loads((ROOT / 'research/runs/phase1-prep/integrity-20260914T004440397334Z/audit.json').read_text())['packet_hashes_after']
    if actual != baseline:
        raise RuntimeError('Original blank review packets differ from baseline')
    return actual


def verify(row):
    path = resolve_project_path(row['storage_path'], ROOT)
    if not path.is_relative_to((ROOT / 'data/raw/edgar').resolve()):
        raise ValueError('Source path outside raw SEC cache')
    meta_path = path.with_suffix(path.suffix + '.meta.json')
    meta = json.loads(meta_path.read_text())
    sha = digest(path)
    if meta.get('sha256') != sha or meta.get('bytes') != path.stat().st_size or meta.get('url') != row['source_url']:
        raise ValueError('Source hash/size/URL mismatch')
    with path.open('rb') as f:
        header = f.read(256 * 1024).split(b'<DOCUMENT>', 1)[0].decode('latin-1')
    accession = re.search(r'ACCESSION NUMBER:\s*([\d-]+)', header)
    date = re.search(r'FILED AS OF DATE:\s*(\d{8})', header)
    form = re.search(r'CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)', header)
    if not accession or accession[1] != row['accession']:
        raise ValueError('Header accession mismatch')
    if not date or date[1] != row['filing_date'].replace('-', ''):
        raise ValueError('Header filing date mismatch')
    if not form or form[1].strip().replace('SCHEDULE ', '').replace('SC ', '') != row['form']:
        raise ValueError('Header form mismatch')
    return {'source_path': str(path.relative_to(ROOT)), 'source_sha256': sha,
            'sidecar_sha256': digest(meta_path), 'source_bytes': path.stat().st_size}


def compact(record, row, audit):
    record.update(audit, filing_date=row['filing_date'], index_filing_date=row['filing_date'],
                  form=row['form'], is_amendment=row['form'].endswith('/A'))
    flags = ['missing_' + k for k in ('cusip', 'item4_text', 'event_date', 'filers', 'subjects', 'acceptance_datetime_et') if not record.get(k)]
    refs = record.get('evidence_bundle', {})
    record['unresolved_detected_references'] = [r['reference'] for k in ('referenced_sections', 'referenced_exhibits') for r in refs.get(k, []) if not r.get('text')]
    if record['unresolved_detected_references']:
        flags.append('unresolved_detected_references')
    if any(d.get('text_status') != 'parsed_text' for d in record['documents']):
        flags.append('binary_document_requires_review')
    for doc in record['documents']:
        doc.pop('text', None)
    record.pop('xml_fields', None)
    record.pop('evidence_bundle', None)
    record.update(flags=flags, eligibility='not_validated', intent_labels=None,
                  evidence_note='Item 4 is a parser candidate; full text remains in raw source. Reference detector is incomplete.')
    return record


def parse_one(row, audit):
    from activist13d.edgar.submission import parse_submission
    path = ROOT / audit['source_path']
    if path.stat().st_size > 20 * 1024**2:
        raise ValueError('Oversize source requires separate bounded review (>20 MiB)')
    record = parse_submission(path.read_bytes())
    if record['accession'] != row['accession']:
        raise ValueError('Parsed accession mismatch')
    return compact(record, row, audit)


def stop(signum, frame):
    global STOP
    STOP = True


def audit_indexes(rows, output):
    expected = {}
    for row in rows:
        path = row['index_source_path']
        sha = row['index_source_sha256']
        if path in expected and expected[path] != sha:
            raise ValueError('Conflicting index hashes in manifest')
        expected[path] = sha
    result = []
    for relative, sha in sorted(expected.items()):
        path = (ROOT / relative).resolve()
        if not path.is_relative_to((ROOT / 'data/raw/edgar').resolve()):
            raise ValueError('Index path outside raw SEC cache')
        actual = digest(path)
        meta_path = path.with_suffix(path.suffix + '.meta.json')
        meta = json.loads(meta_path.read_text())
        if actual != sha or meta.get('sha256') != actual or meta.get('bytes') != path.stat().st_size:
            raise ValueError('Index provenance mismatch: ' + relative)
        result.append({'path': relative, 'sha256': actual, 'sidecar_sha256': digest(meta_path)})
    save(output / 'index-audit.json', result)


def run(output, pilot=0):
    import fcntl
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    check_space(output)
    packets = packet_hashes()
    source_files = sorted(Path(__file__).parent.glob('*.py')) + [ROOT / 'src/activist13d/edgar/submission.py', ROOT / 'requirements-pilot-lock.txt', Path(__file__).with_name('environment-lock.txt')]
    provenance = {'manifest_sha256': digest(MANIFEST), 'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in source_files}, 'python': sys.version, 'pilot_n': pilot}
    provpath = output / 'provenance.json'
    if provpath.exists() and json.loads(provpath.read_text()) != provenance:
        raise ValueError('Resume refused: inputs/code/environment changed; use a new output directory')
    save(provpath, provenance)
    snapshot = output / 'code'
    snapshot.mkdir(exist_ok=True)
    for p in source_files:
        shutil.copy2(p, snapshot / p.name)
    rows = json.loads(MANIFEST.read_text())['records']
    if len({r['accession'] for r in rows}) != len(rows):
        raise ValueError('Duplicate accession in manifest')
    audit_indexes(rows, output)
    if pilot:
        rows = [rows[i * (len(rows) - 1) // max(1, pilot - 1)] for i in range(min(pilot, len(rows)))]
    dbpath = output / 'sec.sqlite'
    db = sqlite3.connect(dbpath)
    db.execute('CREATE TABLE IF NOT EXISTS records(accession TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS failures(accession TEXT PRIMARY KEY, error TEXT NOT NULL, source_json TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS audits(accession TEXT PRIMARY KEY, audit_json TEXT NOT NULL)')
    done = {r[0] for r in db.execute('SELECT accession FROM records UNION SELECT accession FROM failures')}
    started = time.monotonic()
    state = {'status': 'running', 'stage': 'sec_audit_parse', 'pid': os.getpid(), 'started_at': utc(), 'total': len(rows), 'network_calls': 0, 'model_api_calls': 0,
             'processed': len(done), 'parsed': db.execute('SELECT count(*) FROM records').fetchone()[0],
             'failures': db.execute('SELECT count(*) FROM failures').fetchone()[0]}
    save(output / 'progress.json', state)
    try:
        for row in rows:
            if STOP:
                break
            if row['accession'] in done:
                existing = db.execute('SELECT audit_json FROM audits WHERE accession=?', (row['accession'],)).fetchone()
                if not existing and db.execute('SELECT 1 FROM records WHERE accession=?', (row['accession'],)).fetchone():
                    raise ValueError('Parsed record lacks source audit; resume refused')
                if existing and verify(row) != json.loads(existing[0]):
                    raise ValueError('Previously audited source changed; resume refused')
                continue
            check_space(output)
            try:
                audit = verify(row)
                db.execute('INSERT OR REPLACE INTO audits VALUES (?,?)', (row['accession'], json.dumps(audit)))
                with tempfile.TemporaryFile() as parsed_output, tempfile.TemporaryFile() as errors:
                    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--one'],
                                            input=json.dumps({'row': row, 'audit': audit}), text=True,
                                            stdout=parsed_output, stderr=errors, timeout=90, cwd=ROOT)
                    if result.returncode:
                        errors.seek(max(0, errors.tell() - 2000))
                        raise ValueError('Parser subprocess: ' + errors.read(2000).decode('utf-8', errors='replace'))
                    parsed_output.seek(0)
                    record = json.loads(parsed_output.read(32 * 1024**2))
                db.execute('INSERT INTO records VALUES (?,?)', (row['accession'], json.dumps(record)))
            except Exception as exc:
                db.execute('INSERT INTO failures VALUES (?,?,?)', (row['accession'], str(exc), json.dumps(row)))
            db.commit()
            done.add(row['accession'])
            state.update(processed=len(done), parsed=db.execute('SELECT count(*) FROM records').fetchone()[0],
                         failures=db.execute('SELECT count(*) FROM failures').fetchone()[0],
                         updated_at=utc(), elapsed_seconds=round(time.monotonic() - started, 2))
            save(output / 'progress.json', state)
            if len(done) % 100 == 0:
                print(json.dumps(state), flush=True)
        db.close()
        if STOP:
            state['status'] = 'stopped'
        elif pilot:
            state['status'] = 'pilot_completed'
            state['database_bytes'] = dbpath.stat().st_size
        else:
            state.update(stage='wrds_audit', updated_at=utc())
            save(output / 'progress.json', state)
            from wrds_audit import run as audit_wrds
            wrds = audit_wrds(output / 'wrds', stop=lambda: STOP)
            if STOP:
                state['status'] = 'stopped'
            else:
                state.update(stage='candidate_links', updated_at=utc())
                save(output / 'progress.json', state)
                from link_candidates import run as link
                links = link(dbpath, output / 'links')
                state.update(stage='eda_report', updated_at=utc())
                save(output / 'progress.json', state)
                check_space(output)
                from eda import run as eda_report
                eda = eda_report(output)
                save(output / 'summary.json', {'sec': state.copy(), 'wrds': wrds, 'links': links,
                                              'eda': eda,
                                              'original_blank_packets_unchanged': packet_hashes() == packets})
                state.update(status='completed_with_review_required', stage='finished')
                (output / 'REPORT.md').write_text('# Offline Phase 1 feasibility run\n\n'
                    f"SEC processed: {state.get('processed')}; parsed: {state.get('parsed')}; failures requiring review: {state.get('failures')}.\n\n"
                    'See sec.sqlite for source-backed parser candidates and failures, wrds/ for coverage audit, and links/ for candidate groups and historical matches.\n\n'
                    'No corporate eligibility, campaign identity, economic intent, or trading readiness has been validated. WRDS vendor completeness remains unverified. External incorporated evidence is not certified complete. Original human-review packets remain unchanged. No network or model APIs were used.\n')
        state['original_blank_packets_unchanged'] = packet_hashes() == packets
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        state['updated_at'] = utc()
        save(output / 'progress.json', state)
        lock.close()
    print(json.dumps(state), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    p.add_argument('--pilot', type=int, default=0)
    p.add_argument('--one', action='store_true')
    args = p.parse_args()
    if args.one:
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
        value = json.load(sys.stdin)
        print(json.dumps(parse_one(value['row'], value['audit'])))
    elif args.output:
        run(args.output.resolve(), args.pilot)
    else:
        p.error('--output is required')
