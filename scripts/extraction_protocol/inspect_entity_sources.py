"""Tier 0 read-only probe of HFR field labels and exposed Basswood role passages.
Inputs: frozen HFR Fund workbook and first canonical 13D bundle. Output: console.
No joins, inferred roles, source modifications or model labels.
Run with project .venv/bin/python, PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8.
"""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
path = ROOT/'data/raw/hfr/2026-09-13/HFR_HFRDB_EXCEL_Fund.xlsx'
assert hashlib.sha256(path.read_bytes()).hexdigest() == 'aa3cc17cd1662b5c5e984aab52e94d03a6010cab0739d6890c681cc6a8846062'
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(path) as z:
    strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        strings=[''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
    sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)
    print('Sheets:',[(s.get('name'),s.get('sheetId')) for s in sheets])
    for _,row in ET.iterparse(z.open('xl/worksheets/sheet1.xml'),events=['end']):
        if row.tag.endswith('}row'):
            values=[]
            for c in row.findall('m:c',ns):
                v=c.find('m:v',ns)
                raw=v.text if v is not None else ''
                value=strings[int(raw)] if c.get('t')=='s' and raw else raw
                if c.get('t')=='inlineStr':value=''.join(c.find('m:is',ns).itertext())
                if value:values.append((c.get('r'),value))
            print('First row labels:',values)
            break
bundle=json.loads((ROOT/'review/drafts/human-first-52/bundles/0000899140-19-000386.json').read_text())
doc=next(d for d in bundle['documents'] if d['document_id']=='DOCUMENT[1]')
text=doc['text']
for phrase in ['managing members','investment manager or adviser','general partner']:
    match=re.search(phrase,text,re.I)
    if match:print('Basswood passage:',text[max(0,match.start()-200):match.end()+300])
