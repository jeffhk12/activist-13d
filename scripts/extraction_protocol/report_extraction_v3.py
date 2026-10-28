"""Replay shared-rule retests and separately released operational-case results.

Inputs: frozen protocol/sources/control keys, final records and archived drafts.
Outputs: evidence-linked HTML, case comparisons, empirical label distributions,
integrity checks and hashes. Identity: agreement=sum(equal states)/all category
cells; source-control matches/construction cells; no natural accuracy estimate.
Tier:1. Run project Python report_extraction_v3.py --phase development|all [--verify].
"""
import argparse
import hashlib
import json
from html import escape
from pathlib import Path

from extraction_v3_io import ROOT, RUN, delivery, enc, load_job, normalize, read, sha
from extraction_v3_metrics import case_comparison, control_critic, control_inventory
from prepare_extraction_v3 import require_complete_review


def quote_count(value,docs):
    count=0
    if isinstance(value,dict):
        if {'document_id','quote','start','end'}<=set(value):
            text=docs[value['document_id']]['text']
            assert 0<=value['start']<value['end']<=len(text)
            assert text[value['start']:value['end']]==value['quote']
            count+=1
        for v in value.values():
            count+=quote_count(v,docs)
    elif isinstance(value,list):
        count+=sum(quote_count(v,docs) for v in value)
    return count


def build(phase):
    prep=read(RUN/'preparation.json')
    for name,expected in {**prep['input_sha256'],**prep['control_key_sha256']}.items():
        assert sha((RUN/name).read_bytes())==expected,name
    for name,expected in prep['source_code_sha256'].items():
        assert sha((ROOT/name).read_bytes())==expected,name
    preserved=read(RUN/'preservation-before.json')
    for name,expected in preserved.items():
        assert sha((ROOT/name).read_bytes())==expected,name
    jobs=[j for j in read(RUN/'jobs.json') if phase=='all' or j['phase']!='fresh']
    pending=[j['job_id'] for j in jobs if not (RUN/'jobs'/j['job_id']/'record.json').exists()]
    if pending:
        raise ValueError('All phase judgments must finalize before comparison: '+','.join(pending))
    records={}
    hashes={}
    sources={}
    quotes=0
    chars=0
    receipts=0
    for job in jobs:
        path=RUN/'jobs'/job['job_id']/'record.json'
        row=read(path)
        _,bundle,candidate=load_job(job['job_id'])
        covered=delivery(job,bundle)
        require_complete_review(row,bundle)
        assert covered['all_readable_text_delivered']
        rawpath=RUN/'jobs'/job['job_id']/'draft-history'/(row['run_metadata']['raw_draft_sha256']+'.json')
        assert sha(rawpath.read_bytes())==row['run_metadata']['raw_draft_sha256']
        norm=normalize(read(rawpath),job,bundle,candidate,covered)
        assert {k:v for k,v in norm.items() if k!='run_metadata'}=={k:v for k,v in row.items() if k!='run_metadata'},job['job_id']
        metadata=row['run_metadata']
        assert metadata['bundle_sha256']==sha((RUN/job['bundle']).read_bytes())
        assert metadata['common_rules_sha256']==sha((RUN/'inputs/common-rules.md').read_bytes())
        assert metadata['schema_sha256']==sha((RUN/'inputs/schema.json').read_bytes())
        assert metadata['protocol_sha256']==sha((RUN/'inputs/protocol.json').read_bytes())
        assert metadata['candidate_sha256']==(sha(enc(candidate)) if candidate else None)
        quotes+=quote_count(row,{d['document_id']:d for d in bundle['documents']})
        chars+=covered['served_unique_characters']
        receipts+=len(covered['receipts'])
        records[job['job_id']]=row
        hashes[job['job_id']]=sha(path.read_bytes())
        if job['role']=='critic':
            sources[job['case_id']]={'candidate':candidate,'bundle':bundle}
    controls={'critic':control_critic(read(RUN/'hidden-controls/critic-key.json'),records['control_critic'])}
    for role in ['control_extractor','control_blind']:
        controls[role]=control_inventory(read(RUN/'hidden-controls/inventory-key.json'),records[role])
    cases=[]
    changes=[]
    flag_rows=[]
    for inventory in read(RUN/'inventory.json'):
        if phase!='all' and inventory['phase']=='fresh':
            continue
        cid=inventory['case_id']
        a,b,c=[records[f'{r}_{cid.lower()}'] for r in ['extractor','blind','critic']]
        case=case_comparison(a,b,c)
        case.update(case_id=cid,phase=inventory['phase'],issuer=a['issuer']['name'])
        cases.append(case)
        candidate=sources[cid]['candidate']
        claim_map={r['claim_id']:r for r in candidate['claims']}
        flag_rows.extend({'case_id':cid,'claim':claim_map[r['claim_id']],**r} for r in c['reviews'] if r['verdict']!='supported')
        if inventory['phase']=='development':
            old=read(ROOT/'research/runs/extraction-stability/20261025-v2/agents/A/records'/f'{a["accession"]}.json')
            old_bundle=ROOT/'research/runs/extraction-stability/20261025-v2/inputs/bundles'/f'{a["accession"]}.json'
            assert sha(old_bundle.read_bytes())==sha((RUN/inventory['bundle']).read_bytes())
            changes.extend({'case_id':cid,'category':k,'v2':v['status'],'v3_extractor':a['intent'][k]['status'],
                            'v3_blind':b['intent'][k]['status']} for k,v in old['intent'].items() if v['status']!=a['intent'][k]['status'])
    totals={}
    for group in ['development','fresh']:
        rows=[r for r in cases if r['phase']==group]
        if not rows:
            continue
        verdicts={v:sum(r['critic_verdicts'][v] for r in rows) for v in ['supported','contradicted','insufficient_evidence']}
        totals[group]={'filings':len(rows),'intent_cells':sum(r['intent_cells'] for r in rows),
                       'intent_agreement':sum(r['intent_agreement'] for r in rows),
                       'eligible_experimental_intents':sum(r['eligible_experimental_intents'] for r in rows),
                       'critic_claims':sum(r['critic_claims'] for r in rows),'critic_verdicts':verdicts}
    summary={'phase':phase,'status':'completed_automated_experimental_measurements','jobs':len(records),
             'cases':len(cases),'by_phase':totals,'construction_gate_passed':all(r['passed'] for r in controls.values()),
             'controls':{k:{field:value for field,value in v.items() if field!='rows'} for k,v in controls.items()},
             'common_rules_sha256':sha((RUN/'inputs/common-rules.md').read_bytes()),
             'integrity':{'full_review_jobs':len(records),'exact_review_quotes':quotes,'delivered_characters':chars,
                          'delivery_receipts':receipts,'preserved_files':len(preserved)},
             'v2_to_v3_extractor_changed_cells':len(changes),'transaction_counts_used_as_features':False,
             'natural_accuracy':'not_estimated','precision_recall':'not_estimated','validated_categories':[],
             'all_fields_experimental':True,'full_extraction_started':False,'paid_APIs':False,
             'unreleased_reserved_cases':7,'different_model_families':False}
    out=RUN/'development-report' if phase=='development' else RUN
    prefix='../' if phase=='development' else ''
    table=''.join(f'<tr><th>{escape(r["case_id"])} {escape(r["issuer"] or "Unresolved issuer")}</th><td>{escape(r["phase"])}</td><td>{r["intent_agreement"]}/{r["intent_cells"]}</td><td>{r["eligible_experimental_intents"]}/{r["intent_cells"]}</td><td>{r["critic_verdicts"]["supported"]}</td><td>{r["critic_verdicts"]["contradicted"]}</td><td>{r["critic_verdicts"]["insufficient_evidence"]}</td></tr>' for r in cases)
    flags=''.join('<section><h3>'+escape(r['case_id']+' · '+r['claim_id']+' · '+r['verdict'])+'</h3><p>'+escape(r['rationale'])+'</p><p><strong>Candidate:</strong> '+escape(json.dumps(r['claim']['value'],ensure_ascii=False))+'</p>'+''.join('<blockquote>'+escape(e['quote'])+'<br><small>'+escape(e['document_id'])+f' [{e["start"]},{e["end"]})</small></blockquote>' for e in r['evidence'])+'</section>' for r in flag_rows)
    development=totals['development']
    fresh=totals.get('fresh')
    separate=(f'<p>The separate operational batch has {fresh["filings"]} filings: source readers agree on {fresh["intent_agreement"]}/{fresh["intent_cells"]} intent states. {fresh["eligible_experimental_intents"]}/{fresh["intent_cells"]} pass the conservative automated filter for experimental fields. It is a three-case diagnostic, not natural accuracy or population validation.</p>' if fresh else '<p>The three selected operational cases remain a separate next stage. Their source text is closed until the development/control gate passes.</p>')
    controls_html=''.join('<tr><th>'+escape(k)+'</th><td>'+escape(json.dumps({f:v for f,v in c.items() if f not in ['rows','confusion']},ensure_ascii=False))+'</td></tr>' for k,c in controls.items())
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D shared-rule extraction v3</title><style>body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1120px;margin:28px auto;padding:28px;background:white}}h1,h2,h3{{line-height:1.3}}td,th{{padding:11px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e8}}table{{width:100%;border-collapse:collapse;font-size:15px}}thead{{background:#edf3f7}}.scroll{{overflow:auto}}a{{color:#155c99}}blockquote{{border-left:3px solid #7794ad;background:#f3f6f8;padding:12px 18px;margin-left:0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style></head><body><main>
<h1>13D extraction: separate objectives from routine contract facts</h1><p>October 27, 2026 · {escape(phase)} checkpoint · Automated experimental measurements</p>
<p><strong>Do filing-text features improve investment ranking beyond financial information?</strong> This stage improves the measurement process before answering that investment question. The user selected separate issuer-directed objectives, with ordinary merger and financing clauses retained as facts. It adds no return calculation or model fit.</p>
<p>We froze a common policy used byte-for-byte by extractor, independent source-only reader and backward critic. On the ten matched development filings, the two source readers agree on {development['intent_agreement']}/{development['intent_cells']} objective states. {development['eligible_experimental_intents']}/{development['intent_cells']} meet the conservative automated condition for an experimental field: both source readers agree present/not_stated and the critic supports the fixed extractor answer. This is not measured correctness.</p>{separate}
<h2>What changed and why</h2><p>A primary acquisition bid can qualify as a sale objective. Automatic director/officer succession, ordinary delisting, resale-registration and security-conversion clauses do not create extra intervention objectives; their evidence stays in contract facts. An independent continuing nomination right or a distinct governance proposal can qualify. The same qualification rule now applies to every category and every role.</p>
<p>Funding records source, certainty and acquisition link separately, so possible loans and historical affiliate debt cannot silently become confirmed current borrowing. Ownership preserves person/security relation, direct/deemed/group role and overlap; no overlapping totals are added. A beneficial-ownership disclaimer does not erase a reported deemed holding. Scheduled or conditional actions remain distinct from explicitly pending/completed status. Transaction ledgers are summarized as material events/undertakings; transaction row counts are excluded from the first ranking model.</p>
<h2>All cases, with development and separate cases distinguished</h2><div class="scroll"><table><thead><tr><th>Case</th><th>Stage</th><th>Reader agreement</th><th>Eligible experimental intent fields</th><th>Critic supported</th><th>Contradicted</th><th>Insufficient evidence</th></tr></thead><tbody>{table}</tbody></table></div>
<p>Agreement uses present, not_stated and cannot_determine as distinct states. Unknowns and disagreements remain visible. The saved output retains both states and count/2 frequencies; those frequencies are not calibrated truth probabilities. Unsupported or uncertain fields are flagged, never silently changed to a negative. Name/security tuple differences are descriptive; aliases and security wording can differ without an omission.</p>
<h2>Constructed reviewer tests</h2><div class="scroll"><table><thead><tr><th>Role</th><th>Construction-key results and denominators</th></tr></thead><tbody>{controls_html}</tbody></table></div><p>Eight inventory sources contain72 keyed objective states per reader, plus selected funding/ownership requirements and prohibited inferences. Group totals are optional; the overlap fixture rejects invented or duplicate holdings. The16-claim critic set includes8 supported,6 contradicted and2 insufficient-evidence keys. These small constructed sources test specified capabilities, not natural-filing accuracy or recall.</p>
<h2>Read the critic's proposed issues</h2>{flags or '<p>No candidate claim received a non-supported verdict. This does not establish correctness or omission completeness.</p>'}
<h2>What changed relative to the earlier version?</h2><p>The fixed v3 extractor changed {len(changes)} of90 matched intent states relative to saved v2 extractor A. Source bytes are identical on these ten filings. The definition and context differ, so these are label changes after development, not accuracy improvement. The earlier three-agent v2 agreement and the later critic pilot have different roles and denominators; they are preserved history.</p>
<h2>Verification, limits and next decision</h2><p>All {len(records)} records pass exact schema/quote replay and full readable review/delivery checks. Independent source slicing checks cover {quotes} quotations; {chars:,} characters were delivered under {receipts} receipts. {len(preserved)} older-run/source-only-pack files match their saved hashes. Source delivery is not comprehension; unreadable or missing referenced material remains missing. All workers use the inherited configured model and can share errors; separation is procedural in a shared workspace.</p>
<p>No human-reference accuracy, precision, recall or false-pass rate is estimated. The older semantic-acceptance criteria remain unmet; no category is certified. These are experimental automated measurements. Passing the operational gates supports a separately scoped extraction decision, not an established investment edge or a claim of validated labels. Keep uncertainty and source gaps in any later dataset and do not use outcomes to tune extraction.</p>
<p>Next inspect the evidence-linked issues and remaining definition/source gaps, then decide whether to start full extraction in resumable batches under this frozen version. Full extraction has not started. Seven originally reserved cases remain unreleased; the three released operational cases, if present here, are now model-exposed and cannot be reused as untouched references.</p>
<p><a href="summary.json">Summary and denominators</a> · <a href="case-comparisons.json">Reader differences and state frequencies</a> · <a href="critic-flags.json">Critic issues</a> · <a href="control-results.json">Construction keys and all outcomes</a> · <a href="v2-to-v3-changes.json">Matched label changes</a> · <a href="verification.json">Integrity evidence</a> · <a href="{prefix}inputs/common-rules.md">Shared rules</a> · <a href="{prefix}inputs/protocol.json">Frozen plan</a> · <a href="{prefix}../../../../START-HERE.html">Project home</a></p></main></body></html>'''
    verification={**summary['integrity'],'status':'passed','record_hashes':hashes,
                  'source_code_sha256':prep['source_code_sha256'],'natural_accuracy':'not_estimated',
                  'report_code_sha256':sha(Path(__file__).read_bytes()),'semantic_fields_changed_by_reporting':False}
    results={'summary.json':enc(summary),'case-comparisons.json':enc(cases),'critic-flags.json':enc(flag_rows),
             'control-results.json':enc(controls),'v2-to-v3-changes.json':enc(changes),
             'verification.json':enc(verification),'index.html':html.encode()}
    results['provenance.json']=enc({'report_code_sha256':sha(Path(__file__).read_bytes()),
        'output_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in results.items()},
        'preparation_sha256':sha((RUN/'preparation.json').read_bytes())})
    return out,results,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['development','all'],required=True)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    out,results,summary=build(args.phase)
    out.mkdir(parents=True,exist_ok=True)
    for name,payload in results.items():
        path=out/name
        if args.verify or path.exists():
            assert path.read_bytes()==payload,name
        else:
            path.write_bytes(payload)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
