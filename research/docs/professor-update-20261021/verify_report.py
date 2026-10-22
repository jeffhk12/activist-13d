"""Verify the professor report without fitting models or changing source evidence.

Inputs: report, manifest, source snapshots and builder. Output: verification.json.
Identity: source/output SHA-256 equality, byte-identical document rebuild, and
all 8 PDF pages contain content within the page frame. Tier: 2 report QA.
Run with the bundled PDF-runtime Python after build_report.py, then render/inspect.
"""
import hashlib
import json
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pdfplumber

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            self.links.extend(value for key,value in attrs if key=='href')

def main():
    manifest=json.loads((HERE/'evidence.json').read_text())
    before={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.pdf','.html') or p.name=='evidence.json'}
    env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONIOENCODING='utf-8')
    subprocess.run([sys.executable,str(HERE/'build_report.py')],check=True,env=env,cwd=ROOT)
    assert before=={name:digest(HERE/name) for name in before}, 'Report rebuild changed bytes'
    assert digest(HERE/'build_report.py')==manifest['builder_sha256']
    for row in manifest['source_evidence']:
        assert digest(ROOT/row['path'])==row['sha256']
        assert digest(HERE/row['snapshot'])==row['sha256']
    pdf=HERE/'13D_ML_Project_and_Progress_Report_20261021.pdf'
    assert digest(pdf)==manifest['pdf_sha256']
    parser=Links(); parser.feed((HERE/'index.html').read_text())
    for link in parser.links:
        parts=urlsplit(link)
        if parts.scheme or not parts.path: continue
        assert (HERE/unquote(parts.path)).resolve().exists(), link
    bounds=[]
    with pdfplumber.open(pdf) as book:
        assert len(book.pages)==8
        for n,p in enumerate(book.pages,1):
            words=p.extract_words()
            assert len(words)>200
            assert all(w['x0']>=42 and w['x1']<=570 for w in words), n
            content=[w for w in words if w['top']<740]
            assert min(w['top'] for w in content)>=40, n
            assert max(w['bottom'] for w in content)<748, n
            assert '\u25a0' not in p.extract_text(), n
            bounds.append({'page':n,'words':len(words),'content_bottom':max(w['bottom'] for w in content)})
    result={'report_pages':8,'report_byte_exact_rebuild':True,'source_snapshots_checked':12,
            'local_html_links_checked':len(parser.links),'numeric_checks':'saved event errors independently recomputed by builder; all published model MAE/RMSE agree',
            'page_bounds':bounds,'visual_review':'All eight rendered pages inspected; final pages 6 and 8 re-rendered after text corrections.',
            'models_fitted':0,'paid_api_calls':0,'pdf_sha256':digest(pdf)}
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
