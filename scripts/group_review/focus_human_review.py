"""Tier 1: Create the 52-case human-first subset of the frozen 200-case pack.

Inputs: existing bundles and packets, local SEC cache. Outputs: separate focused
pack, blank worksheets, provenance and source checks. Selection is exactly the
intersection of Manager/fund language and Action language, never an intent label.
Identities: raw SHA and copied bytes match; each evidence span equals its quote.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/group_review/focus_human_review.py
"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import sys

from prepare import build_index

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from activist13d.local_paths import resolve_project_path

SOURCE = ROOT / 'review/archive/13d-group-review-20260922'
OUT = ROOT / 'review/archive/13d-human-review-52-20260923'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualifies(bundle):
    return {'Manager/fund language', 'Action language'} <= {
        item['cue'] for item in bundle['search_evidence']}


def main():
    assert qualifies({'search_evidence': [{'cue': 'Manager/fund language'}, {'cue': 'Action language'}]})
    assert not qualifies({'search_evidence': [{'cue': 'Action language'}]})
    assert not qualifies({'search_evidence': []})
    assert not OUT.exists(), 'Use a new dated output; never overwrite human reviews'
    originals = {str(p.relative_to(SOURCE)): sha(p) for p in SOURCE.rglob('*')
                 if p.is_file() and 'node_modules' not in p.parts}
    bundles = [json.loads(p.read_text()) for p in sorted((SOURCE / 'bundles').glob('*.json'))]
    selected = [b for b in bundles if qualifies(b)]
    assert len(bundles) == 200 and len(selected) == 52
    ids = [b['accession'] for b in selected]
    assert len(set(ids)) == 52
    blind = ROOT / 'research/runs/extraction-prep/development-20260916'
    blind_before = {p.name: sha(p) for p in [blind/'sample-manifest.json', blind/'human-labels.jsonl', blind/'COMPLETE.json']}
    excluded = {r['accession'] for r in json.loads((blind/'sample-manifest.json').read_text())['records']}
    assert not set(ids) & excluded
    for folder in ['bundles', 'packets']:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    verified_quotes = 0
    provenance = []
    for bundle in selected:
        accession = bundle['accession']
        assert all(bundle[field] == 'unreviewed' for field in [
            'final_filer_type', 'final_issuer_type', 'hedge_fund_status',
            'activist_event_status', 'outside_investor_status'])
        assert bundle['reviewer'] is None
        raw = resolve_project_path(bundle['source_path'], ROOT)
        assert sha(raw) == bundle['source_sha256']
        docs = {d['document_id']: d for d in bundle['documents']}
        for evidence in bundle['search_evidence']:
            text = docs[evidence['document_id']]['text']
            assert text[evidence['start']:evidence['end']] == evidence['quote']
            assert hashlib.sha256(text.encode()).hexdigest() == evidence['text_sha256']
            verified_quotes += 1
        copied = {}
        for folder, ext in [('bundles', 'json'), ('packets', 'html')]:
            relative = f'{folder}/{accession}.{ext}'
            shutil.copy2(SOURCE / relative, OUT / relative)
            assert sha(OUT / relative) == originals[relative]
            copied[relative] = originals[relative]
        provenance.append({'accession': accession, 'raw_sha256': bundle['source_sha256'], 'copied_sha256': copied})
    shutil.copy2(SOURCE/'GUIDE.html', OUT/'GUIDE.html')
    report = build_index(OUT)
    assert report['prepared'] == report['manager_and_action_phrase_intersection'] == 52
    page = (OUT/'index.html').read_text().replace('Grouped 13D development review', '52-candidate human-first review')
    page = page.replace('<h1>52-candidate human-first review</h1>',
        '<h1>52-candidate human-first review</h1><p>Selected from the 200-filing pack by the intersection of manager/fund and action-language search hits. All human judgments start unreviewed. Read each full packet, then enter your answers in the Excel workbook. Save a dated reviewed copy. The HTML pages do not save answers.</p>')
    (OUT/'index.html').write_text(page)
    with (OUT/'review-worksheet.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 52
    for row in rows:
        for field in ['final_security_type', 'final_issuer_type', 'final_filer_type', 'manager_identity', 'hedge_fund_status', 'outside_investor_status', 'activist_event_status']:
            assert row[field] == 'unreviewed'
        for field in ['specific_action', 'evidence_document_and_offsets', 'reviewer', 'review_date', 'notes']:
            assert row[field] == ''
    assert originals == {relative: sha(SOURCE/relative) for relative in originals}
    assert blind_before == {name: sha(blind/name) for name in blind_before}
    report.update(status='pack_prepared_workbook_pending', source_pack=str(SOURCE),
        selection_rule='Manager/fund language AND Action language',
        raw_sources_verified=52, exact_quotes_verified=verified_quotes,
        original_200_pack_unchanged=True, original_32_pack_unchanged=True,
        model_judgments_provided=0, outcomes_used=False, provenance=provenance)
    (OUT/'preparation.json').write_text(json.dumps(report, indent=2)+'\n')
    (OUT/'START-HERE.txt').write_text(
        '52-CANDIDATE HUMAN-FIRST REVIEW\n\n'
        '1. Open index.html to browse the 52 filings and full-text packets.\n'
        '2. Open Grouped-13D-Review.xlsx. Yellow cells are your answers.\n'
        '3. In Event review, record security type, issuer type, filer type,\n'
        '   relationship to the issuer, and whether a specific action is stated.\n'
        '4. In Filer review, distinguish the reporting fund from its manager.\n'
        '   Hedge-fund status needs supporting evidence and its effective date.\n'
        '5. Cite exact passages and document IDs. Note missing incorporated\n'
        '   documents; use Cannot determine when evidence is insufficient.\n'
        '6. Save a dated reviewed copy, then freeze it before model comparison.\n\n'
        'Selection: both manager/fund and action-language search hits in the\n'
        'existing 200-filing development pack. Hits are navigation aids, not\n'
        'verified activist/HF classifications. No prices or model judgments.\n'
        'The search-guided selection is purposive, not a held-out evaluation set.\n'
        'HTML pages do not save answers. Excel and CSV do not automatically sync;\n'
        'use the Excel workbook as your primary review record.\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'provenance'}, indent=2))


if __name__ == '__main__':
    main()
