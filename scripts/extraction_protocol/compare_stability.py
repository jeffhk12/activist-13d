"""Compare three fixed extraction runs without choosing a correct agent.

Inputs: frozen ten-case inputs/protocol and thirty completed agent record files.
Outputs: stability metrics, cell/pair CSVs, disagreements and readable report.
Identity: agreement=equal eligible labels/eligible comparisons; Jaccard=|A∩B|/|A∪B|
with joint-empty union undefined. Citation integrity is not semantic accuracy.
Tier: 1. Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
 scripts/extraction_protocol/compare_stability.py [--verify]
"""
import argparse
import csv
import hashlib
import io
import itertools
import json
import sys
import unicodedata
from collections import Counter
from decimal import Decimal
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/extraction_protocol'))
from stability_io import normalize  # noqa: E402

RUN=ROOT/'research/runs/extraction-stability/20261025-v1'
AGENTS=['A','B','C']
PAIRS=list(itertools.combinations(AGENTS,2))
STATES=['present','not_stated','cannot_determine']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def agreement(labels):
    if len(labels)<2 or any(v is None for v in labels):
        return None
    return len(set(labels))==1


def jaccard(left,right):
    union=left|right
    return len(left&right)/len(union) if union else None


def mean_or_none(values):
    values=[x for x in values if x is not None]
    return sum(values)/len(values) if values else None


def fraction(n,d):
    return n/d if d else None


def name_key(name):
    return ' '.join(unicodedata.normalize('NFKC',name).casefold().split())


def names(record):
    return {name_key(r['name']) for r in record['reporting_parties']}


def ownership_keys(record):
    return {(name_key(r['reporting_party']),str(Decimal(str(r['percent_of_class'])).normalize()))
            for r in record['ownership'] if r['percent_of_class'] is not None}


def csv_data(rows,fields):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def summarize(records,case_ids,categories):
    cells=[]
    pairs=[]
    fact_pairs=[]
    filings=[]
    for case in case_ids:
        available={agent:records.get((agent,case)) for agent in AGENTS}
        jointly_complete=all(r and r['extraction_status']=='complete_readable_bundle' for r in available.values())
        vector_equal=all(available.values()) and all(agreement([available[a]['intent'][c]['status'] for a in AGENTS]) for c in categories)
        filings.append({'case_id':case,'all_three_records_present':all(available.values()),
                        'all_three_claim_complete_readable_review':jointly_complete,
                        'all_nine_labels_equal':bool(vector_equal),
                        'issuer_names':{a:r['issuer']['name'] if r else None for a,r in available.items()},
                        'positive_intents':{a:[c for c in categories if r['intent'][c]['status']=='present'] if r else None for a,r in available.items()}})
        for category in categories:
            labels={a:r['intent'][category]['status'] if r else None for a,r in available.items()}
            equal=agreement(list(labels.values()))
            counts=Counter(v for v in labels.values() if v is not None)
            cells.append({'case_id':case,'category':category,**labels,'all_three_agree':equal,
                          'all_three_complete_readable_review':jointly_complete,
                          'label_counts':dict(counts),
                          'model_run_frequencies_not_truth_probabilities':{s:counts[s]/3 for s in STATES}})
            for a,b in PAIRS:
                eligible=labels[a] is not None and labels[b] is not None
                pairs.append({'case_id':case,'category':category,'pair':a+b,
                              'label_left':labels[a],'label_right':labels[b],
                              'eligible':eligible,'agree':labels[a]==labels[b] if eligible else None,
                              'both_complete':bool(available[a] and available[b] and
                                available[a]['extraction_status']==available[b]['extraction_status']=='complete_readable_bundle')})
        for a,b in PAIRS:
            left,right=available[a],available[b]
            if left is None or right is None:
                continue
            positive_a={c for c in categories if left['intent'][c]['status']=='present'}
            positive_b={c for c in categories if right['intent'][c]['status']=='present'}
            n_a,n_b=names(left),names(right)
            o_a,o_b=ownership_keys(left),ownership_keys(right)
            f_a,f_b=set(left['funding']['types']),set(right['funding']['types'])
            fact_pairs.append({'case_id':case,'pair':a+b,
                               'both_complete':left['extraction_status']==right['extraction_status']=='complete_readable_bundle',
                               'positive_intents_jaccard':jaccard(positive_a,positive_b),
                               'both_no_positive_intents':not(positive_a|positive_b),
                               'reporting_names_jaccard':jaccard(n_a,n_b),
                               'reporting_names_exact':n_a==n_b,'both_no_reporting_names':not(n_a|n_b),
                               'ownership_person_percent_jaccard':jaccard(o_a,o_b),
                               'ownership_person_percent_exact':o_a==o_b,
                               'both_no_reported_percentages':not(o_a|o_b),
                               'issuer_name_exact':name_key(left['issuer']['name'] or '')==name_key(right['issuer']['name'] or ''),
                               'funding_status_agree':left['funding']['status']==right['funding']['status'],
                               'funding_types_exact':f_a==f_b,'funding_types_jaccard':jaccard(f_a,f_b)})
    eligible_cells=[c for c in cells if c['all_three_agree'] is not None]
    complete_cells=[c for c in eligible_cells if c['all_three_complete_readable_review']]
    eligible_pairs=[p for p in pairs if p['eligible']]
    complete_pairs=[p for p in eligible_pairs if p['both_complete']]
    category_summary={}
    for category in categories:
        subset=[c for c in eligible_cells if c['category']==category]
        category_summary[category]={'threeway_agree':sum(c['all_three_agree'] for c in subset),
           'eligible_filings':len(subset),'threeway_agreement':fraction(sum(c['all_three_agree'] for c in subset),len(subset)),
           'states_by_agent':{a:dict(Counter(c[a] for c in subset)) for a in AGENTS}}
    pair_summary={}
    for a,b in PAIRS:
        subset=[p for p in eligible_pairs if p['pair']==a+b]
        fp=[p for p in fact_pairs if p['pair']==a+b]
        full=[p for p in subset if p['both_complete']]
        fp_full=[p for p in fp if p['both_complete']]
        pair_summary[a+b]={'equal_intent_labels':sum(p['agree'] for p in subset),'eligible_intent_labels':len(subset),
          'intent_agreement':fraction(sum(p['agree'] for p in subset),len(subset)),
          'equal_intent_labels_complete':sum(p['agree'] for p in full),'eligible_intent_labels_complete':len(full),
          'intent_agreement_complete':fraction(sum(p['agree'] for p in full),len(full)),
          'positive_set_mean_jaccard_complete_nonempty_union':mean_or_none([p['positive_intents_jaccard'] for p in fp_full]),
          'positive_set_complete_nonempty_union_cases':sum(p['positive_intents_jaccard'] is not None for p in fp_full),
          'both_complete_no_positive_intent_cases':sum(p['both_no_positive_intents'] for p in fp_full),
          'positive_set_mean_jaccard_nonempty_union':mean_or_none([p['positive_intents_jaccard'] for p in fp]),
          'positive_set_nonempty_union_cases':sum(p['positive_intents_jaccard'] is not None for p in fp),
          'both_no_positive_intent_cases':sum(p['both_no_positive_intents'] for p in fp),
          'reporting_name_set_mean_jaccard_nonempty_union':mean_or_none([p['reporting_names_jaccard'] for p in fp]),
          'reporting_name_set_exact_cases':sum(p['reporting_names_exact'] for p in fp),
          'ownership_person_percent_mean_jaccard_nonempty_union':mean_or_none([p['ownership_person_percent_jaccard'] for p in fp]),
          'ownership_person_percent_exact_cases':sum(p['ownership_person_percent_exact'] for p in fp),
          'both_no_reported_percentages_cases':sum(p['both_no_reported_percentages'] for p in fp),
          'funding_status_equal_cases':sum(p['funding_status_agree'] for p in fp),
          'funding_types_exact_cases':sum(p['funding_types_exact'] for p in fp),'eligible_fact_case_pairs':len(fp)}
    metrics={'expected_filings':len(case_ids),'expected_agent_records':len(case_ids)*3,'records_present':len(records),
      'expected_threeway_intent_cells':len(case_ids)*len(categories),
      'eligible_threeway_intent_cells':len(eligible_cells),'equal_threeway_intent_cells':sum(c['all_three_agree'] for c in eligible_cells),
      'threeway_agreement_all_available':fraction(sum(c['all_three_agree'] for c in eligible_cells),len(eligible_cells)),
      'jointly_complete_review_cells':len(complete_cells),'equal_jointly_complete_review_cells':sum(c['all_three_agree'] for c in complete_cells),
      'threeway_agreement_jointly_complete_reviews':fraction(sum(c['all_three_agree'] for c in complete_cells),len(complete_cells)),
      'eligible_pairwise_intent_comparisons':len(eligible_pairs),'equal_pairwise_intent_comparisons':sum(p['agree'] for p in eligible_pairs),
      'pooled_pairwise_agreement':fraction(sum(p['agree'] for p in eligible_pairs),len(eligible_pairs)),
      'pairwise_complete_review_comparisons':len(complete_pairs),
      'equal_pairwise_complete_review_comparisons':sum(p['agree'] for p in complete_pairs),
      'pairwise_agreement_complete_reviews':fraction(sum(p['agree'] for p in complete_pairs),len(complete_pairs)),
      'all_nine_labels_equal_filings':sum(r['all_nine_labels_equal'] for r in filings),
      'jointly_complete_review_filings':sum(r['all_three_claim_complete_readable_review'] for r in filings),
      'all_nine_labels_equal_jointly_complete_filings':sum(r['all_nine_labels_equal'] and r['all_three_claim_complete_readable_review'] for r in filings),
      'case_statuses_by_agent':{a:dict(Counter(r['extraction_status'] for (agent,_),r in records.items() if agent==a)) for a in AGENTS},
      'state_counts_all_agents':dict(Counter(c[a] for c in eligible_cells for a in AGENTS)),
      'per_category':category_summary,'per_pair':pair_summary,
      'limits':['Agent attested complete reading is not independently certified',
                'No human reference or extraction-accuracy estimate',
                'Frequencies of model labels are not truth probabilities',
                'Same configured model contexts, no distinct-provider or independence claim',
                'No downstream ranking/model fitting or investment returns evaluated']}
    return metrics,cells,pairs,fact_pairs,filings


def collect():
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    categories=[c['id'] for c in json.loads((RUN/'inputs/categories-v1.yaml').read_text())['categories']]
    records={}
    validation=[]
    hashes={}
    expected_hashes={n:sha((RUN/'inputs'/n).read_bytes()) for n in ['extraction-stability-v1.json','extraction-stability-schema-v1.json','extraction-stability-prompt-v1.md','categories-v1.yaml']}
    for item in inventory:
        raw=(RUN/'inputs/bundles'/f'{item["accession"]}.json').read_bytes()
        assert sha(raw)==item['input_sha256']
        bundle=json.loads(raw)
        for agent in AGENTS:
            path=RUN/'agents'/agent/'records'/f'{item["accession"]}.json'
            if not path.exists():
                raise FileNotFoundError(f'Awaiting record {agent}/{item["case_id"]}')
            data=path.read_bytes()
            record=json.loads(data)
            try:
                checked=normalize(record,bundle)
                assert checked==record
                assert record['run_metadata']['agent']==agent
                assert record['run_metadata']['input_bundle_sha256']==item['input_sha256']
                assert record['run_metadata']['protocol_hashes']==expected_hashes
                assert record['run_metadata']['raw_source_sha256']==item['source_sha256']
            except Exception as exc:
                validation.append({'agent':agent,'case_id':item['case_id'],'valid':False,'reason':str(exc)})
                continue
            records[(agent,item['case_id'])]=record
            hashes[str(path.relative_to(ROOT))]=sha(data)
            count=0
            def walk(value):
                nonlocal count
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k=='evidence':
                            count+=len(v)
                        else:
                            walk(v)
                elif isinstance(value,list):
                    for v in value:
                        walk(v)
            walk(record)
            validation.append({'agent':agent,'case_id':item['case_id'],'valid':True,
                               'exact_evidence_entries':count,'semantic_accuracy':'not_evaluated'})
    result=summarize(records,[r['case_id'] for r in inventory],categories)
    return inventory,categories,records,validation,hashes,result


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',
      *['| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in r)+' |' for r in rows]])


def pct(value):
    return f'{value*100:.1f}%' if value is not None else 'undefined'


def render(inventory,categories,records,validation,metrics,cells,fact_pairs,filings):
    disagree=[c for c in cells if c['all_three_agree'] is False]
    title='How consistent are three agents reading the same ten 13D filings?'
    md=f'''# {title}

October 25, 2026. Model-only development stability experiment. Human review was explicitly skipped at Jeff's request.

## What we found

Three separate agent contexts used the same inputs, extraction instructions, schema and nine intent definitions. On filings where all three agents claim complete readable-source review, they agreed on **{metrics['equal_jointly_complete_review_cells']}/{metrics['jointly_complete_review_cells']} filing-by-intent decisions ({pct(metrics['threeway_agreement_jointly_complete_reviews'])})**. These are the comparable full-review cases. Complete reading remains an agent attestation, not an independent comprehension check. This measures repeatability, not accuracy or investment value.

**{metrics['records_present']}/30 records** passed the structural, provenance and exact-citation checks. Including incomplete reviews, three-way agreement is **{metrics['equal_threeway_intent_cells']}/{metrics['eligible_threeway_intent_cells']} cells ({pct(metrics['threeway_agreement_all_available'])})**. The nine-label vector was identical on **{metrics['all_nine_labels_equal_filings']}/{metrics['expected_filings']} filings**. There are **{len(disagree)} cells with label disagreement**, some potentially reflecting source-coverage differences. The checker verifies claimed document coverage and citation matching, not actual complete understanding.

Pairwise agreement among complete-review pairs is **{metrics['equal_pairwise_complete_review_comparisons']}/{metrics['pairwise_complete_review_comparisons']} ({pct(metrics['pairwise_agreement_complete_reviews'])})**. Across all available pairs it is **{metrics['equal_pairwise_intent_comparisons']}/{metrics['eligible_pairwise_intent_comparisons']} ({pct(metrics['pooled_pairwise_agreement'])})**. The three comparisons per cell are dependent and are not 270 independent trials.

## Pairwise consistency and positive objectives

{table(['Agent pair','Equal labels / eligible, complete reviews','Agreement','Mean positive-set Jaccard, complete reviews','Nonempty positive union cases','Both no positive cases'],[(p,f'{v["equal_intent_labels_complete"]}/{v["eligible_intent_labels_complete"]}',pct(v['intent_agreement_complete']),f'{v["positive_set_mean_jaccard_complete_nonempty_union"]:.3f}' if v['positive_set_mean_jaccard_complete_nonempty_union'] is not None else 'undefined',v['positive_set_complete_nonempty_union_cases'],v['both_complete_no_positive_intent_cases']) for p,v in metrics['per_pair'].items()])}

Jaccard is the number of shared positive objective categories divided by the number called positive by either agent. When both agents call no objectives positive, its denominator is zero; those cases are reported separately rather than counted as perfect positive agreement. A high overall rate can otherwise be driven by many not_stated labels.

## By intent category

{table(['Category','All-three equal / filings','Agreement','A present / not stated / uncertain','B present / not stated / uncertain','C present / not stated / uncertain'],[(c,f'{d["threeway_agree"]}/{d["eligible_filings"]}',pct(d['threeway_agreement']),*[ '/'.join(str(d['states_by_agent'][a].get(s,0)) for s in STATES) for a in AGENTS]) for c,d in metrics['per_category'].items()])}

## Reporting names, ownership and funding

{table(['Pair','Exact reporting-name sets / cases','Exact person/percentage sets / cases','Funding status equal / cases','Funding type sets equal / cases'],[(p,f'{d["reporting_name_set_exact_cases"]}/{d["eligible_fact_case_pairs"]}',f'{d["ownership_person_percent_exact_cases"]}/{d["eligible_fact_case_pairs"]}',f'{d["funding_status_equal_cases"]}/{d["eligible_fact_case_pairs"]}',f'{d["funding_types_exact_cases"]}/{d["eligible_fact_case_pairs"]}') for p,d in metrics['per_pair'].items()])}

Names are compared after Unicode NFKC, case folding and whitespace collapse only. Punctuation and party identities remain separate; a string difference need not be an economic disagreement. Ownership compares normalized person-name/percentage pairs, excluding null percentages; separate reported parties are never summed. Empty sets are explicitly flagged in fact-pairs.csv. Narrative summaries and share descriptions are preserved, not assigned an invented semantic similarity score.

## Every filing

{table(['Case','Accession','All nine labels match','All three claim complete source review'],[(f['case_id'],next(i['accession'] for i in inventory if i['case_id']==f['case_id']),f['all_nine_labels_equal'],f['all_three_claim_complete_readable_review']) for f in filings])}

## Disagreements to inspect

{table(['Case','Category','A','B','C'],[(c['case_id'],c['category'],c['A'],c['B'],c['C']) for c in disagree]) if disagree else 'No category-state disagreements observed on the compared cells.'}

The HTML report includes each disagreeing agent's rationale and source quotations without selecting a correct answer. Agreement itself cannot detect a shared mistake.

## Source-review completion by agent

{table(['Agent','Complete readable-bundle reviews','Incomplete source reviews'],[(a,metrics['case_statuses_by_agent'][a].get('complete_readable_bundle',0),metrics['case_statuses_by_agent'][a].get('incomplete_source_review',0)) for a in AGENTS])}

Long exhibits can exceed an agent's context budget. Incomplete records retain their reported evidence gaps and uncertain states. They count as attempted extractions, not completed source reviews. The experiment is preserved without replacing an inconvenient record or silently treating missing reading as absent intent. Source completeness problems are a separate result from label consistency on comparable reviews.

## Meaning, limits and next decision

The human-first requirement was waived for these ten discovery filings only. Their extraction answers are now model-exposed development evidence; no human reference accuracy, population reliability, calibrated truth probability, or final investment holdout is claimed. The ten reserved validation filings were not supplied to the agents. Original source-only human pages and blank answers remain unchanged; model outputs live in this separate run.

These are separate contexts using the inherited configured model. Exact model identifier, temperature and seeds were not exposed by the runner and remain unavailable. Isolation is procedural in a shared workspace, not a security boundary or independent-model claim. Data contain long exhibits, unreadable attachments and external-reference limitations. Readable-document coverage and exact citations do not certify completeness of material evidence.

Next inspect the disagreement cells and source-evidence gaps to decide whether definitions need a new version. Preserve all initial outputs. Any rule revision should receive a new prompt/protocol and new run; this first comparison must remain visible. A later human adjudication can investigate correctness, but these model-exposed discovery cases are not a fresh blind accuracy test. Stability alone does not authorize scaling unvalidated labels into the ranking model.

## Evidence

metrics.json, label-cells.csv, pairwise-labels.csv, fact-pairs.csv, cell-frequencies.json and citation-checks.json contain the calculations and denominators. Raw drafts, hash-named draft history, finalized records, source bundles, fixed instructions and protocol hashes are preserved. No paid APIs, external research, return recomputation, predictive fitting or majority-vote ground truth were used.
'''
    # Escape Markdown into a readable full report plus expanded source-backed conflicts.
    def basic_html(text):
        out=[]
        lines=text.splitlines()
        i=0
        while i<len(lines):
            line=lines[i]
            if line.startswith('| '):
                block=[]
                while i<len(lines) and lines[i].startswith('| '):
                    block.append(lines[i])
                    i+=1
                out.append('<div class="scroll"><table>')
                for j,row in enumerate(block):
                    if j==1:
                        continue
                    tag='th' if j==0 else 'td'
                    out.append('<tr>'+''.join(f'<{tag}>{escape(v.strip())}</{tag}>' for v in row.strip('|').split('|'))+'</tr>')
                out.append('</table></div>')
                continue
            if line.startswith('# '):
                out.append('<h1>'+escape(line[2:])+'</h1>')
            elif line.startswith('## '):
                out.append('<h2>'+escape(line[3:])+'</h2>')
            elif line.strip():
                cleaned=escape(line)
                while '**' in cleaned:
                    cleaned=cleaned.replace('**','<strong>',1).replace('**','</strong>',1)
                out.append('<p>'+cleaned+'</p>')
            i+=1
        return ''.join(out)
    detail=[]
    for cell in disagree:
        case=cell['case_id']
        category=cell['category']
        items=[]
        for agent in AGENTS:
            field=records[(agent,case)]['intent'][category]
            ev=''.join('<blockquote>'+escape(e['quote'])+'</blockquote><small>'+escape(f'{e["document_id"]} [{e["start"]},{e["end"]}) · {e["text_sha256"]}')+'</small>' for e in field['evidence'])
            items.append(f'<h3>Agent {agent}: {escape(field["status"])}</h3><p>{escape(field["rationale"])}</p>{ev or "<p>No cited positive passage. See rationale and reviewed-document attestation.</p>"}')
        detail.append(f'<details><summary>{escape(case+" — "+category)}</summary>{"".join(items)}</details>')
    coverage_details=[]
    for r in inventory:
        sections=[]
        for agent in AGENTS:
            record=records.get((agent,r['case_id']))
            if record:
                sections.append(f'<h3>Agent {agent}: {escape(record["extraction_status"])}</h3><p>Reviewed IDs claimed: {escape(", ".join(record["reviewed_document_ids"]))}</p><ul>'+''.join('<li>'+escape(g)+'</li>' for g in record['evidence_gaps'])+'</ul>')
        coverage_details.append('<details><summary>'+escape(r['case_id']+' — source review and gaps')+'</summary>'+''.join(sections)+'</details>')
    recordlinks=''.join(f'<li>{r["case_id"]} {r["accession"]}: '+ ' · '.join(f'<a href="agents/{a}/records/{r["accession"]}.json">Agent {a}</a>' for a in AGENTS)+'</li>' for r in inventory)
    html=('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      f'<title>{escape(title)}</title><style>body{{font:17px/1.65 system-ui,sans-serif;background:#f4f6f8;color:#203448;margin:0}}main{{max-width:1150px;margin:30px auto;padding:28px;background:white}}h1{{font-size:30px;line-height:1.25}}h2{{font-size:23px;margin-top:30px}}h3{{font-size:19px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}}th{{background:#edf3f7}}.scroll{{overflow:auto}}a{{color:#155c99}}details{{padding:14px;border:1px solid #ccd5de;margin:15px 0}}summary{{cursor:pointer;font-weight:600}}blockquote{{white-space:pre-wrap;border-left:4px solid #9aafbf;padding:10px 18px;margin:12px 0;background:#f4f6f8}}small{{overflow-wrap:anywhere}}</style></head><body><main>'
      '<p><a href="../../../../START-HERE.html">Project home</a> · AI interpretations only · No human reference accuracy</p>'+
      basic_html(md)+'<h2>Source review and evidence gaps</h2>'+''.join(coverage_details)+'<h2>Source-backed disagreement detail</h2>'+''.join(detail)+
      '<h2>Preserved agent records</h2><ul>'+recordlinks+'</ul><p><a href="metrics.json">Machine metrics</a> · <a href="label-cells.csv">Label cells</a> · <a href="fact-pairs.csv">Fact pairs</a> · <a href="citation-checks.json">Citation checks</a> · <a href="REPORT.md">Markdown report</a></p></main></body></html>')
    return md.encode(),html.encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    inventory,categories,records,validation,hashes,result=collect()
    metrics,cells,pairs,fact_pairs,filings=result
    md,html=render(inventory,categories,records,validation,metrics,cells,fact_pairs,filings)
    def enc(value):
        return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    cell_flat=[{k:c[k] for k in ['case_id','category','A','B','C','all_three_agree','all_three_complete_readable_review']} for c in cells]
    outputs={'metrics.json':enc(metrics),'label-cells.csv':csv_data(cell_flat,list(cell_flat[0])),
       'pairwise-labels.csv':csv_data(pairs,list(pairs[0])),
       'fact-pairs.csv':csv_data(fact_pairs,list(fact_pairs[0])) if fact_pairs else b'',
       'cell-frequencies.json':enc(cells),'filing-summary.json':enc(filings),
       'citation-checks.json':enc(validation),'record-hashes.json':enc(hashes),
       'REPORT.md':md,'index.html':html}
    for name,raw in outputs.items():
        path=RUN/name
        if args.verify:
            assert path.read_bytes()==raw,name
        else:
            if path.exists() and path.read_bytes()!=raw:
                raise FileExistsError(f'Preserve differing output: {path}')
            path.write_bytes(raw)
    print(json.dumps({k:metrics[k] for k in ['records_present','equal_threeway_intent_cells','eligible_threeway_intent_cells',
                      'threeway_agreement_all_available','equal_pairwise_intent_comparisons','eligible_pairwise_intent_comparisons',
                      'all_nine_labels_equal_filings']},indent=2))


if __name__=='__main__':
    main()
