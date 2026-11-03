"""Verify report links, source preservation and PDF structure; render contact sheets.
Inputs: generated HTML/PDF and source fingerprints. Outputs: QA JSON and PNGs.
Identity: every local href resolves; every recorded source hash remains identical.
Tier: 1 artifact QA; geometry supplements, never replaces, visual inspection.
Run: project Python research/docs/extraction-results-review-20261102/qa_report.py.
"""
import hashlib
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from PIL import Image,ImageDraw
from pypdf import PdfReader

ROOT=Path('/Users/jefflu/Projects/activist-13d')
HERE=Path(__file__).resolve().parent
PDF=HERE/'13D_Extraction_Results_and_Methods_20261102.pdf'
QA=HERE/'qa'/hashlib.sha256(PDF.read_bytes()).hexdigest()[:12]
QA.mkdir(parents=True,exist_ok=True)


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.images=[];self.data_chunks=[];self.in_data=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id'in a:self.ids.append(a['id'])
        if tag=='a'and'href'in a:self.links.append(a['href'])
        if tag=='img':self.images.append(a['src'])
        if tag=='script'and a.get('id')=='report-data':self.in_data=True
    def handle_data(self,text):
        if self.in_data:self.data_chunks.append(text)
    def handle_endtag(self,tag):
        if tag=='script':self.in_data=False


def main():
    page=Links();page.feed((HERE/'report.html').read_text())
    assert len(set(page.ids))==len(page.ids)
    checked=0
    for href in page.links+page.images:
        parsed=urlsplit(href)
        if parsed.scheme:continue
        if parsed.path:assert(HERE/unquote(parsed.path)).resolve().exists(),href
        elif parsed.fragment:assert parsed.fragment in page.ids,href
        checked+=1
    explorer=json.loads((HERE/'explorer.json').read_bytes())
    assert json.loads(''.join(page.data_chunks))==explorer,'Embedded HTML data differs from explorer JSON'
    for case in explorer['cases']:
        assert(ROOT/f"research/runs/extraction-batches/20261028-v1/batch-{case['batch']:03}/case-notes.html").exists()
    a=json.loads((HERE/'analysis.json').read_bytes())
    for name,expected in a['input_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    pdf=PdfReader(PDF);pages=[];out_of_page=[]
    for i,pdfpage in enumerate(pdf.pages,1):
        text=pdfpage.extract_text()or''
        lines=[line.strip()for line in text.splitlines()if line.strip()]
        pages.append({'page':i,'characters':len(text),'first_lines':lines[:4]})
        def visitor(text,cm,tm,font,size):
            if not text.strip():return
            x=tm[4]*cm[0]+tm[5]*cm[2]+cm[4];y=tm[4]*cm[1]+tm[5]*cm[3]+cm[5]
            if y<12 or y>790 or x<0 or x>612:out_of_page.append({'page':i,'x':x,'y':y,'text':text[:90]})
        pdfpage.extract_text(visitor_text=visitor)
        assert len(text)>100,f'Suspicious near-empty page {i}'
        assert '\u25a0'not in text and '\ufffd'not in text,f'Unknown glyph on page {i}'
    assert not out_of_page,out_of_page[:5]
    subprocess.run(['pdftoppm','-r','65','-png',str(PDF),str(QA/'page')],check=True,capture_output=True)
    paths=sorted(QA.glob('page-*.png'))
    assert len(paths)==len(pdf.pages)
    for start in range(0,len(paths),12):
        sheet=Image.new('RGB',(4*290,3*395),'#dce5ea');draw=ImageDraw.Draw(sheet)
        for j,path in enumerate(paths[start:start+12]):
            im=Image.open(path).convert('RGB');im.thumbnail((272,357))
            x=(j%4)*290+9;y=(j//4)*395+25
            sheet.paste(im,(x,y));draw.text((x,y-19),f'Page {start+j+1}',fill='#18354a')
        sheet.save(QA/f'contact-{start//12+1:02}.png')
    result={'pdf_pages':len(pdf.pages),'local_html_links_and_images_checked':checked,'broken_links':0,
            'all_case_evidence_links_verified':len(explorer['cases']),'input_hashes_verified':len(a['input_sha256']),
            'pdf_text_coordinates_outside_page':out_of_page,'page_text_inventory':pages,
            'pdf_rendered_pages':len(paths),'render_directory':str(QA.relative_to(HERE)),
            'live_browser_preview':'unavailable: browser access host unavailable',
            'visual_review':'pending'}
    (HERE/'qa-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='page_text_inventory'},indent=2))
    for row in pages:print(row['page'],row['characters'],' | '.join(row['first_lines'][:3]))


if __name__=='__main__':main()
