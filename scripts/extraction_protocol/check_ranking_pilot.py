"""Check source-only pilot navigation, text, blanks, hashes and JS syntax.

Inputs: new draft pilot and recorded source bundles/output hashes; no outcomes.
Outputs: QA receipt under its run. Identity: HTML source text == canonical text;
all human observations blank; validation cases have no substantive review pages.
Tier: 1. Run with project Python and PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8:
 .venv/bin/python scripts/extraction_protocol/check_ranking_pilot.py
"""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT/'review/drafts/ranking-llm-pilot-20261025'
RUN = ROOT/'research/runs/ranking-llm-pilot/20261025-v2'


def main():
    manifests = json.loads((RUN/'output-hashes.json').read_text())
    for name, expected in manifests.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    selection = json.loads((RUN/'sample-manifest.json').read_text())['selection']
    source_documents = 0
    for r in selection['discovery']:
        a = r['accession']
        tree = html.fromstring((PACK/'discovery'/f'{a}.html').read_bytes())
        bundle = json.loads((PACK/'discovery/evidence'/f'{a}.json').read_text())
        documents = {d['document_id']: d for d in bundle['documents']}
        for pre in tree.xpath('//pre[@data-document]'):
            d = documents[pre.get('data-document')]
            assert pre.text_content() == d['text'], (a, d['document_id'])
            assert hashlib.sha256(pre.text_content().encode()).hexdigest() == d['text_sha256']
            source_documents += 1
        for area in tree.xpath('//textarea'):
            assert area.text_content() == ('[]' if area.get('id') == 'evidence' else '')
        assert not tree.xpath('//input[@checked]')
        config = json.loads(tree.get_element_by_id('config').text)
        assert config['accession'] == a and config['bundle_sha256'] == hashlib.sha256((PACK/'discovery/evidence'/f'{a}.json.gz').read_bytes()).hexdigest()
    pages = list(PACK.rglob('*.html'))
    for path in pages:
        tree = html.fromstring(path.read_bytes())
        for href in tree.xpath('//a/@href') + tree.xpath('//script[@src]/@src'):
            if not href.startswith(('https:', 'http:', '#')):
                assert (path.parent/href).is_file(), (path, href)
    assert len(list((PACK/'discovery').glob('*.html'))) == 10
    assert not list((PACK/'validation-reserved').glob('0*.html'))
    with (RUN/'financial-checks/field-review.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 90 and len({r['row_id'] for r in rows}) == 10
    assert all(r['review_status'] == 'unreviewed' and not r['public_release_datetime'] for r in rows)
    subprocess.run(['node','--check',str(PACK/'assets/review.js')],check=True,capture_output=True)
    subprocess.run(['node',str(ROOT/'scripts/extraction_protocol/test_ranking_human_review.mjs')],check=True,capture_output=True)
    receipt = {'source_documents_match_canonical_text': source_documents,
               'discovery_pages_blank': 10, 'validation_source_pages_released': 0,
               'local_links_and_output_hashes': 'passed', 'financial_fields_unreviewed': 90,
               'javascript_syntax_and_invented_unicode_export_checks': 'passed',
               'browser_visual_verification': 'unavailable: browser policy blocks file URLs; no workaround attempted',
               'no_real_human_answers_or_model_labels_generated': True}
    output = RUN/'qa/checks.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
