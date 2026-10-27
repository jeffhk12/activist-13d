"""Compare revised extraction delivery/consistency with the preserved first run.

Inputs: 30 v2 records and receipts, identical source bundles, v1 metrics/cells.
Outputs: fixed metrics, before/after comparison, disagreements and HTML/Markdown.
Identity: exact label agreement=matching eligible cells/eligible cells; delivered
coverage=union of receipt intervals/source length. Neither estimates accuracy.
Tier: 1. Run project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8:
 scripts/extraction_protocol/report_stability_v2.py [--verify]
"""
import argparse
import hashlib
import json
from html import escape
from pathlib import Path

from compare_stability import csv_data, pct, summarize, table
from stability_v2_io import INPUT_NAMES, delivery, normalize_v2

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'
OLD=ROOT/'research/runs/extraction-stability/20261025-v1'
AGENTS=['A','B','C']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()


def compute():
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    categories=[c['id'] for c in json.loads((RUN/'inputs/categories-stability-v2.json').read_text())['categories']]
    records={}
    checks=[]
    hashes={}
    for row in inventory:
        raw=(RUN/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
        assert digest(raw)==row['input_sha256']
        assert raw==(OLD/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
        bundle=json.loads(raw)
        for agent in AGENTS:
            path=RUN/'agents'/agent/'records'/f'{row["accession"]}.json'
            if not path.is_file():
                raise FileNotFoundError(f'Pending {agent}/{row["case_id"]}')
            record=json.loads(path.read_text())
            covered=delivery(agent,row['case_id'],bundle)
            assert normalize_v2(record,bundle,covered)==record
            meta=record['run_metadata']
            assert meta['agent']==agent and meta['case_id']==row['case_id']
            assert meta['input_bundle_sha256']==row['input_sha256']
            assert meta['protocol_hashes']=={n:digest((RUN/'inputs'/n).read_bytes()) for n in INPUT_NAMES}
            records[(agent,row['case_id'])]=record
            hashes[str(path.relative_to(ROOT))]=digest(path.read_bytes())
            checks.append({'agent':agent,'case_id':row['case_id'],
              'review_status':record['extraction_status'],
              'all_readable_text_delivered':covered['all_readable_text_delivered'],
              'expected_characters':covered['expected_characters'],
              'served_unique_characters':covered['served_unique_characters'],
              'receipts':len(covered['receipts']),'schema_citations_and_coverage_parity':'passed'})
    metrics,cells,pairs,facts,filings=summarize(records,[r['case_id'] for r in inventory],categories)
    old=json.loads((OLD/'metrics.json').read_text())
    old_cells=json.loads((OLD/'cell-frequencies.json').read_text())
    old_full={c['case_id'] for c in old_cells if c['all_three_complete_readable_review']}
    matched_old=[c for c in old_cells if c['case_id'] in old_full]
    matched_new=[c for c in cells if c['case_id'] in old_full]
    common_full=old_full & {c['case_id'] for c in cells if c['all_three_complete_readable_review']}
    old_by={(c['case_id'],c['category']):c for c in old_cells}
    transitions=[]
    for c in cells:
        prior=old_by[(c['case_id'],c['category'])]
        for a in AGENTS:
            if prior[a]!=c[a]:
                transitions.append({'case_id':c['case_id'],'category':c['category'],'replicate_label':a,
                                    'v1_state':prior[a],'v2_state':c[a],
                                    'limit':'Different fresh context and revised rules; no accuracy/cause inference'})
    comparison={'same_discovery_source_bytes':True,'post_development_rule_refinement':True,
      'v1_threeway_equal':old['equal_threeway_intent_cells'],'v1_threeway_cells':old['eligible_threeway_intent_cells'],
      'v2_threeway_equal':metrics['equal_threeway_intent_cells'],'v2_threeway_cells':metrics['eligible_threeway_intent_cells'],
      'v1_complete_claim_records':sum(d.get('complete_readable_bundle',0) for d in old['case_statuses_by_agent'].values()),
      'v2_complete_claim_records':sum(d.get('complete_readable_bundle',0) for d in metrics['case_statuses_by_agent'].values()),
      'v2_mechanical_full_delivery_records':sum(c['all_readable_text_delivered'] for c in checks),
      'old_complete_case_ids':sorted(old_full),'old_complete_cells':len(matched_old),
      'old_complete_equal':sum(c['all_three_agree'] for c in matched_old),
      'v2_same_old_subset_cells':len(matched_new),'v2_same_old_subset_equal':sum(c['all_three_agree'] for c in matched_new),
      'v2_same_old_subset_all_review_complete':all(c['all_three_complete_readable_review'] for c in matched_new),
      'complete_in_both_versions_case_ids':sorted(common_full),
      'label_state_changes_of_270':len(transitions),
      'unavailable_accuracy_reference':True,'separate_effects_of_rule_and_context_change':'not_identified'}
    return inventory,records,metrics,cells,pairs,facts,filings,checks,hashes,comparison,transitions


def html_table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def make_report(inventory,records,metrics,cells,facts,checks,comparison):
    def percent(n,d):
        return pct(n/d if d else None)
    overview=[
      ['Finalized records',30,len(records)],
      ['Claimed complete readable-source reviews',comparison['v1_complete_claim_records'],comparison['v2_complete_claim_records']],
      ['Mechanical full-delivery checks','Not logged in v1',comparison['v2_mechanical_full_delivery_records']],
      ['All-ten three-way intent agreement',f'{comparison["v1_threeway_equal"]}/{comparison["v1_threeway_cells"]} ({percent(comparison["v1_threeway_equal"],comparison["v1_threeway_cells"])})',f'{comparison["v2_threeway_equal"]}/{comparison["v2_threeway_cells"]} ({percent(comparison["v2_threeway_equal"],comparison["v2_threeway_cells"])})'],
      ['Same original seven filings, three-way agreement',f'{comparison["old_complete_equal"]}/{comparison["old_complete_cells"]} ({percent(comparison["old_complete_equal"],comparison["old_complete_cells"])})',f'{comparison["v2_same_old_subset_equal"]}/{comparison["v2_same_old_subset_cells"]} ({percent(comparison["v2_same_old_subset_equal"],comparison["v2_same_old_subset_cells"])})']]
    pair_rows=[]
    for pair,d in metrics['per_pair'].items():
        j=d['positive_set_mean_jaccard_complete_nonempty_union']
        pair_rows.append([pair,f'{d["equal_intent_labels_complete"]}/{d["eligible_intent_labels_complete"]}',pct(d['intent_agreement_complete']),f'{j:.3f}' if j is not None else 'undefined',d['positive_set_complete_nonempty_union_cases'],d['both_complete_no_positive_intent_cases']])
    disagreed=[c for c in cells if c['all_three_agree'] is False]
    md=f'''# Revised 13D extraction: source coverage and repeatability

October 25, 2026. Same ten discovery filings, revised rules after development results. No human-reference accuracy or new investment results.

## What changed and what it establishes

Each filing now has a fresh context for each replicate: thirty bounded jobs rather than three contexts carrying all ten filings. Canonical text is delivered in logged ranges of at most 16,000 Unicode characters. Finalization checks for gaps and overlaps correctly, verifies exact source quotations, and refuses a complete-review claim without complete delivery. These are mechanical delivery checks and agent reading attestations, not proof of comprehension or complete material evidence.

The same nine intent categories have clarified boundaries. Routine subscriptions/financing closings are preserved as transaction facts rather than automatically treated as issuer-directed objectives. Requests to disclose existing voting/meeting correspondence are distinguished from requests to change governance rules. Specific objectives in missing referenced evidence remain category-specific uncertainty. Generic missing attachments do not automatically make every objective unknown.

These changes were specified after inspecting v1 disagreements. The same source bytes and ten model-exposed discovery cases are reused; this is a development retest. Both context design and rules change, so their separate effects are not identified. Higher agreement would not establish higher accuracy.

## Before and after

{table(['Measure','Original v1','Revised v2'],overview)}

All original-seven comparisons use the same case IDs: {', '.join(comparison['old_complete_case_ids'])}. All v2 reviews complete on that subset: {comparison['v2_same_old_subset_all_review_complete']}. The all-ten comparison also includes the original long-source failures; coverage and classification effects must be distinguished.

## Positive objective consistency

{table(['Pair','Equal labels / complete pairs','Agreement','Mean positive-set Jaccard','Nonempty union cases','Jointly empty positive cases'],pair_rows)}

Jaccard is shared positive categories divided by all categories called positive by either agent. Jointly empty sets have an undefined ratio and are counted separately. Overall not_stated agreement can otherwise obscure disagreement about positive objectives. Replicate comparisons share evidence/model family and are not independent statistical trials.

## Remaining disagreements

{table(['Case','Category','A','B','C'],[(c['case_id'],c['category'],c['A'],c['B'],c['C']) for c in disagreed]) if disagreed else 'No intent-state disagreements observed in this revised development run.'}

{comparison['label_state_changes_of_270']} of 270 replicate-label states differ from the original run. Labels and context design changed; these changes are not a count of corrected errors. Every initial and revised record remains preserved. No majority answer is ground truth.

## Meaning for the project

The engineering goal is a repeatable process that does not silently omit readable source text. The substantive goal remains whether measured filing information adds investment-ranking value beyond financial inputs. This experiment evaluates neither semantic truth nor downstream prediction. Transaction facts and uncertain intent remain separate model interpretations with citations; they are not validated predictors.

The next decision is whether the revised procedure is sufficiently stable and bounded to freeze for a separate reserved-case check. Keep the ten reserved validation sources unexposed until that decision; they were not supplied in either run. A later accuracy claim requires a defensible reference process. The earlier waiver of human-first review applies to these discovery cases; no human answers were invented or overwritten.

Bloomberg historical publication/mapping issues and the financial-versus-LLM ranking experiment remain separate pending work. No paid model API, new financial collection, return calculation or predictive fit was performed here.

## Evidence

metrics.json, before-after.json, label-cells.csv, pairwise-labels.csv, fact-pairs.csv, label-changes.csv, source-delivery-checks.json and record-hashes.json support the figures. The HTML report provides all agent records, current disagreements and source quotes. Missing/binary evidence and model/settings metadata limits remain explicit. Exact model ID, temperature and seeds are not exposed; these are same-configuration contexts, not a distinct-provider comparison.
'''
    details=[]
    for c in disagreed:
        fields=[]
        for agent in ['A','B','C']:
            f=records[(agent,c['case_id'])]['intent'][c['category']]
            ev=''.join('<blockquote>'+escape(e['quote'])+'</blockquote><small>'+escape(f'{e["document_id"]} [{e["start"]},{e["end"]})')+'</small>' for e in f['evidence'])
            fields.append(f'<h3>{agent}: {escape(f["status"])} — {escape(f["evidence_status"])}</h3><p>{escape(f["rationale"])}</p>{ev}')
        details.append('<details><summary>'+escape(c['case_id']+' — '+c['category'])+'</summary>'+''.join(fields)+'</details>')
    links=''.join('<li>'+r['case_id']+' '+r['accession']+': '+' · '.join(f'<a href="agents/{a}/records/{r["accession"]}.json">{a}</a>' for a in ['A','B','C'])+'</li>' for r in inventory)
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Revised 13D extraction: coverage and consistency</title><style>body{{font:17px/1.65 system-ui,sans-serif;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1120px;margin:30px auto;background:white;padding:28px}}h1{{font-size:30px;line-height:1.3}}h2{{font-size:23px;margin-top:30px}}a{{color:#155c99}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce3e9}}th{{background:#edf3f7}}.scroll{{overflow:auto}}details{{padding:14px;border:1px solid #ccd5de;margin:15px 0}}summary{{cursor:pointer;font-weight:600}}blockquote{{white-space:pre-wrap;background:#f4f6f8;border-left:4px solid #a3b4c2;padding:12px 18px;margin:12px 0}}small{{overflow-wrap:anywhere}}</style></head><body><main>
<p><a href="../../../../START-HERE.html">Project home</a> · Development retest · No accuracy reference</p><h1>Did the revised extraction procedure improve coverage and consistency?</h1>
<p>The same ten discovery sources were processed by three fresh contexts per filing. This revision adds logged text delivery, separates routine transaction facts from objectives, clarifies governance/disclosure boundaries, and preserves uncertainty for relevant missing evidence.</p>
<h2>Before and after</h2>{html_table(['Measure','Original v1','Revised v2'],overview)}
<p>Complete delivered ranges show which readable text was served; comprehension and full material evidence are not independently certified. The original-seven rows are the matched comparison. Both rules and context design changed after inspecting development results, so this does not isolate their effects or establish accuracy.</p>
<h2>Positive objective consistency</h2>{html_table(['Pair','Equal / complete labels','Agreement','Positive-set Jaccard','Nonempty union cases','Jointly empty cases'],pair_rows)}
<p>Jointly empty positive sets are separate from the mean Jaccard calculation. High not_stated agreement alone does not establish useful positive extraction.</p>
<h2>Remaining disagreements</h2>{''.join(details) or '<p>No intent-state disagreements observed in this revised run.</p>'}
<h2>Source-delivery records</h2>{html_table(['Case','Agent','Review status','Characters served / expected','Receipts'],[[c['case_id'],c['agent'],c['review_status'],f'{c["served_unique_characters"]:,} / {c["expected_characters"]:,}',c['receipts']] for c in checks])}
<h2>Interpretation and next decision</h2><p>Agreement measures repeatability, not truth or investment value. Keep the ten reserved validation sources unexposed until a separate frozen check is specified. Financial-data timing/mapping and downstream ranking remain pending. No human answers, paid API calls or new predictive fits were introduced.</p>
<h2>All revised records and evidence</h2><ul>{links}</ul><p><a href="REPORT.md">Full report and limitations</a> · <a href="before-after.json">Before/after metrics</a> · <a href="metrics.json">Revised metrics</a> · <a href="label-changes.csv">All label changes</a> · <a href="source-delivery-checks.json">Delivery checks</a> · <a href="../20261025-v1/index.html">Preserved original run</a></p></main></body></html>'''
    return md.encode(),html.encode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify',action='store_true')
    args=p.parse_args()
    inventory,records,metrics,cells,pairs,facts,filings,checks,hashes,comparison,changes=compute()
    md,html=make_report(inventory,records,metrics,cells,facts,checks,comparison)
    flat=[{k:r[k] for k in ['case_id','category','A','B','C','all_three_agree','all_three_complete_readable_review']} for r in cells]
    outputs={'metrics.json':enc(metrics),'before-after.json':enc(comparison),
       'label-cells.csv':csv_data(flat,list(flat[0])),'pairwise-labels.csv':csv_data(pairs,list(pairs[0])),
       'fact-pairs.csv':csv_data(facts,list(facts[0])),'filing-summary.json':enc(filings),
       'cell-frequencies.json':enc(cells),'source-delivery-checks.json':enc(checks),
       'record-hashes.json':enc(hashes),'label-changes.csv':csv_data(changes,['case_id','category','replicate_label','v1_state','v2_state','limit']),
       'transaction-facts.json':enc([{'case_id':case,'agent':agent,'facts':r['transaction_facts']} for (agent,case),r in records.items()]),
       'REPORT.md':md,'index.html':html}
    for name,raw in outputs.items():
        path=RUN/name
        if args.verify:
            assert path.read_bytes()==raw,name
        else:
            if path.exists() and path.read_bytes()!=raw:
                raise ValueError(f'Preserve differing output: {path}')
            path.write_bytes(raw)
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':
    main()
