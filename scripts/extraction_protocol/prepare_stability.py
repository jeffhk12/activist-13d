"""Freeze ten discovery inputs and a common schema for three agent extractions.

Inputs: fixed discovery sample/bundles and new stability protocol/prompt.
Outputs: immutable run inputs, schema, provenance and agent output directories.
Identity: exactly the ten existing discovery accessions; no reserved text read.
Tier: 1. Run with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 project Python.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'research/runs/extraction-stability/20261025-v1'
PACK = ROOT/'review/drafts/ranking-llm-pilot-20261025'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, f'Frozen input differs: {path}'
    else:
        path.write_bytes(raw)


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()


def schema():
    state = {'enum':['present','not_stated','cannot_determine']}
    evidence = {'type':'array','items':{'type':'object','required':['document_id','quote'],
      'properties':{'document_id':{'type':'string'},'quote':{'type':'string','minLength':1},
                    'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},
                    'text_sha256':{'type':'string'}},'additionalProperties':False}}
    categories=json.loads((ROOT/'research/protocol/categories-v1.yaml').read_text())['categories']
    intent_field={'type':'object','required':['status','rationale','actor','target','evidence'],
      'properties':{'status':state,'rationale':{'type':'string','minLength':1},
                    'actor':{'type':['string','null']},'target':{'type':['string','null']},'evidence':evidence},
      'additionalProperties':False}
    properties={
      'accession':{'type':'string'},
      'extraction_status':{'enum':['complete_readable_bundle','incomplete_source_review']},
      'reviewed_document_ids':{'type':'array','items':{'type':'string'},'uniqueItems':True},
      'evidence_gaps':{'type':'array','items':{'type':'string'}},
      'issuer':{'type':'object','required':['status','name','evidence'],
                'properties':{'status':state,'name':{'type':['string','null']},'evidence':evidence},'additionalProperties':False},
      'reporting_parties':{'type':'array','items':{'type':'object','required':['name','evidence'],
                'properties':{'name':{'type':'string','minLength':1},'evidence':evidence},'additionalProperties':False}},
      'ownership':{'type':'array','items':{'type':'object','required':['reporting_party','percent_of_class','shares','security','evidence'],
                'properties':{'reporting_party':{'type':'string'},'percent_of_class':{'type':['number','null']},
                              'shares':{'type':['string','null']},'security':{'type':['string','null']},'evidence':evidence},'additionalProperties':False}},
      'funding':{'type':'object','required':['status','types','summary','evidence'],
                'properties':{'status':state,'types':{'type':'array','uniqueItems':True,'items':{'enum':['working_capital','personal_funds','borrowed_funds','contributions','other','unclear']}},
                              'summary':{'type':'string'},'evidence':evidence},'additionalProperties':False},
      'intent':{'type':'object','required':[c['id'] for c in categories],
                'properties':{c['id']:intent_field for c in categories},'additionalProperties':False},
      'run_metadata':{'type':'object'}
    }
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',
            'title':'Extraction stability v1 record, not a human reference',
            'type':'object','required':[k for k in properties if k!='run_metadata'],
            'properties':properties,'additionalProperties':False}


def main():
    schema_bytes=enc(schema())
    freeze(ROOT/'research/protocol/extraction-stability-schema-v1.json',schema_bytes)
    paths=['extraction-stability-v1.json','extraction-stability-schema-v1.json',
           'extraction-stability-prompt-v1.md','categories-v1.yaml']
    inputs={}
    for name in paths:
        raw=(ROOT/'research/protocol'/name).read_bytes()
        freeze(RUN/'inputs'/name,raw)
        inputs['research/protocol/'+name]=sha(raw)
    selection_path=ROOT/'research/runs/ranking-llm-pilot/20261025-v2/sample-manifest.json'
    selection_raw=selection_path.read_bytes()
    selection=json.loads(selection_raw)['selection']['discovery']
    assert len(selection)==len({r['accession'] for r in selection})==10
    inventory=[]
    for row in selection:
        a=row['accession']
        source=PACK/'discovery/evidence'/f'{a}.json'
        raw=source.read_bytes()
        bundle=json.loads(raw)
        assert bundle['accession']==a and bundle['source_sha256']==row['source_sha256']
        docs=[]
        for d in bundle['documents']:
            text=d.get('text')
            if text is not None:
                assert sha(text.encode())==d['text_sha256']
            docs.append({'document_id':d['document_id'],'type':d.get('type'),'filename':d.get('filename'),
                         'characters':len(text) if isinstance(text,str) else None,'text_sha256':d.get('text_sha256')})
        freeze(RUN/'inputs/bundles'/f'{a}.json',raw)
        inventory.append({'case_id':row['case_id'],'accession':a,'input_sha256':sha(raw),
                          'source_sha256':bundle['source_sha256'],'documents':docs})
        inputs[str(source.relative_to(ROOT))]=sha(raw)
    freeze(RUN/'inputs/inventory.json',enc(inventory))
    freeze(RUN/'prefit-manifest.json',enc({'protocol':'extraction-stability-v1',
        'user_override_human_first_for_ten_discovery':True,'human_reference_count':0,
        'reserved_validation_text_accessed':False,'human_pack_modified':False,
        'sample_manifest_sha256':sha(selection_raw),'source_hashes':inputs,
        'expected_agents':['A','B','C'],'expected_records':30,
        'model_id_and_generation_settings':'not exposed by built-in spawn interface; record null unless actually provided'}))
    for agent in ['A','B','C']:
        for name in ['drafts','draft-history','records']:
            (RUN/'agents'/agent/name).mkdir(parents=True,exist_ok=True)
    print(json.dumps({'run':str(RUN),'cases':len(inventory),
      'readable_characters_per_agent':sum(d['characters'] or 0 for r in inventory for d in r['documents']),
      'cases_inventory':[{ 'case_id':r['case_id'],'accession':r['accession'],
                           'characters':sum(d['characters'] or 0 for d in r['documents'])} for r in inventory]},indent=2))


if __name__=='__main__':
    main()
