"""Hand-computed audit rollup pins; synthetic inputs, no model calls.

Inputs: invented reviewer verdicts and inventory rows. Outputs: assertions.
Identity: conclusive=(supported+contradicted)/n; counter intersections preserve
multiplicity, construction-key agreement differs from non-supported detection.
Tier:1 support. Run project Python -m pytest tests/test_extraction_audit_report.py.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts/extraction_protocol'))
from report_extraction_audit import (  # noqa: E402
    blind_control_summary,
    compare_inventories,
    control_summary,
    verdict_summary,
)
from verify_extraction_audit import review_counts  # noqa: E402


def test_verdict_denominator_and_abstentions():
    rows=[{'verdict':v} for v in ['supported','supported','contradicted','insufficient_evidence']]
    result=verdict_summary(rows)
    assert result['claims']==4
    assert result['verdicts']=={'supported':2,'contradicted':1,'insufficient_evidence':1}
    assert result['conclusive_fraction']==3/4
    with pytest.raises(ValueError):
        verdict_summary([])
    with pytest.raises(ValueError):
        verdict_summary([{'verdict':'unknown'}])


def test_independent_counts_retain_zero_verdict_categories():
    # Two observed supports, no observed contradictions, one abstention.
    assert review_counts([{'verdict':v} for v in ['supported','supported','insufficient_evidence']])=={
        'supported':2,'contradicted':0,'insufficient_evidence':1}
    with pytest.raises(AssertionError):
        review_counts([{'verdict':'unknown'}])


def test_key_agreement_and_problem_detection_are_distinct():
    key=[{'claim_id':'a','expected_verdict':'supported','condition':'unchanged'},
         {'claim_id':'b','expected_verdict':'contradicted','condition':'changed'},
         {'claim_id':'c','expected_verdict':'insufficient_evidence','condition':'changed'},
         {'claim_id':'d','expected_verdict':'supported','condition':'unchanged'}]
    rows=[{'claim_id':k,'verdict':v} for k,v in
          [('a','supported'),('b','insufficient_evidence'),('c','insufficient_evidence'),('d','contradicted')]]
    result=control_summary(key,rows)
    # a,c match the exact key; both b,c flag the changed claim; only a accepts clean text.
    assert result['exact_verdict_matches']==2 and result['fixture_claims']==4
    assert result['changed_claims_flagged']==2 and result['changed_claims']==2
    assert result['unchanged_claims_supported']==1 and result['unchanged_claims']==2
    assert result['confusion_counts']['contradicted -> insufficient_evidence']==1
    with pytest.raises(ValueError):
        control_summary(key,rows+rows[:1])


def test_natural_differences_preserve_multiplicity_but_ignore_security_wording():
    base={'reporting_parties':[{'name':'A, L.P.'}],
          'ownership':[{'reporting_party':'A LP','percent_of_class':7,'security':'common','shares':'7'}],
          'funding':{'types':['personal_funds']},'intent':{'board':{'status':'not_stated'}},
          'transaction_facts':[]}
    other={**base,'reporting_parties':[{'name':'A L.P.'}],
           'ownership':[{'reporting_party':'A, L.P.','percent_of_class':7,'security':'voting common','shares':'9'}]*2,
           'intent':{'board':{'status':'present'}}}
    result=compare_inventories(base,other)
    assert result['reporter_names_only_in_blind']==[]
    assert result['ownership_person_percent_only_in_blind']==[{'key':['alp',7.0],'count':1}]
    assert result['ownership_person_percent_only_in_candidate']==[]
    assert result['ownership_rows_candidate']==1 and result['ownership_rows_blind']==2
    assert len(result['intent_differences'])==1 and result['funding_type_sets_equal']


def test_blind_controls_count_missing_and_extra_rows_separately():
    def owner(party,pct):
        return {'reporting_party':party,'percent_of_class':pct}
    key=[{'case_id':'one','reporters':['A','B'],'ownership':[owner('A',5),owner('B',8)],
          'objective':'board_representation','deleted_candidate_party':'B'}]
    record={'cases':[{'document_id':'one','reporters':[{'name':'A'},{'name':'B'}],
                      'ownership':[owner('A',5),owner('B',8),owner('C',9)],
                      'objectives':[{'category':'board_representation'}]}]}
    result=blind_control_summary(key,record)
    assert result['matched_ownership_rows']==2 and result['expected_ownership_rows']==2
    assert result['extra_ownership_rows']==1
    assert result['matched_reporters']==2 and result['objectives_found']==1
    assert result['deleted_candidate_rows_recovered']==1
    record['cases'][0]['ownership']=[owner('A',5)]
    result=blind_control_summary(key,record)
    assert result['matched_ownership_rows']==1 and result['deleted_candidate_rows_recovered']==0
    with pytest.raises(ValueError):
        blind_control_summary(key,{'cases':record['cases']*2})
