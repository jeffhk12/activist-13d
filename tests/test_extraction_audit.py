"""Synthetic reviewer-harness guards and constructed-control accounting.

Inputs: invented records/source text plus frozen schema, no model or network.
Outputs: assertions. Identity: exact-one review per claim, complete Unicode-range
coverage and quote equality. Tier:1 support. Run project Python -m pytest here.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'scripts/extraction_protocol'))
from audit_io import check_claim_ids, normalize, sha  # noqa: E402

SPEC=importlib.util.spec_from_file_location('prepare_audit',ROOT/'scripts/extraction_protocol/prepare_extraction_audit.py')
prep=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


def test_candidates_hide_authorship_and_rationales_but_preserve_qualifications():
    record={'issuer':{'status':'present','name':'Co','evidence':[]},'reporting_parties':[],
            'ownership':[],'funding':{'types':['borrowed_funds'],'status':'present',
                                      'summary':'May include loans; actual use unknown.','evidence':[]},
            'intent':{'board_representation':{'status':'present','actor':'A','target':'Co',
                      'rationale':'Do not show this argument','evidence':[],'evidence_status':'sufficient_supplied_evidence'}},
            'transaction_facts':[],'run_metadata':{'agent':'A','model':'hidden'}}
    claims=prep.claims_for(record)
    serialized=json.dumps(claims)
    assert 'Do not show this argument' not in serialized and 'run_metadata' not in serialized
    assert claims[1]['value']['candidate_qualification_context']=='May include loans; actual use unknown.'
    assert len(claims)==4


def test_control_counts_and_replay_are_hand_pinned():
    first=prep.control_claims()
    assert first==prep.control_claims()
    bundle,claims,truth=first
    assert len(claims)==len(bundle['documents'])==len(truth)==16
    assert sum(r['expected_verdict']=='supported' for r in truth)==8
    assert sum(r['expected_verdict']=='contradicted' for r in truth)==6
    assert sum(r['expected_verdict']=='insufficient_evidence' for r in truth)==2
    assert 'expected_verdict' not in json.dumps(claims)


def test_source_controls_have_two_people_and_one_objective_each():
    bundle,truth=prep.control_blind()
    assert len(bundle['documents'])==len(truth)==8
    assert sum(len(r['ownership']) for r in truth)==16
    assert len({r['objective'] for r in truth})==8
    assert all(len(r['candidate_with_deleted_row'])==1 for r in truth)


def test_claim_review_must_be_complete_and_unique():
    claims=[{'claim_id':'a'},{'claim_id':'b'}]
    check_claim_ids([{'claim_id':'b'},{'claim_id':'a'}],claims)
    for values in [[{'claim_id':'a'}],[{'claim_id':'a'},{'claim_id':'a'}]]:
        with pytest.raises(ValueError,match='exactly once'):
            check_claim_ids(values,claims)


@pytest.fixture()
def harness(tmp_path,monkeypatch):
    import audit_io
    (tmp_path/'inputs').mkdir()
    schema=ROOT/'research/protocol/extraction-stability-schema-v2.json'
    (tmp_path/'inputs/blind-schema.json').write_bytes(schema.read_bytes())
    monkeypatch.setattr(audit_io,'RUN',tmp_path)
    text='α source'
    bundle={'documents':[{'document_id':'one','text':text,'text_sha256':sha(text.encode())}]}
    job={'role':'critic'}
    candidate={'claims':[{'claim_id':'a','kind':'ownership','value':{}}]}
    record={'review_status':'complete_readable_bundle','reviewed_document_ids':['one'],
            'evidence_gaps':[],'reviews':[{'claim_id':'a','verdict':'supported','rationale':'Source supports claim.',
                                        'issue_codes':[],'evidence':[{'document_id':'one','quote':'α'}]}]}
    return record,job,bundle,candidate


def test_full_review_refused_for_delivery_gap(harness):
    record,job,bundle,candidate=harness
    with pytest.raises(ValueError,match='full delivered'):
        normalize(record,job,bundle,candidate,{'all_readable_text_delivered':False})


def test_conclusive_verdict_requires_source_and_unicode_anchor(harness):
    record,job,bundle,candidate=harness
    actual=normalize(record,job,bundle,candidate,{'all_readable_text_delivered':True})
    assert actual['reviews'][0]['evidence'][0]['start']==0
    assert actual['reviews'][0]['evidence'][0]['end']==1
    wrong=copy.deepcopy(record)
    wrong['reviews'][0]['evidence']=[]
    with pytest.raises(ValueError,match='Conclusive'):
        normalize(wrong,job,bundle,candidate,{'all_readable_text_delivered':True})
    wrong['reviews'][0]['verdict']='insufficient_evidence'
    assert normalize(wrong,job,bundle,candidate,{'all_readable_text_delivered':True})


def test_frozen_protocol_declares_limits_and_selection():
    p=json.loads(prep.PROTOCOL.read_text())
    assert 'saved replicate A' in p['candidate_selection']
    assert 'same inherited configured model' in p['context']
    assert 'not_estimated' in p['metrics']
    assert '22 fresh jobs' in p['jobs']


def test_control_inventory_schema_resolves_ownership_evidence(harness):
    _,_,bundle,_=harness
    record={'review_status':'complete_readable_bundle','reviewed_document_ids':['one'],
            'evidence_gaps':[],'cases':[{'document_id':'one','reporters':[],
            'ownership':[{'reporting_party':'A','percent_of_class':5,'shares':'5','security':'common',
                           'evidence':[{'document_id':'one','quote':'α'}]}],'objectives':[]}]}
    result=normalize(record,{'role':'control_blind'},bundle,None,{'all_readable_text_delivered':True})
    assert result['cases'][0]['ownership'][0]['evidence'][0]['end']==1
