"""Pins for exact source evidence and stability metrics, using invented values."""
import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stability_io',ROOT/'scripts/extraction_protocol/stability_io.py')
io=importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
compare_spec=importlib.util.spec_from_file_location('compare_stability',ROOT/'scripts/extraction_protocol/compare_stability.py')
comparison=importlib.util.module_from_spec(compare_spec)
compare_spec.loader.exec_module(comparison)


def test_evidence_uses_unicode_positions_and_preserves_text():
    docs={'D':{'document_id':'D','text':'A😀BC','text_sha256':'hash'}}
    e=io.anchor({'document_id':'D','quote':'😀'},docs)
    assert (e['start'],e['end'])==(1,2)
    assert e['text_sha256']=='hash' and e['quote']=='😀'


def test_repeated_quotes_require_explicit_occurrence():
    docs={'D':{'document_id':'D','text':'same and same','text_sha256':'hash'}}
    with pytest.raises(ValueError,match='2 matches'):
        io.anchor({'document_id':'D','quote':'same'},docs)
    assert io.anchor({'document_id':'D','quote':'same','start':9},docs)['end']==13


def test_wrong_source_or_invented_quote_refused():
    docs={'D':{'document_id':'D','text':'source fact','text_sha256':'hash'}}
    with pytest.raises(ValueError,match='0 matches'):
        io.anchor({'document_id':'D','quote':'invented'},docs)
    with pytest.raises(ValueError,match='absent'):
        io.anchor({'document_id':'missing','quote':'source'},docs)
    with pytest.raises(ValueError,match='hash differs'):
        io.anchor({'document_id':'D','quote':'source','text_sha256':'wrong'},docs)


def test_agreement_and_positive_jaccard_pinned_to_invented_labels():
    assert comparison.jaccard({'board','sale'},{'board','capital'})==1/3
    assert comparison.jaccard(set(),set()) is None
    records={}
    labels={'A':['present','not_stated'],'B':['present','cannot_determine'],'C':['not_stated','cannot_determine']}
    for agent,states in labels.items():
        records[(agent,'toy')]={'extraction_status':'complete_readable_bundle',
          'issuer':{'name':'Toy'},'reporting_parties':[],'ownership':[],
          'funding':{'status':'not_stated','types':[]},
          'intent':{c:{'status':s} for c,s in zip(['x','y'],states,strict=True)}}
    metrics,*_=comparison.summarize(records,['toy'],['x','y'])
    # No three-way match. AB match x; BC match y: two of six pairs.
    assert metrics['equal_threeway_intent_cells']==0
    assert metrics['equal_pairwise_intent_comparisons']==2
    assert metrics['pooled_pairwise_agreement']==1/3
    records[('C','toy')]['extraction_status']='incomplete_source_review'
    metrics,*_=comparison.summarize(records,['toy'],['x','y'])
    assert metrics['jointly_complete_review_cells']==0
    assert metrics['pairwise_complete_review_comparisons']==2
