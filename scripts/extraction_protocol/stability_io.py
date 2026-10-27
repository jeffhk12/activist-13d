"""Read frozen discovery evidence and mechanically finalize agent citations.

Inputs: fixed stability inputs and one agent's own draft; no other agent results.
Outputs: bounded source text or an immutable raw-draft snapshot/final record.
Identity: quote=canonical_text[start:end] in Unicode; hashes identify exact inputs.
Tier: 1. Run project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8:
 stability_io.py list [--case D01]
 stability_io.py show --case D01 --document 'DOCUMENT[1]' --start 0 --length 24000
 stability_io.py finalize --agent A --case D01 --draft OWN_DRAFT_JSON
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_case(case):
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    found=[r for r in inventory if r['case_id']==case or r['accession']==case]
    if len(found)!=1:
        raise ValueError('Case must be one of the ten discovery cases')
    row=found[0]
    raw=(RUN/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
    if sha(raw)!=row['input_sha256']:
        raise ValueError('Frozen input differs')
    return row,json.loads(raw)


def anchor(entry, documents):
    entry=copy.deepcopy(entry)
    d=documents.get(entry.get('document_id'))
    if d is None or not isinstance(d.get('text'),str):
        raise ValueError('Citation refers to absent or unreadable text')
    text=d['text']
    quote=entry.get('quote')
    if not isinstance(quote,str) or not quote:
        raise ValueError('Nonempty exact quote required')
    if 'start' not in entry:
        positions=[]
        start=0
        while True:
            start=text.find(quote,start)
            if start<0:
                break
            positions.append(start)
            start+=1
        if len(positions)!=1:
            raise ValueError(f'Quote has {len(positions)} matches in {d["document_id"]}; supply an exact start if repeated. Positions: {positions[:20]}')
        entry['start']=positions[0]
    start=entry['start']
    if not isinstance(start,int) or isinstance(start,bool) or start<0:
        raise ValueError('Start must be a nonnegative Unicode offset')
    end=start+len(quote)
    if text[start:end]!=quote:
        raise ValueError('Citation text differs at supplied start')
    if 'end' in entry and entry['end']!=end:
        raise ValueError('Supplied end differs')
    if 'text_sha256' in entry and entry['text_sha256']!=d['text_sha256']:
        raise ValueError('Supplied document hash differs')
    entry.update(end=end,text_sha256=d['text_sha256'])
    return entry


def normalize(record,bundle):
    record=copy.deepcopy(record)
    if record['accession']!=bundle['accession']:
        raise ValueError('Wrong accession')
    documents={d['document_id']:d for d in bundle['documents']}
    readable={k for k,d in documents.items() if isinstance(d.get('text'),str) and d['text']}
    reviewed=set(record['reviewed_document_ids'])
    if not reviewed.issubset(readable):
        raise ValueError('Reviewed document not available')
    if record['extraction_status']=='complete_readable_bundle' and reviewed!=readable:
        raise ValueError(f'Complete review requires all readable IDs; missing {sorted(readable-reviewed)}')

    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='evidence':
                    value[key]=[anchor(e,documents) for e in item]
                else:
                    walk(item)
        elif isinstance(value,list):
            for item in value:
                walk(item)
    walk(record)
    if record['issuer']['status']=='present' and (not record['issuer']['name'] or not record['issuer']['evidence']):
        raise ValueError('Present issuer needs name and evidence')
    for field in ['reporting_parties','ownership']:
        if any(not item['evidence'] for item in record[field]):
            raise ValueError(f'Every {field} entry needs source evidence')
    if record['funding']['status']=='present' and (not record['funding']['types'] or not record['funding']['evidence']):
        raise ValueError('Present funding needs types and evidence')
    for key,item in record['intent'].items():
        if item['status']=='present' and (not item['evidence'] or not item['actor'] or not item['target']):
            raise ValueError(f'Positive {key} needs actor, target and evidence')
        if record['extraction_status']=='incomplete_source_review' and item['status']=='not_stated':
            raise ValueError('Incomplete reading cannot establish a negative intent label')
    schema=json.loads((RUN/'inputs/extraction-stability-schema-v1.json').read_text())
    Draft202012Validator(schema).validate(record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['list','show','finalize'])
    parser.add_argument('--case')
    parser.add_argument('--document')
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--length',type=int,default=24000)
    parser.add_argument('--agent',choices=['A','B','C'])
    parser.add_argument('--draft',type=Path)
    args=parser.parse_args()
    if args.action=='list':
        inventory=json.loads((RUN/'inputs/inventory.json').read_text())
        if args.case:
            inventory=[load_case(args.case)[0]]
        print(json.dumps(inventory,indent=2,ensure_ascii=False))
        return
    row,bundle=load_case(args.case)
    if args.action=='show':
        docs=[d for d in bundle['documents'] if d['document_id']==args.document]
        if len(docs)!=1 or not isinstance(docs[0].get('text'),str):
            raise ValueError('Document text unavailable')
        if args.start<0 or not 0<args.length<=40000:
            raise ValueError('Use nonnegative start and 1..40000 character chunks')
        text=docs[0]['text']
        end=min(len(text),args.start+args.length)
        print(f'CASE {row["case_id"]} ACCESSION {row["accession"]} DOCUMENT {args.document} UNICODE [{args.start},{end}) / {len(text)}')
        print(text[args.start:end])
        return
    if args.agent is None or args.draft is None:
        raise ValueError('Finalize requires own agent ID and draft')
    own=RUN/'agents'/args.agent
    draft=args.draft.resolve()
    if not draft.is_relative_to((own/'drafts').resolve()):
        raise ValueError('Only the specified agent own-draft directory is accepted')
    raw=draft.read_bytes()
    history=own/'draft-history'/f'{row["accession"]}-{sha(raw)}.json'
    if not history.exists():
        history.write_bytes(raw)
    record=normalize(json.loads(raw),bundle)
    protocol_hashes={name:sha((RUN/'inputs'/name).read_bytes()) for name in
      ['extraction-stability-v1.json','extraction-stability-schema-v1.json','extraction-stability-prompt-v1.md','categories-v1.yaml']}
    record['run_metadata']={'agent':args.agent,'producer_kind':'model_interpretation_not_human_reference',
        'provider':'Codex built-in agent','model_identifier':None,'generation_settings':None,
        'metadata_limit':'Exact model identifier, temperature and seed not exposed by spawn interface',
        'finalized_at_utc':datetime.now(timezone.utc).isoformat(),
        'input_bundle_sha256':row['input_sha256'],'raw_source_sha256':row['source_sha256'],
        'raw_draft_sha256':sha(raw),'protocol_hashes':protocol_hashes}
    data=(json.dumps(record,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    dest=own/'records'/f'{row["accession"]}.json'
    if dest.exists():
        existing=json.loads(dest.read_text())
        if existing['run_metadata']['raw_draft_sha256']!=sha(raw):
            raise ValueError('Finalized record is immutable; preserve failure/change in a new run')
        print('Already finalized unchanged:',dest)
        return
    dest.write_bytes(data)
    print(json.dumps({'final_record':str(dest),'citation_and_schema_checks':'passed',
                      'extraction_status':record['extraction_status']},indent=2))


if __name__=='__main__':
    main()
