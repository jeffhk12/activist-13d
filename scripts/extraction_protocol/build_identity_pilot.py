"""Tier 1: create a five-filing identity review from explicit relationship evidence.
Inputs: frozen first-five bundles, HFR Fund snapshot, source-transcribed roles.
Outputs: related JSON evidence and local HTML review, no semantic investment labels.
Identity: text[start:end] == quote; HFR candidates never overwrite historical roles.
Run with project .venv/bin/python, PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'research/runs/investor-identity/20260923-five'
PACK=ROOT/'review/drafts/investor-identity-five-20260923'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
HFR=ROOT/'data/raw/hfr/2026-09-13/HFR_HFRDB_EXCEL_Fund.xlsx'
HFR_HASH='aa3cc17cd1662b5c5e984aab52e94d03a6010cab0739d6890c681cc6a8846062'

def sha(data):return hashlib.sha256(data).hexdigest()
def encode(v):return json.dumps(v,indent=2,ensure_ascii=False,sort_keys=True)+'\n'

def hfr_rows():
    assert sha(HFR.read_bytes())==HFR_HASH
    with ZipFile(HFR) as z:
        strings=[''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)] if 'xl/sharedStrings.xml' in z.namelist() else []
        headers={}
        for _,row in ET.iterparse(z.open('xl/worksheets/sheet1.xml'),events=['end']):
            if row.tag.endswith('}row'):
                values={}
                for c in row.findall('m:c',NS):
                    col=re.sub(r'\d','',c.get('r'))
                    v=c.find('m:v',NS);raw=v.text if v is not None else ''
                    value=strings[int(raw)] if c.get('t')=='s' and raw else raw
                    if c.get('t')=='inlineStr':value=''.join(c.find('m:is',NS).itertext())
                    values[col]=value
                if not headers:headers=values
                else:yield int(row.get('r')),{headers.get(col,col):value for col,value in values.items()},headers
                row.clear()

def discover():
    OUT.mkdir(parents=True,exist_ok=True)
    files=sorted((ROOT/'review/drafts/human-first-52/bundles').glob('*.json'))[:5]
    records=[json.loads(p.read_text()) for p in files]
    manifest=[{'accession':r['accession'],'filing_date':r['filing_date'],'bundle_path':str(p.relative_to(ROOT)), 'bundle_sha256':sha(p.read_bytes()),'source_sha256':r['source_sha256'],'filers':r['filers'],'subjects':r['subjects']} for r,p in zip(records,files,strict=True)]
    (OUT/'input-manifest.json').write_text(encode(manifest))
    print(encode(manifest))
    # Discovery only: first distinctive word of the header filer, no identity merge.
    terms={re.findall(r'[A-Za-z]+',f['name'])[0].casefold() for r in records for f in r['filers']}
    keep={'Fund_ID','Fund','Firm_ID','Firm','Principals','Firm_SEC_Number','Firm_IARD_CRD_Number','Website','Family_ID','SEC_PFID_Number'}
    matches=[]
    for row_no,row,headers in hfr_rows():
        terms_hit=sorted(t for t in terms if re.search(r'\b'+re.escape(t)+r'\b',(row.get('Firm','') or '')+' '+(row.get('Fund','') or ''),re.I))
        if terms_hit:
            matches.append({'excel_row':row_no,'matched_tokens':terms_hit,'match_status':'name_search_candidate_not_verified','fields':{key:row.get(key) or None for key in sorted(keep)},'cells':{key:col+str(row_no) for col,key in headers.items() if key in keep},'source_sha256':HFR_HASH,'snapshot_datestamp':'2026-09-08','sheet':'HFR_HFRDB_EXCEL_Fund'})
    (OUT/'hfr-candidates.json').write_text(encode(matches))
    print('HFR candidates:',encode(matches))

if __name__=='__main__':discover()
