"""Independently replay v3 case selection and receipt interval coverage.

Inputs: completed42-job archive, outcome-free metadata and original cached source.
Outputs: archive-verification.json. Identity: selected3 unique new groups follow
frozen seed/slots; raw/gzip copies match original hashes; sorted delivered ranges
cover [0,len(text)) without a gap. Tier:1 integrity. No semantic accuracy claim.
Run: project Python verify_extraction_v3_archive.py after completed full report.
"""
import gzip
import json
from pathlib import Path

from extraction_v3_io import ROOT, RUN, enc, read, sha
from extraction_v3_sampling import select_fresh


def main():
    jobs=read(RUN/'jobs.json')
    assert len(jobs)==42 and all((RUN/'jobs'/j['job_id']/'record.json').is_file() for j in jobs)
    assert (RUN/'fresh-release.json').exists()
    pilot=ROOT/'research/runs/ranking-llm-pilot/20261025-v2'
    old=read(pilot/'sample-manifest.json')['selection']
    chosen,trace=select_fresh(old['validation_reserved'],[r['accession'] for r in old['discovery']],
        excluded_groups=[r['connected_group'] for r in old['discovery']],
        excluded_issuers=[r['issuer'] for r in old['discovery']])
    expected=[{**r,'reserved_case_id':r['case_id'],'case_id':f'N{i:02}'} for i,r in enumerate(chosen,1)]
    selection=read(RUN/'selection.json')
    assert selection['selected']==expected and selection['trace']==trace
    assert selection['semantic_freeze_sha256']==sha((RUN/'freeze.json').read_bytes())
    assert len({r['connected_group'] for r in old['discovery']+chosen})==13
    pack=ROOT/'review/drafts/ranking-llm-pilot-20261025/validation-reserved'
    for row in expected:
        original=pack/'evidence'/f'{row["accession"]}.json.gz'
        copied=RUN/f'inputs/cases/{row["case_id"]}/bundle.json.gz'
        assert original.read_bytes()==copied.read_bytes()
        raw=pack/'raw'/f'{row["accession"]}.txt'
        assert sha(raw.read_bytes())==row['source_sha256']
    total=0
    receipts=0
    for job in jobs:
        record=read(RUN/'jobs'/job['job_id']/'record.json')
        metadata=record['run_metadata']
        assert metadata['job_id']==job['job_id'] and metadata['role']==job['role']
        assert metadata['case_id']==job['case_id'] and metadata['accession']==job['accession']
        path=RUN/job['bundle']
        bundle=json.loads(gzip.decompress(path.read_bytes())) if path.suffix=='.gz' else read(path)
        docs={d['document_id']:d for d in bundle['documents'] if d.get('text')}
        ranges={k:[] for k in docs}
        for receipt in (RUN/'jobs'/job['job_id']/'delivery').glob('*.json'):
            r=read(receipt)
            text=docs[r['document_id']]['text']
            assert r['job_id']==job['job_id'] and r['text_sha256']==sha(text.encode())
            assert r['chunk_sha256']==sha(text[r['start']:r['end']].encode())
            assert 0<=r['start']<r['end']<=len(text) and r['end']-r['start']<=16000
            ranges[r['document_id']].append((r['start'],r['end']))
            receipts+=1
        for did,doc in docs.items():
            cursor=0
            for start,end in sorted(ranges[did]):
                assert start<=cursor,('Gap',job['job_id'],did,cursor,start)
                cursor=max(cursor,end)
            assert cursor==len(doc['text'])
            total+=cursor
    summary=read(RUN/'summary.json')
    assert total==summary['integrity']['delivered_characters']
    assert receipts==summary['integrity']['delivery_receipts']
    result={'status':'passed','jobs':42,'replayed_new_case_selection':3,'unreleased_reserved_cases':7,
            'unique_old_plus_new_groups':13,'receipt_count':receipts,'independent_character_union':total,
            'new_raw_and_gzip_sources_unchanged':True,'semantic_accuracy':'not_estimated',
            'code_sha256':sha(Path(__file__).read_bytes())}
    target=RUN/'archive-verification.json'
    payload=enc(result)
    if target.exists():
        assert target.read_bytes()==payload
    else:
        target.write_bytes(payload)
    print(payload.decode())


if __name__=='__main__':
    main()
