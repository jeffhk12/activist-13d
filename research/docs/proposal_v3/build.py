"""Tier: 0. Render the V3 proposal and direction review as a local HTML page.

Inputs: canonical V3 and direction-review Markdown. Output: index.html.
Identity: preserve source prose; escape HTML and render the used Markdown subset.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python research/docs/proposal_v3/build.py
"""
import hashlib
import html
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent


def inline(text):
    value = html.escape(text)
    value = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  lambda m: f'<a href="../{m[2]}">{m[1]}</a>', value)


def render(source):
    lines = source.splitlines()
    result, paragraph = [], []

    def flush():
        if paragraph:
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush()
        elif line.startswith('#'):
            flush()
            level = len(line) - len(line.lstrip('#'))
            result.append(f'<h{level}>' + inline(line[level:].strip()) + f'</h{level}>')
        elif line.startswith('|'):
            flush()
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i])
                i += 1
            result.append('<div class="table-scroll"><table>')
            for n, row in enumerate(block):
                if re.fullmatch(r'[| :\-]+', row):
                    continue
                tag = 'th' if n == 0 else 'td'
                cells = row.strip('|').split('|')
                result.append('<tr>' + ''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in cells) + '</tr>')
            result.append('</table></div>')
            continue
        elif line.startswith('- ') or re.match(r'^\d+\. ', line):
            flush()
            ordered = bool(re.match(r'^\d+\. ', line))
            tag = 'ol' if ordered else 'ul'
            result.append(f'<{tag}>')
            pattern = r'^\d+\. ' if ordered else r'^- '
            while i < len(lines) and re.match(pattern, lines[i]):
                item = re.sub(pattern, '', lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith('  '):
                    item += ' ' + lines[i].strip()
                    i += 1
                result.append('<li>' + inline(item) + '</li>')
            result.append(f'</{tag}>')
            continue
        else:
            paragraph.append(line.strip())
        i += 1
    flush()
    return '\n'.join(result)


class LinkCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for key, value in attrs:
                if key == 'href':
                    url = urlsplit(value)
                    if not url.scheme and url.path:
                        assert (HERE / unquote(url.path)).resolve().exists(), value


def main():
    old = DOCS / 'PROFESSOR-PROPOSAL-v2.md'
    old_hash = hashlib.sha256(old.read_bytes()).hexdigest()
    proposal = (DOCS / 'PROFESSOR-PROPOSAL-v3.md').read_text()
    review = (DOCS / 'PROPOSAL-v3-DIRECTION-REVIEW.md').read_text()
    content = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D proposal V3 — Direction review</title><style>
body{margin:0;background:#f3f5f7;color:#243647;font:17px/1.65 system-ui,sans-serif}main{max-width:980px;margin:30px auto;padding:0 22px}article,section{background:white;border:1px solid #dce2e8;border-radius:8px;padding:35px;margin:24px 0}nav{display:flex;gap:20px;flex-wrap:wrap}a{color:#145b92}h1{font-size:30px;line-height:1.25}h2{font-size:22px;margin-top:32px}p{max-width:80ch}li{margin:8px 0}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce2e8;vertical-align:top}th{background:#edf3f7}.sequence{padding:18px;background:#eaf1f6;border-left:4px solid #245f86}.muted{color:#536575}@media(max-width:600px){article,section{padding:20px}h1{font-size:25px}}@media print{body{background:white;font-size:11pt}main{max-width:none;margin:0;padding:0}nav{display:none}article,section{border:0;padding:0}h2{break-after:avoid}tr{break-inside:avoid}}
</style></head><body><main><nav><a href="../../../START-HERE.html">Project home</a><a href="#proposal">Proposal</a><a href="#direction">Direction and open decisions</a><a href="../PROFESSOR-PROPOSAL-v3.md">Markdown source</a></nav><p class="sequence"><strong>Simple following → structured-data ML → incremental NLP</strong><br>Direction review draft · 24 September 2026 · No performance results claimed</p><article id="proposal">'''
    content += render(proposal) + '</article><section id="direction">' + render(review)
    content += '</section></main></body></html>'
    (HERE / 'index.html').write_text(content)
    LinkCheck().feed(content)
    assert hashlib.sha256(old.read_bytes()).hexdigest() == old_hash
    assert content.count('<table>') == content.count('</table>')
    print(f'Built {HERE / "index.html"}; local links checked; V2 unchanged.')


if __name__ == '__main__':
    main()
