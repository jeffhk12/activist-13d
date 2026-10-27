"""Tier 1 hand-computed delivery coverage and uncertainty-guard pins."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/extraction_protocol'))
spec=importlib.util.spec_from_file_location('stability_v2',ROOT/'scripts/extraction_protocol/stability_v2_io.py')
v2=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


def test_delivery_intervals_count_union_not_overlaps_or_repeats():
    # [0,5) plus [3,8) covers exactly eight of ten characters.
    result=v2.interval_coverage([(0,5),(3,8),(0,5)],10)
    assert result['served_unique_characters']==8
    assert result['missing_ranges']==[[8,10]] and not result['complete']
    assert v2.interval_coverage([(8,10),(3,8),(0,5)],10)['complete']


def test_gaps_and_invalid_ranges_cannot_claim_full_delivery():
    result=v2.interval_coverage([(0,2),(3,4)],4)
    assert result['missing_ranges']==[[2,3]]
    with pytest.raises(ValueError):
        v2.interval_coverage([(0,5)],4)


def test_frozen_schema_requires_category_evidence_and_keeps_transaction_facts():
    schema=json.loads((v2.RUN/'inputs/extraction-stability-schema-v2.json').read_text())
    assert 'evidence_status' in schema['$defs']['intent']['required']
    assert 'transaction_facts' in schema['required']
    assert set(schema['properties']['intent']['required'])==set(schema['properties']['intent']['properties'])
    protocol=json.loads((v2.RUN/'inputs/extraction-stability-v2.json').read_text())
    assert protocol['replicates_per_filing']==3
    assert 'No context processes a second filing' in protocol['context_design']


def toy_record():
    categories=json.loads((v2.RUN/'inputs/categories-stability-v2.json').read_text())['categories']
    return {'accession':'toy','extraction_status':'complete_readable_bundle','reviewed_document_ids':['D'],
      'evidence_gaps':[],'issuer':{'status':'cannot_determine','name':None,'evidence':[]},
      'reporting_parties':[],'ownership':[],'funding':{'status':'not_stated','types':[],'summary':'not supplied','evidence':[]},
      'transaction_facts':[],
      'intent':{c['id']:{'status':'not_stated','evidence_status':'sufficient_supplied_evidence',
         'rationale':'invented complete source has no objective','actor':None,'target':None,'evidence':[]} for c in categories}}


def test_complete_claim_refused_without_full_mechanical_delivery():
    bundle={'accession':'toy','documents':[{'document_id':'D','text':'A😀BC','text_sha256':'hash'}]}
    with pytest.raises(ValueError,match='Complete claim'):
        v2.normalize_v2(toy_record(),bundle,{'all_readable_text_delivered':False})
    assert v2.normalize_v2(toy_record(),bundle,{'all_readable_text_delivered':True})['review_delivery']['all_readable_text_delivered']


def test_material_gap_cannot_be_silently_labeled_not_stated():
    bundle={'accession':'toy','documents':[{'document_id':'D','text':'source','text_sha256':'hash'}]}
    record=toy_record()
    record['intent']['capital_return']['evidence_status']='material_reference_missing'
    with pytest.raises(ValueError,match='Not_stated cannot mask'):
        v2.normalize_v2(record,bundle,{'all_readable_text_delivered':True})
    record['intent']['capital_return']['status']='cannot_determine'
    assert v2.normalize_v2(record,bundle,{'all_readable_text_delivered':True})['intent']['capital_return']['status']=='cannot_determine'
