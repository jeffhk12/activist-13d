"""Deliver bounded audit evidence and finalize source-grounded reviewer records.

Inputs: assigned frozen job, canonical source, optional anonymous candidate/draft.
Outputs: logged text ranges, schema/citation checks and immutable model judgments.
Identity: union(delivered intervals) covers readable Unicode text; source slices
equal quotations; each candidate claim is reviewed exactly once. Tier:1.
Run: project Python scripts/extraction_protocol/audit_io.py ACTION --job JOB_ID
 actions:list,candidate,schema,show,coverage,finalize; show needs --document/--start.
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from stability_io import anchor
from stability_v2_io import interval_coverage, normalize_v2

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-audit/20261027-v1'
ISSUES=['value_or_unit','actor_or_target','temporal_scope','conditionality','overlap_or_attribution',
        'missing_reference','inadequate_support','definition_ambiguity','candidate_internal_inconsistency','other']
VERDICTS=['supported','contradicted','insufficient_evidence']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()


def load_job(job_id):
    setup=json.loads((RUN/'preparation.json').read_text())
    jobs=json.loads((RUN/'inputs/jobs.json').read_text())
    matching=[r for r in jobs if r['job_id']==job_id]
    if len(matching)!=1:
        raise ValueError('Use an assigned frozen job')
    job=matching[0]
    for name in ['inputs/jobs.json',job['bundle']]+([job['candidate']] if job['candidate'] else []):
        if sha((RUN/name).read_bytes())!=setup['input_sha256'][name]:
            raise ValueError('Frozen job/input hash changed')
    bundle=json.loads((RUN/job['bundle']).read_text())
    candidate=json.loads((RUN/job['candidate']).read_text()) if job['candidate'] else None
    return job,bundle,candidate


def schema_for(role):
    base=json.loads((RUN/'inputs/blind-schema.json').read_text())
    if role=='blind':
        return base
    evidence=base['$defs']['evidence']
    if role in ['critic','control_critic']:
        item={'type':'object','additionalProperties':False,'required':['claim_id','verdict','rationale','issue_codes','evidence'],
              'properties':{'claim_id':{'type':'string'},'verdict':{'enum':VERDICTS},'rationale':{'type':'string','minLength':1},
                            'issue_codes':{'type':'array','items':{'enum':ISSUES},'uniqueItems':True},'evidence':evidence}}
        prop={'reviews':{'type':'array','items':item}}
    else:
        reporter={'type':'object','additionalProperties':False,'required':['name','evidence'],
                  'properties':{'name':{'type':'string'},'evidence':evidence}}
        owner=copy.deepcopy(base['properties']['ownership']['items'])
        objective={'type':'object','additionalProperties':False,'required':['category','actor','target','evidence'],
                   'properties':{'category':{'enum':list(base['properties']['intent']['properties'])},
                                 'actor':{'type':'string'},'target':{'type':'string'},'evidence':evidence}}
        case={'type':'object','additionalProperties':False,'required':['document_id','reporters','ownership','objectives'],
              'properties':{'document_id':{'type':'string'},'reporters':{'type':'array','items':reporter},
                            'ownership':{'type':'array','items':owner},'objectives':{'type':'array','items':objective}}}
        prop={'cases':{'type':'array','items':case}}
    properties={'review_status':{'enum':['complete_readable_bundle','incomplete_source_review']},
                'reviewed_document_ids':{'type':'array','items':{'type':'string'},'uniqueItems':True},
                'evidence_gaps':{'type':'array','items':{'type':'string'}},**prop}
    return {'$defs':base['$defs'],'type':'object','additionalProperties':False,
            'required':list(properties),'properties':properties}


def delivery(job,bundle):
    docs={d['document_id']:d for d in bundle['documents'] if isinstance(d.get('text'),str) and d['text']}
    intervals={key:[] for key in docs}
    receipts=[]
    for path in sorted((RUN/'jobs'/job['job_id']/'delivery').glob('*.json')):
        r=json.loads(path.read_text())
        d=docs[r['document_id']]
        if r['job_id']!=job['job_id'] or r['text_sha256']!=d['text_sha256'] or sha(d['text'][r['start']:r['end']].encode())!=r['chunk_sha256']:
            raise ValueError('Wrong delivery receipt identity/text')
        intervals[r['document_id']].append((r['start'],r['end']))
        receipts.append({'path':str(path.relative_to(RUN)),'sha256':sha(path.read_bytes())})
    per_doc={key:interval_coverage(intervals[key],len(d['text'])) for key,d in docs.items()}
    return {'job_id':job['job_id'],'all_readable_text_delivered':all(r['complete'] for r in per_doc.values()),
            'served_unique_characters':sum(r['served_unique_characters'] for r in per_doc.values()),
            'expected_characters':sum(r['expected_characters'] for r in per_doc.values()),
            'documents':per_doc,'receipts':receipts,
            'limit':'Mechanical delivery plus worker review attestation, not comprehension or material-source completeness.'}


def check_claim_ids(reviews,claims):
    ids=[r['claim_id'] for r in reviews]
    expected=[c['claim_id'] for c in claims]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('Each candidate claim must be reviewed exactly once')


def normalize(record,job,bundle,candidate,covered):
    record=copy.deepcopy(record)
    role=job['role']
    Draft202012Validator(schema_for(role)).validate(record)
    if role=='blind':
        return normalize_v2(record,bundle,covered)
    docs={d['document_id']:d for d in bundle['documents']}
    readable={k for k,d in docs.items() if isinstance(d.get('text'),str) and d['text']}
    if not set(record['reviewed_document_ids'])<=readable:
        raise ValueError('Reviewed IDs include unavailable document')
    if record['review_status']=='complete_readable_bundle' and (set(record['reviewed_document_ids'])!=readable or not covered['all_readable_text_delivered']):
        raise ValueError('Complete review requires full delivered coverage and all readable IDs')
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='evidence':
                    value[key]=[anchor(e,docs) for e in item]
                else:
                    walk(item)
        elif isinstance(value,list):
            for item in value:
                walk(item)
    walk(record)
    if role in ['critic','control_critic']:
        check_claim_ids(record['reviews'],candidate['claims'])
        claims={c['claim_id']:c for c in candidate['claims']}
        for r in record['reviews']:
            if r['verdict'] in ['supported','contradicted'] and not r['evidence']:
                raise ValueError('Conclusive verdict requires exact source evidence')
            if role=='control_critic' and any(e['document_id']!=claims[r['claim_id']]['source_document_id'] for e in r['evidence']):
                raise ValueError('Control evidence must come from its own fixture')
            claim=claims[r['claim_id']]
            if (record['review_status']=='incomplete_source_review' and r['verdict']=='supported'
                    and claim['kind']=='intent' and claim['value']['status']=='not_stated'):
                raise ValueError('Incomplete review cannot support broad absence')
    else:
        case_ids=[c['document_id'] for c in record['cases']]
        if len(set(case_ids))!=len(case_ids) or set(case_ids)!=readable:
            raise ValueError('Every source-only control fixture must appear once')
        for case in record['cases']:
            for collection in ['reporters','ownership','objectives']:
                for item in case[collection]:
                    if not item['evidence'] or any(e['document_id']!=case['document_id'] for e in item['evidence']):
                        raise ValueError('Control fact needs evidence in its own fixture')
    record['review_delivery']=covered
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['list','candidate','schema','show','coverage','finalize'])
    parser.add_argument('--job',required=True)
    parser.add_argument('--document')
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--length',type=int,default=16000)
    parser.add_argument('--draft',type=Path)
    args=parser.parse_args()
    job,bundle,candidate=load_job(args.job)
    own=RUN/'jobs'/args.job
    if args.action=='list':
        print(json.dumps({'job':job,'documents':[{k:d.get(k) for k in ['document_id','filename','type']}|
                          {'characters':len(d['text']) if isinstance(d.get('text'),str) else None} for d in bundle['documents']],
                          'claim_count':len(candidate['claims']) if candidate else None,
                          'schema_action':'schema --job '+args.job,
                          'instructions':'research/protocol/extraction-audit-'+('critic' if 'critic' in job['role'] else 'blind')+'-v1.txt'},indent=2))
        return
    if args.action=='candidate':
        if candidate is None:
            raise ValueError('Source-only role is blinded to candidates')
        print(json.dumps(candidate,indent=2,ensure_ascii=False))
        return
    if args.action=='schema':
        print(json.dumps(schema_for(job['role']),indent=2))
        return
    if args.action=='show':
        found=[d for d in bundle['documents'] if d['document_id']==args.document]
        if len(found)!=1 or not isinstance(found[0].get('text'),str):
            raise ValueError('Readable document ID required')
        d=found[0]
        if not 0<=args.start<len(d['text']) or not 1<=args.length<=16000:
            raise ValueError('Valid range <=16000 characters required')
        end=min(len(d['text']),args.start+args.length)
        chunk=d['text'][args.start:end]
        receipt={'job_id':args.job,'document_id':args.document,'start':args.start,'end':end,
                 'text_sha256':d['text_sha256'],'chunk_sha256':sha(chunk.encode())}
        path=own/'delivery'/(sha((args.document+str(args.start)+':'+str(end)).encode())+'.json')
        payload=enc(receipt)
        if path.exists() and path.read_bytes()!=payload:
            raise ValueError('Receipt changed')
        path.write_bytes(payload)
        print(f'JOB {args.job} DOCUMENT {args.document} UNICODE [{args.start},{end}) / {len(d["text"])}')
        print(chunk)
        return
    covered=delivery(job,bundle)
    if args.action=='coverage':
        print(json.dumps(covered,indent=2))
        return
    if args.draft is None or not args.draft.resolve().is_relative_to((own/'drafts').resolve()):
        raise ValueError('Write only in own assigned drafts directory')
    raw=args.draft.read_bytes()
    history=own/'draft-history'/(sha(raw)+'.json')
    if not history.exists():
        history.write_bytes(raw)
    record=normalize(json.loads(raw),job,bundle,candidate,covered)
    record['run_metadata']={'protocol':'extraction-audit-v1','job_id':args.job,'role':job['role'],
                            'case_id':job['case_id'],'accession':job['accession'],
                            'producer_kind':'model_judgment_not_independent_reference',
                            'provider':'Codex built-in agent','model_identifier':None,'generation_settings':None,
                            'metadata_limit':'Exact model/temperature/seed not exposed; fresh context same inherited model',
                            'finalized_at_utc':datetime.now(timezone.utc).isoformat(),'raw_draft_sha256':sha(raw),
                            'bundle_sha256':sha((RUN/job['bundle']).read_bytes()),
                            'candidate_sha256':sha((RUN/job['candidate']).read_bytes()) if job['candidate'] else None,
                            'protocol_sha256':sha((RUN/'inputs/protocol.json').read_bytes())}
    dest=own/'record.json'
    if dest.exists():
        if json.loads(dest.read_text())['run_metadata']['raw_draft_sha256']!=sha(raw):
            raise ValueError('Preserve finalized record')
    else:
        dest.write_bytes(enc(record))
    print(json.dumps({'record':str(dest),'all_readable_text_delivered':covered['all_readable_text_delivered'],
                      'schema_and_quotes':'passed'},indent=2))


if __name__=='__main__':
    main()
