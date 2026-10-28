"""Explain the completed ten-filing extraction without new interpretation calls.

Inputs: thirty frozen v2 model records, canonical bundles, categories and hashes.
Outputs: readable case report, empirical category-state counts, issue inventory,
source/protocol checks and replay hashes. Identity: three state counts sum to 3;
every cited quote equals the canonical Unicode slice. No majority truth label.
Tier: 1. Development review only; no new filings, APIs, targets or model fitting.
Run: project Python scripts/extraction_protocol/review_discovery_batch.py [--verify].
"""
import argparse
import hashlib
import json
from html import escape
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'research/runs/extraction-stability/20261025-v2'
RUN=ROOT/'research/runs/extraction-discovery-review/20261027-v1'
STATES=('present','not_stated','cannot_determine')
AGENTS=('A','B','C')


def state_counts(values):
    values=list(values)
    if len(values)!=3 or any(v not in STATES for v in values):
        raise ValueError('Exactly three valid category states required')
    return {s:values.count(s) for s in STATES}


def same_type_sets(values):
    values=[tuple(sorted(set(v))) for v in values]
    return len(set(values))==1


def cited_entries(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='evidence':
                yield from item
            else:
                yield from cited_entries(item)
    elif isinstance(value,list):
        for item in value:
            yield from cited_entries(item)


def validate_quotes(record,bundle):
    docs={d['document_id']:d for d in bundle['documents']}
    count=0
    for citation in cited_entries(record):
        doc=docs[citation['document_id']]
        if doc['text'][citation['start']:citation['end']]!=citation['quote']:
            raise ValueError('Citation does not equal canonical text')
        if hashlib.sha256(doc['text'].encode()).hexdigest()!=citation['text_sha256']:
            raise ValueError('Canonical text hash changed')
        count+=1
    return count


def encode(value):
    return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()


def build():
    sources={}
    def load(path):
        raw=path.read_bytes()
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    inventory=load(SOURCE/'inputs/inventory.json')
    categories=load(SOURCE/'inputs/categories-stability-v2.json')['categories']
    schema=load(SOURCE/'inputs/extraction-stability-schema-v2.json')
    validator=Draft202012Validator(schema)
    original_hashes=load(SOURCE/'record-hashes.json')
    labels={c['id']:c['name'] for c in categories}
    model_rows=[]
    all_records={}
    citations=0
    for row in inventory:
        accession,case=row['accession'],row['case_id']
        bundle_path=SOURCE/'inputs/bundles'/f'{accession}.json'
        bundle=load(bundle_path)
        assert sources[str(bundle_path.relative_to(ROOT))]==row['input_sha256']
        records={}
        for agent in AGENTS:
            path=SOURCE/'agents'/agent/'records'/f'{accession}.json'
            record=load(path)
            assert sources[str(path.relative_to(ROOT))]==original_hashes[str(path.relative_to(ROOT))]
            validator.validate(record)
            assert record['accession']==accession
            citations+=validate_quotes(record,bundle)
            records[agent]=record
        all_records[case]={'records':records,'bundle':bundle}
        intents={}
        for category in labels:
            agent_states={a:d['intent'][category]['status'] for a,d in records.items()}
            counts=state_counts(agent_states.values())
            intents[category]={'agent_states':agent_states,'counts':counts,
                               'present_fraction_of_runs':counts['present']/3,
                               'cannot_determine_fraction_of_runs':counts['cannot_determine']/3,
                               'all_three_agree':max(counts.values())==3}
        model_rows.append({'case_id':case,'accession':accession,'filing_date':bundle['filing_date'],
                           'issuer_names':{a:d['issuer']['name'] for a,d in records.items()},
                           'intent':intents,
                           'funding_types_by_agent':{a:d['funding']['types'] for a,d in records.items()},
                           'funding_status_by_agent':{a:d['funding']['status'] for a,d in records.items()},
                           'funding_type_sets_identical':same_type_sets(d['funding']['types'] for d in records.values()),
                           'ownership_row_counts':{a:len(d['ownership']) for a,d in records.items()},
                           'transaction_fact_counts':{a:len(d['transaction_facts']) for a,d in records.items()},
                           'limitation':'Empirical same-model repeat frequencies, not truth probabilities or validated investment inputs.'})
    category_rows=[]
    for category,label in labels.items():
        rows=[r['intent'][category] for r in model_rows]
        category_rows.append({'category':category,'name':label,
                              'unanimous_present_filings':sum(r['counts']['present']==3 for r in rows),
                              'any_present_filings':sum(r['counts']['present']>0 for r in rows),
                              'unanimous_not_stated_filings':sum(r['counts']['not_stated']==3 for r in rows),
                              'any_cannot_determine_filings':sum(r['counts']['cannot_determine']>0 for r in rows),
                              'disagreement_filings':sum(not r['all_three_agree'] for r in rows)})
    summary={'filings':len(model_rows),'model_records':3*len(model_rows),'exact_quote_entries':citations,
             'intent_cells':9*len(model_rows),
             'unanimous_intent_cells':sum(v['all_three_agree'] for r in model_rows for v in r['intent'].values()),
             'funding_type_disagreement_cases':[r['case_id'] for r in model_rows if not r['funding_type_sets_identical']],
             'ownership_row_count_difference_cases':[r['case_id'] for r in model_rows if len(set(r['ownership_row_counts'].values()))>1],
             'transaction_fact_count_difference_cases':[r['case_id'] for r in model_rows if len(set(r['transaction_fact_counts'].values()))>1],
             'categories':category_rows,'new_extraction_calls':0,'new_filings_read':0,
             'reserved_filings_supplied':False,'return_targets_read':False,'accuracy_established':False}
    assert summary['filings']==10 and summary['model_records']==30
    assert summary['unanimous_intent_cells']==89 and citations==700

    def quote_block(evidence):
        return ''.join(f'<blockquote>{escape(e["quote"])}<br><small>{escape(e["document_id"])} · Unicode [{e["start"]}, {e["end"]})</small></blockquote>' for e in evidence)
    table_rows=[]
    cards=[]
    for row in model_rows:
        case=row['case_id']
        data=all_records[case]
        records=data['records']
        unanimous=[labels[k] for k,v in row['intent'].items() if v['counts']['present']==3]
        uncertain=[labels[k] for k,v in row['intent'].items() if v['counts']['cannot_determine']]
        disputed=[labels[k] for k,v in row['intent'].items() if not v['all_three_agree']]
        table_rows.append(f'<tr><th><a href="#{case}">{case} · {escape(row["issuer_names"]["A"])}</a></th><td>{row["filing_date"]}</td><td>{escape("; ".join(unanimous) or "No qualifying objective labelled present")}</td><td>{escape("; ".join(uncertain) or "None in nine categories")}</td><td>{escape("; ".join(disputed) or "All nine states agree")}</td></tr>')
        intent_rows=''.join(f'<tr><th>{escape(labels[k])}</th>'+''.join(f'<td>{escape(v["agent_states"][a])}</td>' for a in AGENTS)+f'<td>{v["counts"]["present"]}/3</td><td>{v["counts"]["cannot_determine"]}/3</td></tr>' for k,v in row['intent'].items())
        agent_sections=[]
        for agent,d in records.items():
            people=', '.join(p['name'] for p in d['reporting_parties'])
            ownership_rows=''.join(f'<tr><td>{escape(o["reporting_party"])}</td><td>{escape(str(o["percent_of_class"])) if o["percent_of_class"] is not None else "Not an exact numeric percentage"}</td><td>{escape(o["shares"] or "Unavailable")}</td><td>{escape(o["security"] or "Unresolved")}</td></tr>' for o in d['ownership'])
            objective_notes=''.join(f'<h5>{escape(labels[k])}: {escape(v["status"])}</h5><p>{escape(v["rationale"])}</p>'+quote_block(v['evidence']) for k,v in d['intent'].items() if v['status']!='not_stated')
            facts=''.join(f'<h5>{escape(f["kind"])} · {escape(f["timing"])}</h5><p>{escape(f["actor"])} → {escape(f["target"])}: {escape(f["description"])}</p>'+quote_block(f['evidence']) for f in d['transaction_facts'])
            gaps=''.join(f'<li>{escape(g)}</li>' for g in d['evidence_gaps']) or '<li>No gap listed; this does not certify complete external evidence.</li>'
            record_href=f'../../extraction-stability/20261025-v2/agents/{agent}/records/{row["accession"]}.json'
            agent_sections.append(f'''<details><summary>Saved extraction {agent}: facts, reasoning and evidence</summary><p><strong>Reporting parties:</strong> {escape(people)}</p><h4>Ownership rows</h4><div class="scroll"><table><thead><tr><th>Party</th><th>Reported percent</th><th>Shares as extracted</th><th>Security</th></tr></thead><tbody>{ownership_rows}</tbody></table></div><h4>Funding labels: {escape(', '.join(d['funding']['types']))}</h4><p>{escape(d['funding']['summary'])}</p>{quote_block(d['funding']['evidence'])}<h4>Objectives labelled present or uncertain</h4>{objective_notes or '<p>No category is present or uncertain in this saved interpretation.</p>'}<h4>Separately recorded transactions and terms</h4>{facts}<h4>Evidence gaps and caveats</h4><ul>{gaps}</ul><p><a href="{record_href}">Original immutable model record {agent}</a></p></details>''')
        cards.append(f'''<section id="{case}"><h3>{case} · {escape(row['issuer_names']['A'])}</h3><p>Filing date {row['filing_date']}; accession {row['accession']}. <a href="{escape(data['bundle']['source_url'],quote=True)}">SEC source</a></p><div class="scroll"><table><thead><tr><th>Objective category</th><th>A</th><th>B</th><th>C</th><th>Present runs</th><th>Uncertain runs</th></tr></thead><tbody>{intent_rows}</tbody></table></div><p>Ownership-row counts A/B/C: {' / '.join(str(row['ownership_row_counts'][a]) for a in AGENTS)}. Transaction-fact counts A/B/C: {' / '.join(str(row['transaction_fact_counts'][a]) for a in AGENTS)}. Funding types identical across runs: {row['funding_type_sets_identical']}.</p>{''.join(agent_sections)}</section>''')
    category_table=''.join(f'<tr><th>{escape(c["name"])}</th><td>{c["unanimous_present_filings"]}/10</td><td>{c["any_present_filings"]}/10</td><td>{c["any_cannot_determine_filings"]}/10</td><td>{c["disagreement_filings"]}/10</td></tr>' for c in category_rows)
    report=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>What the first ten 13D extractions contain</title><style>body{{font:17px/1.65 system-ui;background:#f4f6f8;color:#203448;margin:0}}main{{max-width:1160px;margin:28px auto;background:white;padding:28px}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dae2e8}}thead th{{background:#edf3f7}}.scroll{{overflow:auto}}a{{color:#155c99}}blockquote{{margin:12px 0;padding:12px 18px;background:#f4f6f8;border-left:3px solid #7794ad;overflow-wrap:anywhere}}details{{margin:15px 0}}h1,h2,h3{{line-height:1.25}}section{{padding-top:14px}}</style></head><body><main>
<h1>What did we extract from the first ten 13D filings?</h1><p>October 27, 2026 · Review of completed development extractions · No new model calls or investment results</p>
<p><strong>We have source-backed model records for who reported, what ownership was disclosed, how purchases were funded, what transactions occurred and which specific company-directed objectives were stated.</strong> The revised run contains thirty records from three fresh same-configuration contexts per filing. This page organizes those existing results while the Bloomberg pilot is corrected.</p>
<p>The nine intent states agree across all three runs in 89/90 filing/category cells. That figure does not cover every extracted field. Funding-type sets differ on {len(summary['funding_type_disagreement_cases'])}/10 filings ({', '.join(summary['funding_type_disagreement_cases'])}); ownership-row counts differ on {len(summary['ownership_row_count_difference_cases'])}/10 ({', '.join(summary['ownership_row_count_difference_cases'])}); transaction-fact counts differ on {len(summary['transaction_fact_count_difference_cases'])}/10. Counts can differ because of granularity or coverage, so they are not automatically a tally of semantic errors.</p>
<h2>The ten filings at a glance</h2><p>These are model judgments with exact quotations, not human reference answers. “No qualifying objective labelled present” does not mean passive ownership or no private intentions. Multiple objectives can coexist, and objectives describe stated plans rather than realized outcomes.</p><div class="scroll"><table><thead><tr><th>Filing</th><th>Date</th><th>Objectives all three label present</th><th>Cannot-determine categories</th><th>Intent disagreement</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<h2>Which objectives appear in this batch?</h2><div class="scroll"><table><thead><tr><th>Category</th><th>All three present</th><th>At least one present</th><th>At least one uncertain</th><th>Different states</th></tr></thead><tbody>{category_table}</tbody></table></div><p>The categories overlap and counts must not be added as different filings. These ten were deliberately selected; the table does not estimate population prevalence. Categories with no positives here are untested for positive extraction quality, not proven irrelevant.</p>
<h2>What this teaches us about the information</h2><p><strong>A 13D is not a uniform activist signal.</strong> Nine Energy records shares received in an acquisition with no qualifying current objective labelled present. Continental includes family distribution/trust arrangements. Adesto concerns merger support and an acquirer's arrangements. Other cases contain specific requests for board, leadership, governance or strategic action. These are differing disclosure contexts, not validated campaign classifications.</p>
<p><strong>Ownership belongs to named people/entities and particular securities.</strong> Related reporting persons can disclose overlapping deemed ownership. We preserve each row and never sum their percentages. Geospace's three saved interpretations contain 3/3/2 ownership rows and differ on a null-versus-zero entry; that coverage/attribution issue needs inspection before collapsing ownership into a single feature.</p>
<p><strong>Funding labels need sharper boundaries.</strong> Geospace's own-net-assets description maps to working_capital in A/B and other in C. Catalyst has a borrowing type in A alongside language that margin loans may be used; B/C omit that type. Continental has existing trust-level borrowing in A's funding types while B/C preserve the noncash distribution as other. The narratives distinguish possibilities/history more carefully than the flat type list. A borrowed-funds flag is not yet a validated measure of actual debt-funded acquisition.</p>
<p><strong>Transaction facts and objectives carry different information.</strong> A completed securities purchase, private placement, gift/distribution, contract term or merger-support agreement should not automatically become a current demand to change issuer financing or operations. Transaction counts vary in seven cases because the unit of a “fact” was not fully standardized. Do not interpret raw fact count as engagement intensity.</p>
<p><strong>Preserve uncertainty.</strong> Capital return in Geospace, operating change in NextDecade and sale-of-company in At Home remain cannot_determine in all three runs. TriState's other-objective category remains split: A/C not_stated, B present. Three repeated labels are evidence of repeatability, not calibrated truth probabilities.</p>
<h2>What we can work on while Bloomberg is pending</h2><ol><li><strong>Use this first-batch review now.</strong> Walk through each source-backed case below and identify which information is economically meaningful, without looking at later investment outcomes.</li><li><strong>Specify a next schema revision.</strong> Separate confirmed acquisition borrowing, possible margin availability and historical/affiliate debt. Define ownership-row inclusion and transaction-fact granularity. Settle contractual registration rights versus a separate current objective. A new interpretation rule needs a new protocol/run; the saved v2 answers remain intact.</li><li><strong>Prioritize evidence gaps.</strong> Distinguish material incorporated references from immaterial graphics and ordinary missing attachments. Retrieve only specifically needed disclosure-time material under the defined source procedure.</li><li><strong>Prepare feature definitions and evaluation rules.</strong> The saved state distributions can be inspected now. New transaction/contract features such as standstills, lockups, instrument types or deadlines are candidates for later source-backed schema work, not fields we claim to have standardized already.</li><li><strong>Keep the reserved ten untouched.</strong> Freeze the revised procedure and reference/evaluation plan before that separate check. No new development or reserved batch was run here, following Jeff's choice to review these completed ten first.</li></ol>
<p>The immediate deliverables are a readable evidence view and a machine-readable distribution table. They do not turn ten already exposed cases into a useful predictive training sample or establish that filing features improve investment rankings. Financial-data repair, extraction accuracy and final investment evaluation remain separate tasks.</p>
<h2>Read each saved case</h2><p>Each case shows all three status vectors, reporting parties, individual ownership rows, funding descriptions, transaction facts, quotations and recorded gaps. The agent tabs are saved interpretations; none is selected as the reference answer.</p>{''.join(cards)}
<h2>Reproducible outputs</h2><p>All thirty saved record hashes and canonical input hashes agree with the preserved v2 run. All700 cited entries match their exact source slices. <a href="summary.json">Counts and issues</a> · <a href="feature-distributions.jsonl">Empirical state distributions</a> · <a href="provenance.json">Source/output hashes</a> · <a href="../../extraction-stability/20261025-v2/index.html">Original stability report</a> · <a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p></main></body></html>'''
    artifacts={'summary.json':encode(summary),'feature-distributions.jsonl':b''.join((json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n').encode() for r in model_rows),'index.html':report.encode()}
    sources[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    artifacts['provenance.json']=encode({'source_sha256':sources,'outputs_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in artifacts.items()},'interpretation':'Source-backed saved model interpretations; no human reference, empirical truth calibration or outcome evaluation.'})
    return artifacts,summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    artifacts,summary=build()
    RUN.mkdir(parents=True,exist_ok=True)
    for name,payload in artifacts.items():
        p=RUN/name
        if args.verify or p.exists():
            assert p.read_bytes()==payload,name
        else:
            p.write_bytes(payload)
    print(json.dumps({k:v for k,v in summary.items() if k!='categories'},indent=2))


if __name__=='__main__':
    main()
