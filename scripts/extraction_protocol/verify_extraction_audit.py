"""Offline independent integrity checks for the completed 13D reviewer pilot.

Inputs: frozen sources, delivery receipts, drafts, finalized records, preservation
manifest and rollup artifacts. Outputs: verification.json. Identities: each quote
equals its Unicode slice; union of served ranges covers [0,len(text)); all old
bytes equal their pre-run hashes; verdict counts sum to the fixed claim count.
Tier:1 integrity (no semantic accuracy estimate). Run project Python this file.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from audit_io import normalize

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-audit/20261027-v1'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quotes(value,documents):
    count=0
    if isinstance(value,dict):
        if {'document_id','quote','start','end'}<=set(value):
            text=documents[value['document_id']]['text']
            assert 0<=value['start']<value['end']<=len(text)
            assert text[value['start']:value['end']]==value['quote']
            count+=1
        for item in value.values():
            count+=quotes(item,documents)
    elif isinstance(value,list):
        count+=sum(quotes(item,documents) for item in value)
    return count


def coverage_length(ranges,length):
    """Independent sorted range sweep; gap or out-of-bound receipts refuse."""
    end=0
    for a,b in sorted(ranges):
        assert 0<=a<b<=length and b-a<=16000
        assert a<=end,('Delivery gap',end,a)
        end=max(end,b)
    assert end==length,('Undelivered tail',end,length)
    return end


def review_counts(reviews):
    counts=Counter(r['verdict'] for r in reviews)
    categories=['supported','contradicted','insufficient_evidence']
    assert set(counts)<=set(categories)
    return {v:counts[v] for v in categories}


def main():
    jobs=read(RUN/'inputs/jobs.json')
    assert len(jobs)==22
    # Refuse before any label comparisons if one job remains unfinished.
    assert all((RUN/'jobs'/j['job_id']/'record.json').is_file() for j in jobs)
    preserved=read(RUN/'preservation-before.json')
    for name,expected in preserved.items():
        assert digest(ROOT/name)==expected,name
    summary=read(RUN/'summary.json')
    reviews=[]
    quote_count=0
    baseline_quotes=0
    source_characters=0
    receipt_count=0
    for job in jobs:
        own=RUN/'jobs'/job['job_id']
        record=read(own/'record.json')
        bundle=read(RUN/job['bundle'])
        documents={d['document_id']:d for d in bundle['documents']}
        readable={k:d for k,d in documents.items() if d.get('text')}
        ranges={k:[] for k in readable}
        receipts=list((own/'delivery').glob('*.json'))
        receipt_count+=len(receipts)
        for path in receipts:
            r=read(path)
            text=readable[r['document_id']]['text']
            assert r['job_id']==job['job_id']
            assert hashlib.sha256(text.encode()).hexdigest()==r['text_sha256']
            assert hashlib.sha256(text[r['start']:r['end']].encode()).hexdigest()==r['chunk_sha256']
            ranges[r['document_id']].append((r['start'],r['end']))
        for key,doc in readable.items():
            source_characters+=coverage_length(ranges[key],len(doc['text']))
        covered=record['review_delivery']
        assert covered['all_readable_text_delivered']
        assert covered['expected_characters']==covered['served_unique_characters']==sum(len(d['text']) for d in readable.values())
        assert set(record['reviewed_document_ids'])==set(readable)
        metadata=record['run_metadata']
        assert metadata['job_id']==job['job_id'] and metadata['role']==job['role']
        assert metadata['bundle_sha256']==digest(RUN/job['bundle'])
        assert metadata['protocol_sha256']==digest(RUN/'inputs/protocol.json')
        candidate=read(RUN/job['candidate']) if job['candidate'] else None
        assert metadata['candidate_sha256']==(digest(RUN/job['candidate']) if job['candidate'] else None)
        rawpath=own/'draft-history'/(metadata['raw_draft_sha256']+'.json')
        assert digest(rawpath)==metadata['raw_draft_sha256']
        normalized=normalize(read(rawpath),job,bundle,candidate,covered)
        # Finalization intentionally replaces optional worker-supplied metadata.
        # Compare every semantic/structural field while checking trusted metadata
        # explicitly above; preserve optional original metadata in raw history.
        assert {k:v for k,v in normalized.items() if k!='run_metadata'}=={k:v for k,v in record.items() if k!='run_metadata'},job['job_id']
        quote_count+=quotes(record,documents)
        if job['role']=='critic':
            reviews.extend(record['reviews'])
            claim_ids=[r['claim_id'] for r in record['reviews']]
            assert len(claim_ids)==len(set(claim_ids))==len(candidate['claims'])
            assert set(claim_ids)=={r['claim_id'] for r in candidate['claims']}
            baseline=read(ROOT/'research/runs/extraction-stability/20261025-v2/agents/A/records'/f'{job["accession"]}.json')
            baseline_quotes+=quotes(baseline,documents)
    counts=review_counts(reviews)
    assert len(reviews)==summary['natural_claims']['claims']
    assert counts==summary['natural_claims']['verdicts']
    assert sum(counts.values())==len(reviews)
    assert source_characters==summary['expected_readable_characters']==summary['delivered_readable_characters']
    assert summary['natural_data_accuracy']=='not_estimated'
    assert summary['natural_data_precision_recall']=='not_estimated'
    for name,expected in read(RUN/'record-hashes.json').items():
        assert digest(RUN/'jobs'/name/'record.json')==expected
    provenance=read(RUN/'provenance.json')
    for name,expected in provenance['output_sha256'].items():
        assert digest(RUN/name)==expected
    result={'status':'passed','semantic_accuracy':'not_estimated','finalized_jobs':22,
            'source_delivery_characters':source_characters,'delivery_receipts':receipt_count,
            'review_record_quote_checks':quote_count,'original_A_quote_checks':baseline_quotes,
            'original_A_semantic_accuracy':'not_estimated',
            'natural_claim_count':len(reviews),'natural_verdict_counts':dict(sorted(counts.items())),
            'preserved_manifest_files':len(preserved),'preserved_manifest_sha256':digest(RUN/'preservation-before.json'),
            'verification_code_sha256':digest(Path(__file__)),
            'report_code_sha256':digest(ROOT/'scripts/extraction_protocol/report_extraction_audit.py'),
            'limit':'Integrity, range coverage, schema, arithmetic and replay checks do not verify semantic judgments.'}
    payload=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    target=RUN/'verification.json'
    if target.exists():
        assert target.read_bytes()==payload
    else:
        target.write_bytes(payload)
    print(payload.decode())


if __name__=='__main__':
    main()
