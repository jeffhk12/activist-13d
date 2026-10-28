"""Serve frozen evidence and finalize the shared-rule extraction-v3 experiment.

Inputs: assigned job, frozen rules/schema/source, own draft; critics receive only
mechanically selected extractor-A claims. Outputs: bounded delivery receipts,
hash-preserved drafts and immutable records. Identity: served interval union
covers every readable character; quote==canonical[start:end); every claim once.
Tier:1. Run project Python extraction_v3_io.py ACTION --job JOB [--draft PATH].
"""
import argparse
import copy
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from audit_io import ISSUES, check_claim_ids
from jsonschema import Draft202012Validator
from stability_io import anchor
from stability_v2_io import interval_coverage

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-revision/20261027-v3'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()


def read(path):
    return json.loads(path.read_text())


def claims_for(record):
    claims=[]
    def add(cid,kind,value,evidence):
        claims.append({'claim_id':cid,'kind':kind,'value':value,'candidate_evidence':evidence})
    add('issuer','issuer',{k:v for k,v in record['issuer'].items() if k!='evidence'},record['issuer']['evidence'])
    for field,kind in [('reporting_parties','reporter'),('ownership','ownership'),('transaction_facts','transaction')]:
        for i,item in enumerate(record[field],1):
            add(f'{kind}.{i:03}',kind,{k:v for k,v in item.items() if k!='evidence'},item['evidence'])
    add('funding.summary','funding_summary',{'status':record['funding']['status'],'summary':record['funding']['summary']},record['funding']['evidence'])
    for i,item in enumerate(record['funding']['components'],1):
        add(f'funding.component.{i:03}','funding_component',{k:v for k,v in item.items() if k!='evidence'},item['evidence'])
    for category,item in record['intent'].items():
        add('intent.'+category,'intent',{k:v for k,v in item.items() if k not in ['evidence','rationale']},item['evidence'])
    return claims


def load_job(job_id,need_candidate=True):
    prep=read(RUN/'preparation.json')
    jobs=read(RUN/'jobs.json')
    found=[j for j in jobs if j['job_id']==job_id]
    if len(found)!=1:
        raise ValueError('Assigned frozen job required')
    job=found[0]
    role='critic' if 'critic' in job['role'] else 'blind' if 'blind' in job['role'] else 'extractor'
    for name in ['jobs.json',job['bundle'],'inputs/protocol.json','inputs/common-rules.md','inputs/schema.json','inputs/categories.json',f'inputs/role-{role}.txt']:
        if sha((RUN/name).read_bytes())!=prep['input_sha256'][name]:
            raise ValueError('Frozen input changed: '+name)
    candidate=None
    if job['role']=='control_critic':
        path=RUN/job['candidate']
        if sha(path.read_bytes())!=prep['input_sha256'][job['candidate']]:
            raise ValueError('Control candidate changed')
        candidate=read(path)
    elif job['role']=='critic' and need_candidate:
        seal=read(RUN/'candidates'/f'{job_id}.seal.json')
        path=RUN/'candidates'/f'{job_id}.json'
        original=RUN/'jobs'/job['candidate_source_job']/'record.json'
        if sha(path.read_bytes())!=seal['candidate_sha256'] or sha(original.read_bytes())!=seal['original_record_sha256']:
            raise ValueError('Candidate/original changed')
        candidate=read(path)
    if job.get('phase')=='fresh':
        release=RUN/'fresh-release.json'
        if not release.exists() or job['case_id'] not in read(release)['released_case_ids']:
            raise ValueError('Fresh sources stay closed until the declared development gate')
    bundle_path=RUN/job['bundle']
    bundle=json.loads(gzip.decompress(bundle_path.read_bytes())) if bundle_path.suffix=='.gz' else read(bundle_path)
    return job,bundle,candidate


def schema_for(role):
    base=read(RUN/'inputs/schema.json')
    if role in ['extractor','blind']:
        return base
    if role in ['critic','control_critic']:
        item={'type':'object','additionalProperties':False,
              'required':['claim_id','verdict','rationale','issue_codes','evidence'],
              'properties':{'claim_id':{'type':'string'},'verdict':{'enum':['supported','contradicted','insufficient_evidence']},
                            'rationale':{'type':'string','minLength':1},'issue_codes':{'type':'array','items':{'enum':ISSUES},'uniqueItems':True},
                            'evidence':{'$ref':'#/$defs/evidence'}}}
        prop={'reviews':{'type':'array','items':item}}
    else:
        item={k:v for k,v in base.items() if k not in ['$schema','$defs','title']}
        prop={'cases':{'type':'array','items':item}}
    properties={'review_status':{'enum':['complete_readable_bundle','incomplete_source_review']},
                'reviewed_document_ids':{'type':'array','items':{'type':'string'},'uniqueItems':True},
                'evidence_gaps':{'type':'array','items':{'type':'string'}},**prop}
    return {'type':'object','additionalProperties':False,'$defs':base['$defs'],
            'properties':properties,'required':list(properties)}


def delivery(job,bundle):
    docs={d['document_id']:d for d in bundle['documents'] if isinstance(d.get('text'),str) and d['text']}
    intervals={k:[] for k in docs}
    receipts=[]
    for path in sorted((RUN/'jobs'/job['job_id']/'delivery').glob('*.json')):
        r=read(path)
        doc=docs[r['document_id']]
        if r['job_id']!=job['job_id'] or r['text_sha256']!=doc['text_sha256'] or r['chunk_sha256']!=sha(doc['text'][r['start']:r['end']].encode()):
            raise ValueError('Delivery identity/source mismatch')
        if r['end']-r['start']>16000:
            raise ValueError('Oversize source chunk')
        intervals[r['document_id']].append((r['start'],r['end']))
        receipts.append({'path':str(path.relative_to(RUN)),'sha256':sha(path.read_bytes())})
    covered={k:interval_coverage(intervals[k],len(d['text'])) for k,d in docs.items()}
    return {'job_id':job['job_id'],'all_readable_text_delivered':all(v['complete'] for v in covered.values()),
            'expected_characters':sum(v['expected_characters'] for v in covered.values()),
            'served_unique_characters':sum(v['served_unique_characters'] for v in covered.values()),
            'documents':covered,'receipts':receipts,
            'limit':'Source delivery plus worker attestation; not comprehension or unavailable-exhibit completeness.'}


def anchor_all(value,docs):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='evidence':
                value[key]=[anchor(e,docs) for e in item]
            else:
                anchor_all(item,docs)
    elif isinstance(value,list):
        for item in value:
            anchor_all(item,docs)


def check_extraction(record,bundle,covered):
    if record['accession']!=bundle['accession']:
        raise ValueError('Wrong accession')
    readable={d['document_id'] for d in bundle['documents'] if d.get('text')}
    if not set(record['reviewed_document_ids'])<=readable:
        raise ValueError('Unreviewable source ID')
    if record['extraction_status']=='complete_readable_bundle' and (set(record['reviewed_document_ids'])!=readable or not covered['all_readable_text_delivered']):
        raise ValueError('Complete review requires full delivered coverage')
    if record['issuer']['status']=='present' and (not record['issuer']['name'] or not record['issuer']['evidence']):
        raise ValueError('Present issuer needs name and evidence')
    for field in ['reporting_parties','ownership','transaction_facts']:
        if any(not row['evidence'] for row in record[field]):
            raise ValueError('Every returned fact needs evidence')
    funding=record['funding']
    if funding['status']=='present' and (not funding['components'] or not funding['evidence']):
        raise ValueError('Present funding needs components and evidence')
    for item in funding['components']:
        if not item['evidence']:
            raise ValueError('Funding component needs exact source')
        if item['certainty']=='confirmed_actual' and (item['acquisition_link']!='current_acquisition' or item['type']=='unknown'):
            raise ValueError('Confirmed actual funding must concern current acquisition')
        if item['certainty']=='historical_indirect' and item['acquisition_link']!='historical_affiliate':
            raise ValueError('Historical financing must retain historical link')
    for category,item in record['intent'].items():
        if item['status']=='present':
            if not item['actor'] or not item['target'] or not item['evidence'] or item['qualification_basis'] not in ['separate_intervention','primary_control_bid']:
                raise ValueError('Positive objective needs actor/target, evidence and qualifying basis')
            if item['qualification_basis']=='primary_control_bid' and category!='sale_of_company':
                raise ValueError('Primary control bid qualifies sale category only')
        if item['status']=='not_stated' and (item['evidence_status']!='sufficient_supplied_evidence' or record['extraction_status']!='complete_readable_bundle'):
            raise ValueError('Absence needs adequate reviewed source, not missing evidence')


def normalize(record,job,bundle,candidate,covered):
    record=copy.deepcopy(record)
    Draft202012Validator(schema_for(job['role'])).validate(record)
    docs={d['document_id']:d for d in bundle['documents']}
    anchor_all(record,docs)
    if job['role'] in ['extractor','blind']:
        check_extraction(record,bundle,covered)
    else:
        readable={k for k,d in docs.items() if d.get('text')}
        if not set(record['reviewed_document_ids'])<=readable:
            raise ValueError('Reviewed ID unavailable')
        if record['review_status']=='complete_readable_bundle' and (set(record['reviewed_document_ids'])!=readable or not covered['all_readable_text_delivered']):
            raise ValueError('Complete review needs full delivery and all readable IDs')
        if job['role'] in ['critic','control_critic']:
            check_claim_ids(record['reviews'],candidate['claims'])
            claims={c['claim_id']:c for c in candidate['claims']}
            for r in record['reviews']:
                if r['verdict']!='insufficient_evidence' and not r['evidence']:
                    raise ValueError('Conclusive verdict needs evidence')
                if job['role']=='control_critic' and any(e['document_id']!=claims[r['claim_id']]['source_document_id'] for e in r['evidence']):
                    raise ValueError('Control claim evidence must be its own fixture')
                if record['review_status']!='complete_readable_bundle' and r['verdict']=='supported' and claims[r['claim_id']]['kind']=='intent' and claims[r['claim_id']]['value']['status']=='not_stated':
                    raise ValueError('Incomplete critic cannot approve broad absence')
        else:
            ids=[c['accession'] for c in record['cases']]
            if len(ids)!=len(set(ids)) or set(ids)!=readable:
                raise ValueError('Each control fixture once')
            for case in record['cases']:
                did=case['accession']
                check_extraction(case,{'accession':did,'documents':[docs[did]]},covered)
                def own(value,did=did):
                    if isinstance(value,dict):
                        if 'quote' in value and value.get('document_id')!=did:
                            raise ValueError('Control inventory fact must cite its own fixture')
                        for v in value.values():
                            own(v)
                    elif isinstance(value,list):
                        for v in value:
                            own(v)
                own(case)
    record['review_delivery']=covered
    return record


def seal_candidate(job):
    if job['role']!='critic':
        raise ValueError('Only natural critic candidates are sealed')
    path=RUN/'jobs'/job['candidate_source_job']/'record.json'
    original=read(path)
    candidate={'accession':job['accession'],'case_id':job['case_id'],'claims':claims_for(original)}
    payload=enc(candidate)
    target=RUN/'candidates'/f'{job["job_id"]}.json'
    seal={'original_record_sha256':sha(path.read_bytes()),'candidate_sha256':sha(payload),
          'candidate_source_job':job['candidate_source_job'],'selection':'always preassigned extractor; no best-answer selection'}
    for dest,raw in [(target,payload),(target.with_suffix('.seal.json'),enc(seal))]:
        if dest.exists() and dest.read_bytes()!=raw:
            raise ValueError('Sealed candidate changed')
        if not dest.exists():
            dest.write_bytes(raw)
    return {'candidate':str(target),'claims':len(candidate['claims'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['instructions','list','schema','candidate','show','coverage','finalize','seal-candidate'])
    parser.add_argument('--job',required=True)
    parser.add_argument('--document')
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--length',type=int,default=16000)
    parser.add_argument('--draft',type=Path)
    args=parser.parse_args()
    job,bundle,candidate=load_job(args.job,need_candidate=args.action not in ['seal-candidate','instructions'])
    own=RUN/'jobs'/args.job
    if args.action=='seal-candidate':
        print(json.dumps(seal_candidate(job)))
        return
    if args.action=='instructions':
        role='critic' if 'critic' in job['role'] else 'blind' if 'blind' in job['role'] else 'extractor'
        print((RUN/'inputs/common-rules.md').read_text())
        print((RUN/'inputs'/f'role-{role}.txt').read_text())
        if job['role'].startswith('control_') and role!='critic':
            print('CONTROL INVENTORY: each readable document is a separate complete fictional filing. Return top review_status, reviewed_document_ids, evidence_gaps, cases. Each cases entry follows the FULL extraction schema with accession=document_id and reviewed_document_ids=[that ID]. All evidence must come from its own fixture. No candidate/key is supplied.')
        return
    if args.action=='schema':
        print(json.dumps(schema_for(job['role']),ensure_ascii=False))
        return
    if args.action=='candidate':
        if candidate is None:
            raise ValueError('Source-only role has no candidate access')
        print(json.dumps(candidate,indent=2,ensure_ascii=False))
        return
    if args.action=='list':
        print(json.dumps({'job':job,'documents':[{'document_id':d['document_id'],'filename':d.get('filename'),'type':d.get('type'),
                         'characters':len(d['text']) if isinstance(d.get('text'),str) else None} for d in bundle['documents']],
                          'claim_count':len(candidate['claims']) if candidate else None},indent=2))
        return
    if args.action=='show':
        found=[d for d in bundle['documents'] if d['document_id']==args.document]
        if len(found)!=1 or not isinstance(found[0].get('text'),str):
            raise ValueError('Readable assigned document required')
        doc=found[0]
        if not 0<=args.start<len(doc['text']) or not 1<=args.length<=16000:
            raise ValueError('Valid range <=16000 characters required')
        end=min(len(doc['text']),args.start+args.length)
        chunk=doc['text'][args.start:end]
        receipt={'job_id':args.job,'document_id':args.document,'start':args.start,'end':end,
                 'text_sha256':doc['text_sha256'],'chunk_sha256':sha(chunk.encode())}
        target=own/'delivery'/(sha((args.document+str(args.start)+':'+str(end)).encode())+'.json')
        payload=enc(receipt)
        if target.exists() and target.read_bytes()!=payload:
            raise ValueError('Receipt changed')
        target.write_bytes(payload)
        print(f'JOB {args.job} DOCUMENT {args.document} UNICODE [{args.start},{end}) / {len(doc["text"])}')
        print(chunk)
        return
    covered=delivery(job,bundle)
    if args.action=='coverage':
        print(json.dumps(covered,indent=2))
        return
    if args.draft is None or not args.draft.resolve().is_relative_to((own/'drafts').resolve()):
        raise ValueError('Own assigned drafts only')
    raw=args.draft.read_bytes()
    history=own/'draft-history'/(sha(raw)+'.json')
    if not history.exists():
        history.write_bytes(raw)
    record=normalize(json.loads(raw),job,bundle,candidate,covered)
    record['run_metadata']={'protocol':'extraction-v3','job_id':args.job,'role':job['role'],'case_id':job['case_id'],
                            'accession':job['accession'],'producer_kind':'model_judgment_not_independent_reference',
                            'provider':'Codex built-in subscription agent','model_identifier':None,'generation_settings':None,
                            'context':'fresh one-role one-case context; same configured model; settings not exposed',
                            'finalized_at_utc':datetime.now(timezone.utc).isoformat(),'raw_draft_sha256':sha(raw),
                            'bundle_sha256':sha((RUN/job['bundle']).read_bytes()),
                            'candidate_sha256':sha(enc(candidate)) if candidate else None,
                            'common_rules_sha256':sha((RUN/'inputs/common-rules.md').read_bytes()),
                            'schema_sha256':sha((RUN/'inputs/schema.json').read_bytes()),
                            'protocol_sha256':sha((RUN/'inputs/protocol.json').read_bytes())}
    dest=own/'record.json'
    if dest.exists() and read(dest)['run_metadata']['raw_draft_sha256']!=sha(raw):
        raise ValueError('Finalized judgments immutable')
    if not dest.exists():
        dest.write_bytes(enc(record))
    print(json.dumps({'record':str(dest),'full_readable_delivery':covered['all_readable_text_delivered'],'schema_and_quotes':'passed'}))


if __name__=='__main__':
    main()
