"""Tier: 1. Isolate HFR Event-Driven fund rows and screen SEC filer names.
Inputs: frozen HFR workbook, read-only local SEC record database.
Outputs: dated JSON evidence and HTML manager review; no identity auto-merges.
Identities: fund universe = Main_Strategy exactly Event-Driven; managers grouped
only by supplied Firm_ID. Name matches remain candidates, not identifier links.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/match_hfr_event_driven.py
"""
from collections import Counter, defaultdict
from contextlib import closing
import hashlib
import html
import json
import os
import re
import sqlite3
from build_identity_pilot import ROOT, HFR, HFR_HASH, hfr_rows

OUT=ROOT/'research/runs/investor-identity/20260923-hfr-event-driven-v1'
PACK=ROOT/'review/drafts/hfr-event-driven-20260923'
DB=ROOT/'research/runs/phase1-overnight/full-20260915/sec.sqlite'

def norm(name):
    value=re.sub(r'\bL\s*\.\s*L\s*\.\s*C\b',' LLC',name,flags=re.I)
    value=re.sub(r'\bL\s*\.\s*P\b',' LP',value,flags=re.I)
    return ' '.join(re.findall(r'[a-z0-9]+',value.lower()))

def base(name):
    words=norm(name).split()
    while words and words[-1] in {'llc','lp','ltd','limited','inc','incorporated','corp','corporation','llp'}:
        words.pop()
    return ' '.join(words)

def build():
    assert norm('ALPHA, L.P.')==norm('Alpha LP')
    assert base('Alpha Capital LLC')==base('Alpha Capital, L.P.')
    assert base('Alpha Capital')!=base('Alpha Partners')
    assert base('Beta')!=base('Alphabet')
    keep=['Fund_ID','Fund','Firm_ID','Firm','Main_Strategy','Sub_Strategy','Principals','Firm_SEC_Number','Firm_IARD_CRD_Number','Website']
    funds=[]
    for rowno,row,headers in hfr_rows():
        if row.get('Main_Strategy')=='Event-Driven':
            funds.append({'excel_row':rowno,'fields':{k:row.get(k) for k in keep},'cells':{k:c+str(rowno) for c,k in headers.items() if k in keep}})
    managers={}
    for row in funds:
        f=row['fields']; key=f['Firm_ID'] or f'missing-firm-id-row-{row["excel_row"]}'
        managers.setdefault(key,{'firm_id':key,'names':set(),'fund_rows':[],'substrategies':set(),'crd':set(),'sec':set()})
        m=managers[key]; m['names'].add(f['Firm']); m['fund_rows'].append(row['excel_row']); m['substrategies'].add(f['Sub_Strategy'])
        for target,source in [('crd','Firm_IARD_CRD_Number'),('sec','Firm_SEC_Number')]:
            if f[source]: m[target].add(f[source])
    assert sum(len(m['fund_rows']) for m in managers.values())==len(funds)
    # Index only EDGAR reporting-party names, never issuer names or body mentions.
    filers=defaultdict(dict)
    count=0
    with closing(sqlite3.connect(f'file:{DB}?mode=ro',uri=True)) as db:
        for (raw,) in db.execute('SELECT record_json FROM records ORDER BY accession'):
            r=json.loads(raw)
            if r.get('form') not in {'13D','13D/A'}: continue
            count+=1
            for f in r.get('filers',[]):
                if f.get('name'):
                    filers[(f['name'],f.get('cik'))][r['accession']]={k:r.get(k) for k in ['accession','filing_date','form','subjects','source_path','source_sha256']}
    for m in managers.values():
        exact={norm(n) for n in m['names']}; reduced={base(n) for n in m['names']}
        # Fund names also searched, but never used as proof of adviser identity.
        fund_names={norm(r['fields']['Fund']) for r in funds if r['excel_row'] in m['fund_rows']}
        hits=[]
        for (name,cik),records in filers.items():
            method=None
            if norm(name) in exact: method='Exact normalized firm name'
            elif base(name) in reduced: method='Firm name after legal-suffix removal'
            elif norm(name) in fund_names: method='Exact normalized fund name'
            if method:
                hits.append({'sec_filer_name':name,'cik':cik,'method':method,'status':'name_candidate_not_identity_verified','filings':sorted(records.values(),key=lambda r:(r['filing_date'],r['accession']))})
        m['matches']=sorted(hits,key=lambda h:(h['method'],h['sec_filer_name'],h['cik'] or ''))
        m['unique_filings']=len({r['accession'] for h in hits for r in h['filings']})
        for key in ['names','substrategies','crd','sec']:m[key]=sorted(m[key])
    ordered=sorted(managers.values(),key=lambda m:(not bool(m['matches']), 'Activist' not in m['substrategies'],m['names'][0]))
    sub=Counter(r['fields']['Sub_Strategy'] for r in funds)
    summary={'hfr_fund_rows':len(funds),'hfr_firm_ids':len(managers),'firms_with_name_candidates':sum(bool(m['matches']) for m in ordered),'activist_fund_rows':sub['Activist'],'activist_firms':sum('Activist' in m['substrategies'] for m in ordered),'activist_firms_with_name_candidates':sum('Activist' in m['substrategies'] and bool(m['matches']) for m in ordered),'local_13d_records_scanned':count,'substrategy_fund_rows':dict(sorted(sub.items())),'verified_cross_database_identifier_matches':0}
    result={'summary':summary,'hfr_snapshot':'2026-09-08','hfr_path':str(HFR),'hfr_sha256':HFR_HASH,'hfr_sheet':'HFR_HFRDB_EXCEL_Fund','database_path':str(DB),'database_sha256':hashlib.sha256(DB.read_bytes()).hexdigest(),'rules':'Exact Event-Driven fund classification; deduplicate managers by HFR Firm_ID. Match normalized firm names, then legal-suffix-stripped firm names, then exact normalized fund names to SEC reporting-party names. All are unverified identity candidates. No fuzzy or substring matching. CRD/SEC adviser file numbers are not CIKs.','funds':funds,'managers':ordered}
    return result

def render(result):
    e=html.escape;s=result['summary']; rows=[]
    for m in result['managers']:
        hits=[]
        for h in m['matches']:
            links=[]
            for r in h['filings']:
                path=ROOT/r['source_path']
                issuer='; '.join(x['name'] for x in r.get('subjects',[]))
                label=f'{e(r["filing_date"])} · {e(r["form"])} · {e(issuer)} · {e(r["accession"])}'
                if path.is_file():
                    links.append(f'<li><a href="{e(os.path.relpath(path,PACK))}">{label}</a></li>')
                else:
                    links.append(f'<li>{label} — metadata only; raw source unavailable at recorded path</li>')
            hits.append(f'<details><summary>{e(h["sec_filer_name"])} · CIK {e(h["cik"] or "missing")} · {len(h["filings"])} filings</summary><p>{e(h["method"])} — identity verification pending</p><ul>'+''.join(links)+'</ul></details>')
        rows.append('<tr><td>'+e('; '.join(m['names']))+f'<br>HFR Firm_ID {e(m["firm_id"])}<br>{len(m["fund_rows"])} fund rows</td><td>'+e('; '.join(m['substrategies']))+'</td><td>'+e('CRD: '+', '.join(m['crd'])+' / SEC: '+', '.join(m['sec']))+'</td><td>'+(''.join(hits) or 'No candidate under these name rules')+'</td></tr>')
    counts=''.join(f'<tr><td>{e(k)}</td><td>{v}</td></tr>' for k,v in s['substrategy_fund_rows'].items())
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HFR Event-Driven managers in 13D</title><style>body{{font:16px/1.55 system-ui;color:#203448;background:#f4f6f8;max-width:1400px;margin:30px auto;padding:20px}}section{{background:white;padding:24px;margin:20px 0}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #ddd}}a{{color:#176699}}summary{{cursor:pointer}}input{{font:inherit;padding:12px;width:70%}}</style><h1>HFR Event-Driven managers → local 13D archive</h1><p>HFR snapshot 8 September 2026 · exploratory name matching, not verified entity resolution</p><section><h2>Coverage</h2><p><b>{s['hfr_fund_rows']} fund rows · {s['hfr_firm_ids']} manager Firm_IDs · {s['firms_with_name_candidates']} managers with name candidates ({s['firms_with_name_candidates']/s['hfr_firm_ids']:.1%})</b></p><p>HFR Activist subset: {s['activist_fund_rows']} fund rows, {s['activist_firms']} managers, {s['activist_firms_with_name_candidates']} with name candidates. Scanned {s['local_13d_records_scanned']:,} local 13D/13D-A metadata records. Verified cross-database identifier matches: 0; adviser CRD and SEC file numbers require a separate bridge to filer CIK.</p><table><tr><th>HFR substrategy</th><th>Fund rows (not unique portfolios)</th></tr>{counts}</table><p>Managers can occur in several substrategies. Fund rows may include share classes. Current HFR strategy labels are not historical labels. Missing matches may reflect aliases, fund vehicles, non-US activity, or local archive gaps. Event-driven membership is not proof of activist intent or investment quality. No filing intent labels were generated.</p></section><section><h2>Manager review</h2><p>Matched activist-substrategy managers appear first. Expand a filer to access its cached raw submissions. Search filters displayed rows.</p><input id="q" aria-label="Filter manager table" placeholder="Search manager, strategy or CIK" oninput="document.querySelectorAll('#managers tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table id="managers"><thead><tr><th>HFR manager</th><th>HFR substrategies</th><th>HFR identifiers</th><th>SEC name candidates and filings</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section><section><h2>Method and provenance</h2><p>{e(result['rules'])}</p><p>HFR source: {e(str(HFR))}; sheet HFR_HFRDB_EXCEL_Fund. Exact source row/cell addresses and all candidate accessions are preserved in <a href="{e(os.path.relpath(OUT/'matches.json',PACK))}">the evidence JSON</a>.</p><p>Next verification: resolve CRD/SEC adviser identities to dated CIKs and fund relationships; then review Item 4 separately. No-match firms are retained for review.</p><a href="../../../START-HERE.html">Project home</a></section></html>'''

if __name__=='__main__':
    result=build()
    assert result==build(), 'Offline replay differs'
    OUT.mkdir(parents=True,exist_ok=True);PACK.mkdir(parents=True,exist_ok=True)
    for path,content in [(OUT/'matches.json',json.dumps(result,indent=2)+'\n'),(PACK/'index.html',render(result))]:
        if path.exists():assert path.read_text()==content,'Refusing changed run output'
        else:path.write_text(content)
    print(json.dumps(result['summary'],indent=2))
    print('Matched activist firms:',[(m['names'],m['unique_filings']) for m in result['managers'] if m['matches'] and 'Activist' in m['substrategies']])
