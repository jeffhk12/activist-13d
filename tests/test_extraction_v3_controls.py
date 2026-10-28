"""Hand-pinned control accounting and separation guards for extraction v3.

Inputs: invented fixtures only. Outputs: assertions. Identity: 16 critic controls
have 8/6/2 expected verdicts; 8 inventory fixtures have 72 objective states with
9 positive, 1 unknown and 62 not-stated. Tier:1 support. Run project Python -m
pytest tests/test_extraction_v3_controls.py. No network or model calls.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/extraction_protocol'))
from extraction_v3_controls import (  # noqa: E402
    CATEGORIES,
    claim_controls,
    inventory_controls,
)


def test_critic_counts_and_separate_hidden_keys():
    bundle, candidate, key = claim_controls()
    assert len(bundle['documents']) == len(candidate['claims']) == len(key) == 16
    assert Counter(row['expected_verdict'] for row in key) == {
        'supported': 8, 'contradicted': 6, 'insufficient_evidence': 2,
    }
    assert Counter(row['condition'] for row in key) == {'unchanged': 8, 'changed': 8}
    exposed = json.dumps({'bundle': bundle, 'candidate': candidate})
    assert 'expected_verdict' not in exposed and 'error_type' not in exposed
    docs = {doc['document_id']: doc for doc in bundle['documents']}
    assert len(docs) == 16
    assert {row['claim_id'] for row in key} == {row['claim_id'] for row in candidate['claims']}
    assert all(row['source_document_id'] in docs for row in candidate['claims'])


def test_replay_and_exact_text_hashes_are_stable():
    assert claim_controls() == claim_controls()
    assert inventory_controls() == inventory_controls()
    critic_bundle, _, _ = claim_controls()
    inventory_bundle, _ = inventory_controls()
    for doc in critic_bundle['documents'] + inventory_bundle['documents']:
        assert 200 <= len(doc['text']) <= 900
        assert doc['text_sha256'] == hashlib.sha256(doc['text'].encode()).hexdigest()
        assert doc['type'] == 'SYNTHETIC'


def test_inventory_has_all_nine_positive_categories_and_explicit_unknown():
    bundle, key = inventory_controls()
    assert len(bundle['documents']) == len(key) == 8
    assert {r['case_id'] for r in key} == {d['document_id'] for d in bundle['documents']}
    assert all(set(row['expected_intent']) == set(CATEGORIES) for row in key)
    # 8 complete fixtures x 9 categories = 72 states: 9 + 1 + 62.
    states = Counter(v for row in key for v in row['expected_intent'].values())
    assert states == {'present': 9, 'cannot_determine': 1, 'not_stated': 62}
    positive_categories = {k for row in key for k, v in row['expected_intent'].items() if v == 'present'}
    assert positive_categories == set(CATEGORIES)
    rows = {row['case_id']: row for row in key}
    assert [k for k, v in rows['S01']['expected_intent'].items() if v == 'present'] == ['sale_of_company']
    assert rows['S08']['expected_intent']['governance_change'] == 'cannot_determine'


def test_funding_requirements_separate_current_possible_and_indirect():
    _, key = inventory_controls()
    rows = {row['case_id']: row for row in key}
    assert rows['S03']['funding_requirements'] == [
        {'type': 'personal_funds', 'certainty': 'confirmed_actual', 'acquisition_link': 'current_acquisition'},
        {'type': 'borrowed_funds', 'certainty': 'possible', 'acquisition_link': 'future_possible'},
    ]
    assert rows['S06']['funding_requirements'] == [
        {'type': 'noncash_distribution', 'certainty': 'confirmed_actual', 'acquisition_link': 'current_acquisition'},
        {'type': 'borrowed_funds', 'certainty': 'historical_indirect', 'acquisition_link': 'historical_affiliate'},
    ]
    assert rows['S03']['forbidden_funding'] == rows['S06']['forbidden_funding'] == [
        {'type': 'borrowed_funds', 'certainty': 'confirmed_actual', 'acquisition_link': 'current_acquisition'},
    ]
    assert rows['S07']['timing_forbidden'] == ['pending_explicit', 'completed']


def test_overlapping_rows_preserve_roles_without_new_distinct_holdings():
    _, key = inventory_controls()
    case = next(r for r in key if r['case_id'] == 'S02')
    overlap = case['ownership_requirements']
    optional = case['optional_ownership_requirements']
    assert len(overlap) == 2
    assert {r['ownership_role'] for r in overlap} == {'direct_or_beneficial', 'deemed'}
    assert 'group_aggregate' not in {r['ownership_role'] for r in overlap}
    assert {r['percent_of_class'] for r in overlap} == {5}
    assert {r['overlap'] for r in overlap} == {'overlapping'}
    assert optional == [{'reporting_party': 'Aster reporting group', 'percent_of_class': 5,
                         'ownership_role': 'group_aggregate', 'overlap': 'overlapping'}]
    assert sum(len(r['optional_ownership_requirements']) for r in key) == 1
    assert case['ownership_exhaustive'] is True
    assert case['permitted_ownership_tuples'] == overlap + optional
    assert len(case['permitted_ownership_tuples']) == 3
    invented = {'reporting_party': 'Aster and Alice combined', 'percent_of_class': 10,
                'ownership_role': 'direct_or_beneficial', 'overlap': 'explicitly_distinct'}
    assert invented not in case['permitted_ownership_tuples']
    assert sum(row['ownership_exhaustive'] for row in key) == 1
    assert all(row['permitted_ownership_tuples'] == [] for row in key if row['case_id'] != 'S02')
