"""Audit the prepared development pack and original blank packet hashes.

Inputs: completed development pack and original frozen hash baseline. Outputs:
separate audit JSON; no edits to packets, worksheets, or protocol definitions.
Identity: every output digest equals COMPLETE.json and all reference labels
remain null/unreviewed. No model predictions are generated.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/audit_pack.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == '__main__':
    folder = ROOT / 'research/runs/extraction-prep/development-20260916'
    complete = json.loads((folder / 'COMPLETE.json').read_text())
    for relative, digest in complete['outputs_sha256'].items():
        assert sha(folder / relative) == digest, relative
    labels = [json.loads(line) for line in (folder / 'human-labels.jsonl').read_text().splitlines()]
    assert len(labels) == 32 and len({r['accession'] for r in labels}) == 32
    assert all(r['workflow_status'] == 'unreviewed' and r['intent'] is None and r['fields'] is None and r['evidence'] == [] for r in labels)
    docs_n = 0
    for p in (folder / 'document-text').glob('*.json'):
        bundle = json.loads(p.read_text())
        for d in bundle['documents']:
            assert d['source_accession'] == bundle['accession']
            if d['text'] is not None:
                assert hashlib.sha256(d['text'].encode()).hexdigest() == d['text_sha256']
            docs_n += 1
    result = {'sample_size': 32, 'output_hashes_verified': True, 'all_worksheets_blank': True, 'canonical_documents_verified': docs_n,
              'paid_model_api_calls': 0, 'original_packet_hash_verification': 'pending'}
    (folder / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    original = ROOT / 'research/runs/phase1-prep/20260914T003050627334Z/packets'
    baseline = json.loads((ROOT / 'research/runs/phase1-prep/integrity-20260914T004440397334Z/audit.json').read_text())['packet_hashes_after']
    current = {p.name: sha(p) for p in original.glob('*.html')}
    assert current == baseline
    result['original_packet_hash_verification'] = 'verified_unchanged'
    (folder / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
