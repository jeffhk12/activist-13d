"""Compare completed reviewer judgments and construction-key control outcomes.

Inputs:22 finalized audit records, frozen candidates/sources/control keys.
Outputs: verdict/coverage counts, blind differences, control tables, evidence HTML
and replay hashes. Identity: conclusive=(supported+contradicted)/all claims;
control exact/detection counts use frozen fixture keys, not natural-data truth.
Tier:1. Natural-data precision/recall/accuracy remain unestimated.
Run: project Python scripts/extraction_protocol/report_extraction_audit.py [--verify].
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-audit/20261027-v1'
VERDICTS=('supported','contradicted','insufficient_evidence')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()


def verdict_summary(reviews):
    reviews=list(reviews)
    if not reviews or any(r['verdict'] not in VERDICTS for r in reviews):
        raise ValueError('Nonempty valid review verdicts required')
    counts={v:sum(r['verdict']==v for r in reviews) for v in VERDICTS}
    return {'claims':len(reviews),'verdicts':counts,
            'conclusive_fraction':(counts['supported']+counts['contradicted'])/len(reviews)}


def name_key(value):
    return re.sub(r'[^a-z0-9]','',value.lower())


def ownership_key(row):
    # Deliberately narrow descriptive key: ignores shares/security wording.
    value=row['percent_of_class']
    return name_key(row['reporting_party']),None if value is None else round(float(value),6)


def compare_inventories(candidate,blind):
    original_parties=Counter(name_key(r['name']) for r in candidate['reporting_parties'])
    observed_parties=Counter(name_key(r['name']) for r in blind['reporting_parties'])
    a,b=Counter(ownership_key(r) for r in candidate['ownership']),Counter(ownership_key(r) for r in blind['ownership'])
    def items(counter):
        return [{'key':list(k) if isinstance(k,tuple) else k,'count':v} for k,v in sorted(counter.items(),key=lambda kv:str(kv[0]))]
    return {'reporter_names_only_in_blind':items(observed_parties-original_parties),
            'reporter_names_only_in_candidate':items(original_parties-observed_parties),
            'ownership_person_percent_only_in_blind':items(b-a),
            'ownership_person_percent_only_in_candidate':items(a-b),
            'ownership_rows_candidate':len(candidate['ownership']),'ownership_rows_blind':len(blind['ownership']),
            'funding_types_candidate':sorted(candidate['funding']['types']),
            'funding_types_blind':sorted(blind['funding']['types']),
            'funding_type_sets_equal':set(candidate['funding']['types'])==set(blind['funding']['types']),
            'intent_differences':[{ 'category':k,'candidate':v['status'],'blind':blind['intent'][k]['status']}
                                  for k,v in candidate['intent'].items() if v['status']!=blind['intent'][k]['status']],
            'transaction_rows_candidate':len(candidate['transaction_facts']),
            'transaction_rows_blind':len(blind['transaction_facts']),
            'limit':'Name/person-percentage string-key differences are descriptive; alias/security/coverage differences are not automatically errors or confirmed omissions.'}


def control_summary(key,reviews):
    reviews=list(reviews)
    observed={r['claim_id']:r for r in reviews}
    if len(reviews)!=len(key) or len(observed)!=len(key) or set(observed)!={r['claim_id'] for r in key}:
        raise ValueError('All control IDs required exactly once')
    result=[]
    for truth in key:
        r=observed[truth['claim_id']]
        result.append({**truth,'observed_verdict':r['verdict'],
                       'exact_verdict_match':r['verdict']==truth['expected_verdict'],
                       'changed_claim_flagged':r['verdict']!='supported' if truth['condition']=='changed' else None})
    changed=[r for r in result if r['condition']=='changed']
    clean=[r for r in result if r['condition']=='unchanged']
    return {'fixture_claims':len(result),'exact_verdict_matches':sum(r['exact_verdict_match'] for r in result),
            'changed_claims':len(changed),'changed_claims_flagged':sum(r['changed_claim_flagged'] for r in changed),
            'unchanged_claims':len(clean),'unchanged_claims_supported':sum(r['observed_verdict']=='supported' for r in clean),
            'confusion_counts':dict(Counter(r['expected_verdict']+' -> '+r['observed_verdict'] for r in result)),
            'rows':result,'limit':'Simple constructed fixtures with designer-specified keys; not natural-data or externally validated semantic accuracy.'}


def blind_control_summary(key,record):
    observed={c['document_id']:c for c in record['cases']}
    if len(record['cases'])!=len(key) or set(observed)!={r['case_id'] for r in key}:
        raise ValueError('Source-control IDs differ')
    rows=[]
    for truth in key:
        r=observed[truth['case_id']]
        expected_owners=Counter(ownership_key(o) for o in truth['ownership'])
        got_owners=Counter(ownership_key(o) for o in r['ownership'])
        expected_names=set(name_key(p) for p in truth['reporters'])
        got_names=set(name_key(p['name']) for p in r['reporters'])
        got_objectives=set(o['category'] for o in r['objectives'])
        deleted=[o for o in truth['ownership'] if o['reporting_party']==truth['deleted_candidate_party']][0]
        rows.append({'case_id':truth['case_id'],'expected_ownership_rows':sum(expected_owners.values()),
                     'matched_ownership_rows':sum((expected_owners&got_owners).values()),
                     'extra_ownership_rows':sum((got_owners-expected_owners).values()),
                     'expected_reporters':len(expected_names),'matched_reporters':len(expected_names&got_names),
                     'extra_reporters':len(got_names-expected_names),
                     'expected_objective':truth['objective'],'objective_found':truth['objective'] in got_objectives,
                     'extra_objective_ids':sorted(got_objectives-{truth['objective']}),
                     'deleted_candidate_row_recovered':got_owners[ownership_key(deleted)]>0})
    return {'fixtures':len(rows),'expected_ownership_rows':sum(r['expected_ownership_rows'] for r in rows),
            'matched_ownership_rows':sum(r['matched_ownership_rows'] for r in rows),
            'extra_ownership_rows':sum(r['extra_ownership_rows'] for r in rows),
            'expected_reporters':sum(r['expected_reporters'] for r in rows),
            'matched_reporters':sum(r['matched_reporters'] for r in rows),
            'objectives_found':sum(r['objective_found'] for r in rows),
            'deleted_candidate_rows_recovered':sum(r['deleted_candidate_row_recovered'] for r in rows),
            'rows':rows,'limit':'Recovery in eight short constructed fixtures, not omission recall on real filings.'}


def build():
    prep=json.loads((RUN/'preparation.json').read_text())
    revised={}
    if (RUN/'implementation-revisions.json').exists():
        revisions=json.loads((RUN/'implementation-revisions.json').read_text())
        revised={r['source_path']:r for r in revisions['revisions']}
    for name,expected in prep['source_sha256'].items():
        actual=sha(ROOT/name)
        if actual!=expected:
            assert name in revised and revised[name]['original_sha256']==expected and revised[name]['revised_sha256']==actual,name
    for name,expected in {**prep['input_sha256'],**prep['control_key_sha256']}.items():
        assert sha(RUN/name)==expected,name
    jobs=json.loads((RUN/'inputs/jobs.json').read_text())
    pending=[j['job_id'] for j in jobs if not (RUN/'jobs'/j['job_id']/'record.json').exists()]
    if pending:
        raise ValueError('Wait for all22 finalized jobs: '+', '.join(pending))
    records={j['job_id']:json.loads((RUN/'jobs'/j['job_id']/'record.json').read_text()) for j in jobs}
    record_hashes={j['job_id']:sha(RUN/'jobs'/j['job_id']/'record.json') for j in jobs}
    all_reviews=[]
    cases=[]
    details=[]
    for number in range(1,11):
        cid=f'D{number:02}'
        stem=cid.lower()
        source_path=RUN/f'inputs/cases/{cid}'
        candidate=json.loads((source_path/'candidate.json').read_text())
        # Read original candidate from the exact saved source hash after every job.
        original_path=ROOT/'research/runs/extraction-stability/20261025-v2/agents/A/records'/f'{candidate["accession"]}.json'
        original=json.loads(original_path.read_text())
        blind=records['blind_'+stem]
        critic=records['critic_'+stem]
        claims={c['claim_id']:c for c in candidate['claims']}
        reviews=[{**r,'case_id':cid,'kind':claims[r['claim_id']]['kind']} for r in critic['reviews']]
        assert len(reviews)==len(claims) and {r['claim_id'] for r in reviews}==set(claims)
        all_reviews.extend(reviews)
        summary=verdict_summary(reviews)
        differences=compare_inventories(original,blind)
        cases.append({'case_id':cid,'accession':candidate['accession'],'issuer':original['issuer']['name'],
                      'critic':summary,'differences':differences,
                      'critic_full_delivery':critic['review_delivery']['all_readable_text_delivered'],
                      'blind_full_delivery':blind['review_delivery']['all_readable_text_delivered']})
        flags=[]
        for r in reviews:
            if r['verdict']=='supported':
                continue
            evidence=''.join(f'<blockquote>{escape(e["quote"])}<br><small>{escape(e["document_id"])} [{e["start"]},{e["end"]})</small></blockquote>' for e in r['evidence'])
            flags.append(f'<h4>{escape(r["claim_id"])}: {escape(r["verdict"])}</h4><p><strong>Candidate:</strong> {escape(json.dumps(claims[r["claim_id"]]["value"],ensure_ascii=False))}</p><p>{escape(r["rationale"])}</p><p>Issue codes: {escape(", ".join(r["issue_codes"]))}</p>{evidence}')
        details.append(f'<section id="{cid}"><h3>{cid} · {escape(original["issuer"]["name"])}</h3>{"".join(flags) or "<p>No candidate claim received a non-supported verdict. This is not proof of correctness.</p>"}<details><summary>Blind source-reader differences</summary><pre>{escape(json.dumps(differences,indent=2,ensure_ascii=False))}</pre></details><p><a href="jobs/critic_{stem}/record.json">Backward review</a> · <a href="jobs/blind_{stem}/record.json">Blind source inventory</a> · <a href="inputs/cases/{cid}/candidate.json">Frozen candidate</a></p></section>')
    natural=verdict_summary(all_reviews)
    by_kind={kind:verdict_summary(r for r in all_reviews if r['kind']==kind) for kind in sorted({r['kind'] for r in all_reviews})}
    control=control_summary(json.loads((RUN/'hidden-controls/critic-key.json').read_text()),records['control_critic']['reviews'])
    omission=blind_control_summary(json.loads((RUN/'hidden-controls/blind-key.json').read_text()),records['control_blind'])
    verdict_table=''.join(f'<tr><th>{escape(k)}</th><td>{v["claims"]}</td>'+''.join(f'<td>{v["verdicts"][s]}</td>' for s in VERDICTS)+'</tr>' for k,v in by_kind.items())
    cases_table=''.join(f'<tr><th><a href="#{c["case_id"]}">{c["case_id"]} {escape(c["issuer"])}</a></th><td>{c["critic"]["claims"]}</td>'+''.join(f'<td>{c["critic"]["verdicts"][s]}</td>' for s in VERDICTS)+f'<td>{len(c["differences"]["intent_differences"])}</td><td>{c["differences"]["ownership_rows_candidate"]}/{c["differences"]["ownership_rows_blind"]}</td></tr>' for c in cases)
    counts=natural['verdicts']
    summary={'status':'completed_automated_development_audit','jobs':len(records),'candidate_filings':10,
             'candidate_selection':'savedA for everycase, fixed before reviewers','natural_claims':natural,
             'by_claim_kind':by_kind,'control_claims':{k:v for k,v in control.items() if k!='rows'},
             'source_controls':{k:v for k,v in omission.items() if k!='rows'},
             'full_delivery_jobs':sum(r['review_delivery']['all_readable_text_delivered'] for r in records.values()),
             'expected_readable_characters':sum(r['review_delivery']['expected_characters'] for r in records.values()),
             'delivered_readable_characters':sum(r['review_delivery']['served_unique_characters'] for r in records.values()),
             'blind_intent_difference_cells':sum(len(c['differences']['intent_differences']) for c in cases),
             'blind_funding_type_difference_filings':sum(not c['differences']['funding_type_sets_equal'] for c in cases),
             'natural_data_accuracy':'not_estimated','natural_data_precision_recall':'not_estimated',
             'different_model_families':False,'reserved_case_exposure':False,'model_judgments_are_reference_truth':False}
    report=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D backward-review pilot</title><style>body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1160px;margin:28px auto;padding:28px;background:white}}table{{width:100%;border-collapse:collapse;font-size:15px}}td,th{{text-align:left;vertical-align:top;padding:11px;border-bottom:1px solid #dce3e8}}thead th{{background:#edf3f7}}a{{color:#155c99}}.scroll{{overflow:auto}}blockquote{{margin:12px 0;padding:12px 18px;background:#f3f6f8;border-left:3px solid #7794ad}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}}h1,h2,h3{{line-height:1.25}}</style></head><body><main>
<h1>Can another agent work backward to check our 13D answers?</h1><p>October 27, 2026 · Completed 22-job automated development audit · Same configured model, no independent semantic reference</p>
<p><strong>We reused one fixed extractor answer per filing and ran two separate reviewer roles.</strong> The backward critic checked {natural['claims']} field/relationship claims: {counts['supported']} supported, {counts['contradicted']} contradicted and {counts['insufficient_evidence']} with insufficient evidence. These are reviewer judgments, not a measured count of true errors. A separate source-only reader searched before seeing candidate answers.</p>
<h2>What “work backward” means</h2><p>The extractor maps source→structured answer. The critic maps each candidate answer→the original source and checks who, what security, what amount, when and with which conditions. It receives complete readable text and definitions, with extractor identity and intent rationales hidden. It must give exact evidence and can abstain. The blind reader maps source→an independent inventory to reveal information that checking only returned answers can miss.</p>
<p>Candidate selection was saved replicateA for every D01–D10, fixed before any review. OriginalA/B/C answers remain preserved. We did not re-extract a new development sample. The ten source-only readings and ten critics each used fresh one-filing contexts. Two additional fresh jobs handled constructed controls. These agents share the inherited model; distinct roles/contexts do not establish independent errors.</p>
<h2>Reviewer verdicts by field</h2><div class="scroll"><table><thead><tr><th>Claim kind</th><th>Claims</th><th>Supported</th><th>Contradicted</th><th>Insufficient evidence</th></tr></thead><tbody>{verdict_table}</tbody></table></div><p>Conclusive verdict coverage is {counts['supported']+counts['contradicted']}/{natural['claims']} ({100*natural['conclusive_fraction']:.1f}%). Coverage is not accuracy. Contradiction requires incompatible source evidence; missing support, unavailable references and genuine definition ambiguity can produce insufficient_evidence.</p>
<h2>All ten discovery cases</h2><div class="scroll"><table><thead><tr><th>Case</th><th>Claims</th><th>Supported</th><th>Contradicted</th><th>Insufficient evidence</th><th>Intent differences with blind reader</th><th>Ownership rows candidate/blind</th></tr></thead><tbody>{cases_table}</tbody></table></div><p>Blind-reader differences identify candidates for inspection, not confirmed omissions. Name/person-percentage comparisons use simple normalized strings and retain multiplicity; they do not resolve aliases, security wording or substantive attribution. Transaction counts can differ in granularity. Neither reviewer is selected as the truth.</p>
<h2>Did the reviewers catch deliberately constructed problems?</h2><p>The critic's exact verdict matched the construction key on {control['exact_verdict_matches']}/{control['fixture_claims']} short claims. It flagged {control['changed_claims_flagged']}/{control['changed_claims']} changed claims and supported {control['unchanged_claims_supported']}/{control['unchanged_claims']} unchanged claims. The cases test percentage scale, actor identity, confirmed versus possible funding, negation, historical plans, overlapping ownership and missing references. IDs/order were fixed and shuffled before review; keys were withheld.</p><p>The blind control reader recovered {omission['matched_ownership_rows']}/{omission['expected_ownership_rows']} expected ownership rows and {omission['objectives_found']}/{omission['fixtures']} objective IDs. It recovered the deliberately deleted candidate row in {omission['deleted_candidate_rows_recovered']}/{omission['fixtures']} source-only fixtures, with {omission['extra_ownership_rows']} extra ownership rows. These are simple constructed tests with designer-specified answers, not realistic filing-recall or human-validated error estimates.</p>
<p><a href="control-results.json">All control comparisons and denominators</a> · <a href="jobs/control_critic/record.json">Control critic evidence</a> · <a href="jobs/control_blind/record.json">Control source inventory</a></p>
<h2>Read the flagged claims and source passages</h2>{''.join(details)}
<h2>What this establishes and what remains open</h2><p>Deterministic quote/schema checks establish structure and source-span presence; the critic tests interpretation. Natural-data precision, recall, false-pass rate and semantic accuracy remain unestimated. Reviewer approval cannot certify a missing exhibit, source completeness, economic manager identity or a future investment outcome. Simple controls test specific capabilities and can be easier than natural documents. The same-model setup can share mistakes despite procedural blinding.</p>
<p>The fixed audit rubric emphasizes actor, security, timing and conditionality. It retains v2 objective definitions, while explicitly preserving financing qualifications and allowing definition ambiguity. Thus blind-versus-extractor differences can reflect prompt/rubric emphasis as well as omissions; the critic's benefit is not isolated by a randomized causal design.</p>
<p>All readable text delivery and exact quote checks are audited separately from interpretation. One early control finalization exposed a missing local schema-definition reference. The structural repair and regression test are archived, with the failed draft retained and semantic rubric/inputs/control keys unchanged. No numerical result or answer was selected because of a favorable review.</p>
<h2>Next decision</h2><p>Inspect the evidence-linked flags and distinguish substantive corrections from ambiguous definitions and harmless representation differences. Keep proposed corrections separate from originals. A next version may clarify financing qualifiers, ownership-row inclusion and transaction granularity. Do not expose reserved cases or scale solely because controls or model agreement look strong. A natural-data accuracy claim still needs an appropriate independent reference or separately justified validation method. No Bloomberg extraction, return recomputation or investment-model fit was performed here.</p>
<p><a href="summary.json">Machine-readable summary</a> · <a href="case-comparisons.json">Blind differences</a> · <a href="claim-reviews.json">All natural claim verdicts</a> · <a href="inputs/protocol.json">Frozen protocol</a> · <a href="preparation.json">Prefit/input record</a> · <a href="provenance.json">Hashes and replay</a> · <a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p></main></body></html>'''
    artifacts={'summary.json':encode(summary),'case-comparisons.json':encode(cases),
               'claim-reviews.json':encode(all_reviews),'control-results.json':encode({'critic':control,'blind':omission}),
               'record-hashes.json':encode(record_hashes),'index.html':report.encode()}
    artifacts['provenance.json']=encode({'preparation_sha256':sha(RUN/'preparation.json'),
                                         'report_code_sha256':sha(Path(__file__)),
                                         'output_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in artifacts.items()}})
    return artifacts,summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    artifacts,summary=build()
    for name,payload in artifacts.items():
        path=RUN/name
        if args.verify or path.exists():
            assert path.read_bytes()==payload,name
        else:
            path.write_bytes(payload)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
