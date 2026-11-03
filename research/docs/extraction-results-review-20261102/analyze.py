"""Compute the detailed extraction report from frozen local evidence.

Inputs: completed queue, 126 checkpoint outputs and 1,881 finalized role records.
Outputs: analysis.json and explorer.json; no labels, protocols or returns changed.
Identity: 667 = 13 earlier + 27 protected + 627 production; 5,643 = 627*9;
eligible = matching nonunknown states plus critic support. Issue counts overlap.
Tier: 1 descriptive report calculation. Run project Python this file; re-run
must reproduce byte-identical analysis and verify all recorded source hashes.
"""
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/Users/jefflu/Projects/activist-13d')
HERE = Path(__file__).resolve().parent
BASE = ROOT/'research/runs/extraction-batches/20261028-v1'
OVERVIEW = ROOT/'research/runs/extraction-overview/20261102-v1'
HASHES = {}


def read(path):
    blob = path.read_bytes()
    HASHES[str(path.relative_to(ROOT))] = hashlib.sha256(blob).hexdigest()
    return json.loads(blob)


def field(claim_id):
    return claim_id.split('.')[0]


def ratio(n, d):
    return None if d == 0 else round(100*n/d, 4)


def checks():
    assert ratio(1,4) == 25 and ratio(0,4) == 0 and ratio(0,0) is None
    assert field('funding.component.001') == 'funding'
    assert sum(Counter(['a','a','b']).values()) == 3
    assert statistics.median([10,20,90]) == 20


def write(name, value):
    content=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    path=HERE/name
    if path.exists():
        assert path.read_bytes()==content, f'Re-run changed {name}'
    else:
        path.write_bytes(content)


def main():
    checks()
    overview=read(OVERVIEW/'overview.json')
    flags_summary=read(OVERVIEW/'flag-inventory.json')
    register=read(OVERVIEW/'flag-register.json')
    queue=read(BASE/'queue.json')
    protocol=read(BASE/'protocol.json')
    prior=read(ROOT/'research/runs/extraction-revision/20261027-v3/summary.json')
    policy=read(ROOT/'research/runs/extraction-revision/20261027-v3/feature-use-policy.json')
    completion=read(BASE/'reporting-25-v1/batch-030/completion-verification.json')
    ranking=read(ROOT/'research/protocol/ranking-no-llm-v1.json')
    rows=queue['queue']
    assert len(rows)==627 and queue['panel_filings']==667==627+13+27
    assert Counter(row['workload'] for row in rows)==Counter({'regular':593,'long':34})
    inventory, cases, summaries, jobs = [], [], [], []
    record_metrics={role:{'funding_status':Counter(),'funding_types':Counter(),'funding_type_filings':Counter(),
                          'funding_certainty':Counter(),'funding_link':Counter(),'funding_components':0,
                          'ownership_rows':0,'transaction_rows':0,'reporting_party_rows':0,
                          'filings_with_evidence_gaps':0,'ownership_roles':Counter(),
                          'transaction_kinds':Counter(),'transaction_timing':Counter()}
                    for role in ['extractor','blind']}
    verdict_by_field=defaultdict(Counter)
    objective_pairs=Counter()
    timestamps=[]
    role_delivery=Counter()
    case_rows=[]
    for number in range(1,127):
        run=BASE/f'batch-{number:03}'
        inv=read(run/'inventory.json')
        inventory.extend(inv)
        comps=read(run/'case-comparisons.json')
        cases.extend(comps)
        summaries.append(read(run/'summary.json'))
        manifest=read(run/'jobs.json')
        jobs.extend(manifest)
        for job in manifest:
            record=read(run/f"jobs/{job['job_id']}/record.json")
            assert record['run_metadata']['job_id']==job['job_id']
            assert record['run_metadata']['common_rules_sha256']==protocol['common_rules_sha256']
            assert record['review_delivery']['all_readable_text_delivered']
            role_delivery[job['role']]+=1
            timestamps.append(record['run_metadata']['finalized_at_utc'])
            if job['role']=='critic':
                assert len(record['reviews'])==len({r['claim_id'] for r in record['reviews']})
                for review in record['reviews']:
                    verdict_by_field[field(review['claim_id'])][review['verdict']]+=1
                continue
            metric=record_metrics[job['role']]
            funding=record['funding']
            metric['funding_status'][funding['status']]+=1
            metric['funding_components']+=len(funding['components'])
            for component in funding['components']:
                metric['funding_types'][component['type']]+=1
                metric['funding_certainty'][component['certainty']]+=1
                metric['funding_link'][component['acquisition_link']]+=1
            metric['funding_type_filings'].update(set(c['type'] for c in funding['components']))
            metric['ownership_rows']+=len(record['ownership'])
            metric['ownership_roles'].update(row['ownership_role'] for row in record['ownership'])
            metric['transaction_rows']+=len(record['transaction_facts'])
            metric['transaction_kinds'].update(row['kind'] for row in record['transaction_facts'])
            metric['transaction_timing'].update(row['timing'] for row in record['transaction_facts'])
            metric['reporting_party_rows']+=len(record['reporting_parties'])
            metric['filings_with_evidence_gaps']+=bool(record['evidence_gaps'])
        for case in comps:
            source=next(item for item in inv if item['case_id']==case['case_id'])
            for cell in case['intent']:
                objective_pairs[(cell['extractor'],cell['blind'])]+=1
            case_rows.append({'case_id':case['case_id'],'accession':case['accession'],'issuer':case['issuer'],
                              'year':source['accepted_et'][:4],'accepted_et':source['accepted_et'],
                              'batch':number,'readable_characters':source['readable_characters'],
                              'eligible_positive':[cell['category'] for cell in case['intent'] if cell['eligible_experimental_label'] and cell['extractor']=='present'],
                              'unresolved':[cell['category'] for cell in case['intent'] if not cell['eligible_experimental_label']],
                              'decisions':case['intent'],'critic_flags':sum(case['critic_verdicts'].get(key,0) for key in ['contradicted','insufficient_evidence'])})
    assert len(cases)==len(inventory)==627 and len(jobs)==1881
    assert role_delivery==Counter({'extractor':627,'blind':627,'critic':627})
    assert sum(sum(values.values()) for values in verdict_by_field.values())==overview['critic_claims']==19069
    assert sum(objective_pairs.values())==627*9==5643
    assert sum(value for (a,b),value in objective_pairs.items() if a==b)==5581
    assert sum(s['exact_quote_entries'] for s in summaries)==119360
    positive_union=sum(value for (a,b),value in objective_pairs.items() if a=='present' or b=='present')
    chars=[row['readable_characters'] for row in inventory]
    sources={
        'accepted_et_min':min(row['accepted_et'] for row in inventory),
        'accepted_et_max':max(row['accepted_et'] for row in inventory),
        'filings_by_acceptance_year':dict(Counter(row['accepted_et'][:4] for row in inventory)),
        'source_forms':dict(Counter(row['source_form'] for row in inventory)),
        'unique_issuer_ciks':len({row['issuer'] for row in inventory}),
        'reporter_cik_union':len({cik for row in inventory for cik in row['reporter_ciks']}),
        'readable_characters_per_filing':{'minimum':min(chars),'median':statistics.median(chars),'maximum':max(chars),'total':sum(chars)},
        'canonical_documents':sum(row['canonical_documents'] for row in inventory),
        'filings_with_documents_without_text':sum(row['documents_without_text']>0 for row in inventory),
        'documents_without_text':sum(row['documents_without_text'] for row in inventory),
        'filings_with_unresolved_reference_detections':sum(row['unresolved_references']>0 for row in inventory),
        'unresolved_reference_detections':sum(row['unresolved_references'] for row in inventory),
        'workload_counts':queue['workload_counts'],
        'first_role_finalized_at_utc':min(timestamps),'last_role_finalized_at_utc':max(timestamps),
        'limits':'Reference detections and textless items are inventory warnings, not counts of material missing exhibits. Issuer CIKs are identifiers, not validated independent campaigns.'}
    outcomes={'pair_counts':{f'{a}|{b}':value for (a,b),value in sorted(objective_pairs.items())},
              'both_present':objective_pairs[('present','present')], 'either_reader_present':positive_union,
              'positive_set_overlap_percent':ratio(objective_pairs[('present','present')],positive_union),
              'all_cells_agreement_percent':overview['reader_agreement_percent'],
              'meaning':'Positive set overlap is both readers positive / at least one reader positive; it is not precision or recall.'}
    comparisons={'funding_tuple_difference_filings':sum(bool(case['funding_difference']['only_extractor'] or case['funding_difference']['only_blind']) for case in cases),
                 'ownership_tuple_difference_filings':sum(bool(case['ownership_difference']['only_extractor'] or case['ownership_difference']['only_blind']) for case in cases),
                 'transaction_row_count_difference_filings':sum(case['transaction_rows_extractor']!=case['transaction_rows_blind'] for case in cases),
                 'limit':'String/tuple or row-count differences are descriptive representation differences, not confirmed factual errors or omissions.'}
    by_field={name:{**dict(values),'total':sum(values.values()),'flagged':sum(v for k,v in values.items() if k!='supported')} for name,values in verdict_by_field.items()}
    selected=[('B001_01',None),('B118_02','transaction.001'),('B119_02','intent.board_representation'),
              ('B122_01','intent.governance_change'),('B124_02','funding.component.001'),('B120_05','ownership.024')]
    examples=[]
    for cid,claim in selected:
        case=next(row for row in case_rows if row['case_id']==cid)
        number=case['batch']
        record=read(BASE/f"batch-{number:03}/jobs/extractor_{cid.lower()}/record.json")
        item={'case':case,'claim_id':claim}
        if claim:
            flag=next(row for row in register if row['case_id']==cid and row['claim_id']==claim)
            item['flag']=flag
            if claim.startswith('intent.'):
                item['candidate']=record['intent'][claim.split('.',1)[1]]
            elif claim.startswith('funding.component.'):
                item['candidate']=record['funding']['components'][int(claim.split('.')[-1])-1]
            else:
                key='transaction_facts' if claim.startswith('transaction.') else 'ownership'
                item['candidate']=record[key][int(claim.split('.')[-1])-1]
        else:
            item['candidate']={'board':record['intent']['board_representation'],'funding':record['funding']}
        examples.append(item)
    result={'overview':{k:v for k,v in overview.items() if k!='input_sha256'},
            'flags':{k:v for k,v in flags_summary.items() if k!='input_sha256'},
            'sources':sources,'reader_field_records':record_metrics,'critic_by_field':by_field,
            'objective_pair_analysis':outcomes,'representation_differences':comparisons,
            'protocol':protocol,'prior_v3_summary':prior,'feature_use_policy':policy,
            'final_completion_receipt':completion,'ranking_protocol':ranking,'worked_examples':examples,
            'input_sha256':dict(sorted(HASHES.items()))}
    write('analysis.json',result)
    write('explorer.json',{'cases':case_rows,'flags':register})
    for relative,expected in HASHES.items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected,relative
    print(json.dumps({key:result[key] for key in ['sources','reader_field_records','critic_by_field','objective_pair_analysis','representation_differences']},indent=2))


if __name__=='__main__':
    main()
