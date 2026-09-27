"""Tier: 0. Read-only HFR category inventory; stdout only.
Run with project Python; uses frozen workbook reader, no workbook changes.
"""
from collections import Counter
from build_identity_pilot import hfr_rows
counts=Counter()
sample=[]
for rownum,row,headers in hfr_rows():
    counts[(row.get('Main_Strategy'),row.get('Sub_Strategy'))]+=1
    if 'event' in str(row.get('Main_Strategy','')).lower() and len(sample)<8:
        sample.append({k:row.get(k) for k in ['Fund','Firm','Firm_ID','Main_Strategy','Sub_Strategy','Firm_IARD_CRD_Number','Firm_SEC_Number']})
print(counts)
print(sample)
