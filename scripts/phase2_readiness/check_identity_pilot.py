"""Tier: 0. Check generated pilot links, blank worksheets and JavaScript syntax.
Inputs: generated six-case pack. Output: QA receipt; no human/model answers.
Run: project Python this file.
"""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from lxml import html
ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'review/drafts/ownership-identity-pilot-20260925'
OUT = ROOT / 'research/runs/phase2-identity-pilot/20260925-v1/qa'
OUT.mkdir(exist_ok=True)
node = shutil.which('node')
assert node, 'Node needed for JavaScript syntax validation'
count = 0
for path in sorted(PACK.glob('*.html')):
    tree = html.fromstring(path.read_text())
    for href in tree.xpath('//a/@href'):
        if not href.startswith(('https://', '#')):
            assert (path.parent / href).exists(), href
    for area in tree.xpath('//textarea'):
        assert not area.text_content()
    scripts = tree.xpath('//script/text()')
    if scripts:
        target = OUT / (path.stem + '.js')
        target.write_text('\n'.join(scripts))
        subprocess.run([node, '--check', str(target)], check=True, capture_output=True)
        count += 1
assert count == 6
protocols = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'research/protocol/ownership-identity-pilot-v1.md', ROOT/'research/protocol/ownership-identity-prompt-v1.md']}
(OUT / 'checks.json').write_text(json.dumps(dict(case_pages=6, local_links='passed', blank_worksheets='passed', javascript_syntax='passed', protocol_hashes=protocols), indent=2))
print('Six pages: links, blank answers and JavaScript syntax passed; protocol hashes saved.')
