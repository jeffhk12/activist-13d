"""Tier: 0. Display only the first practice filing's SEC header for instruction.
Input: frozen pilot bundle. Output: header text, no model ownership labels.
Run: project Python this file.
"""
import gzip
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
p = root / 'review/drafts/ownership-identity-pilot-20260925/bundles/0001104659-20-044387.json.gz'
b = json.loads(gzip.decompress(p.read_bytes()))
print(next(d['text'] for d in b['documents'] if d['document_id'] == 'SEC-HEADER'))
