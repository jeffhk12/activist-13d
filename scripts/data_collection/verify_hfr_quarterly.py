"""Tier: 1. Verify HFR report links, source integrity and saved run provenance.

Inputs: completed quarterly run, preserved archive, local report pages.
Outputs: frozen verification receipt. Identity: recorded hash == actual SHA-256;
every relative HTML link resolves to an existing project artifact.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_hfr_quarterly.py
"""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ingest_hfr_quarterly import OUT, ROOT, digest, encode, freeze


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href')


def main():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert digest(Path(manifest['raw_archive'])) == manifest['archive_sha256']
    assert digest(Path(__file__).with_name('ingest_hfr_quarterly.py')) == manifest['script_sha256']
    checked = 0
    for page in [ROOT / 'START-HERE.html', OUT / 'index.html', OUT / 'manager-review.html']:
        parser = Links()
        parser.feed(page.read_text())
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.exists(), f'Broken link in {page}: {link}'
            checked += 1
    files = ['ingest_hfr_quarterly.py', 'screen_hfr_quarterly.py',
             'report_hfr_quarterly.py', 'verify_hfr_quarterly.py',
             'test_hfr_quarterly.py', 'test_screen_hfr_quarterly.py']
    receipt = {'archive_hash_verified': True, 'local_links_checked': checked,
               'code_hashes': {name: digest(Path(__file__).with_name(name)) for name in files},
               'manifest_sha256': digest(OUT / 'manifest.json'),
               'screen_summary_sha256': digest(OUT / 'sec-screen/summary.json'),
               'validation_sha256': digest(OUT / 'validation.json')}
    freeze(OUT / 'verification.json', encode(receipt))
    print(encode(receipt))


if __name__ == '__main__':
    main()
