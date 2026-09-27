"""Tier 1: validate explanatory report links, evidence and deterministic rendering.
Inputs: report.html, evidence.json, builder. Output: console validation only.
Identity: a local href resolves to an existing file; repeated rendering is byte-identical.
Run with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 project .venv/bin/python.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import runpy

HERE = Path(__file__).resolve().parent
report = HERE.parent/'report.html'
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids
            self.ids.add(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])

before = report.read_bytes()
runpy.run_path(str(HERE/'build_report.py'), run_name='__main__')
assert report.read_bytes() == before
parser = Links()
parser.feed(before.decode())
for href in parser.links:
    parts = urlsplit(href)
    if parts.scheme:
        assert parts.scheme in ('http','https')
    elif parts.path:
        assert (report.parent/unquote(parts.path)).exists(), href
    elif parts.fragment:
        assert parts.fragment in parser.ids, href
evidence = json.loads((HERE/'evidence.json').read_text())
assert len(evidence) == 10
assert all(len(x['source_sha256']) == len(x['text_sha256']) == 64 for x in evidence)
print('PASS: deterministic rendering, all local links/anchors, ten quotation records and hash shapes.')
