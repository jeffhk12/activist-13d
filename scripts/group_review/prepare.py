"""Prepare 200 grouped development filings with evidence and blank human labels.

Inputs: read-only Phase-1 SQLite, frozen SEC submissions, exclusion manifests.
Outputs: separate HTML packets, filterable index, editable CSV and audit JSON.
Identity: every quote = canonical_text[start:end]; every raw SHA matches cache.
Tier: 1. Selection is purposive development sampling, not a population estimate.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/group_review/prepare.py --out review/archive/13d-group-review-20260922
Offline; no model calls, market outcomes, external reference retrieval or labels.
"""
from pathlib import Path
import argparse,csv,hashlib,html,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,time
from collections import Counter
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from activist13d.local_paths import resolve_project_path
DB=ROOT/'research/runs/phase1-overnight/full-20260915/sec.sqlite'
BLIND=ROOT/'research/runs/extraction-prep/development-20260916'
SEED='group-review-development-20260922-v1'
BUCKETS=[(2013,2015),(2016,2018),(2019,2021),(2022,2024)]
NAME=re.compile(r'\b(capital|investment[s]?|investors|asset management|partners|fund|advis[oe]rs?)\b',re.I)
ACTION=re.compile(r'\b(nominat(?:e|ed|ing|ion)|proxy contest|shareholder proposal|stockholder proposal|urge[sd]?|request(?:ed|s)?|board representation)\b',re.I)
CUES={
 'Manager/fund language':r'\b(?:investment (?:manager|advis[oe]r|fund)|asset manager|private investment|hedge fund)\b',
 'Hedge-fund phrase':r'\bhedge funds?\b',
 'Action language':ACTION.pattern,
 'Insider/board language':r'\b(?:chief executive officer|founder|director of the issuer|member of the board)\b',
 'Sponsor/SPAC language':r'\b(?:founder shares|blank check company|sponsor)\b',
 'Transaction language':r'\b(?:merger agreement|spin.off|debt conversion|contribution agreement)\b',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def rank(r):return sha((SEED+':'+r['accession']).encode())
def write(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def frozen(path,data):
    if path.exists():assert path.read_bytes()==data,'Frozen artifact changed: '+str(path)
    else:path.write_bytes(data)
def select(rows,excluded,n):
    selected=[];used=set();groups=set();counts={}
    quota=n//4
    for lo,hi in BUCKETS:
        pool=sorted([r for r in rows if lo<=int(r['filing_date'][:4])<=hi and r['accession'] not in excluded],key=rank)
        plan=[('manager_name_search',quota*3//5,lambda r:bool(NAME.search(' '.join(p.get('name','') for p in r.get('filers',[]))))),('action_text_search',quota//5,lambda r:bool(ACTION.search(r.get('item4_text') or ''))),('broad_comparison',quota-(quota*3//5)-(quota//5),lambda r:True)]
        chosen_before=len(selected)
        def add(label,want,predicate):
            count=0
            for r in pool:
                g=(tuple(sorted(str(x.get('cik')) for x in r.get('subjects',[]))),tuple(sorted(str(x.get('cik')) for x in r.get('filers',[]))))
                if r['accession'] in used or g in groups or not predicate(r):continue
                selected.append({'selection_stratum':f'{lo}-{hi}:{label}','record':r});used.add(r['accession']);groups.add(g);count+=1
                if count==want:break
            counts[f'{lo}-{hi}:{label}']=count
        for label,want,pred in plan:
            if want:add(label,want,pred)
        short=quota-(len(selected)-chosen_before)
        if short:add('broad_shortfall_fill',short,lambda r:True)
    assert len(selected)==n,'Insufficient distinct candidates for requested strata'
    return selected,counts
def cues(documents):
    evidence=[]
    for label,pattern in CUES.items():
        for d in documents:
            if d['document_id']=='SEC-HEADER' or not d['text']:continue
            hits=list(re.finditer(pattern,d['text'],re.I))[:3]
            for m in hits:
                a=max(0,m.start()-150);b=min(len(d['text']),m.end()+250);quote=d['text'][a:b]
                assert d['text'][a:b]==quote
                evidence.append({'cue':label,'document_id':d['document_id'],'start':a,'end':b,'quote':quote,'matched_phrase':m[0],'text_sha256':d['text_sha256']})
            if hits:break
    return evidence
def security(docs):
    for d in docs:
        text=d['text'] or ''
        m=re.search(r'\(\s*Name of Issuer\s*\)\s*(.{1,400}?)\s*\(\s*Title of (?:Class of )?Securities\s*\)',text,re.I)
        if m:return {'raw_title':m[1],'document_id':d['document_id'],'start':m.start(1),'end':m.end(1),'status':'cover_regex_candidate'}
    return {'raw_title':None,'status':'not_found_by_cover_regex'}
def security_hint(title):
    if not title:return 'Unresolved'
    matches=[label for label,pat in [('Preferred',r'preferred'),('ADR/depositary',r'depositary|\bADR\b'),('Units',r'\bunits?\b'),('Common/ordinary',r'common|ordinary')] if re.search(pat,title,re.I)]
    return ' / '.join(matches) if matches else 'Other / review'
def one(out,acc):
    spec=importlib.util.spec_from_file_location('canonical',ROOT/'scripts/extraction_prep/prepare_sample.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    chosen=json.loads((out/'selection.json').read_text());entry=next(x for x in chosen['selected'] if x['record']['accession']==acc);r=entry['record']
    source=resolve_project_path(r['source_path'],ROOT);assert source.is_relative_to((ROOT/'data/raw/edgar').resolve())
    assert source.stat().st_size<=20*1024**2
    raw=source.read_bytes();meta=json.loads(source.with_suffix(source.suffix+'.meta.json').read_text());digest=sha(raw)
    assert digest==r['source_sha256']==meta['sha256'] and len(raw)==meta['bytes']
    documents=mod.docs(raw);header=documents[0]['text'];assert mod.header_field(header,'ACCESSION NUMBER')==acc
    assert mod.header_field(header,'FILED AS OF DATE')==r['filing_date'].replace('-','')
    form=mod.header_field(header,'CONFORMED SUBMISSION TYPE')
    if '/A' in (form or '').upper():raise ValueError('Source header is amendment despite initial-index candidate')
    if (form or '').upper() not in ['SC 13D','SCHEDULE 13D','13D']:raise ValueError('Source form is not initial 13D')
    ev=cues(documents);sec=security(documents)
    bundle={'accession':acc,'filing_date':r['filing_date'],'acceptance_datetime_et':r.get('acceptance_datetime_et'),'source_url':meta.get('url'),'source_sha256':digest,'source_path':str(source),'source_form':form,'filers':r.get('filers',[]),'subjects':r.get('subjects',[]),'cusip_candidate':r.get('cusip'),'security_candidate':sec,'security_search_group':security_hint(sec['raw_title']),'selection_stratum':entry['selection_stratum'],'search_evidence':ev,'documents':documents,'final_filer_type':'unreviewed','final_issuer_type':'unreviewed','hedge_fund_status':'unreviewed','activist_event_status':'unreviewed','outside_investor_status':'unreviewed','reviewer':None,'canonicalizer_sha256':sha((ROOT/'scripts/extraction_prep/prepare_sample.py').read_bytes())}
    frozen(out/'bundles'/f'{acc}.json',(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode())
    esc=html.escape
    body=[f'<h1>{esc(acc)}</h1>',f'<p>Filed {r["filing_date"]} · <a href="{esc(meta.get("url", ""),quote=True)}">SEC source</a> · <a href="../index.html">Review index</a></p>', '<p>Full supplied canonical text. External incorporated documents are not retrieved. Record your answers in review-worksheet.csv or your own dated notes; this page does not save edits.</p>','<h2>Classification worksheet</h2><p>Issuer type / security class / filer entity type / manager identity / hedge-fund status / outside-investor relationship / specific activist action / exact evidence / reviewer / date: <b>all unreviewed</b>.</p>','<details><summary>Show mechanical search evidence (not classifications)</summary><p>A phrase may refer to a third party or boilerplate. No hit is not a negative label.</p>']
    for e in ev:body.append(f'<p><b>{esc(e["cue"])}</b> · {esc(e["document_id"])} [{e["start"]},{e["end"]})</p><blockquote>{esc(e["quote"])}</blockquote>')
    body.append('</details>')
    for d in documents:body.append(f'<h2>{esc(d["document_id"])} — {esc(d["filename"] or "unnamed")}</h2><p>{esc(d["status"])}</p><pre>{esc(d["text"] or "[Binary or unavailable text: inspect raw source]")}</pre>')
    page='<!doctype html><meta charset="utf-8"><title>13D evidence review</title><style>body{max-width:1050px;margin:35px auto;padding:20px;font:16px/1.55 system-ui;color:#243b53}pre{white-space:pre-wrap;font:inherit}blockquote{background:#eef3f8;padding:15px}h2{margin-top:40px}</style>'+''.join(body)
    frozen(out/'packets'/f'{acc}.html',page.encode())
def build_index(out):
    bundles=[json.loads(p.read_text()) for p in sorted((out/'bundles').glob('*.json'))]
    rows=[]
    for b in bundles:
        labels=sorted({e['cue'] for e in b['search_evidence']})
        rows.append({'accession':b['accession'],'date':b['filing_date'],'issuer':'; '.join(x['name'] for x in b['subjects']),'filer':'; '.join(x['name'] for x in b['filers']),'security':b['security_search_group'],'cues':labels,'stratum':b['selection_stratum']})
    safe=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
    page='''<!doctype html><meta charset="utf-8"><title>Grouped 13D review</title><style>body{font:15px/1.5 system-ui;margin:30px;color:#243b53}table{border-collapse:collapse;width:100%}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}th{background:#243b53;color:white}input,select{padding:8px;margin:5px}a{color:#1864ab}.note{max-width:1100px;background:#eef3f8;padding:15px}</style><h1>Grouped 13D development review</h1><p class="note">Search groups are mechanical phrase/title matches, not verified investor categories. An investment adviser is not automatically a hedge fund; an action phrase is not automatically an activist demand. Review actor, target, timing and context. These development examples are selected without returns and do not estimate population prevalence.</p><p><a href="Grouped-13D-Review.xlsx">Excel review workbook</a> · <a href="review-worksheet.csv">CSV worksheet</a> · <a href="filer-verification.csv">Filer verification queue</a> · <a href="GUIDE.html">Classification guide</a></p><label>Issuer / filer / accession <input id="q" placeholder="Search names"></label><label>Evidence filter <select id="cue"><option value="">All evidence groups</option></select></label><label>Security-title hint <select id="security"><option value="">All securities</option></select></label><button id="focus">Manager + action candidates</button><button id="reset">Reset</button><p id="count"></p><table><thead><tr><th>Filing</th><th>Issuer (header)</th><th>Filer (header)</th><th>Security-title hint</th><th>Search evidence</th></tr></thead><tbody id="rows"></tbody></table><script>const data=DATA;let focus=false;const el=id=>document.getElementById(id);for(const [id,values] of [['cue',[...new Set(data.flatMap(r=>r.cues))]],['security',[...new Set(data.map(r=>r.security))]]])for(const v of values.sort()){let o=document.createElement('option');o.value=v;o.textContent=v;el(id).append(o)}function render(){let q=el('q').value.toLowerCase();let rows=data.filter(r=>(r.issuer+' '+r.filer+' '+r.accession).toLowerCase().includes(q)&&(!el('cue').value||r.cues.includes(el('cue').value))&&(!el('security').value||r.security===el('security').value)&&(!focus||(r.cues.includes('Manager/fund language')&&r.cues.includes('Action language'))));el('count').textContent=rows.length+' of '+data.length+' prepared filings'+(focus?' · manager + action phrase intersection; not verified activist hedge funds':'');el('rows').replaceChildren();for(const r of rows){let tr=document.createElement('tr');for(const [i,v] of [r.date+' '+r.accession,r.issuer,r.filer,r.security,r.cues.join('; ')].entries()){let td=document.createElement('td');if(i===0){let a=document.createElement('a');a.href='packets/'+r.accession+'.html';a.textContent=v;td.append(a)}else td.textContent=v;tr.append(td)}el('rows').append(tr)}}for(const id of ['q','cue','security'])el(id).addEventListener('input',render);el('focus').onclick=()=>{focus=true;render()};el('reset').onclick=()=>{focus=false;for(const id of ['q','cue','security'])el(id).value='';render()};render();</script>'''.replace('DATA',safe)
    (out/'index.html').write_text(page)
    columns=['accession','filing_date','issuer_header','filer_header','filer_ciks','security_title_candidate','security_search_group','mechanical_evidence_groups','final_security_type','final_issuer_type','final_filer_type','manager_identity','hedge_fund_status','outside_investor_status','activist_event_status','specific_action','evidence_document_and_offsets','missing_evidence','reviewer','review_date','notes']
    target=out/'review-worksheet.csv'
    if not target.exists():
        with target.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
            for b,r in zip(bundles,rows):w.writerow({'accession':b['accession'],'filing_date':b['filing_date'],'issuer_header':r['issuer'],'filer_header':r['filer'],'filer_ciks':'; '.join(x.get('cik','') for x in b['filers']),'security_title_candidate':b['security_candidate']['raw_title'],'security_search_group':r['security'],'mechanical_evidence_groups':'; '.join(r['cues']),**{c:'unreviewed' for c in ['final_security_type','final_issuer_type','final_filer_type','manager_identity','hedge_fund_status','outside_investor_status','activist_event_status']}})
    filers={}
    for b in bundles:
        for f in b['filers']:
            key=f.get('cik') or f['name'];a=filers.setdefault(key,{'cik':f.get('cik'),'raw_names':set(),'accessions':set()});a['raw_names'].add(f['name']);a['accessions'].add(b['accession'])
    if not (out/'filer-verification.csv').exists():
        with (out/'filer-verification.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['CIK','Source names','Filings','Manager identity','Filer type','Hedge fund status','Evidence URL / passage','Evidence as-of date','Reviewer'])
            for _,v in sorted(filers.items()):w.writerow([v['cik'],'; '.join(sorted(v['raw_names'])),'; '.join(sorted(v['accessions'])),'unreviewed','unreviewed','unreviewed','','',''])
    return {'prepared':len(rows),'unique_header_filer_keys':len(filers),'security_title_hints':dict(Counter(r['security'] for r in rows)),'overlapping_evidence_groups':dict(Counter(c for r in rows for c in r['cues'])),'manager_and_action_phrase_intersection':sum('Manager/fund language' in r['cues'] and 'Action language' in r['cues'] for r in rows)}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--size',type=int,default=200);parser.add_argument('--one');args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if args.one:return one(out,args.one)
    if args.size%4 or args.size<4:raise ValueError('Size must be positive multiple of four')
    start=time.monotonic();progress=lambda **kw:write(out/'progress.json',{'updated_utc':datetime.now(timezone.utc).isoformat(),**kw})
    for d in ['bundles','packets','errors']:(out/d).mkdir(exist_ok=True)
    if shutil.disk_usage(out).free<20*1024**3:raise RuntimeError('20 GiB disk reserve required')
    progress(status='running',stage='loading_selection',target=args.size,worker_pid=os.getpid())
    baseline={p.name:sha(p.read_bytes()) for p in [BLIND/'sample-manifest.json',BLIND/'human-labels.jsonl',BLIND/'COMPLETE.json']}
    exclusions={r['accession'] for r in json.loads((BLIND/'sample-manifest.json').read_text())['records']}
    exclusions.update(r['accession'] for r in json.loads((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text()))
    exclusions.update(p.stem for p in (ROOT/'research/runs/phase1-prep').glob('*/packets/*.html'))
    if (out/'selection.json').exists():
        selection=json.loads((out/'selection.json').read_text());assert selection['script_sha256']==sha(Path(__file__).read_bytes()),'Changed code: choose a new output directory';assert selection['size']==args.size
    else:
        rows=[];scanned=0
        with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as db:
            for (raw,) in db.execute('SELECT record_json FROM records ORDER BY accession'):
                r=json.loads(raw);scanned+=1
                if not r.get('is_amendment') and r.get('form') in ['13D','SC 13D','SCHEDULE 13D'] and r.get('source_bytes',0)<=20*1024**2 and 2013<=int(r['filing_date'][:4])<=2024:rows.append(r)
        selected,counts=select(rows,exclusions,args.size)
        frame_sha=sha(json.dumps([(r['accession'],r['source_sha256']) for r in rows],separators=(',',':')).encode())
        selection={'seed':SEED,'size':args.size,'script_sha256':sha(Path(__file__).read_bytes()),'frame_rows':len(rows),'scanned_rows':scanned,'frame_identity_sha256':frame_sha,'source_database':str(DB),'excluded_accessions':sorted(exclusions),'blind_baseline':baseline,'strata':counts,'selected':selected,'is_probability_sample':False,'is_validated_campaign_sample':False,'outcomes_used':False}
        write(out/'selection.json',selection)
    assert not ({e['record']['accession'] for e in selection['selected']}&exclusions)
    frozen(out/'GUIDE.html',(ROOT/'scripts/group_review/GUIDE.html').read_bytes())
    processed=0;failures=0
    for e in selection['selected']:
        acc=e['record']['accession']
        if time.monotonic()-start>7200:progress(status='paused_at_runtime_limit',processed=processed,target=args.size);return
        if shutil.disk_usage(out).free<20*1024**3:raise RuntimeError('20 GiB reserve reached')
        if sum(p.stat().st_size for folder in ['bundles','packets'] for p in (out/folder).glob('*'))>512*1024**2:raise RuntimeError('512 MiB output cap reached')
        progress(status='running',stage='verifying_and_preparing',processed=processed,target=args.size,accession=acc,failures=failures,worker_pid=os.getpid())
        try:
            if (out/'bundles'/f'{acc}.json').exists() and (out/'packets'/f'{acc}.html').exists():
                b=json.loads((out/'bundles'/f'{acc}.json').read_text());assert b['source_sha256']==sha(resolve_project_path(e['record']['source_path'],ROOT).read_bytes())
            else:
                subprocess.run([sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--one',acc],check=True,timeout=90,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        except (Exception,) as error:
            failures+=1;write(out/'errors'/f'{acc}.json',{'accession':acc,'error':str(error),'stderr':(getattr(error,'stderr',None) or b'').decode(errors='replace')[-3000:]})
        processed+=1
        if processed%10==0:print(f'Processed {processed}/{args.size}; failures {failures}',flush=True)
    report=build_index(out)
    if not (out/'Grouped-13D-Review.xlsx').exists():
        progress(status='running',stage='building_excel',processed=processed,target=args.size,failures=failures)
        subprocess.run(['/Users/jefflu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node',str(ROOT/'scripts/group_review/workbook.mjs'),str(out)],check=True,timeout=600)
    after={p.name:sha(p.read_bytes()) for p in [BLIND/'sample-manifest.json',BLIND/'human-labels.jsonl',BLIND/'COMPLETE.json']};assert after==baseline==selection['blind_baseline']
    report.update(target=args.size,failures=failures,selection_strata=selection['strata'],blind32_manifest_labels_completion_unchanged=True,network_calls=0,model_api_calls=0,elapsed_seconds=round(time.monotonic()-start,2),status='completed' if failures==0 else 'completed_with_gaps',issuer_type_verified=0,hedge_fund_status_verified=0,activist_event_status_verified=0)
    write(out/'completion.json',report);progress(stage='finished',**report)
    (out/'MORNING-HANDOFF.txt').write_text('Open index.html to review by mechanical evidence groups. Open review-worksheet.csv in Excel for classifications. No verified hedge-fund/activist labels or returns were generated. '+json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
