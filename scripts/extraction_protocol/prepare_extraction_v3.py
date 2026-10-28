"""Freeze shared-rule v3, stage ten discovery retests and three closed new cases.

Inputs: approved objective scope, versioned code/schema, preserved sources and
outcome-free reserved metadata. Outputs: immutable protocol/input/code hashes,
42 one-role jobs and an explicit gated release of three operational cases.
Identity: 10*3 development +3 controls +3*3 separate-case jobs=42;7 original
reserved cases remain unreleased. Tier:1. No paid/network/return/model fitting.
Run: project Python prepare_extraction_v3.py prepare|status|release-fresh.
"""
import argparse
import gzip
import json
from datetime import datetime, timezone

from build_extraction_v3 import artifacts
from extraction_v3_controls import claim_controls, inventory_controls
from extraction_v3_io import ROOT, RUN, enc, read, sha
from extraction_v3_metrics import control_critic, control_inventory
from extraction_v3_sampling import select_fresh

BASE=ROOT/'research/runs/extraction-stability/20261025-v2'
PILOT=ROOT/'research/runs/ranking-llm-pilot/20261025-v2'
PACK=ROOT/'review/drafts/ranking-llm-pilot-20261025'
PROTOCOL=ROOT/'research/protocol/extraction-revision-v3.json'
CODE_NAMES=['build_extraction_v3.py','extraction_v3_controls.py','extraction_v3_sampling.py',
            'extraction_v3_io.py','extraction_v3_metrics.py','prepare_extraction_v3.py',
            'stability_io.py','stability_v2_io.py','audit_io.py']
TEST_NAMES=['test_extraction_v3_rules.py','test_extraction_v3_controls.py',
            'test_extraction_v3_sampling.py','test_extraction_v3_io_metrics.py']


def protocol():
    return {'version':'extraction-v3','created_on':'2026-10-27',
        'authority':'User approved four steps and explicitly chose separate objectives with routine provisions retained as facts. No per-filing human review is required for this bounded automated development and three-case operational branch. Full extraction is not started by this protocol.',
        'question':'Can consistently defined filing measurements be produced and automatically reviewed before the financial-only versus text-added ranking comparison?',
        'scope':'Ten same-source development cases, two independent source readings and one backward critic per case, three synthetic-control jobs, then three separately released operational cases with same roles. No outcomes or future amendments.',
        'objective_policy':'Separate issuer-directed intervention beyond routine implementation. Primary whole-issuer control bid qualifies sale; routine succession, delisting, resale registration, charter/security implementation and vote-support alone stay contract facts. All roles receive identical shared semantic rules.',
        'measurement_contract':'Qualified funding components, person/security ownership role and overlap, current-scope timing, category-specific unknowns. Transaction count is excluded from first ranking model. Preserve original models and raw clause evidence.',
        'contexts':'One role/one natural filing per fresh subscription-agent context. Extractor and blind reader see only source and identical definitions, not one another. Critic sees mechanically preassigned extractor claims with author/intent rationales hidden. Same inherited model; exact model/settings not exposed; procedural isolation only.',
        'selection':'Candidate always new extractor record, never best-of-two. Three separate cases selected only after this protocol/schema/prompt freeze, using reserved metadata and extraction_v3_sampling.select_fresh. One early, one recent, third prefers unreadable-doc complexity then multidoc then any. Metadata workload cap100000 chars; seed extraction-v3-fresh-20261027. No outcome inputs; old affiliation/unlogged reading limits persist.',
        'fresh_release':'Compressed evidence may be copied and hashed without decoding after freeze. Source helper refuses fresh text until all33 development/control records complete and deterministic integrity plus all construction criteria pass. Release records three selected IDs separately; original reserved assets unchanged and remaining7 unreleased. Released cases become model-exposed operational examples, not untouched accuracy references.',
        'controls':'Two source-only inventories on8 invented fixtures, and one16-claim critic (8 supported/6 contradicted/2 insufficient). Hidden keys withheld. Score all72 intent states per inventory plus selected funding/ownership tuples and forbidden inferences. Group aggregates optional. Keys constructed before workers; no score-selected retries.',
        'technical_gate':'All expected records finalized; exact schema/quotes, reviewed IDs and readable-source interval coverage pass; every original/input hash unchanged; each returned candidate claim reviewed exactly once. Missing exhibits remain explicit. No numerical intent-agreement cutoff or forced positive/negative label.',
        'construction_gate':'16/16 critic construction verdicts plus72/72 intent states for EACH source control; all selected required funding/ownership tuples recovered, no forbidden current-financing/timing or optional-aggregate-role violations. These are simple constructed capabilities, not natural accuracy.',
        'natural_uncertainty':'Retain both reader states and their empirical count/2 frequencies, not calibrated truth probabilities. A label is eligible only as an experimental field if both readers agree present/not_stated and critic supports preassigned candidate. Disagreements/unknowns/non-supported judgments stay flagged and are not silently changed or coded as zero.',
        'evaluation_claim':'This is automated operational/measurement-consistency testing. No natural-data precision, recall, semantic accuracy or false-pass rate is estimated. The older human-reference acceptance rules remain unmet, not bypassed or claimed satisfied. All natural fields remain experimental. Scaling recommendation is separate from validated-category acceptance.',
        'stopping_rule':'No paid APIs, new online filing sources, Bloomberg extraction, fitting or full667 interpretation. If technical/control gate fails, record failure and keep fresh sources closed; any semantic/rubric change gets a new version/run, never in-place tuning.',
        'publication':'Report every case/abstention and all control denominators, source/quote integrity, v2-to-v3 label changes on matched10 as rule-change description not accuracy improvement, separate3-case results, issues and next decision. Preserve prior runs/human assets. Update home and learning checkpoint.'}


def prepare():
    if RUN.exists():
        raise ValueError('Preserve existing run')
    # Final generated artifact equality and schema check precede new-case selection.
    for name,payload in artifacts().items():
        if (ROOT/'research/protocol'/name).read_bytes()!=payload:
            raise ValueError('Generated artifact mismatch: '+name)
    frozen=enc(protocol())
    if PROTOCOL.exists() and PROTOCOL.read_bytes()!=frozen:
        raise ValueError('Existing protocol immutable')
    if not PROTOCOL.exists():
        PROTOCOL.write_bytes(frozen)
    RUN.mkdir(parents=True)
    inputs=RUN/'inputs'
    inputs.mkdir()
    (RUN/'candidates').mkdir()
    (RUN/'hidden-controls').mkdir()
    # Freeze semantic policy AND implementation before metadata selection.
    code_hashes={}
    for directory,names in [('scripts/extraction_protocol',CODE_NAMES),('tests',TEST_NAMES)]:
        for name in names:
            path=ROOT/directory/name
            raw=path.read_bytes()
            code_hashes[str(path.relative_to(ROOT))]=sha(raw)
            target=RUN/'code'/name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
    copied={
        'protocol.json':PROTOCOL,'categories.json':ROOT/'research/protocol/categories-extraction-v3.json',
        'common-rules.md':ROOT/'research/protocol/extraction-common-rules-v3.md',
        'schema.json':ROOT/'research/protocol/extraction-schema-v3.json',
        **{f'role-{r}.txt':ROOT/'research/protocol'/f'extraction-role-{r}-v3.txt' for r in ['extractor','blind','critic']}}
    for name,path in copied.items():
        (inputs/name).write_bytes(path.read_bytes())
    freeze={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(frozen),
            'semantic_sha256':{str(p.relative_to(RUN)):sha(p.read_bytes()) for p in inputs.iterdir()},
            'source_code_sha256':code_hashes,'timing':'before new-case selection, source release and all v3 model jobs'}
    (RUN/'freeze.json').write_bytes(enc(freeze))
    old=read(PILOT/'sample-manifest.json')['selection']
    # Only metadata is read for these reserved cases. Canonical text stays compressed.
    selected,trace=select_fresh(old['validation_reserved'],[r['accession'] for r in old['discovery']],
        excluded_groups=[r['connected_group'] for r in old['discovery']],
        excluded_issuers=[r['issuer'] for r in old['discovery']])
    new=[]
    for i,row in enumerate(selected,1):
        new.append({**row,'reserved_case_id':row['case_id'],'case_id':f'N{i:02}'})
    (RUN/'selection.json').write_bytes(enc({'selected':new,'trace':trace,
        'original_reserved_cases':10,'selected_for_operational_release':3,'remain_reserved':7,
        'semantic_freeze_sha256':sha((RUN/'freeze.json').read_bytes()),'fresh_source_text_read':False}))
    inventory=[]
    jobs=[]
    old_inventory=read(BASE/'inputs/inventory.json')
    def add_case(row,bundle_path,raw):
        target=RUN/bundle_path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        inventory.append({**row,'bundle':bundle_path,'bundle_sha256':sha(raw)})
        for role in ['extractor','blind','critic']:
            job_id=f'{role}_{row["case_id"].lower()}'
            jobs.append({'job_id':job_id,'role':role,'phase':row['phase'],'case_id':row['case_id'],
                         'accession':row['accession'],'bundle':bundle_path,
                         'candidate_source_job':f'extractor_{row["case_id"].lower()}' if role=='critic' else None})
    for row in old_inventory:
        raw=(BASE/'inputs/bundles'/f'{row["accession"]}.json').read_bytes()
        assert sha(raw)==row['input_sha256']
        add_case({**row,'phase':'development'},f'inputs/cases/{row["case_id"]}/bundle.json',raw)
    old_hashes=read(PILOT/'output-hashes.json')
    for row in new:
        path=PACK/'validation-reserved/evidence'/f'{row["accession"]}.json.gz'
        raw=path.read_bytes()
        assert sha(raw)==old_hashes[str(path.relative_to(ROOT))]
        add_case({**row,'phase':'fresh'},f'inputs/cases/{row["case_id"]}/bundle.json.gz',raw)
    bundle,candidate,key=claim_controls()
    (inputs/'control-critic-bundle.json').write_bytes(enc(bundle))
    (inputs/'control-critic-candidate.json').write_bytes(enc(candidate))
    (RUN/'hidden-controls/critic-key.json').write_bytes(enc(key))
    jobs.append({'job_id':'control_critic','role':'control_critic','phase':'controls','case_id':'CONTROL',
                 'accession':bundle['accession'],'bundle':'inputs/control-critic-bundle.json',
                 'candidate':'inputs/control-critic-candidate.json','candidate_source_job':None})
    bundle,key=inventory_controls()
    (inputs/'control-inventory-bundle.json').write_bytes(enc(bundle))
    (RUN/'hidden-controls/inventory-key.json').write_bytes(enc(key))
    for role in ['control_extractor','control_blind']:
        jobs.append({'job_id':role,'role':role,'phase':'controls','case_id':'CONTROL',
                     'accession':bundle['accession'],'bundle':'inputs/control-inventory-bundle.json','candidate_source_job':None})
    (RUN/'jobs.json').write_bytes(enc(jobs))
    (RUN/'inventory.json').write_bytes(enc(inventory))
    for job in jobs:
        for sub in ['delivery','drafts','draft-history']:
            (RUN/'jobs'/job['job_id']/sub).mkdir(parents=True,exist_ok=True)
    preserved={}
    for base in [BASE,ROOT/'research/runs/extraction-audit/20261027-v1']:
        preserved.update({str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()})
    preserved.update(old_hashes)
    for name,expected in preserved.items():
        assert sha((ROOT/name).read_bytes())==expected,name
    (RUN/'preservation-before.json').write_bytes(enc(preserved))
    input_hashes={str(p.relative_to(RUN)):sha(p.read_bytes()) for p in inputs.rglob('*') if p.is_file()}
    input_hashes['jobs.json']=sha((RUN/'jobs.json').read_bytes())
    (RUN/'preparation.json').write_bytes(enc({'jobs':len(jobs),'development_cases':10,'fresh_cases':3,
        'source_code_sha256':code_hashes,'input_sha256':input_hashes,
        'control_key_sha256':{str(p.relative_to(RUN)):sha(p.read_bytes()) for p in (RUN/'hidden-controls').iterdir()},
        'preservation_files':len(preserved),'no_paid_APIs':True,'no_outcomes':True,
        'source_only_fresh_gzip_copied_without_decoding':True}))
    print(json.dumps({'jobs':len(jobs),'development_cases':10,'fresh_cases_closed':3,'run':str(RUN)}))


def progress():
    jobs=read(RUN/'jobs.json')
    complete=[]
    pending=[]
    for job in jobs:
        path=RUN/'jobs'/job['job_id']/'record.json'
        if path.exists():
            row=read(path)
            complete.append({'job_id':job['job_id'],'phase':job['phase'],
                             'full_delivery':row['review_delivery']['all_readable_text_delivered']})
        else:
            pending.append({'job_id':job['job_id'],'phase':job['phase']})
    result={'complete':complete,'pending':pending,'complete_count':len(complete),'total_jobs':len(jobs)}
    (RUN/'progress.json').write_bytes(enc(result))
    return result


def require_complete_review(record,bundle):
    readable={d['document_id'] for d in bundle['documents'] if d.get('text')}
    status=record.get('extraction_status',record.get('review_status'))
    if status!='complete_readable_bundle' or set(record['reviewed_document_ids'])!=readable:
        raise ValueError('Gate needs complete review attestation and every readable document ID')
    for case in record.get('cases',[]):
        if case['extraction_status']!='complete_readable_bundle' or set(case['reviewed_document_ids'])!={case['accession']}:
            raise ValueError('Gate needs complete review for every control fixture')


def release_fresh():
    # Import only at use: no circular import or source decoding during preparation.
    from extraction_v3_io import delivery, load_job, normalize
    prep=read(RUN/'preparation.json')
    for name,expected in {**prep['input_sha256'],**prep['control_key_sha256']}.items():
        assert sha((RUN/name).read_bytes())==expected,name
    for name,expected in prep['source_code_sha256'].items():
        assert sha((ROOT/name).read_bytes())==expected,name
    jobs=[j for j in read(RUN/'jobs.json') if j['phase']!='fresh']
    pending=[j['job_id'] for j in jobs if not (RUN/'jobs'/j['job_id']/'record.json').exists()]
    if pending:
        raise ValueError('Keep fresh sources closed; unfinished development/control jobs: '+','.join(pending))
    for job in jobs:
        row=read(RUN/'jobs'/job['job_id']/'record.json')
        _,bundle,candidate=load_job(job['job_id'])
        require_complete_review(row,bundle)
        covered=delivery(job,bundle)
        raw=read(RUN/'jobs'/job['job_id']/'draft-history'/(row['run_metadata']['raw_draft_sha256']+'.json'))
        expected=normalize(raw,job,bundle,candidate,covered)
        assert {k:v for k,v in expected.items() if k!='run_metadata'}=={k:v for k,v in row.items() if k!='run_metadata'},job['job_id']
        assert covered['all_readable_text_delivered']
    controls={'critic':control_critic(read(RUN/'hidden-controls/critic-key.json'),read(RUN/'jobs/control_critic/record.json'))}
    for role in ['control_extractor','control_blind']:
        controls[role]=control_inventory(read(RUN/'hidden-controls/inventory-key.json'),read(RUN/'jobs'/role/'record.json'))
    report={'status':'passed' if all(c['passed'] for c in controls.values()) else 'failed',
            'controls':controls,'natural_semantic_accuracy':'not_estimated','development_jobs':len(jobs)}
    target=RUN/'development-gate.json'
    payload=enc(report)
    if target.exists() and target.read_bytes()!=payload:
        raise ValueError('Preserve first development gate')
    if not target.exists():
        target.write_bytes(payload)
    if report['status']!='passed':
        raise ValueError('Construction gate failed; fresh evidence stays closed')
    # Gzip was copied unopened earlier. Release itself inventories text only now.
    selected=read(RUN/'selection.json')['selected']
    stats=[]
    for row in selected:
        bundle=json.loads(gzip.decompress((RUN/f'inputs/cases/{row["case_id"]}/bundle.json.gz').read_bytes()))
        assert bundle['accession']==row['accession']
        stats.append({'case_id':row['case_id'],'accession':row['accession'],
                      'readable_characters':sum(len(d['text']) for d in bundle['documents'] if d.get('text'))})
    release={'released_case_ids':[r['case_id'] for r in selected],
             'development_gate_sha256':sha(target.read_bytes()),'source_inventory':stats,
             'status':'now_model_exposed_operational_cases_not_accuracy_references','remaining_reserved':7}
    target=RUN/'fresh-release.json'
    payload=enc(release)
    if target.exists() and target.read_bytes()!=payload:
        raise ValueError('Release record changed')
    target.write_bytes(payload)
    print(json.dumps(release,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','status','release-fresh'])
    args=parser.parse_args()
    if args.action=='prepare':
        prepare()
    elif args.action=='release-fresh':
        release_fresh()
    else:
        print(json.dumps(progress(),indent=2))


if __name__=='__main__':
    main()
