"""Tier 1: Verify saved XLSX text preservation and citations against frozen inputs.
Run: PYTHONNOUSERSITE=1 .venv/bin/python scripts/extraction_protocol/verify_pilot_workbook_v2.py
Reads the v2 review workbook and JSON; writes a validation report only.
Identity: ordered XLSX chunks reconstruct each canonical document exactly.
"""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[2]
out=root/'review/archive/13d-structured-review-20260922'
records=json.loads((out/'review-inputs.json').read_text())
data=json.loads((out/'review-data.json').read_text())
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
book=out/'13D-Structured-Extraction-Review.xlsx'
with zipfile.ZipFile(book) as z:
    shared=ET.fromstring(z.read('xl/sharedStrings.xml'))
    strings=[''.join(n.itertext()) for n in shared]
    sheet=ET.fromstring(z.read('xl/worksheets/sheet12.xml'))
    chunks={}
    for row in sheet.findall('s:sheetData/s:row',ns):
        if int(row.attrib['r'])<5:continue
        cells={}
        for c in row:
            v=c.find('s:v',ns)
            if v is None:continue
            cells[''.join(x for x in c.attrib['r'] if x.isalpha())]=strings[int(v.text)] if c.attrib.get('t')=='s' else v.text
        if 'A' not in cells:continue
        chunks.setdefault((cells['A'],cells['B']),[]).append((int(cells['C']),int(cells['D']),cells['E']))
    assert len(chunks)==27
    for r in records:
        for d in r['documents']:
            parts=sorted(chunks[(r['accession'],d['document_id'])])
            cursor=0
            for start,end,text in parts:
                assert start==cursor and end-start==len(text)
                cursor=end
            assert ''.join(p[2] for p in parts)==d['text']
    assert len(ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets',ns))==12
    review=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
    assert review.find('s:dataValidations',ns) is not None
for e in data['evidence']:
    if e[7].startswith('Exact match'):
        r=next(r for r in records if r['accession']==e[1])
        d=next(d for d in r['documents'] if d['document_id']==e[2])
        assert d['text'][e[3]:e[4]]==e[5]
report={'workbook_sha256':hashlib.sha256(book.read_bytes()).hexdigest(),'sheets':12,'documents_reconstructed_exactly':27,'exact_citations':sum(e[7].startswith('Exact match') for e in data['evidence']),'unresolved_ledger_quotes':sum(e[7]=='QUOTE MISMATCH' for e in data['evidence']),'review_rows':len(data['reviews']),'limits':['Semantic labels remain preliminary/unreviewed.','Externally incorporated documents not retrieved.','Native Excel application not exercised.'],'canonicalizer_sha256':hashlib.sha256((root/'scripts/extraction_prep/prepare_sample.py').read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256((out/'build.mjs').read_bytes()).hexdigest()}
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
