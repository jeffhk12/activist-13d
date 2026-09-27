"""Tier 1: bounded Elliott identity discovery from local SEC index and HFR.
Inputs: read-only SEC SQLite metadata and frozen HFR workbook. Outputs: candidate
inventory with exact names/IDs; no merging or activist labels. Name hits are not identity proof.
Run with project .venv/bin/python and PYTHONNOUSERSITE/PYTHONIOENCODING.
"""
from contextlib import closing
import json
import re
import sqlite3
from build_identity_pilot import ROOT, hfr_rows, encode, HFR_HASH

OUT=ROOT/'research/runs/investor-identity/20260923-elliott'
OUT.mkdir(parents=True,exist_ok=True)
dbpath=ROOT/'research/runs/phase1-overnight/full-20260915/sec.sqlite'
records=[]
with closing(sqlite3.connect(f'file:{dbpath}?mode=ro',uri=True)) as db:
    for (raw,) in db.execute("SELECT record_json FROM records WHERE record_json LIKE '%elliott%'"):
        record=json.loads(raw)
        if any(re.search(r'\belliott?\b',f.get('name',''),re.I) for f in record.get('filers',[])):
            records.append(record)
records.sort(key=lambda r:(r['filing_date'],r['accession']),reverse=True)
(OUT/'local-filing-candidates.json').write_text(encode(records))
print('Filer-name matched local records:',len(records))
for r in records[:12]:print({k:r.get(k) for k in ['accession','filing_date','form','filers','subjects','source_path','source_sha256']})
keep=['Fund_ID','Fund','Firm_ID','Firm','Principals','Firm_SEC_Number','Firm_IARD_CRD_Number','Website','Family_ID']
matches=[]
for rowno,row,headers in hfr_rows():
    if re.search(r'\belliott?\b',(row.get('Firm','') or '')+' '+(row.get('Fund','') or ''),re.I):
        matches.append({'excel_row':rowno,'source_sha256':HFR_HASH,'snapshot_datestamp':'2026-09-08','sheet':'HFR_HFRDB_EXCEL_Fund','fields':{k:row.get(k) or None for k in keep},'cells':{k:c+str(rowno) for c,k in headers.items() if k in keep},'status':'name_candidate_not_verified'})
(OUT/'hfr-candidates.json').write_text(encode(matches))
print('HFR candidates:',encode(matches))
