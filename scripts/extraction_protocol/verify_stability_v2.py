"""Independently verify revised-run text coverage, citations and reported counts.

Inputs: final 30 records, source bundles, range receipts, metric CSV/JSON and
preservation manifests. Output: immutable verification JSON; no label judgment.
Identity: direct codepoint slice equals quote; independent byte occupancy of
Unicode index ranges covers every readable character; CSV labels reproduce sums.
Tier: 1. Run project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8.
"""
import csv
import hashlib
import json
from pathlib import Path

from lxml import html

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    metrics=json.loads((RUN/'metrics.json').read_text())
    before_after=json.loads((RUN/'before-after.json').read_text())
    record_count=0
    citation_count=0
    full_delivery=0
    total_expected=0
    total_served=0

    def citations(value,docs):
        nonlocal citation_count
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='evidence':
                    for e in item:
                        d=docs[e['document_id']]
                        assert d['text'][e['start']:e['end']]==e['quote']
                        assert hashlib.sha256(d['text'].encode()).hexdigest()==e['text_sha256']
                        citation_count+=1
                else:
                    citations(item,docs)
        elif isinstance(value,list):
            for item in value:
                citations(item,docs)

    for row in inventory:
        bundle=json.loads((RUN/'inputs/bundles'/f'{row["accession"]}.json').read_text())
        docs={d['document_id']:d for d in bundle['documents']}
        for agent in ['A','B','C']:
            record=json.loads((RUN/'agents'/agent/'records'/f'{row["accession"]}.json').read_text())
            record_count+=1
            citations(record,docs)
            masks={key:bytearray(len(d['text'])) for key,d in docs.items() if isinstance(d.get('text'),str) and d['text']}
            casepath=RUN/'agents'/agent/'cases'/row['case_id']
            for path in (casepath/'delivery').glob('*.json'):
                receipt=json.loads(path.read_text())
                d=docs[receipt['document_id']]
                start,end=receipt['start'],receipt['end']
                assert 0<=start<end<=len(d['text'])
                assert hashlib.sha256(d['text'][start:end].encode()).hexdigest()==receipt['chunk_sha256']
                assert receipt['text_sha256']==d['text_sha256']
                masks[receipt['document_id']][start:end]=b'\x01'*(end-start)
            expected=sum(len(mask) for mask in masks.values())
            served=sum(sum(mask) for mask in masks.values())
            complete=expected==served
            assert complete==record['review_delivery']['all_readable_text_delivered']
            assert served==record['review_delivery']['served_unique_characters']
            full_delivery+=complete
            total_expected+=expected
            total_served+=served
    assert record_count==30
    with (RUN/'label-cells.csv').open(newline='') as f:
        cells=list(csv.DictReader(f))
    assert len(cells)==90
    def equal(row):
        return row['A']==row['B']==row['C']
    assert sum(equal(r) for r in cells)==metrics['equal_threeway_intent_cells']
    pair_equal=sum(sum(r[a]==r[b] for a,b in [('A','B'),('A','C'),('B','C')]) for r in cells)
    assert pair_equal==metrics['equal_pairwise_intent_comparisons']
    subset=set(before_after['old_complete_case_ids'])
    matched=[r for r in cells if r['case_id'] in subset]
    assert len(matched)==63
    assert sum(equal(r) for r in matched)==before_after['v2_same_old_subset_equal']
    assert full_delivery==before_after['v2_mechanical_full_delivery_records']
    preserved=json.loads((RUN/'v1-preservation-before.json').read_text())
    for name,expected_hash in preserved.items():
        assert digest(ROOT/name)==expected_hash,name
    pilot=ROOT/'research/runs/ranking-llm-pilot/20261025-v2'
    for name,expected_hash in json.loads((pilot/'output-hashes.json').read_text()).items():
        assert digest(ROOT/name)==expected_hash,name
    protected=json.loads((pilot/'protected-assets-before.json').read_text())
    for name,expected_hash in protected.items():
        p=ROOT/name
        assert (digest(p) if p.is_file() else 'not_present_at_resolved_path')==expected_hash,name
    code_hashes=json.loads((RUN/'implementation-snapshot.json').read_text())
    for name,expected_hash in code_hashes.items():
        assert digest(ROOT/name)==expected_hash,name
    tree=html.fromstring((RUN/'index.html').read_bytes())
    links=tree.xpath('//a/@href')
    for href in links:
        if not href.startswith(('http:','https:','#')):
            assert (RUN/href).resolve().is_file(),href
    result={'finalized_records':record_count,'exact_citation_entries':citation_count,
      'independent_full_delivery_records':full_delivery,'expected_readable_unicode_characters':total_expected,
      'served_unique_unicode_characters':total_served,'csv_agreement_parity':'passed',
      'original_v1_files_preserved':len(preserved),'protected_paths_preserved':len(protected),
      'source_only_human_and_reserved_packs_unchanged':True,'implementation_hashes_unchanged':True,
      'report_links_checked':len(links),'semantic_accuracy':'not_established',
      'visual_browser_check':'unavailable: browser policy blocks file URLs'}
    raw=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode()
    path=RUN/'verification.json'
    if path.exists() and path.read_bytes()!=raw:
        raise ValueError('Preserve differing verification result')
    path.write_bytes(raw)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
