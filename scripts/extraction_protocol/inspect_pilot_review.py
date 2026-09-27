"""Inspect cached pilot fields and selected source passages for review. Tier: 0.
Run with the project Python; reads review-inputs.json and writes only stdout.
"""
import json
import re
from pathlib import Path

root=Path(__file__).resolve().parents[2]
for r in json.loads((root/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text()):
    p=r['pilot']
    print('\nACCESSION',r['accession'])
    print(json.dumps({k:v for k,v in p.items() if k not in ['documents','item4_text','xml_fields']},ensure_ascii=False))
    print('XML',json.dumps(p.get('xml_fields'),ensure_ascii=False)[:1800])
    main=r['documents'][1]['text']
    print('COVER',main[:1100])
    for label in ['Item 3','Item 6']:
        hits=list(re.finditer(label+r'\.?',main,re.I))
        print(label,[(m.start(),main[max(0,m.start()-40):m.start()+1200]) for m in hits][-3:])
