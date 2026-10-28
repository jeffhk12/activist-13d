"""Freeze inputs and constructed controls for the ten-filing reviewer pilot.

Inputs: preserved v2 replicateA records, canonical bundles, schema/categories and
new audit protocol. Outputs: new frozen job inputs, blinded claim packets, hidden
control construction keys and preservation/source hashes. Identity:22 jobs;
16 known claim controls and8 source-only controls. Tier:1; no model/API calls.
Run: project Python scripts/extraction_protocol/prepare_extraction_audit.py.
"""
import hashlib
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'research/runs/extraction-stability/20261025-v2'
RUN=ROOT/'research/runs/extraction-audit/20261027-v1'
PROTOCOL=ROOT/'research/protocol/extraction-audit-v1.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()


def claims_for(record):
    claims=[]
    def add(cid,kind,value,evidence):
        claims.append({'claim_id':cid,'kind':kind,'value':value,'candidate_evidence':evidence})
    add('issuer','issuer',{'status':record['issuer']['status'],'name':record['issuer']['name']},record['issuer']['evidence'])
    for i,r in enumerate(record['reporting_parties'],1):
        add(f'reporter.{i:03}','reporter',{'name':r['name']},r['evidence'])
    for i,r in enumerate(record['ownership'],1):
        add(f'ownership.{i:03}','ownership',{k:v for k,v in r.items() if k!='evidence'},r['evidence'])
    for kind in record['funding']['types']:
        add('funding.type.'+kind,'funding_type',{'type':kind,'funding_status':record['funding']['status'],
                                               'candidate_qualification_context':record['funding']['summary']},record['funding']['evidence'])
    add('funding.summary','funding_summary',{'status':record['funding']['status'],'summary':record['funding']['summary']},record['funding']['evidence'])
    for key,r in record['intent'].items():
        add('intent.'+key,'intent',{k:v for k,v in r.items() if k not in ['evidence','rationale']},r['evidence'])
    for i,r in enumerate(record['transaction_facts'],1):
        add(f'transaction.{i:03}','transaction',{k:v for k,v in r.items() if k!='evidence'},r['evidence'])
    assert len({c['claim_id'] for c in claims})==len(claims)
    return claims


def control_claims():
    pairs=[
      ('On the disclosure date, Aster Fund reports 7.5% of Orion common stock.',
       ('Aster Fund reports 7.5% of Orion common stock.','supported'),
       ('Aster Fund reports 75% of Orion common stock.','contradicted'),'percentage'),
      ('Aster Fund reports 7% of Orion common stock. Birch Fund reports 3% of the same class.',
       ('Birch Fund reports 3% of Orion common stock.','supported'),
       ('Birch Fund reports 7% of Orion common stock.','contradicted'),'actor'),
      ('Aster funded its purchase entirely from cash already held. It did not borrow for this purchase.',
       ('Aster used its existing cash for the purchase.','supported'),
       ('Aster borrowed to finance this purchase.','contradicted'),'confirmed_funding'),
      ('Aster may obtain margin loans in future. The source of funds for this purchase is not disclosed.',
       ('Future margin borrowing is possible; actual purchase financing is unspecified.','supported'),
       ('This purchase was financed by margin borrowing.','insufficient_evidence'),'possible_funding'),
      ('Aster states that it will not nominate directors and has no current board-nomination plan.',
       ('Aster has no current stated board-nomination plan.','supported'),
       ('Aster currently intends to nominate directors.','contradicted'),'negation'),
      ('Aster sought CEO replacement in 2018, withdrew that request in 2019, and states it has no current leadership-change plan.',
       ('The withdrawn 2018 request is historical, not a current leadership-change plan.','supported'),
       ('Aster currently seeks to replace the CEO.','contradicted'),'temporal_scope'),
      ('Aster Fund owns 10% of the class. Alice controls Aster and reports the very same 10% block as deemed ownership. These interests overlap entirely.',
       ('The two reports refer to the same 10% ownership block and must not be added.','supported'),
       ('Together Aster and Alice own 20% of the class.','contradicted'),'ownership_overlap'),
      ('Aster bought shares with cash. A separate document describing its current objectives is referenced but not supplied. No objective text is available in this fixture.',
       ('The current objectives cannot be determined from this supplied fixture.','supported'),
       ('Aster has a current objective to nominate directors.','insufficient_evidence'),'missing_reference'),
    ]
    rng=random.Random(4172)
    rows=[]
    for text,clean,changed,kind in pairs:
        for label,(claim,expected) in [('unchanged',clean),('changed',changed)]:
            token=f'K{rng.randrange(100000,999999)}'
            rows.append({'claim_id':token,'kind':'constructed_control','value':{'statement':claim},
                         '_source':text,'_expected':expected,'_condition':label,'_error_type':kind})
    rng.shuffle(rows)
    assert len(rows)==16 and len({r['claim_id'] for r in rows})==16
    docs=[]
    claims=[]
    truth=[]
    for row in rows:
        did='FIXTURE-'+row['claim_id']
        text=row['_source']
        docs.append({'document_id':did,'filename':did+'.txt','type':'SYNTHETIC','text':text,'text_sha256':sha(text.encode())})
        claims.append({'claim_id':row['claim_id'],'kind':row['kind'],'value':row['value'],'source_document_id':did,'candidate_evidence':[]})
        truth.append({'claim_id':row['claim_id'],'expected_verdict':row['_expected'],'condition':row['_condition'],'error_type':row['_error_type']})
    return {'accession':'CONTROL-CRITIC','documents':docs},claims,truth


def control_blind():
    docs=[]
    truth=[]
    categories=['board_representation','leadership_change','capital_return','capital_structure',
                'sale_of_company','asset_transaction','operational_change','governance_change']
    statements=['nominate two directors','replace the chief executive','pay a special dividend',
                'reduce issuer debt','sell the whole company','spin off the distribution subsidiary',
                'close loss-making manufacturing sites','remove the classified board structure']
    for i,(category,statement) in enumerate(zip(categories,statements,strict=True),1):
        cid=f'S{i:02}'
        party1,party2=f'Aster{i} Fund',f'Birch{i} Fund'
        p1,p2=5+i,2+i
        text=(f'Fictional complete source {cid}. Issuer: Orion{i} Corporation; security: common stock. '
              f'The two reporting persons are {party1} and {party2}. '
              f'{party1} reports {p1}% and {p1*1000} shares. {party2} reports {p2}% and {p2*1000} shares. '
              f'These are distinct holdings and neither is attributed to the other. '
              f'{party1} currently requests that the issuer {statement}. No other objective is stated. '
              'All relevant evidence for this constructed fixture is supplied.')
        docs.append({'document_id':cid,'filename':cid+'.txt','type':'SYNTHETIC','text':text,'text_sha256':sha(text.encode())})
        truth.append({'case_id':cid,'reporters':[party1,party2],
                      'ownership':[{'reporting_party':party1,'percent_of_class':p1},{'reporting_party':party2,'percent_of_class':p2}],
                      'objective':category,'deleted_candidate_party':party2,
                      'candidate_with_deleted_row':[{'reporting_party':party1,'percent_of_class':p1}]})
    return {'accession':'CONTROL-BLIND','documents':docs},truth


def main():
    if RUN.exists():
        raise ValueError('Existing audit preparation must be preserved')
    RUN.mkdir(parents=True)
    inputs=RUN/'inputs'
    inputs.mkdir()
    (RUN/'hidden-controls').mkdir()
    source_hashes={}
    def copy(path,dest):
        raw=path.read_bytes()
        source_hashes[str(path.relative_to(ROOT))]=sha(raw)
        target=inputs/dest
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        return json.loads(raw)
    protocol=copy(PROTOCOL,'protocol.json')
    assert protocol['version']=='extraction-audit-v1'
    inventory=copy(SOURCE/'inputs/inventory.json','inventory.json')
    copy(SOURCE/'inputs/categories-stability-v2.json','categories.json')
    copy(SOURCE/'inputs/extraction-stability-schema-v2.json','blind-schema.json')
    for name in ['extraction-audit-critic-v1.txt','extraction-audit-blind-v1.txt']:
        path=ROOT/'research/protocol'/name
        raw=path.read_bytes()
        source_hashes[str(path.relative_to(ROOT))]=sha(raw)
        (inputs/name).write_bytes(raw)
    old_hashes=copy(SOURCE/'record-hashes.json','old-record-hashes.json')
    jobs=[]
    for row in inventory:
        case,acc=row['case_id'],row['accession']
        copy(SOURCE/'inputs/bundles'/f'{acc}.json',f'cases/{case}/bundle.json')
        record_path=SOURCE/'agents/A/records'/f'{acc}.json'
        raw=record_path.read_bytes()
        assert sha(raw)==old_hashes[str(record_path.relative_to(ROOT))]
        source_hashes[str(record_path.relative_to(ROOT))]=sha(raw)
        candidate={'case_id':case,'accession':acc,'claims':claims_for(json.loads(raw))}
        (inputs/'cases'/case/'candidate.json').write_bytes(enc(candidate))
        for role in ['blind','critic']:
            job=f'{role}_{case.lower()}'
            jobs.append({'job_id':job,'role':role,'case_id':case,'accession':acc,
                         'bundle':f'inputs/cases/{case}/bundle.json',
                         'candidate':f'inputs/cases/{case}/candidate.json' if role=='critic' else None})
    bundle,claims,truth=control_claims()
    (inputs/'control-critic-bundle.json').write_bytes(enc(bundle))
    (inputs/'control-critic-candidate.json').write_bytes(enc({'claims':claims}))
    (RUN/'hidden-controls/critic-key.json').write_bytes(enc(truth))
    jobs.append({'job_id':'control_critic','role':'control_critic','case_id':'CONTROL',
                 'accession':'CONTROL-CRITIC','bundle':'inputs/control-critic-bundle.json','candidate':'inputs/control-critic-candidate.json'})
    bundle,truth=control_blind()
    (inputs/'control-blind-bundle.json').write_bytes(enc(bundle))
    (RUN/'hidden-controls/blind-key.json').write_bytes(enc(truth))
    jobs.append({'job_id':'control_blind','role':'control_blind','case_id':'CONTROL',
                 'accession':'CONTROL-BLIND','bundle':'inputs/control-blind-bundle.json','candidate':None})
    (inputs/'jobs.json').write_bytes(enc(jobs))
    for job in jobs:
        for directory in ['delivery','drafts','draft-history']:
            (RUN/'jobs'/job['job_id']/directory).mkdir(parents=True,exist_ok=True)
    # Snapshot old run files and source-only pack outputs before any reviewer.
    preserved={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in SOURCE.rglob('*') if p.is_file()}
    pilot=ROOT/'research/runs/ranking-llm-pilot/20261025-v2'
    for name,expected in json.loads((pilot/'output-hashes.json').read_text()).items():
        assert sha((ROOT/name).read_bytes())==expected
        preserved[name]=expected
    (RUN/'preservation-before.json').write_bytes(enc(preserved))
    for name in ['prepare_extraction_audit.py','audit_io.py','stability_io.py','stability_v2_io.py']:
        path=Path(__file__).with_name(name)
        source_hashes[str(path.relative_to(ROOT))]=sha(path.read_bytes())
        dest=RUN/'code'/name
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(path.read_bytes())
    test_path=ROOT/'tests/test_extraction_audit.py'
    source_hashes[str(test_path.relative_to(ROOT))]=sha(test_path.read_bytes())
    (RUN/'code/test_extraction_audit.py').write_bytes(test_path.read_bytes())
    (RUN/'preparation.json').write_bytes(enc({'source_sha256':source_hashes,
        'input_sha256':{str(p.relative_to(RUN)):sha(p.read_bytes()) for p in inputs.rglob('*') if p.is_file()},
        'control_key_sha256':{str(p.relative_to(RUN)):sha(p.read_bytes()) for p in (RUN/'hidden-controls').glob('*.json')},
        'candidate_selection':'A for all10; chosen before reviews','jobs':len(jobs),
        'control_claims':16,'source_control_cases':8,'same_configured_model':True,
        'exact_model_settings':'not_exposed','paid_APIs':False,'reserved_sources':False}))
    print(json.dumps({'jobs':len(jobs),'run':str(RUN),'selected_candidates':10,'claim_controls':16,'source_controls':8},indent=2))


if __name__=='__main__':
    main()
