"""Tier: 1. Build offline Elliott filing readers without semantic labels.
Inputs: frozen verified-CIK inventory and raw SEC submissions.
Outputs: canonical document bundles, exact Item 4 spans, chronological HTML.
Identity: source SHA-256 matches inventory; text[start:end] equals excerpt.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/build_elliott_filings.py
"""
import hashlib
import html
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from activist13d.edgar.submission import parse_submission

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'research/runs/investor-identity/20260923-elliott'
PACK = ROOT/'review/drafts/investor-identity-elliott-20260923'
OUT = RUN/'filing-readers-v1'
e = html.escape

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def page(title, body):
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<style>body{{font:17px/1.65 system-ui;color:#233747;background:#f3f6f8;max-width:1050px;margin:30px auto;padding:20px}}section{{background:white;padding:25px;margin:20px 0;border-radius:10px}}a{{color:#176699}}td,th{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #ddd}}table{{width:100%;border-collapse:collapse}}.text{{white-space:pre-wrap;overflow-wrap:anywhere}}summary{{cursor:pointer;font-weight:bold}}code{{overflow-wrap:anywhere}}</style>
<p><a href="index.html">Identity review</a> · <a href="filings.html">All filing timelines</a></p><h1>{e(title)}</h1>{body}</html>'''

def build():
    records = json.loads((RUN/'verified-cik-filings.json').read_text())
    records.sort(key=lambda r:(r['filing_date'],r['accession']))
    groups = {}
    for r in records:
        key = tuple(s['cik'] for s in r['subjects'])
        groups.setdefault(key,[]).append(r)
    files = {}
    excerpts = 0
    for r in records:
        raw = (ROOT/r['source_path']).read_bytes()
        assert sha(raw) == r['source_sha256']
        parsed = parse_submission(raw)
        assert parsed['accession'] == r['accession']
        docs = []
        for d in parsed['documents']:
            docs.append({**d,'document_id':f'DOCUMENT[{d["source_document_index"]}]','text_sha256':sha(d['text'].encode()) if d['text'] is not None else None})
        excerpt = parsed.get('item4_text')
        citations = []
        if excerpt:
            for d in docs:
                if d['text'] and excerpt in d['text']:
                    start = d['text'].index(excerpt)
                    citations.append({'document_id':d['document_id'],'start':start,'end':start+len(excerpt),'quote':excerpt})
                    assert d['text'][start:start+len(excerpt)] == excerpt
            assert citations, r['accession']
            excerpts += 1
        bundle = {'accession':r['accession'],'filing_date':r['filing_date'],'source_path':r['source_path'],'source_sha256':r['source_sha256'],'documents':docs,'item4_status':parsed.get('item4_status'),'item4_citations':citations,'transformation_sha256':sha((ROOT/'src/activist13d/edgar/submission.py').read_bytes())}
        files[OUT/(r['accession']+'.json')] = json.dumps(bundle,indent=2)+'\n'
        issuer = '; '.join(s['name'] for s in r['subjects'])
        siblings = groups[tuple(s['cik'] for s in r['subjects'])]
        timeline = ' → '.join(f'<a href="{x["accession"]}.html">{e(x["filing_date"])} ({e(x["form"])})</a>' for x in siblings)
        body = f'<p>{e(r["form"])} · Filed {e(r["filing_date"])} · {e(r["accession"])}</p><section><h2>Cached disclosure timeline</h2><p>{timeline}</p><p>Local coverage may be incomplete. An amendment supplements earlier disclosures; it is not a new initial investment signal.</p></section>'
        body += '<section id="purpose"><h2>Item 4 — Purpose of Transaction</h2><p>Exact parser-selected source passage. This is disclosed language, not a recommendation or an inferred activist label. Read incorporated references and full documents below; the excerpt alone may be incomplete.</p><div class="text">'+e(excerpt or 'No Item 4 passage extracted; inspect full source.')+'</div></section>'
        body += '<section><h2>Full extracted documents and exhibits</h2><p>Expand a document to read the complete canonical text. HTML layout is flattened; binary attachments are listed but not converted. Externally incorporated documents have not been retrieved.</p>'
        for d in docs:
            body += '<details><summary>'+e(f'{d["document_id"]} · {d["type"]} · {d["filename"]}')+'</summary><div class="text">'+e(d['text'] if d['text'] is not None else d['text_status'])+'</div></details>'
        body += '</section><p><a href="'+e(os.path.relpath(ROOT/r['source_path'],PACK))+'">Original raw SEC submission</a> · <a href="'+e(os.path.relpath(OUT/(r['accession']+'.json'),PACK))+'">Canonical text and exact excerpt offsets</a></p>'
        files[PACK/(r['accession']+'.html')] = page(issuer,body)
    rows = []
    for group in sorted(groups.values(),key=lambda g:g[0]['subjects'][0]['name']):
        issuer = '; '.join(s['name'] for s in group[0]['subjects'])
        entries = '<br>'.join(f'<a href="{r["accession"]}.html#purpose">{e(r["filing_date"])} — {e(r["form"])} — Item 4</a>' for r in group)
        rows.append(f'<tr><td>{e(issuer)}</td><td>{entries}</td></tr>')
    body = f'<section><p>{len(records)} cached filings, grouped by disclosed issuer CIK. All raw-source hashes verified; {excerpts} Item 4 excerpts checked against canonical text. No completeness claim for these timelines.</p><p><a href="0000902664-23-005125.html#purpose"><b>Start with E2open: initial filing, 16 October 2023</b></a></p><p>Review questions: What is stated as the investment rationale? What action is intended, merely possible, or already completed? Who proposes it? Does an exhibit or earlier filing contain the actual terms? Ownership control and a holding period require separate evidence.</p><table><tr><th>Issuer</th><th>Disclosure timeline</th></tr>'+''.join(rows)+'</table></section>'
    files[PACK/'filings.html'] = page('Elliott — purposes and filing timelines',body)
    return files

if __name__ == '__main__':
    first = build()
    assert first == build(), 'Non-reproducible output'
    OUT.mkdir(parents=True,exist_ok=True)
    for path, content in first.items():
        if path.exists():
            assert path.read_text() == content, f'Refusing changed existing artifact: {path}'
        else:
            path.write_text(content)
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if tag == 'a' and key == 'href':
                    target = value.split('#', 1)[0]
                    assert (self.parent / target).exists(), value
    for path, content in first.items():
        if path.suffix == '.html':
            checker = Links()
            checker.parent = path.parent
            checker.feed(content)
    print(f'Validated and wrote {len(first)} reproducible artifacts. Open {PACK / "filings.html"}')
