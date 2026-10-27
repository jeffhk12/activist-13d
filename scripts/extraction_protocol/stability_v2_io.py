"""Serve fixed canonical chunks with receipts and finalize revised extractions.

Inputs: one assigned discovery case, replicate A/B/C and own raw draft.
Outputs: bounded source chunks, immutable range receipts and model record.
Identity: complete delivery iff union of served [start,end) covers every readable
document exactly; cited quote equals canonical text slice in Unicode coordinates.
Tier: 1. Use project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8:
 stability_v2_io.py list --agent A --case D01
 stability_v2_io.py show --agent A --case D01 --document 'DOCUMENT[1]' --start 0
 stability_v2_io.py coverage --agent A --case D01
 stability_v2_io.py finalize --agent A --case D01 --draft OWN_DRAFT
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from stability_io import anchor

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'
INPUT_NAMES=['extraction-stability-v2.json','extraction-stability-prompt-v2.md','extraction-stability-schema-v2.json','categories-stability-v2.json']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()


def interval_coverage(intervals,length):
    merged=[]
    for start,end in sorted(intervals):
        if not (isinstance(start,int) and isinstance(end,int) and 0<=start<end<=length):
            raise ValueError('Invalid delivery interval')
        if merged and start<=merged[-1][1]:
            merged[-1][1]=max(end,merged[-1][1])
        else:
            merged.append([start,end])
    cursor=0
    missing=[]
    for start,end in merged:
        if start>cursor:
            missing.append([cursor,start])
        cursor=end
    if cursor<length:
        missing.append([cursor,length])
    return {'served_unique_characters':sum(e-s for s,e in merged),'expected_characters':length,
            'missing_ranges':missing,'complete':not missing,'merged_ranges':merged}


def load_case(case):
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    found=[r for r in inventory if r['case_id']==case]
    if len(found)!=1:
        raise ValueError('Only the ten discovery case IDs are accepted')
    row=found[0]
    raw=(RUN/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
    if sha(raw)!=row['input_sha256']:
        raise ValueError('Frozen canonical input differs')
    return row,json.loads(raw)


def delivery(agent,case,bundle):
    own=RUN/'agents'/agent/'cases'/case
    docs={d['document_id']:d for d in bundle['documents'] if isinstance(d.get('text'),str) and d['text']}
    intervals={key:[] for key in docs}
    receipts=[]
    for path in sorted((own/'delivery').glob('*.json')):
        r=json.loads(path.read_text())
        if r['agent']!=agent or r['case_id']!=case or r['document_id'] not in docs:
            raise ValueError('Delivery receipt has wrong identity')
        d=docs[r['document_id']]
        if r['text_sha256']!=d['text_sha256'] or r['chunk_sha256']!=sha(d['text'][r['start']:r['end']].encode()):
            raise ValueError('Delivery receipt text/hash differs')
        intervals[r['document_id']].append((r['start'],r['end']))
        receipts.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path.read_bytes())})
    per_doc={key:interval_coverage(intervals[key],len(d['text'])) for key,d in docs.items()}
    return {'agent':agent,'case_id':case,'all_readable_text_delivered':all(d['complete'] for d in per_doc.values()),
            'served_unique_characters':sum(d['served_unique_characters'] for d in per_doc.values()),
            'expected_characters':sum(d['expected_characters'] for d in per_doc.values()),
            'documents':per_doc,'receipts':receipts,
            'limit':'Mechanical delivery log; not independent evidence of comprehension or material-source completeness'}


def normalize_v2(record,bundle,delivery_summary):
    record=copy.deepcopy(record)
    schema=json.loads((RUN/'inputs/extraction-stability-schema-v2.json').read_text())
    Draft202012Validator(schema).validate(record)
    if record['accession']!=bundle['accession']:
        raise ValueError('Wrong accession')
    docs={d['document_id']:d for d in bundle['documents']}
    readable={k for k,d in docs.items() if isinstance(d.get('text'),str) and d['text']}
    if not set(record['reviewed_document_ids']).issubset(readable):
        raise ValueError('Reviewed document not readable')
    if record['extraction_status']=='complete_readable_bundle':
        if set(record['reviewed_document_ids'])!=readable or not delivery_summary['all_readable_text_delivered']:
            raise ValueError('Complete claim requires all readable IDs and complete delivered interval coverage')
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
    if record['issuer']['status']=='present' and (not record['issuer']['name'] or not record['issuer']['evidence']):
        raise ValueError('Present issuer needs name/evidence')
    for field in ['reporting_parties','ownership','transaction_facts']:
        if any(not r['evidence'] for r in record[field]):
            raise ValueError(f'Every {field} entry needs exact source support')
    if record['funding']['status']=='present' and (not record['funding']['types'] or not record['funding']['evidence']):
        raise ValueError('Present funding needs types and evidence')
    for key,item in record['intent'].items():
        if item['status']=='present' and (not item['actor'] or not item['target'] or not item['evidence']):
            raise ValueError(f'Positive {key} needs actor, target and citation')
        if item['status']=='not_stated' and item['evidence_status']!='sufficient_supplied_evidence':
            raise ValueError('Not_stated cannot mask a material or unresolved evidence gap')
        if record['extraction_status']=='incomplete_source_review' and item['status']=='not_stated':
            raise ValueError('Incomplete review cannot establish negative intent')
    record['review_delivery']=delivery_summary
    Draft202012Validator(schema).validate(record)
    return record


def template(case):
    row,bundle=load_case(case)
    cats=json.loads((RUN/'inputs/categories-stability-v2.json').read_text())['categories']
    return {'accession':row['accession'],'extraction_status':'STATUS',
      'reviewed_document_ids':['READABLE_DOCUMENT_IDS'],'evidence_gaps':[],
      'issuer':{'status':'STATE','name':None,'evidence':[]},'reporting_parties':[],
      'ownership':[],'funding':{'status':'STATE','types':[],'summary':'','evidence':[]},
      'transaction_facts':[],
      'intent':{c['id']:{'status':'STATE','evidence_status':'EVIDENCE_STATUS',
                'rationale':'','actor':None,'target':None,'evidence':[]} for c in cats}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['list','show','coverage','finalize','schema'])
    p.add_argument('--agent',choices=['A','B','C'],required=True)
    p.add_argument('--case',required=True)
    p.add_argument('--document')
    p.add_argument('--start',type=int,default=0)
    p.add_argument('--length',type=int,default=16000)
    p.add_argument('--draft',type=Path)
    args=p.parse_args()
    row,bundle=load_case(args.case)
    own=RUN/'agents'/args.agent/'cases'/args.case
    if args.action=='list':
        print(json.dumps({'inventory':row,'template_not_a_model_answer':template(args.case)},indent=2,ensure_ascii=False))
        return
    if args.action=='schema':
        print(json.dumps(json.loads((RUN/'inputs/extraction-stability-schema-v2.json').read_text()),ensure_ascii=False))
        return
    if args.action=='show':
        ds=[d for d in bundle['documents'] if d['document_id']==args.document]
        if len(ds)!=1 or not isinstance(ds[0].get('text'),str):
            raise ValueError('No readable text for document')
        d=ds[0]
        if args.start<0 or args.start>=len(d['text']) or not 1<=args.length<=16000:
            raise ValueError('Use valid start and chunk length 1..16000')
        end=min(len(d['text']),args.start+args.length)
        chunk=d['text'][args.start:end]
        receipt={'agent':args.agent,'case_id':args.case,'accession':row['accession'],
                 'document_id':d['document_id'],'start':args.start,'end':end,
                 'text_sha256':d['text_sha256'],'chunk_sha256':sha(chunk.encode())}
        path=own/'delivery'/f'{sha((d["document_id"]+str(args.start)+":"+str(end)).encode())}.json'
        raw=enc(receipt)
        if path.exists() and path.read_bytes()!=raw:
            raise ValueError('Frozen delivery receipt differs')
        path.write_bytes(raw)
        print(f'CASE {args.case} AGENT {args.agent} DOCUMENT {d["document_id"]} UNICODE [{args.start},{end}) / {len(d["text"])}')
        print(chunk)
        return
    covered=delivery(args.agent,args.case,bundle)
    if args.action=='coverage':
        print(json.dumps(covered,indent=2))
        return
    if args.draft is None or not args.draft.resolve().is_relative_to((own/'drafts').resolve()):
        raise ValueError('Only own case draft path accepted')
    raw=args.draft.read_bytes()
    archive=own/'draft-history'/f'{sha(raw)}.json'
    if not archive.exists():
        archive.write_bytes(raw)
    record=normalize_v2(json.loads(raw),bundle,covered)
    record['run_metadata']={'protocol':'extraction-stability-v2','agent':args.agent,'case_id':args.case,
      'context_design':'fresh context for one filing only','producer_kind':'model_interpretation_not_human_reference',
      'provider':'Codex built-in agent','model_identifier':None,'generation_settings':None,
      'metadata_limit':'Exact model/temperature/seed not exposed by spawn interface',
      'finalized_at_utc':datetime.now(timezone.utc).isoformat(),'input_bundle_sha256':row['input_sha256'],
      'raw_source_sha256':row['source_sha256'],'raw_draft_sha256':sha(raw),
      'protocol_hashes':{n:sha((RUN/'inputs'/n).read_bytes()) for n in INPUT_NAMES}}
    dest=RUN/'agents'/args.agent/'records'/f'{row["accession"]}.json'
    if dest.exists():
        if json.loads(dest.read_text())['run_metadata']['raw_draft_sha256']!=sha(raw):
            raise ValueError('Finalized record immutable')
        print('Already finalized unchanged:',dest)
        return
    dest.write_bytes(enc(record))
    print(json.dumps({'record':str(dest),'status':record['extraction_status'],
                      'all_readable_text_delivered':covered['all_readable_text_delivered'],
                      'schema_and_citations':'passed'},indent=2))


if __name__=='__main__':
    main()
