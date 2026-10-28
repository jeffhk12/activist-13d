"""Synthetic v3 evidence-contract and hand-computed rollup pins.

Inputs: invented source/records and construction keys. Outputs: assertions.
Identity: exact Unicode anchors; 2/3 key matches; two-reader state frequencies;
optional aggregate rows are not required recovery. Tier:1 support.
Run: project Python -m pytest tests/test_extraction_v3_io_metrics.py.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts/extraction_protocol'))
import extraction_v3_io as io  # noqa:E402
from build_extraction_v3 import extraction_schema  # noqa:E402
from extraction_v3_metrics import case_comparison, control_critic, control_inventory  # noqa:E402
from prepare_extraction_v3 import require_complete_review  # noqa:E402


@pytest.fixture()
def record(tmp_path,monkeypatch):
    (tmp_path/'inputs').mkdir()
    (tmp_path/'inputs/schema.json').write_text(json.dumps(extraction_schema()))
    monkeypatch.setattr(io,'RUN',tmp_path)
    row={'accession':'test','extraction_status':'complete_readable_bundle','reviewed_document_ids':['one'],
         'evidence_gaps':[],'issuer':{'status':'not_stated','name':None,'evidence':[]},'reporting_parties':[],
         'ownership':[],'transaction_facts':[],
         'funding':{'status':'not_stated','summary':'None disclosed.','components':[],'evidence':[]},
         'intent':{k:{'status':'not_stated','evidence_status':'sufficient_supplied_evidence','qualification_basis':'none',
                      'actor':None,'target':None,'rationale':'No proposal in complete invented source.','evidence':[]}
                   for k in extraction_schema()['properties']['intent']['properties']}}
    bundle={'accession':'test','documents':[{'document_id':'one','text':'α cash','text_sha256':io.sha('α cash'.encode())}]}
    return row,bundle,{'all_readable_text_delivered':True}


def test_exact_unicode_and_funding_attribution_contract(record):
    row,bundle,coverage=record
    item={'actor':'A','type':'borrowed_funds','certainty':'possible','acquisition_link':'current_acquisition',
          'description':'Conditional source in an invented example.','evidence':[{'document_id':'one','quote':'α'}]}
    row['funding']={'status':'present','components':[item],'summary':'May borrow.','evidence':[{'document_id':'one','quote':'cash'}]}
    actual=io.normalize(row,{'role':'extractor'},bundle,None,coverage)
    assert actual['funding']['components'][0]['evidence'][0]['end']==1
    claims=io.claims_for(actual)
    funding=next(c for c in claims if c['kind']=='funding_component')
    assert funding['value']['certainty']=='possible' and funding['value']['acquisition_link']=='current_acquisition'
    assert 'rationale' not in next(c for c in claims if c['kind']=='intent')['value']
    item['certainty']='confirmed_actual'
    item['acquisition_link']='historical_affiliate'
    with pytest.raises(ValidationError):
        io.normalize(row,{'role':'extractor'},bundle,None,coverage)


def test_missing_evidence_cannot_become_negative_or_positive_control_bid(record):
    row,bundle,coverage=record
    row['extraction_status']='incomplete_source_review'
    with pytest.raises(ValueError,match='Absence needs'):
        io.normalize(row,{'role':'extractor'},bundle,None,coverage)
    row['extraction_status']='complete_readable_bundle'
    row['intent']['board_representation'].update(status='present',actor='A',target='Co',
        qualification_basis='primary_control_bid',evidence=[{'document_id':'one','quote':'α'}])
    with pytest.raises(ValidationError):
        io.normalize(row,{'role':'extractor'},bundle,None,coverage)


def test_control_wrapper_resolves_full_extraction_evidence_and_own_scope(record):
    row,bundle,coverage=record
    row['accession']='one'
    row['issuer']={'status':'present','name':'Invented','evidence':[{'document_id':'one','quote':'α'}]}
    wrapper={'review_status':'complete_readable_bundle','reviewed_document_ids':['one'],
             'evidence_gaps':[],'cases':[row]}
    actual=io.normalize(wrapper,{'role':'control_blind'},bundle,None,coverage)
    assert actual['cases'][0]['issuer']['evidence'][0]['end']==1


def test_fresh_text_refused_before_release(record):
    _,bundle,_=record
    job={'job_id':'extractor_n01','role':'extractor','phase':'fresh','bundle':'inputs/bundle.json','case_id':'N01'}
    paths={'jobs.json':[job],'inputs/bundle.json':bundle,'inputs/protocol.json':{},
           'inputs/categories.json':{},'inputs/common-rules.md':'common','inputs/role-extractor.txt':'task'}
    for name,value in paths.items():
        path=io.RUN/name
        path.write_bytes(value.encode() if isinstance(value,str) else io.enc(value))
    all_paths=list(paths)+['inputs/schema.json']
    (io.RUN/'preparation.json').write_bytes(io.enc({'input_sha256':{p:io.sha((io.RUN/p).read_bytes()) for p in all_paths}}))
    with pytest.raises(ValueError,match='stay closed'):
        io.load_job('extractor_n01')


def test_critic_controls_separate_key_agreement_from_flagging():
    key=[{'claim_id':'a','condition':'unchanged','expected_verdict':'supported'},
         {'claim_id':'b','condition':'changed','expected_verdict':'contradicted'},
         {'claim_id':'c','condition':'changed','expected_verdict':'insufficient_evidence'}]
    rows={'reviews':[{'claim_id':k,'verdict':v} for k,v in [('a','supported'),('b','insufficient_evidence'),('c','insufficient_evidence')]]}
    r=control_critic(key,rows)
    assert r['claims']==3 and r['matched']==2 and r['changed_flagged']==2 and not r['passed']
    with pytest.raises(ValueError):
        control_critic(key,{'reviews':rows['reviews']*2})


def test_optional_aggregate_not_in_recovery_denominator(record):
    row,_,_=record
    row['accession']='S'
    row['ownership']=[{'reporting_party':'Fund','percent_of_class':5,'ownership_role':'direct_or_beneficial','overlap':'overlapping'}]
    key=[{'case_id':'S','expected_intent':{'board_representation':'not_stated'},'funding_requirements':[],
          'ownership_requirements':[dict(row['ownership'][0])],
          'optional_ownership_requirements':[{'reporting_party':'Group','percent_of_class':5,'ownership_role':'group_aggregate','overlap':'overlapping'}],
          'forbidden_funding':[],'timing_forbidden':[]}]
    r=control_inventory(key,{'cases':[row]})
    assert r['ownership_required']==r['ownership_matches']==1 and r['passed']
    row['ownership'].append({'reporting_party':'Group','percent_of_class':10,'ownership_role':'direct_or_beneficial','overlap':'explicitly_distinct'})
    r=control_inventory(key,{'cases':[row]})
    assert r['optional_ownership_violations']==1 and not r['passed']


def test_complete_control_rejects_invented_combined_total(record):
    row,_,_=record
    row['accession']='S'
    owner={'reporting_party':'Fund','percent_of_class':5,'ownership_role':'direct_or_beneficial','overlap':'overlapping'}
    row['ownership']=[owner]
    key=[{'case_id':'S','expected_intent':{},'funding_requirements':[],
          'ownership_requirements':[owner],'optional_ownership_requirements':[],
          'ownership_exhaustive':True,'forbidden_funding':[],'timing_forbidden':[]}]
    assert control_inventory(key,{'cases':[row]})['passed']
    row['ownership'].append({**owner,'reporting_party':'Fund and controller combined','percent_of_class':10})
    actual=control_inventory(key,{'cases':[row]})
    assert actual['ownership_extra_or_duplicate']==1 and not actual['passed']


def test_delivery_does_not_replace_complete_review_attestation(record):
    row,bundle,_=record
    require_complete_review(row,bundle)
    row['extraction_status']='incomplete_source_review'
    with pytest.raises(ValueError,match='complete review attestation'):
        require_complete_review(row,bundle)
    row['extraction_status']='complete_readable_bundle'
    row['reviewed_document_ids']=[]
    with pytest.raises(ValueError,match='every readable'):
        require_complete_review(row,bundle)


def test_two_reader_frequencies_and_quarantine_do_not_turn_unknown_into_zero(record):
    a,_,_=record
    a['intent']={k:a['intent'][k] for k in ['board_representation','capital_return']}
    b=copy.deepcopy(a)
    b['intent']['board_representation']['status']='cannot_determine'
    critic={'reviews':[{'claim_id':'intent.'+k,'verdict':'supported'} for k in a['intent']]}
    r=case_comparison(a,b,critic)
    assert r['intent_agreement']==1 and r['eligible_experimental_intents']==1
    board=r['intent'][0]
    assert board['state_frequency']=={'present':0,'not_stated':0.5,'cannot_determine':0.5}
    assert not board['eligible_experimental_label']
