"""Validate completed v1 extraction records and exact canonical-text evidence.

Inputs: completed record JSON and per-accession canonical evidence JSON.
Outputs: pass/fail only; writes no labels or raw evidence. Identity: cited quote
= canonical document text[start:end], and every referenced SHA matches bytes.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/validate.py RECORD EVIDENCE
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'protocol'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def protocol_hashes():
    return {key: digest((PROTOCOL / filename).read_bytes()) for key, filename in {
        'categories': 'categories-v1.yaml', 'prompt': 'extraction-prompt-v1.md',
        'schema': 'schema-v1.json', 'workflow': 'extraction-workflow-v1.md',
        'validation_plan': 'validation-plan-v1.md'}.items()}


def validate(record, bundle, bundle_bytes):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((PROTOCOL / 'schema-v1.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    if record['input_manifest_sha256'] != digest(bundle_bytes):
        raise ValueError('Input manifest hash mismatch')
    if record['protocol_hashes'] != protocol_hashes():
        raise ValueError('Protocol hash mismatch')
    if record['accession'] != bundle['accession'] or record['raw_source_sha256'] != bundle['source_sha256']:
        raise ValueError('Accession/raw source hash mismatch')
    form = bundle.get('source_form', '').replace('SCHEDULE ', '').replace('SC ', '').strip()
    if form not in ('13D', '13D/A'):
        raise ValueError('Evidence bundle must identify the observed source form')
    expected_scope = 'amendment_diagnostic' if form.endswith('/A') else 'initial_disclosure'
    if record['analysis_scope'] != expected_scope:
        raise ValueError('Analysis scope differs from source filing form')
    docs = {d['document_id']: d for d in bundle['documents']}
    if len(docs) != len(bundle['documents']):
        raise ValueError('Duplicate document ID in evidence bundle')
    for d in docs.values():
        if d.get('source_accession') != bundle['accession']:
            raise ValueError('v1 accepts only documents embedded in the same source accession')
        if isinstance(d.get('text'), str) and digest(d['text'].encode('utf-8')) != d['text_sha256']:
            raise ValueError('Canonical text hash mismatch')
    reviewed = set(record['reviewed_document_ids'])
    if not reviewed.issubset(docs):
        raise ValueError('Reviewed document missing from input bundle')
    ids = [c['id'] for c in json.loads((PROTOCOL / 'categories-v1.yaml').read_text())['categories']]
    if sorted(c['category'] for c in record['intent']) != sorted(ids):
        raise ValueError('Every category must appear exactly once')
    producer = record['producer']
    if datetime.fromisoformat(producer['created_at'].replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Producer timestamp requires a timezone')
    if producer['kind'] == 'human_reference' and (producer['model'] is not None or producer['provider'] is not None):
        raise ValueError('Human references must not claim model/provider generation')
    if producer['kind'] == 'model_extraction' and not all(producer[k] for k in ('model', 'provider', 'raw_response_path')):
        raise ValueError('Model extraction requires archived response and model/provider metadata')
    if producer['kind'] == 'mechanical_extraction' and any(c['label'] != 'cannot_determine' for c in record['intent']):
        raise ValueError('Mechanical extraction cannot assign semantic labels')
    for c in record['intent']:
        if c['label'] == 'not_stated' and (record['evidence_completeness'] != 'adequate' or record['evidence_gaps']):
            raise ValueError('not_stated requires adequate evidence without unresolved gaps')
    if record['evidence_completeness'] != 'adequate' and not record['evidence_gaps']:
        raise ValueError('Incomplete/uncertain evidence requires an explicit gap explanation')
    for item in list(record['fields'].values()) + record['intent']:
        for e in item['evidence']:
            d = docs.get(e['document_id'])
            if d is None or e['document_id'] not in reviewed:
                raise ValueError('Citation document was not supplied and reviewed')
            text = d.get('text')
            if not isinstance(text, str) or e['text_sha256'] != d['text_sha256']:
                raise ValueError('Citation text hash mismatch or unavailable text')
            if e['end'] <= e['start'] or e['end'] > len(text) or text[e['start']:e['end']] != e['quote']:
                raise ValueError('Citation is not the exact canonical-text substring')
    for name in ('event_date', 'filing_date', 'acceptance_datetime_et'):
        if record['fields'][name]['status'] == 'present' and len(record['fields'][name]['values']) != 1:
            raise ValueError('Multiple dates must be marked ambiguous')
    return {'status': 'valid_structure_and_citations', 'accession': record['accession'],
            'semantic_accuracy': 'requires_source_based_human_evaluation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    payload = args.evidence.read_bytes()
    print(json.dumps(validate(json.loads(args.record.read_text()), json.loads(payload), payload)))
