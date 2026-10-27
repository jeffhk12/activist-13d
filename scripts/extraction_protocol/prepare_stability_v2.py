"""Freeze revised extraction inputs and one-filing-per-context job inventory.

Inputs: same ten v1 discovery bundles, v2 rules/prompt and prior schema.
Outputs: new immutable v2 schema/categories/source bytes and 30 empty job areas.
Identity: v2 canonical input hashes equal v1; 10 cases x 3 replicates=30 jobs.
Tier: 1. Run project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8.
"""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'research/runs/extraction-stability/20261025-v1'
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:
            raise ValueError(f'Frozen input differs: {path}')
    else:
        path.write_bytes(raw)


def make_schema():
    s=json.loads((ROOT/'research/protocol/extraction-stability-schema-v1.json').read_text())
    evidence=s['properties']['issuer']['properties']['evidence']
    intent=copy.deepcopy(next(iter(s['properties']['intent']['properties'].values())))
    intent['properties']['evidence']={'$ref':'#/$defs/evidence'}
    intent['required'].append('evidence_status')
    intent['properties']['evidence_status']={'enum':['sufficient_supplied_evidence','material_reference_missing','attribution_ambiguous','review_incomplete']}
    ids=list(s['properties']['intent']['properties'])
    s['properties']['intent']['properties']={key:{'$ref':'#/$defs/intent'} for key in ids}
    s['$defs']={'evidence':evidence,'intent':intent}
    for prop in ['issuer','funding']:
        s['properties'][prop]['properties']['evidence']={'$ref':'#/$defs/evidence'}
    for prop in ['reporting_parties','ownership']:
        s['properties'][prop]['items']['properties']['evidence']={'$ref':'#/$defs/evidence'}
    s['properties']['transaction_facts']={'type':'array','items':{'type':'object','additionalProperties':False,
        'required':['kind','timing','actor','target','description','evidence'],
        'properties':{'kind':{'enum':['security_purchase','issuer_financing','completed_action','procedural_disclosure_request','other']},
          'timing':{'enum':['past','pending','current','unclear']},'actor':{'type':'string'},'target':{'type':'string'},
          'description':{'type':'string','minLength':1},'evidence':{'$ref':'#/$defs/evidence'}}}}
    s['required'].append('transaction_facts')
    s['properties']['review_delivery']={'type':'object'}
    s['title']='Extraction stability v2, post-development rules and mechanical delivery coverage'
    Draft202012Validator.check_schema(s)
    return s


def main():
    protocol=json.loads((ROOT/'research/protocol/extraction-stability-v2.json').read_text())
    category=json.loads((ROOT/'research/protocol/categories-v1.yaml').read_text())
    category['version']='stability-v2'
    category['status']='development_refinement_after_v1_stability_not_accuracy_validated'
    category['additional_boundary_rules']=protocol['semantic_refinements']
    freeze(ROOT/'research/protocol/categories-stability-v2.json',enc(category))
    freeze(ROOT/'research/protocol/extraction-stability-schema-v2.json',enc(make_schema()))
    filenames=['extraction-stability-v2.json','extraction-stability-prompt-v2.md',
               'extraction-stability-schema-v2.json','categories-stability-v2.json']
    hashes={}
    for name in filenames:
        raw=(ROOT/'research/protocol'/name).read_bytes()
        freeze(RUN/'inputs'/name,raw)
        hashes['research/protocol/'+name]=sha(raw)
    inventory=json.loads((OLD/'inputs/inventory.json').read_text())
    assert len(inventory)==10
    for row in inventory:
        raw=(OLD/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
        assert sha(raw)==row['input_sha256']
        freeze(RUN/'inputs/bundles'/f'{row["accession"]}.json',raw)
    freeze(RUN/'inputs/inventory.json',enc(inventory))
    jobs=[]
    for row in inventory:
        for agent in ['A','B','C']:
            for name in ['drafts','draft-history','delivery']:
                (RUN/'agents'/agent/'cases'/row['case_id']/name).mkdir(parents=True,exist_ok=True)
            (RUN/'agents'/agent/'records').mkdir(exist_ok=True)
            jobs.append({'case_id':row['case_id'],'agent':agent,'accession':row['accession'],
                         'context_rule':'one filing only; fresh context; prior answers excluded'})
    freeze(RUN/'job-inventory.json',enc(jobs))
    freeze(RUN/'prefit-manifest.json',enc({'protocol':'extraction-stability-v2','expected_jobs':30,
        'source_hashes':hashes,'same_source_bytes_as_v1':True,'v1_inventory_sha256':sha((OLD/'inputs/inventory.json').read_bytes()),
        'revision_after_development_results':True,'human_reference_accuracy_not_established':True,
        'reserved_validation_sources_supplied':False,'old_metrics_sha256':sha((OLD/'metrics.json').read_bytes())}))
    print(json.dumps({'run':str(RUN),'cases':len(inventory),'fresh_context_jobs':len(jobs)},indent=2))


if __name__=='__main__':
    main()
