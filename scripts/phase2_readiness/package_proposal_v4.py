"""Tier: 0. Package existing proposal prose as standalone review HTML.
Inputs: proposal V4 and direction-review Markdown, dated evidence documents.
Outputs: HTML/Markdown review package and source-hash receipt; no new estimates.
Run: project Python scripts/phase2_readiness/package_proposal_v4.py
"""
import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/proposal-review/20260926-v4'
PHONE = Path('/Users/jefflu/Library/CloudStorage/OneDrive-Personal/Project-Transfer/Activist-13D/2026-09-26-Proposal-v4')
DOCS = ROOT / 'research/docs'
OUT.mkdir(parents=True, exist_ok=True)


def inline(s):
    s = escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', s)


def render(text):
    lines, blocks, i = text.splitlines(), [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('#'):
            n = len(s) - len(s.lstrip('#'))
            blocks.append(f'<h{n}>' + inline(s[n:].strip()) + f'</h{n}>')
            i += 1
        elif s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in row):
                    rows.append(row)
                i += 1
            blocks.append('<div class="table"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>' for row in rows[1:]) + '</tbody></table></div>')
        elif re.match(r'^\d+\. ', s):
            items = []
            while i < len(lines) and re.match(r'^\d+\. ', lines[i].strip()):
                items.append(re.sub(r'^\d+\. ', '', lines[i].strip()))
                i += 1
            blocks.append('<ol>' + ''.join('<li>' + inline(s) + '</li>' for s in items) + '</ol>')
        else:
            p = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|')) and not re.match(r'^\d+\. ', lines[i]):
                p.append(lines[i].strip())
                i += 1
            blocks.append('<p>' + inline(' '.join(p)) + '</p>')
    return '\n'.join(blocks)


style = 'body{font:17px/1.6 Georgia,serif;color:#203244;background:#eef2f5;margin:0}main{max-width:970px;margin:25px auto;padding:36px 44px;background:white}h1,h2,h3,nav{font-family:system-ui,sans-serif}h1{font-size:31px;line-height:1.25}h2{font-size:22px;border-top:1px solid #ccd7df;padding-top:20px;margin-top:32px}h3{font-size:18px}nav{font-size:14px;display:flex;gap:20px;flex-wrap:wrap}a{color:#175d8d}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font:14px/1.5 system-ui}th,td{padding:12px;text-align:left;vertical-align:top;border:1px solid #d9e1e7}th{background:#e9f1f6}li{margin:12px 0}code{overflow-wrap:anywhere}@media(max-width:650px){main{margin:0;padding:20px}body{font-size:16px}}@media print{body{background:white;font-size:11pt}main{max-width:none;margin:0;padding:0}nav{display:none}h1{font-size:23pt}h2{font-size:15pt;break-after:avoid}h3{break-after:avoid}tr{break-inside:avoid}table{font-size:9pt}.table{overflow:visible}@page{size:A4;margin:18mm}}'
files = [('PROFESSOR-PROPOSAL-v4.md', 'proposal-v4.html', 'Proposal V4'), ('PROJECT-DIRECTION-REVIEW-v4.md', 'direction-review.html', 'Project direction review')]
for source, target, title in files:
    md = (DOCS / source).read_text()
    result = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + title + '</title><style>' + style + '</style></head><body><main><nav><a href="proposal-v4.html">Professor proposal</a><a href="direction-review.html">What changed</a><a href="' + source + '">Markdown source</a></nav>' + render(md) + '</main></body></html>'
    (OUT / target).write_text(result)
    shutil.copyfile(DOCS / source, OUT / source)
    tree = html.fromstring(result)
    assert len(tree.xpath('//h1')) == 1
    assert len(tree.xpath('//h2')) >= 5
    assert tree.xpath('//table')
    assert not tree.xpath('//script|//iframe')
for p in OUT.glob('*.html'):
    for href in html.fromstring(p.read_text()).xpath('//a/@href'):
        assert (OUT / href).is_file(), href
paths = [DOCS / x[0] for x in files] + [DOCS / 'PROFESSOR-PROPOSAL-v3.md', DOCS / 'PHASE1-FINAL-CONCLUSION-20260924.md', DOCS / 'PHASE2-DETAILED-PROGRESS-20260925.md', ROOT / 'research/protocol/phase1-long-horizon-v1.md', ROOT / 'research/protocol/ownership-identity-pilot-v1.md', ROOT / 'research/runs/phase2-readiness/20260924-full-v1/progress.json', ROOT / 'research/runs/phase2-readiness/20260924-full-v1/field-coverage.json', ROOT / 'research/runs/phase2-identity-pilot/20260925-v1/checks.json']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {'date': '2026-09-26', 'status': 'draft_for_user_and_professor_review_not_sent', 'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths}, 'artifact_hashes': {p.name: sha(p) for p in OUT.iterdir() if p.suffix in {'.html', '.md'}}, 'checks': 'HTML parsed; headings, tables, local links and absence of active content checked; source counts reused without new estimates'}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
(OUT / '00-START-HERE.txt').write_text('Proposal V4 — September 26, 2026\n\nRead direction-review.html for the plain-English changes.\nRead proposal-v4.html for the professor-facing proposal.\nBoth HTML files are standalone and printable. Markdown versions are included.\nDraft for review; not sent to the professor. No returns or frozen protocols changed.\nLocal OneDrive copy only; remote delivery is not independently verified.\n')
PHONE.mkdir(parents=True, exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():
        shutil.copyfile(p, PHONE / p.name)
        assert sha(p) == sha(PHONE / p.name)
print(json.dumps({'local': str(OUT), 'onedrive_local': str(PHONE), 'checks': 'passed'}, indent=2))
