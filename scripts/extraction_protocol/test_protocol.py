"""Synthetic contracts for immutable categories, abstention and exact evidence.

Inputs: invented quoted sentence and completed mechanical record. Outputs:
assertions, never real human/model labels. Identity: offsets [0,n) recover n chars.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest -q scripts/extraction_protocol/test_protocol.py
"""
import copy
import json

import pytest
from build_v1 import PROTOCOL, build, save_new
from validate import digest, protocol_hashes, validate


def example():
    text = 'We intend to nominate two directors.'
    sha = digest(text.encode())
    accession = '0000000001-26-000001'
    bundle = {'accession': accession, 'source_sha256': 'a' * 64, 'source_form': 'SC 13D',
              'documents': [{'document_id': 'DOCUMENT-1', 'source_accession': accession, 'text': text, 'text_sha256': sha}]}
    raw = json.dumps(bundle).encode()
    evidence = {'document_id': 'DOCUMENT-1', 'text_sha256': sha, 'start': 0, 'end': len(text), 'quote': text}
    fields = {k: {'status': 'not_found_in_supplied_text', 'values': [], 'evidence': [], 'rationale': 'Synthetic input does not contain this field.'}
              for k in ['issuer_ciks','reporting_party_ciks','cusips','event_date','filing_date','acceptance_datetime_et','item4']}
    categories = json.loads((PROTOCOL / 'categories-v1.yaml').read_text())['categories']
    result = {'schema_version': 'extraction-v1', 'workflow_status': 'completed', 'accession': accession,
              'analysis_scope': 'initial_disclosure', 'input_manifest_sha256': digest(raw), 'raw_source_sha256': 'a' * 64,
              'protocol_hashes': protocol_hashes(), 'producer': {'kind': 'mechanical_extraction', 'identifier': 'synthetic-test',
              'model': None, 'provider': None, 'settings': {}, 'created_at': '2026-09-16T12:00:00Z', 'raw_response_path': None},
              'reviewed_document_ids': ['DOCUMENT-1'], 'evidence_completeness': 'uncertain', 'evidence_gaps': ['Invented excerpt only.'],
              'fields': fields, 'intent': [{'category': c['id'], 'label': 'cannot_determine', 'stance': 'unclear', 'rationale': 'Unassessed synthetic example.', 'evidence': []} for c in categories]}
    result['fields']['item4'] = {'status': 'present', 'values': [text], 'evidence': [evidence], 'rationale': 'Synthetic located text; not a semantic label.'}
    return result, bundle, raw


def test_generated_replay_and_immutability(tmp_path):
    before = {p.name: p.read_bytes() for p in PROTOCOL.glob('*v1*')}
    build()
    assert before == {p.name: p.read_bytes() for p in PROTOCOL.glob('*v1*')}
    p = tmp_path / 'fixed.md'
    save_new(p, 'one')
    with pytest.raises(ValueError, match='Immutable'):
        save_new(p, 'two')


def test_valid_and_quote_refusal():
    record, bundle, raw = example()
    assert validate(record, bundle, raw)['status'] == 'valid_structure_and_citations'
    broken = copy.deepcopy(record)
    broken['fields']['item4']['evidence'][0]['end'] -= 1
    with pytest.raises(ValueError, match='substring'):
        validate(broken, bundle, raw)


def test_duplicate_categories_and_human_blinding():
    record, bundle, raw = example()
    record['intent'][1]['category'] = record['intent'][0]['category']
    with pytest.raises(ValueError, match='exactly once'):
        validate(record, bundle, raw)
    record, bundle, raw = example()
    record['intent'][0]['label'] = 'not_stated'
    with pytest.raises(ValueError, match='Mechanical'):
        validate(record, bundle, raw)


def test_evidence_gaps_and_positive_citation():
    record, bundle, raw = example()
    record['producer']['kind'] = 'human_reference'
    record['intent'][0]['label'] = 'not_stated'
    with pytest.raises(ValueError, match='adequate'):
        validate(record, bundle, raw)
    record['intent'][0].update(label='present', stance='explicit_request_or_stated_plan')
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):
        validate(record, bundle, raw)


def test_protocol_and_source_hash_refusal():
    record, bundle, raw = example()
    record['protocol_hashes']['prompt'] = 'b' * 64
    with pytest.raises(ValueError, match='Protocol'):
        validate(record, bundle, raw)


def test_amendment_and_external_evidence_refusal():
    record, bundle, raw = example()
    bundle['source_form'] = 'SC 13D/A'
    raw = json.dumps(bundle).encode()
    record['input_manifest_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='scope'):
        validate(record, bundle, raw)
    record['analysis_scope'] = 'amendment_diagnostic'
    bundle['documents'][0]['source_accession'] = '0000000002-26-000002'
    raw = json.dumps(bundle).encode()
    record['input_manifest_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='same source accession'):
        validate(record, bundle, raw)
    record, bundle, raw = example()
    bundle['documents'][0]['text'] += ' altered'
    raw = json.dumps(bundle).encode()
    record['input_manifest_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='Canonical text'):
        validate(record, bundle, raw)
