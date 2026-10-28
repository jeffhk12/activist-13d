"""Deterministic control scoring and descriptive shared-rule reviewer comparison.

Inputs: construction keys, finalized model records, frozen candidate claims.
Outputs: counts, disagreements and empirical state frequencies (not calibrated
truth probabilities). Identity: construction matches/n; natural state counts/2;
eligible experimental label iff both source readers agree non-unknown and critic
supports that claim. Tier:1. Run via report_extraction_v3.py; no fitting/network.
"""
import re
from collections import Counter

STATES=('present','not_stated','cannot_determine')
VERDICTS=('supported','contradicted','insufficient_evidence')


def name_key(value):
    return re.sub('[^a-z0-9]','',value.lower())


def tuple_key(row,fields):
    return tuple(name_key(row[f]) if f in ['reporting_party','actor','security'] and isinstance(row[f],str) else row[f] for f in fields)


def control_critic(key,record):
    rows=record['reviews']
    observed={r['claim_id']:r for r in rows}
    if len(rows)!=len(key) or len(observed)!=len(key) or set(observed)!={r['claim_id'] for r in key}:
        raise ValueError('Each construction claim once')
    compared=[{**r,'observed':observed[r['claim_id']]['verdict'],
               'matches':observed[r['claim_id']]['verdict']==r['expected_verdict']} for r in key]
    return {'claims':len(key),'matched':sum(r['matches'] for r in compared),
            'changed':sum(r['condition']=='changed' for r in compared),
            'changed_flagged':sum(r['condition']=='changed' and r['observed']!='supported' for r in compared),
            'confusion':dict(Counter(r['expected_verdict']+' -> '+r['observed'] for r in compared)),
            'passed':all(r['matches'] for r in compared),'rows':compared}


def control_inventory(key,record):
    observed={r['accession']:r for r in record['cases']}
    if len(record['cases'])!=len(key) or set(observed)!={r['case_id'] for r in key}:
        raise ValueError('Each construction fixture once')
    results=[]
    for truth in key:
        row=observed[truth['case_id']]
        states=[{'category':k,'expected':v,'observed':row['intent'][k]['status']} for k,v in truth['expected_intent'].items()]
        funding=row['funding']['components']
        def matches(actual,expected):
            return tuple_key(actual,list(expected))==tuple_key(expected,list(expected))
        funding_matches=sum(any(matches(a,e) for a in funding) for e in truth['funding_requirements'])
        ownership_matches=sum(any(matches(a,e) for a in row['ownership']) for e in truth['ownership_requirements'])
        optional_violations=[]
        for expected in truth.get('optional_ownership_requirements',[]):
            same_actor=[a for a in row['ownership'] if name_key(a['reporting_party'])==name_key(expected['reporting_party'])]
            optional_violations.extend(a for a in same_actor if not matches(a,expected))
        ownership_extra=0
        if truth.get('ownership_exhaustive'):
            allowed=truth['ownership_requirements']+truth.get('optional_ownership_requirements',[])
            fields=list(allowed[0])
            allowance=Counter(tuple_key(a,fields) for a in allowed)
            actual=Counter(tuple_key(a,fields) for a in row['ownership'])
            ownership_extra=sum((actual-allowance).values())
        forbidden=sum(any(matches(a,e) for a in funding) for e in truth['forbidden_funding'])
        timing=sum(a['timing'] in truth['timing_forbidden'] for a in row['transaction_facts'])
        item={'case_id':truth['case_id'],'intent_cells':len(states),
              'intent_matches':sum(a['expected']==a['observed'] for a in states),
              'funding_required':len(truth['funding_requirements']),'funding_matches':funding_matches,
              'ownership_required':len(truth['ownership_requirements']),'ownership_matches':ownership_matches,
              'optional_ownership_violations':len(optional_violations),
              'ownership_extra_or_duplicate':ownership_extra,
              'forbidden_funding':forbidden,'forbidden_timing':timing,'states':states}
        item['passed']=(item['intent_cells']==item['intent_matches'] and item['funding_required']==funding_matches
                        and item['ownership_required']==ownership_matches and not forbidden and not timing and not optional_violations and not ownership_extra)
        results.append(item)
    return {'fixtures':len(results),'intent_cells':sum(r['intent_cells'] for r in results),
            'intent_matches':sum(r['intent_matches'] for r in results),
            'funding_required':sum(r['funding_required'] for r in results),'funding_matches':sum(r['funding_matches'] for r in results),
            'ownership_required':sum(r['ownership_required'] for r in results),'ownership_matches':sum(r['ownership_matches'] for r in results),
            'forbidden_funding':sum(r['forbidden_funding'] for r in results),
            'forbidden_timing':sum(r['forbidden_timing'] for r in results),
            'optional_ownership_violations':sum(r['optional_ownership_violations'] for r in results),
            'ownership_extra_or_duplicate':sum(r['ownership_extra_or_duplicate'] for r in results),
            'passed':all(r['passed'] for r in results),'rows':results}


def case_comparison(a,b,critic):
    reviews={r['claim_id']:r for r in critic['reviews']}
    result=[]
    for category,item in a['intent'].items():
        states=[item['status'],b['intent'][category]['status']]
        if any(s not in STATES for s in states):
            raise ValueError('Invalid label state')
        verdict=reviews['intent.'+category]['verdict']
        result.append({'category':category,'extractor':states[0],'blind':states[1],
                       'states_count':{s:states.count(s) for s in STATES},
                       'state_frequency':{s:states.count(s)/2 for s in STATES},
                       'critic':verdict,'agree':states[0]==states[1],
                       'eligible_experimental_label':states[0]==states[1] and states[0]!='cannot_determine' and verdict=='supported'})
    counts={v:sum(r['verdict']==v for r in critic['reviews']) for v in VERDICTS}
    if sum(counts.values())!=len(critic['reviews']):
        raise ValueError('Invalid verdict')
    owner_fields=['reporting_party','security','shares','percent_of_class','ownership_role','overlap']
    fund_fields=['actor','type','certainty','acquisition_link']
    def difference(first,second,fields):
        aa,bb=Counter(tuple_key(r,fields) for r in first),Counter(tuple_key(r,fields) for r in second)
        def entries(counter):
            return [{'tuple':list(k),'count':v} for k,v in sorted(counter.items(),key=lambda kv:str(kv[0]))]
        return {'only_extractor':entries(aa-bb),'only_blind':entries(bb-aa)}
    return {'accession':a['accession'],'intent':result,'intent_cells':len(result),
            'intent_agreement':sum(r['agree'] for r in result),
            'eligible_experimental_intents':sum(r['eligible_experimental_label'] for r in result),
            'critic_claims':len(critic['reviews']),'critic_verdicts':counts,
            'ownership_difference':difference(a['ownership'],b['ownership'],owner_fields),
            'funding_difference':difference(a['funding']['components'],b['funding']['components'],fund_fields),
            'transaction_rows_extractor':len(a['transaction_facts']),'transaction_rows_blind':len(b['transaction_facts']),
            'limit':'Descriptive string/tuple differences are not confirmed omissions; empirical two-reader frequencies are not truth probabilities. Transaction count excluded from modeling.'}
