"""Build the extraction review as a navigable HTML report and reading PDF.

Inputs: analysis.json, explorer.json, typed narrative and frozen evidence links.
Outputs: report.html, PDF, chart assets and build-verification.json.
Identity: identical narrative sections and tables feed HTML and PDF; numerical
results reconcile to frozen 627-filing outputs. Tier: 2 reported descriptive
counts; hand pins, source parity, refusal checks and rendering QA accompany it.
Run: project Python research/docs/extraction-results-review-20261102/build_report.py.
"""
import hashlib
import html
import importlib.metadata
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak,
                               PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from content import LABELS, SOURCES, make_sections

ROOT=Path('/Users/jefflu/Projects/activist-13d')
HERE=Path(__file__).resolve().parent
PDF_NAME='13D_Extraction_Results_and_Methods_20261102.pdf'
ASSETS=HERE/'assets'
ASSETS.mkdir(exist_ok=True)
NAVY='#18354a'; TEAL='#087d82'; AMBER='#ac6a17'; GRAY='#657887'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path):return os.path.relpath(path,HERE)
def clean(text):return text.replace('\u2011','-').replace('\u2013','-').replace('\u2014',' - ')


def charts(a):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False})
    fig,ax=plt.subplots(figsize=(7.8,2.55))
    names=['At least one eligible positive','All nine eligible as not stated','No positive and unresolved']
    values=[265,314,48]
    bars=ax.barh(names,values,color=[TEAL,NAVY,AMBER],height=.57)
    ax.invert_yaxis();ax.set_xlim(0,365);ax.set_xlabel('Production filings (n = 627)')
    ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
    for bar,value in zip(bars,values):ax.text(value+5,bar.get_y()+bar.get_height()/2,f'{value} ({100*value/627:.1f}%)',va='center',fontsize=10)
    fig.tight_layout();fig.savefig(ASSETS/'filing-groups.png',dpi=220,bbox_inches='tight',facecolor='white');plt.close(fig)
    rows=sorted(a['overview']['categories'].items(),key=lambda item:item[1].get('eligible_present',0),reverse=True)
    fig,ax=plt.subplots(figsize=(7.8,3.55))
    labels=[LABELS[key] for key,_ in rows];values=[value.get('eligible_present',0) for _,value in rows]
    bars=ax.barh(labels,values,color=[TEAL if i<2 else NAVY for i in range(9)],height=.66)
    ax.invert_yaxis();ax.set_xlim(0,185);ax.set_xlabel('Eligible positive filings (n = 627; categories overlap)')
    ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.13);ax.set_axisbelow(True)
    for bar,value in zip(bars,values):ax.text(value+2,bar.get_y()+bar.get_height()/2,str(value),va='center')
    fig.tight_layout();fig.savefig(ASSETS/'objective-positives.png',dpi=220,bbox_inches='tight',facecolor='white');plt.close(fig)


def cite_html(text):
    return re.sub(r'\[(S\d+)\]',lambda match:f'<a class="cite" href="#source-{match[1]}">[{match[1]}]</a>',clean(text))


def build_html(a,explorer,sections):
    navigation=''.join(f'<a href="#{section["id"]}"><span>{i:02}</span>{html.escape(section["title"])}</a>' for i,section in enumerate(sections,1))
    parts=[]
    for i,section in enumerate(sections,1):
        body=[]
        for block in section['blocks']:
            kind=block['type']
            if kind in ['p','h','callout']:
                tag={'p':'p','h':'h3','callout':'aside'}[kind]
                body.append(f'<{tag}>{cite_html(block["text"])}</{tag}>')
            elif kind=='bullets':body.append('<ul>'+''.join(f'<li>{cite_html(item)}</li>' for item in block['items'])+'</ul>')
            elif kind=='table':
                head=''.join(f'<th scope="col">{html.escape(value)}</th>' for value in block['headers'])
                rows=''.join('<tr>'+''.join(f'<td>{cite_html(html.escape(str(value)))}</td>' for value in row)+'</tr>' for row in block['rows'])
                body.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
            elif kind=='figure':body.append(f'<figure><img src="assets/{block["name"]}" alt="{html.escape(block["caption"])}"><figcaption>{html.escape(block["caption"])}</figcaption></figure>')
        parts.append(f'<section id="{section["id"]}"><div class="section-number">{i:02}</div><h2>{html.escape(section["title"])}</h2><p class="dek">{html.escape(section["subtitle"])}</p>{"".join(body)}</section>')
    sources=''.join(f'<li id="source-{sid}"><b>[{sid}] {html.escape(label)}</b><br><a href="{html.escape(rel(ROOT/path),quote=True)}">{html.escape(path)}</a></li>' for sid,label,path in SOURCES)
    options=''.join(f'<option value="{key}">{html.escape(value)}</option>' for key,value in LABELS.items())
    body=''.join(parts)
    payload=json.dumps(explorer,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    labels=json.dumps(LABELS)
    text=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D Extraction Results and Methods Review</title>
<style>
:root{{--ink:{NAVY};--teal:{TEAL};--muted:{GRAY};--gold:{AMBER};--line:#d7e1e7;--paper:#fff;--back:#f1f5f7}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth;scroll-padding-top:24px}}body{{margin:0;background:var(--back);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.layout{{max-width:1480px;margin:0 auto;display:grid;grid-template-columns:290px minmax(0,1fr);gap:34px;padding:28px}}nav{{position:sticky;top:18px;height:calc(100vh - 36px);overflow:auto;padding:14px 6px;font-size:13px}}nav strong{{display:block;margin-bottom:12px;color:var(--teal);letter-spacing:.08em}}nav a{{display:flex;gap:10px;color:var(--ink);text-decoration:none;padding:8px;border-radius:6px;line-height:1.35}}nav a:hover,nav a:focus{{background:#ddecef}}nav a span{{color:var(--muted);font-variant-numeric:tabular-nums}}
main{{min-width:0}}header,section{{background:white;border:1px solid var(--line);border-radius:12px;padding:34px 40px;margin-bottom:26px}}header{{border-top:7px solid var(--teal)}}h1{{font-size:38px;line-height:1.15;margin:14px 0 20px;max-width:800px}}h2{{font-size:26px;line-height:1.25;margin:3px 0 12px}}h3{{font-size:18px;margin:25px 0 8px}}p{{margin:12px 0}}.eyebrow,.section-number{{font-size:12px;font-weight:700;color:var(--teal);letter-spacing:.12em;text-transform:uppercase}}.dek{{color:var(--muted);font-size:18px;margin-bottom:25px}}a{{color:#086a88;text-underline-offset:3px}}.actions{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}.actions a{{border:1px solid #98b9c4;border-radius:7px;padding:9px 14px;text-decoration:none;font-weight:600;font-size:14px}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:24px}}.metric{{background:#eff6f6;padding:18px;border-radius:8px}}.metric b{{display:block;font-size:30px;line-height:1.1}}.metric span{{font-size:13px;color:var(--muted)}}aside{{background:#f0f7f7;border-left:4px solid var(--teal);padding:15px 19px;margin:22px 0}}li{{margin:9px 0}}.table-wrap{{overflow:auto;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{background:#e9f1f4;font-size:12px;color:var(--ink)}}tbody tr:nth-child(even){{background:#f7f9fa}}figure{{margin:23px 0}}figure img{{display:block;width:100%;height:auto}}figcaption,.small{{font-size:12px;color:var(--muted)}}.cite{{font-size:12px;white-space:nowrap}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}input,select,button{{font:inherit;font-size:14px;padding:9px 11px;border:1px solid #aebfc9;border-radius:6px;background:white;color:var(--ink)}}input{{flex:1;min-width:210px}}button{{cursor:pointer}}button:disabled{{opacity:.4;cursor:default}}.case-card,details.flag{{border:1px solid var(--line);border-radius:8px;padding:14px 17px;margin:12px 0}}summary{{cursor:pointer;font-weight:650}}.pill{{display:inline-block;padding:2px 7px;border-radius:4px;background:#edf3f5;font-size:12px;margin:3px}}.positive{{background:#d9eeea}}.unresolved{{background:#fcf0db}}.pager{{display:flex;gap:14px;align-items:center;margin:18px 0}}.source-list a{{overflow-wrap:anywhere}}code{{font-size:.9em;background:#eff3f5;padding:2px 4px}}.print-note{{display:none}}
@media(max-width:1000px){{.layout{{display:block;padding:14px}}nav{{position:static;height:auto;max-height:260px;margin-bottom:20px}}header,section{{padding:25px 22px}}h1{{font-size:31px}}.metrics{{grid-template-columns:1fr}}}}
@media print{{body{{background:white}}.layout{{display:block;padding:0}}nav,.actions,.controls,.pager,#case-list,#flag-list{{display:none}}header,section{{border:0;padding:10px 0;break-inside:avoid-page}}.print-note{{display:block}}a{{color:inherit}}}}
</style></head><body><div class="layout"><nav aria-label="Report contents"><strong>13D RESEARCH REVIEW</strong>{navigation}<a href="#filing-explorer">A1 Filing explorer</a><a href="#flag-explorer">A2 Critic flag register</a><a href="#sources">A3 Evidence and downloads</a></nav><main>
<header><div class="eyebrow">2 November 2026 / Experimental data preparation</div><h1>13D Extraction Results and Methods Review</h1><p class="dek">What we are trying to learn, what the filing extraction found, and how we assess its quality.</p><p>The investment question is whether stated objectives and qualified funding improve ranking beyond comparable structured inputs. Extraction is complete. Natural-data accuracy and incremental investment value remain unmeasured.</p><div class="actions"><a href="{PDF_NAME}">Download the reading PDF</a><a href="../../../START-HERE.html">Project start page</a><a href="#filing-explorer">Explore the filings</a><a href="#flag-explorer">Inspect the flags</a></div><div class="metrics"><div class="metric"><b>640</b><span>Eligible filings complete, including 13 earlier cases</span></div><div class="metric"><b>627</b><span>Production filings used for this report's aggregate results</span></div><div class="metric"><b>221</b><span>Critic flags across 127 production filings</span></div></div></header>
{body}
<section id="filing-explorer"><div class="section-number">Appendix A1</div><h2>Explore all 627 production filings</h2><p>These are frozen model measurements. A positive requires the experimental eligibility rule; unresolved decisions remain visible. The source notes link contains original records and quotations.</p><div class="controls"><input id="case-search" aria-label="Search filings" placeholder="Search issuer, accession or case"><select id="case-filter" aria-label="Filter filings"><option value="all">All filings</option><option value="positive">At least one eligible positive</option><option value="unresolved">Any unresolved objective</option><option value="negative">All nine eligible not stated</option></select><select id="category-filter" aria-label="Filter positive objective category"><option value="all">Any positive category</option>{options}</select></div><p id="case-count" class="small" aria-live="polite"></p><div id="case-list"></div><div class="pager"><button id="case-prev">Previous</button><span id="case-page"></span><button id="case-next">Next</button></div><p class="print-note">The searchable explorer is available in the HTML version.</p></section>
<section id="flag-explorer"><div class="section-number">Appendix A2</div><h2>Inspect all 221 critic flags</h2><p>Every verdict and rationale below is the original critic's model judgment. No flag has been adjudicated in this report. The register covers critic objections; the 101 additional excluded objective decisions without a critic flag can be found through the filing explorer's unresolved filter.</p><div class="controls"><input id="flag-search" aria-label="Search flags" placeholder="Search issuer, case, claim, rationale or issue"><select id="flag-field" aria-label="Filter flag field"><option value="all">All fields</option><option value="intent">Objectives</option><option value="funding">Funding</option><option value="ownership">Ownership</option><option value="transaction">Transactions</option></select><select id="flag-verdict" aria-label="Filter critic verdict"><option value="all">Both verdicts</option><option value="insufficient_evidence">Insufficient evidence</option><option value="contradicted">Contradicted</option></select></div><p id="flag-count" class="small" aria-live="polite"></p><div id="flag-list"></div><div class="pager"><button id="flag-prev">Previous</button><span id="flag-page"></span><button id="flag-next">Next</button></div><p class="print-note">The complete register is available in the HTML version and linked JSON.</p></section>
<section id="sources"><div class="section-number">Appendix A3</div><h2>Evidence and reproducible calculations</h2><p>All numerical results are derived from preserved local evidence. No new filing extraction, financial download, adjudication or model fit was performed to create this report.</p><ol class="source-list">{sources}</ol><div class="actions"><a href="analysis.json">Detailed calculations and source hashes</a><a href="explorer.json">Every filing decision and original flag</a><a href="build-verification.json">Report checks</a><a href="analyze.py">Calculation script</a><a href="build_report.py">Report builder</a></div><p class="small">Production role records were finalized from 28 October to 2 November 2026. Earlier execution gaps and the integrity-helper recovery are recorded separately; completion does not establish uninterrupted overnight execution.</p></section>
</main></div><script id="report-data" type="application/json">{payload}</script><script>
'use strict';const DATA=JSON.parse(document.getElementById('report-data').textContent);const LABELS={labels};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const note=c=>`../../runs/extraction-batches/20261028-v1/batch-${{String(c.batch).padStart(3,'0')}}/case-notes.html`;
let cp=0,fp=0;const PAGE=20;
function casesFiltered(){{const q=document.getElementById('case-search').value.toLowerCase(),f=document.getElementById('case-filter').value,cat=document.getElementById('category-filter').value;return DATA.cases.filter(c=>(c.issuer+' '+c.accession+' '+c.case_id).toLowerCase().includes(q)&&(f==='all'||f==='positive'&&c.eligible_positive.length>0||f==='unresolved'&&c.unresolved.length>0||f==='negative'&&!c.eligible_positive.length&&!c.unresolved.length)&&(cat==='all'||c.eligible_positive.includes(cat)));}}
function renderCases(reset=false){{if(reset)cp=0;const all=casesFiltered(),pages=Math.max(1,Math.ceil(all.length/PAGE));cp=Math.min(cp,pages-1);document.getElementById('case-count').textContent=`${{all.length}} matching filings of 627. Positive categories can overlap.`;document.getElementById('case-page').textContent=`Page ${{cp+1}} of ${{pages}}`;document.getElementById('case-prev').disabled=cp===0;document.getElementById('case-next').disabled=cp>=pages-1;document.getElementById('case-list').innerHTML=all.slice(cp*PAGE,(cp+1)*PAGE).map(c=>`<details class="case-card"><summary>${{esc(c.issuer)}} <span class="small">${{esc(c.case_id)}} / ${{esc(c.year)}}</span></summary><p class="small">Accession ${{esc(c.accession)}} / ${{c.readable_characters.toLocaleString()}} readable characters / ${{c.critic_flags}} critic flag(s)</p><p><b>Eligible positive:</b> ${{c.eligible_positive.map(x=>`<span class="pill positive">${{esc(LABELS[x])}}</span>`).join('')||'None recorded'}}</p><p><b>Unresolved:</b> ${{c.unresolved.map(x=>`<span class="pill unresolved">${{esc(LABELS[x])}}</span>`).join('')||'None'}}</p><div class="table-wrap"><table><thead><tr><th>Objective</th><th>Extractor</th><th>Independent reader</th><th>Critic</th><th>Experimental use</th></tr></thead><tbody>${{c.decisions.map(d=>`<tr><td>${{esc(LABELS[d.category])}}</td><td>${{esc(d.extractor)}}</td><td>${{esc(d.blind)}}</td><td>${{esc(d.critic)}}</td><td>${{d.eligible_experimental_label?'Eligible':'Excluded'}}</td></tr>`).join('')}}</tbody></table></div><a href="${{note(c)}}">Original case notes and source evidence</a></details>`).join('')||'<p>No filings match these filters.</p>';}}
function flagsFiltered(){{const q=document.getElementById('flag-search').value.toLowerCase(),field=document.getElementById('flag-field').value,v=document.getElementById('flag-verdict').value;return DATA.flags.filter(f=>(f.issuer+' '+f.case_id+' '+f.claim_id+' '+f.rationale+' '+f.issue_codes.join(' ')).toLowerCase().includes(q)&&(field==='all'||f.claim_id.split('.')[0]===field)&&(v==='all'||f.verdict===v));}}
function renderFlags(reset=false){{if(reset)fp=0;const all=flagsFiltered(),pages=Math.max(1,Math.ceil(all.length/PAGE));fp=Math.min(fp,pages-1);document.getElementById('flag-count').textContent=`${{all.length}} matching claim flags of 221. No flags adjudicated.`;document.getElementById('flag-page').textContent=`Page ${{fp+1}} of ${{pages}}`;document.getElementById('flag-prev').disabled=fp===0;document.getElementById('flag-next').disabled=fp>=pages-1;document.getElementById('flag-list').innerHTML=all.slice(fp*PAGE,(fp+1)*PAGE).map(f=>`<details class="flag"><summary>${{esc(f.case_id)}} / ${{esc(f.claim_id)}} / ${{esc(f.verdict.replaceAll('_',' '))}}</summary><p><b>${{esc(f.issuer)}}</b></p><p>${{esc(f.rationale)}}</p><p>${{f.issue_codes.map(x=>`<span class="pill">${{esc(x.replaceAll('_',' '))}}</span>`).join('')}}</p><p class="small">Original critic judgment / resolution status: unreviewed</p><a href="${{note(f)}}">Original case evidence and records</a></details>`).join('')||'<p>No flags match these filters.</p>';}}
for(const id of ['case-search','case-filter','category-filter'])document.getElementById(id).addEventListener(id==='case-search'?'input':'change',()=>renderCases(true));for(const id of ['flag-search','flag-field','flag-verdict'])document.getElementById(id).addEventListener(id==='flag-search'?'input':'change',()=>renderFlags(true));
document.getElementById('case-prev').onclick=()=>{{cp--;renderCases();}};document.getElementById('case-next').onclick=()=>{{cp++;renderCases();}};document.getElementById('flag-prev').onclick=()=>{{fp--;renderFlags();}};document.getElementById('flag-next').onclick=()=>{{fp++;renderFlags();}};renderCases();renderFlags();
</script></body></html>'''
    (HERE/'report.html').write_text(text)
    # Validate the literal inline script separately with node --check.
    (HERE/'report-ui.js').write_text(text.split('<script>')[-1].split('</script>')[0])


def build_pdf(a,sections):
    fontdir=Path('/System/Library/Fonts/Supplemental')
    for name,file in [('Arial','Arial.ttf'),('Arial-Bold','Arial Bold.ttf'),('Arial-Italic','Arial Italic.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
    pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
    styles={
      'title':ParagraphStyle('Title',fontName='Arial-Bold',fontSize=33,leading=39,textColor=colors.HexColor(NAVY),spaceAfter=21),
      'h1':ParagraphStyle('H1',fontName='Arial-Bold',fontSize=22,leading=27,textColor=colors.HexColor(NAVY),spaceAfter=11,keepWithNext=True),
      'h2':ParagraphStyle('H2',fontName='Arial-Bold',fontSize=11.5,leading=15,textColor=colors.HexColor(TEAL),spaceBefore=12,spaceAfter=5,keepWithNext=True),
      'p':ParagraphStyle('Body',fontName='Arial',fontSize=10.3,leading=15.1,textColor=colors.HexColor(NAVY),spaceAfter=10),
      'dek':ParagraphStyle('Dek',fontName='Arial',fontSize=11.5,leading=16,textColor=colors.HexColor(GRAY),spaceAfter=17,keepWithNext=True),
      'cell':ParagraphStyle('Cell',fontName='Arial',fontSize=8.65,leading=12,textColor=colors.HexColor(NAVY),spaceAfter=0),
      'th':ParagraphStyle('TH',fontName='Arial-Bold',fontSize=8.5,leading=11.5,textColor=colors.HexColor(NAVY)),
      'small':ParagraphStyle('Small',fontName='Arial',fontSize=8.2,leading=11.5,textColor=colors.HexColor(GRAY),spaceAfter=10),
      'source':ParagraphStyle('Source',fontName='Arial',fontSize=9.4,leading=13,textColor=colors.HexColor(NAVY),spaceAfter=3),
      'call':ParagraphStyle('Call',fontName='Arial',fontSize=10.2,leading=15,textColor=colors.HexColor(NAVY),spaceAfter=0),
      'bullet':ParagraphStyle('Bullet',fontName='Arial',fontSize=10.1,leading=14.7,textColor=colors.HexColor(NAVY),leftIndent=12,firstLineIndent=-10,spaceAfter=8)}
    width=letter[0]-1.35*inch
    class Doc(BaseDocTemplate):
        def afterFlowable(self,flowable):
            if hasattr(flowable,'section_title'):
                self.canv.bookmarkPage(flowable.section_id)
                self.canv.addOutlineEntry(flowable.section_title,flowable.section_id,0,False)
                self.notify('TOCEntry',(0,flowable.section_title,self.page,flowable.section_id))
    def footer(canvas,doc):
        canvas.saveState()
        if doc.page>1:
            canvas.setStrokeColor(colors.HexColor('#d7e1e7'));canvas.line(.68*inch,letter[1]-.48*inch,letter[0]-.68*inch,letter[1]-.48*inch)
            canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor(GRAY));canvas.drawString(.68*inch,letter[1]-.35*inch,'13D extraction results and methods')
            canvas.drawRightString(letter[0]-.68*inch,letter[1]-.35*inch,'Experimental measurements')
        canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor(GRAY));canvas.drawString(.68*inch,.35*inch,'2 November 2026  |  Local evidence review');canvas.drawRightString(letter[0]-.68*inch,.35*inch,str(doc.page));canvas.restoreState()
    doc=Doc(str(HERE/PDF_NAME),pagesize=letter,leftMargin=.68*inch,rightMargin=.67*inch,topMargin=.77*inch,bottomMargin=.64*inch,title='13D Extraction Results and Methods Review',author='13D Research Project')
    doc.addPageTemplates(PageTemplate(id='normal',frames=[Frame(doc.leftMargin,doc.bottomMargin,width,doc.height,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=footer))
    def para(text,style='p'):return Paragraph(clean(text),styles[style])
    def pdf_table(headers,rows,widths=None,compact=False):
        widths=widths or [1/len(headers)]*len(headers)
        data=[[para(html.escape(str(value)),'th') for value in headers]]+[[para(html.escape(str(value)),'cell') for value in row] for row in rows]
        out=Table(data,colWidths=[width*x for x in widths],repeatRows=1,hAlign='LEFT')
        pad=5 if compact else 7
        out.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f0f3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8f9')]),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d7e1e7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad)]))
        return out
    story=[Spacer(1,.55*inch),para('13D RESEARCH / EXTRACTION REVIEW','h2'),para('13D Extraction Results<br/>and Methods Review','title'),para('What we are trying to learn, what the filing extraction found, and how we assess its quality.','dek'),Spacer(1,.12*inch),para('The investment question is whether stated objectives and qualified funding improve ranking beyond comparable structured inputs. The extraction is complete; natural-data accuracy and incremental investment value remain unmeasured.'),Spacer(1,.18*inch),pdf_table(['640','627','221'],[['Eligible filings complete, including 13 earlier cases','Production filings summarized in this report','Critic flags across 127 production filings']],[.333,.334,.333]),Spacer(1,.3*inch),para('Prepared for Jeff Lu | 2 November 2026','small'),para('Reading scope: this PDF contains the full narrative review. The companion HTML report adds searchable explorers for every production filing and critic flag. The original extraction records remain unchanged.','small'),para('Start with the investment question, then the objective definitions and quality-method sections. Use the results and adjudication sections for the next project discussion.','small'),PageBreak(),para('Reading map','h1'),para('The sections follow the research decision, the measurement process, the results and the next actions.','dek')]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC',fontName='Arial',fontSize=9.2,leading=13,textColor=colors.HexColor(NAVY),leftIndent=0,firstLineIndent=0,rightIndent=10,spaceBefore=1,spaceAfter=0)]
    story.append(toc)
    for i,section in enumerate(sections,1):
        story.append(PageBreak());title=para(f'{i:02}  {section["title"]}','h1');title.section_title=f'{i:02}  {section["title"]}';title.section_id=section['id'];story.extend([title,para(section['subtitle'],'dek')])
        for block in section['blocks']:
            kind=block['type']
            if kind=='p':story.append(para(block['text']))
            elif kind=='h':story.append(para(block['text'],'h2'))
            elif kind=='bullets':story.extend(para('- '+item,'bullet') for item in block['items'])
            elif kind=='table':story.extend([Spacer(1,4),pdf_table(block['headers'],block['rows'],block.get('widths'),compact=i in [12,14]),Spacer(1,13)])
            elif kind=='callout':
                box=Table([[para(block['text'],'call')]],colWidths=[width]);box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf6f5')),('LINEBEFORE',(0,0),(0,-1),3,colors.HexColor(TEAL)),('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)]));story.extend([box,Spacer(1,13)])
            elif kind=='figure':
                image=Image(str(ASSETS/block['name']));image.drawHeight=image.imageHeight*width/image.imageWidth;image.drawWidth=width
                if i==12:
                    image.drawHeight*=.90;image.drawWidth*=.90
                story.append(KeepTogether([image,Spacer(1,5),para(block['caption'],'small')]))
    story.extend([PageBreak(),para('Source map and reproducibility','h1'),para('These are the local evidence sources behind the report. The companion HTML provides clickable links and complete searchable appendices.','dek')])
    for sid,label,path in SOURCES:
        story.extend([para(f'<b>[{sid}] {html.escape(label)}</b>','source'),para(html.escape(path),'small')])
    story.append(para('Report folder: '+html.escape(str(HERE)),'small'))
    doc.multiBuild(story)


def main():
    a=json.loads((HERE/'analysis.json').read_bytes());explorer=json.loads((HERE/'explorer.json').read_bytes())
    for path,expected in a['input_sha256'].items():
        assert sha(ROOT/path)==expected,path
    assert len(explorer['cases'])==627 and len(explorer['flags'])==221
    assert a['overview']['eligible_objective_cells']==5112+366==5478
    assert a['flags']['excluded_objective_cells']+221-a['flags']['excluded_objectives_with_critic_flags']==322
    assert 376/408*100>92 and 376/408*100<93
    sections=make_sections(a)
    charts(a);build_html(a,explorer,sections);build_pdf(a,sections)
    from pypdf import PdfReader
    pdf=PdfReader(HERE/PDF_NAME)
    text='\n'.join(page.extract_text() or '' for page in pdf.pages)
    for phrase in ['640','627','221','165','98.9%','92.2%','322','5,478','Source map and reproducibility']:
        assert phrase in text,phrase
    assert len(pdf.pages)>=18
    verification={'report_status':'built_pending_visual_review','production_filings':627,'overall_completed_filings':640,
                  'narrative_sections':len(sections),'pdf_pages':len(pdf.pages),'pdf_text_characters':len(text),
                  'explorer_filings':627,'explorer_flags':221,'input_source_hashes_verified':len(a['input_sha256']),
                  'source_facts_and_judgments_preserved':True,'new_model_judgments':0,'new_model_fits':0,
                  'dependencies':{name:importlib.metadata.version(name) for name in ['reportlab','pypdf','matplotlib','pillow']},
                  'output_sha256':{name:sha(HERE/name) for name in ['report.html',PDF_NAME,'analysis.json','explorer.json','assets/filing-groups.png','assets/objective-positives.png']}}
    (HERE/'build-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    (HERE/'pdf-extracted-text.txt').write_text(text)
    print(json.dumps({key:value for key,value in verification.items() if key not in ['output_sha256','dependencies']},indent=2))


if __name__=='__main__':main()
