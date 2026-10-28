"""Hand-pinned transfer accounting, state counts and citation refusal checks.

Inputs: invented examples plus optional frozen local pilot/extraction artifacts.
Outputs: assertions. Identity: requests=n_events*9; three categorical counts sum
to3; supported evidence equals canonical slice. Tier: 1 support, no network calls.
Run: project Python -m pytest tests/test_remediation_handoff_and_batch_review.py.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


handoff=module('bbg_remediation','scripts/ml_experiment/build_bloomberg_remediation_handoff.py')
review=module('discovery_review','scripts/extraction_protocol/review_discovery_batch.py')


def test_two_events_have_eighteen_keyed_unrequested_cells():
    events=[{'row_id':name,'case_id':name,'as_of_date':'2020-01-02'} for name in ['a','b']]
    rows=handoff.request_rows(events)
    assert len(rows)==18 and len({r['request_id'] for r in rows})==18
    assert all(r['status']=='not_requested' for r in rows)
    assert {r['as_of_date'] for r in rows}=={'2020-01-02'}
    with pytest.raises(ValueError,match='Duplicate'):
        handoff.request_rows(events+[events[0]])


def test_state_distribution_preserves_uncertainty_and_not_stated():
    assert review.state_counts(['present','not_stated','cannot_determine'])=={
        'present':1,'not_stated':1,'cannot_determine':1}
    assert review.state_counts(['not_stated']*3)=={'present':0,'not_stated':3,'cannot_determine':0}
    for values in [['present'],['present','present','unknown']]:
        with pytest.raises(ValueError):
            review.state_counts(values)


def test_funding_sets_ignore_order_but_not_different_claims():
    assert review.same_type_sets([['other','working_capital'],['working_capital','other'],['other','working_capital']])
    assert not review.same_type_sets([['working_capital'],['working_capital','borrowed_funds'],['working_capital']])


def test_wrong_source_quote_refused():
    bundle={'documents':[{'document_id':'one','text':'abc'}]}
    record={'funding':{'evidence':[{'document_id':'one','quote':'wrong','start':0,'end':3,'text_sha256':'irrelevant'}]}}
    with pytest.raises(ValueError,match='Citation'):
        review.validate_quotes(record,bundle)


def test_optional_portable_handoff_replay():
    if not (handoff.AUDIT/'selected-workbook-rows.json').exists():
        pytest.skip('Frozen local Bloomberg pilot absent in CI')
    first,summary=handoff.build()
    second,replay=handoff.build()
    assert first==second and summary==replay
    assert summary['requests']==90 and summary['actual_results_populated']==0
    assert b'{{' not in first[handoff.HANDOFF]
    assert b'prior-session date' in first['pilot_events.csv']


def test_optional_first_batch_replay():
    if not (review.SOURCE/'inputs/inventory.json').exists():
        pytest.skip('Frozen local model records absent in CI')
    first,summary=review.build()
    second,replay=review.build()
    assert first==second and summary==replay
    assert summary['funding_type_disagreement_cases']==['D02','D05','D06']
    assert summary['ownership_row_count_difference_cases']==['D02']
    assert summary['unanimous_intent_cells']==89 and summary['intent_cells']==90
    assert summary['new_extraction_calls']==0 and not summary['reserved_filings_supplied']
