"""Build an outcome-free, auditable 13D model input snapshot.

Inputs: frozen 667-row baseline features/event map, production and earlier v3
reader/critic records and comparisons, model-input-table-v1 measurement contract.
Outputs: model_inputs.csv, features.jsonl, objective/funding audits, dictionary,
coverage, summary and hashed provenance under a new dated research run.
Identity: 667 = 627 production + 13 earlier + 27 protected; 640*9 objective cells;
reader frequency = count(state)/2; eligible = matching nonunknown + critic support.
Funding frequency = readers with confirmed_actual/current_acquisition type / 2,
only after the declared conservative all-funding eligibility gate.
Tier: 1 experimental measurement preparation. No targets, fitting or network.
Run: env PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/build_model_input_table.py [--verify]
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/model-input-table/20261105-v1'
BASE = ROOT / 'research/runs/extraction-batches/20261028-v1'
PRIOR = ROOT / 'research/runs/extraction-revision/20261027-v3'
PREVIEW = ROOT / 'research/runs/ml-feature-preview/20261012-v1'
PROTOCOL = ROOT / 'research/protocol/model-input-table-v1.json'
CATEGORIES = ('asset_transaction', 'board_representation', 'capital_return',
              'capital_structure', 'governance_change', 'leadership_change',
              'operational_change', 'other_stated_objective', 'sale_of_company')
STATES = ('present', 'not_stated', 'cannot_determine')
HASHES = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(path):
    relative = str(path.relative_to(ROOT))
    require(not any(t in relative for t in ('targets.jsonl', 'row-metadata.jsonl', 'panels.json', 'hidden-controls', 'human-first', 'review/current', 'bundle.json', 'submission.txt')), 'Forbidden input: '+relative)
    blob = path.read_bytes()
    HASHES[relative] = hashlib.sha256(blob).hexdigest()
    return blob


def read(path):
    return json.loads(raw(path))


def objective_measurement(first, second, critic):
    require(first in STATES and second in STATES, 'Invalid objective state')
    require(critic in ('supported', 'contradicted', 'insufficient_evidence'), 'Invalid critic verdict')
    frequencies = {state: (int(first == state)+int(second == state))/2 for state in STATES}
    eligible = first == second and first != 'cannot_determine' and critic == 'supported'
    reason = ('eligible' if eligible else 'reader_disagreement' if first != second
              else 'shared_unknown' if first == 'cannot_determine'
              else 'matching_nonunknown_without_critic_support')
    return {'extractor': first, 'blind': second, 'critic': critic,
            'state_frequency': frequencies, 'eligible': eligible, 'reason': reason}


def funding_signature(components):
    return Counter((re.sub('[^a-z0-9]', '', c['actor'].lower()), c['type'],
                    c['certainty'], c['acquisition_link']) for c in components)


def funding_measurement(first, second, reviews, funding_types):
    expected = {'funding.summary'} | {f'funding.component.{i:03}' for i in range(1, len(first['components'])+1)}
    require(set(reviews) == expected, 'Funding claim coverage mismatch')
    require(first['status'] in STATES and second['status'] in STATES, 'Invalid funding status')
    reasons = []
    if first['status'] != second['status']: reasons.append('reader_status_disagreement')
    if 'cannot_determine' in (first['status'], second['status']): reasons.append('reader_unknown')
    equal = funding_signature(first['components']) == funding_signature(second['components'])
    if not equal: reasons.append('qualified_tuple_difference')
    if any(v != 'supported' for v in reviews.values()): reasons.append('critic_flag')
    components = first['components'] + second['components']
    if any(c['type'] not in funding_types or c['certainty'] == 'not_disclosed' or c['acquisition_link'] == 'unknown' for c in components):
        reasons.append('unresolved_component_qualifier')
    if any(f['status'] == 'not_stated' and f['components'] for f in (first,second)):
        reasons.append('not_stated_with_components')
    if any(f['status'] == 'present' and not f['components'] for f in (first,second)):
        reasons.append('present_without_components')
    raw_frequencies = {}
    for kind in funding_types:
        raw_frequencies[kind] = sum(any(c['type'] == kind and c['certainty'] == 'confirmed_actual' and c['acquisition_link'] == 'current_acquisition' for c in f['components']) for f in (first, second))/2
    eligible = not reasons
    return {'eligible': eligible, 'reasons': reasons, 'tuple_agreement': equal,
            'critic_flags': sum(v != 'supported' for v in reviews.values()),
            'raw_frequencies': raw_frequencies,
            'features': {k: v if eligible else None for k,v in raw_frequencies.items()}}


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode()


def csv_bytes(rows, fields=None):
    fields = fields or list(rows[0])
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def emit(name, blob, verify):
    path = OUT / name
    if verify or path.exists():
        require(path.is_file() and path.read_bytes() == blob, 'Replay differs or file missing: '+name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def build(verify=False):
    contract = read(PROTOCOL)
    types = contract['funding_types']
    queue = read(BASE/'queue.json')
    base_dictionary = read(PREVIEW/'feature-dictionary.json')['features']
    baseline = [json.loads(line) for line in raw(PREVIEW/'features.jsonl').decode().splitlines()]
    require(len(baseline) == len({r['row_id'] for r in baseline}) == 667, 'Baseline keys')
    baseline_map = {r['row_id']: r['features'] for r in baseline}
    events = list(csv.DictReader(io.StringIO(raw(ROOT/'research/runs/bloomberg-extraction-handoff/20261017-v2/event_requests.csv').decode())))
    require(len(events) == len({e['row_id'] for e in events}) == 667, 'Event keys')
    require(set(baseline_map) == {e['row_id'] for e in events}, 'Baseline/event exact join')
    metadata = {r['accession']: r for r in queue['queue']+queue['excluded']}
    require(len(metadata) == 667, 'Queue accession uniqueness')
    protected = {r['accession'] for r in queue['excluded'] if r['reason'] == 'unreleased_reserved_connected_group'}
    earlier = {r['accession'] for r in queue['excluded'] if r['reason'] == 'already_completed_v3'}
    require(len(protected) == 27 and len(earlier) == 13, 'Frozen scope counts')
    comparisons, records, locations = {}, {}, {}
    production_accessions = set()
    for run in [PRIOR] + [BASE/f'batch-{i:03}' for i in range(1,127)]:
        comps = read(run/'case-comparisons.json')
        for comp in comps:
            accession = comp['accession']
            require(accession not in protected and accession not in comparisons, 'Protected or duplicate comparison')
            comparisons[accession] = comp
            locations[accession] = run
            if run != PRIOR: production_accessions.add(accession)
        for job in read(run/'jobs.json'):
            if job['role'] not in ('extractor','blind','critic'): continue
            require(job['accession'] not in protected, 'Refuse protected role record')
            require(job['accession'] in {c['accession'] for c in comps}, 'Role outside this run comparisons')
            record_path = run/'jobs'/job['job_id']/'record.json'
            record = read(record_path)
            require(record['run_metadata']['accession'] == job['accession'], 'Role accession mismatch')
            require(record['run_metadata']['role'] == job['role'], 'Role mismatch')
            require(record['run_metadata']['common_rules_sha256'] == 'f636ddf8ca39022a5ef9bc34d016b62898bb8bd12acd0e9971a71e0fcfe4ba02', 'Rule version drift')
            require(record['review_delivery']['all_readable_text_delivered'], 'Incomplete delivered source')
            key = (job['accession'], job['role'])
            require(key not in records, 'Duplicate role record')
            records[key] = (record, str(record_path.relative_to(ROOT)))
    require(len(comparisons) == 640 and len(records) == 1920 and len(production_accessions) == 627, 'Completed scope counts')
    require(set(comparisons) == set(metadata)-protected, 'Extraction scope exact join')
    source_controls = read(ROOT/'research/docs/extraction-results-review-20261102/analysis.json')['input_sha256']
    for path, digest in HASHES.items():
        if path in source_controls: require(digest == source_controls[path], 'Frozen report source changed: '+path)

    objective_columns = [f'obj__{cat}__{state}_freq' for cat in CATEGORIES for state in STATES]
    objective_masks = [f'obj__{cat}__unresolved' for cat in CATEGORIES]
    funding_columns = [f'funding__{kind}__confirmed_current_freq' for kind in types]
    baseline_columns = sorted(base_dictionary)
    text_columns = objective_columns + objective_masks + funding_columns + ['funding__unresolved']
    default_objectives = [f'obj__{cat}__present_freq' for cat in CATEGORIES] + objective_masks
    feature_sets = {'baseline': baseline_columns,
                    'baseline_plus_objectives': baseline_columns+default_objectives,
                    'baseline_plus_objectives_and_funding': baseline_columns+default_objectives+funding_columns+['funding__unresolved']}
    dictionaries = []
    for key, definition in sorted(base_dictionary.items()):
        dictionaries.append({'column': key, 'role': 'baseline_feature', 'kind': definition['kind'], 'unit': definition['unit'], 'definition': definition['description'], 'missing_rule': 'Preserve original null; no preparation-stage imputation', 'default_feature_sets': '|'.join(feature_sets), 'source': 'ml-feature-preview-v1'})
    for cat in CATEGORIES:
        for state in STATES:
            key=f'obj__{cat}__{state}_freq'
            dictionaries.append({'column':key,'role':'objective_feature' if state=='present' else 'retained_distribution','kind':'numeric','unit':'reader fraction','definition':f'Two-reader count of {state}/2 for {cat}, only if matching nonunknown plus critic support. Not a truth probability.','missing_rule':'Blank if excluded or protected','default_feature_sets':'|'.join(k for k,v in feature_sets.items() if key in v),'source':'frozen v3 reader/critic records'})
        dictionaries.append({'column':f'obj__{cat}__unresolved','role':'objective_feature','kind':'numeric','unit':'indicator','definition':'1 if the objective cell fails the experimental eligibility gate; 0 if eligible.','missing_rule':'Blank for protected rows; no inference from unprocessed text','default_feature_sets':'baseline_plus_objectives|baseline_plus_objectives_and_funding','source':'frozen v3 eligibility rule'})
    for kind in types:
        dictionaries.append({'column':f'funding__{kind}__confirmed_current_freq','role':'funding_feature','kind':'numeric','unit':'reader fraction','definition':f'Readers reporting {kind} with confirmed_actual AND current_acquisition / 2, after conservative full funding gate. Zero is absence of that qualifying extracted component, not proof of no financing.','missing_rule':'Blank if any funding gate fails or protected','default_feature_sets':'baseline_plus_objectives_and_funding','source':'model-input-table-v1; actor/qualifier-preserving funding records'})
    dictionaries.append({'column':'funding__unresolved','role':'funding_feature','kind':'numeric','unit':'indicator','definition':'1 if the full declared funding gate fails; 0 if eligible.','missing_rule':'Blank for protected rows','default_feature_sets':'baseline_plus_objectives_and_funding','source':'model-input-table-v1'})

    model_rows, objective_audit, funding_audit, components, lineage = [], [], [], [], []
    totals = {'production':Counter(), 'earlier':Counter()}
    for event in events:
        accession, row_id = event['accession'], event['row_id']
        meta = metadata[accession]
        require(meta['row_id'] == row_id and meta['issuer'] == event['issuer_cik'] and meta['accepted_et'] == event['accepted_et'], 'Identity disagreement: '+row_id)
        split = row_id.split('|')
        require(len(split)==3 and split[0]==accession and split[2]==event['accepted_et'][:10], 'Malformed event identity')
        require(event['as_of_date'] < event['accepted_et'][:10] < split[1], 'Cutoff/publication/entry chronology')
        require(set(baseline_map[row_id]) == set(baseline_columns), 'Baseline column drift')
        cohort = 'protected_connected' if accession in protected else 'earlier_v3' if accession in earlier else 'production'
        row = {'row_id':row_id,'accession':accession,'issuer_name':event['issuer_name_sec'],'issuer_cik':event['issuer_cik'],'permno':event['permno'],
               'accepted_et':event['accepted_et'],'entry_date':split[1],'financial_as_of_date':event['as_of_date'],'cutoff_timezone':event['cutoff_timezone'],
               'extraction_cohort':cohort,'primary_development_scope':int(cohort=='production'),'extraction_case_id':None,
               'objective_eligible_cells':None,'objective_unresolved_cells':None,'funding_transform_status':'not_processed_protected' if accession in protected else None,
               'source_url':meta['source_url'],'source_sha256':meta['source_sha256']}
        row.update(baseline_map[row_id])
        row.update({key:None for key in text_columns})
        if accession not in protected:
            comp = comparisons[accession]
            row['extraction_case_id'] = comp['case_id']
            reader, reader_path = records[accession,'extractor']
            blind, blind_path = records[accession,'blind']
            critic, critic_path = records[accession,'critic']
            reviews = {r['claim_id']:r for r in critic['reviews']}
            require(len(reviews)==len(critic['reviews']), 'Duplicate critic claims')
            require(set(reader['intent'])==set(blind['intent'])==set(CATEGORIES), 'Objective category drift')
            oldcells = {c['category']:c for c in comp['intent']}
            eligible_count = 0
            group = 'production' if cohort=='production' else 'earlier'
            totals[group]['filings'] += 1
            for cat in CATEGORIES:
                measure = objective_measurement(reader['intent'][cat]['status'], blind['intent'][cat]['status'], reviews['intent.'+cat]['verdict'])
                old = oldcells[cat]
                require(measure['eligible']==old['eligible_experimental_label'] and measure['state_frequency']==old['state_frequency'] and measure['extractor']==old['extractor'] and measure['blind']==old['blind'] and measure['critic']==old['critic'], 'Saved comparison parity: '+accession+'/'+cat)
                for state in STATES:
                    row[f'obj__{cat}__{state}_freq'] = measure['state_frequency'][state] if measure['eligible'] else None
                row[f'obj__{cat}__unresolved'] = int(not measure['eligible'])
                eligible_count += measure['eligible']
                totals[group]['objective_cells'] += 1
                totals[group][measure['reason']] += 1
                if measure['eligible']: totals[group]['eligible_'+measure['extractor']] += 1
                objective_audit.append({'row_id':row_id,'accession':accession,'case_id':comp['case_id'],'cohort':cohort,'category':cat,
                    'extractor_state':measure['extractor'],'blind_state':measure['blind'],'critic_verdict':measure['critic'],
                    **{f'raw_{state}_freq':measure['state_frequency'][state] for state in STATES},
                    'eligible_experimental':int(measure['eligible']),'exclusion_reason':measure['reason'],
                    'extractor_record':reader_path,'blind_record':blind_path,'critic_record':critic_path})
                lineage.append({'row_id':row_id,'field':'intent.'+cat,'extractor':reader['intent'][cat],'blind':blind['intent'][cat], 'critic':reviews['intent.'+cat], 'record_paths':{'extractor':reader_path,'blind':blind_path,'critic':critic_path}})
            row['objective_eligible_cells'],row['objective_unresolved_cells'] = eligible_count,9-eligible_count
            fund_reviews={k:v['verdict'] for k,v in reviews.items() if k.startswith('funding.')}
            fund = funding_measurement(reader['funding'],blind['funding'],fund_reviews,types)
            require(fund['tuple_agreement'] == (not comp['funding_difference']['only_extractor'] and not comp['funding_difference']['only_blind']), 'Funding tuple parity')
            row['funding_transform_status'] = 'eligible_experimental' if fund['eligible'] else '|'.join(fund['reasons'])
            row['funding__unresolved'] = int(not fund['eligible'])
            for kind,value in fund['features'].items(): row[f'funding__{kind}__confirmed_current_freq']=value
            totals[group]['funding_eligible' if fund['eligible'] else 'funding_withheld'] += 1
            funding_audit.append({'row_id':row_id,'accession':accession,'case_id':comp['case_id'],'cohort':cohort,
                'extractor_status':reader['funding']['status'],'blind_status':blind['funding']['status'],
                'qualified_tuple_agreement':int(fund['tuple_agreement']),'critic_flags':fund['critic_flags'],
                'eligible_experimental':int(fund['eligible']),'reasons':'|'.join(fund['reasons']),
                **{f'raw_{k}_confirmed_current_freq':v for k,v in fund['raw_frequencies'].items()},
                'extractor_record':reader_path,'blind_record':blind_path,'critic_record':critic_path})
            lineage.append({'row_id':row_id,'field':'funding','extractor':reader['funding'],'blind':blind['funding'], 'critic_reviews':{k:v for k,v in reviews.items() if k.startswith('funding.')},'measurement_gate':fund,'record_paths':{'extractor':reader_path,'blind':blind_path,'critic':critic_path}})
            for role, rec, rec_path in [('extractor',reader,reader_path),('blind',blind,blind_path)]:
                for index,component in enumerate(rec['funding']['components'],1):
                    components.append({'row_id':row_id,'accession':accession,'case_id':comp['case_id'],'cohort':cohort,'role':role,'component_index':index,
                        'actor':component['actor'],'type':component['type'],'certainty':component['certainty'],'acquisition_link':component['acquisition_link'],
                        'description':component['description'],'critic_verdict':fund_reviews[f'funding.component.{index:03}'] if role=='extractor' else 'not_separately_reviewed',
                        'record_path':rec_path,'evidence_json':json.dumps(component['evidence'],ensure_ascii=False,sort_keys=True)})
        model_rows.append(row)
    require(len(model_rows)==667 and len(objective_audit)==5760 and len(funding_audit)==640,'Output coverage')
    require(totals['production']['eligible']==5478 and totals['production']['eligible_present']==366 and totals['production']['eligible_not_stated']==5112,'Independent frozen production controls')
    require(totals['production']['reader_disagreement']==62 and totals['production']['shared_unknown']==65 and totals['production']['matching_nonunknown_without_critic_support']==38,'Independent unresolved controls')
    require(totals['earlier']['eligible']==109 and totals['earlier']['objective_cells']==117,'Earlier cohort controls')
    for row in model_rows:
        for key in text_columns:
            require(row[key] is None or row[key] in (0,0.5,1), 'Invalid feature range')
        if row['extraction_cohort']=='protected_connected': require(all(row[k] is None for k in text_columns),'Protected text feature contamination')
        require(all(row[k]==baseline_map[row['row_id']][k] for k in baseline_columns),'Baseline value altered')
    all_feature_names=baseline_columns+text_columns
    for item in dictionaries:
        require(item['column'] in all_feature_names,'Dictionary mismatch')
    require(len(dictionaries)==len(all_feature_names),'Dictionary completeness')
    metadata_columns=[key for key in model_rows[0] if key not in all_feature_names]
    for key in metadata_columns:
        dictionaries.append({'column':key,'role':'metadata_only','kind':'text' if key not in ('primary_development_scope','objective_eligible_cells','objective_unresolved_cells') else 'numeric','unit':'identifier/status/date','definition':{'primary_development_scope':'1 only for production cohort; scope flag, not a predictor','objective_eligible_cells':'Count of qualifying objective cells, not a model feature','objective_unresolved_cells':'Count of excluded objective cells, not a model feature','financial_as_of_date':'Existing financial cutoff; filing-text features become public at accepted_et, not this prior-session cutoff'}.get(key,'Event identity, coverage or provenance; excluded from all feature allowlists'),'missing_rule':'Null when unavailable; identifiers remain text','default_feature_sets':'','source':'Saved event map, queue and extraction metadata'})
    missingness={key:sum(row[key] is None for row in model_rows) for key in all_feature_names}
    summary={'version':contract['version'],'created_on':contract['created_on'],'status':'prepared_experimental_inputs_not_fitted',
        'panel_events':667,'production_events':627,'earlier_events':13,'protected_events':27,'extracted_events':640,
        'baseline_exact_matches':667,'extraction_exact_matches':640,'objective_audit_cells':5760,
        'cohort_totals':{key:dict(val) for key,val in totals.items()},'funding_component_rows':len(components),
        'feature_set_sizes':{key:len(val) for key,val in feature_sets.items()},'table_feature_columns':len(all_feature_names),
        'feature_null_counts':missingness,'adjudications_applied':0,'new_model_fits':0,'targets_read':False,'protected_text_read':False,
        'all_labels_experimental':True,'natural_data_accuracy':'not_estimated'}
    coverage=[{key:row[key] for key in metadata_columns} for row in model_rows]
    payload={'model_inputs.csv':csv_bytes(model_rows),'objective_readings.csv':csv_bytes(objective_audit),
        'funding_readings.csv':csv_bytes(funding_audit),'funding_components.csv':csv_bytes(components),
        'event_coverage.csv':csv_bytes(coverage),'column_dictionary.csv':csv_bytes(dictionaries),
        'feature_sets.json':encoded({'status':contract['status'],'feature_sets':feature_sets,'metadata_columns':metadata_columns,
             'primary_development_scope':'production only; protected excluded; earlier separately flagged',
             'preprocessing':'Not fitted. Any later imputation/scaling/one-hot encoding must use matured training rows only.'}),
        'summary.json':encoded(summary),
        'features.jsonl':''.join(json.dumps({'row_id':row['row_id'],'features':{k:row[k] for k in all_feature_names}},sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n' for row in model_rows).encode(),
        'evidence_lineage.jsonl':''.join(json.dumps(item,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n' for item in lineage).encode(),
        'workbook_data.json':encoded({'rows':model_rows,'objective_audit':objective_audit,'funding_audit':funding_audit,'dictionary':dictionaries,'summary':summary,'feature_sets':feature_sets})}
    raw(Path(__file__).resolve())
    provenance={'input_sha256':dict(sorted(HASHES.items())),'output_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(payload.items())},
        'join':{'panel_keys':667,'baseline_matches':667,'baseline_unmatched':0,'extraction_matches':640,'protected_unprocessed':27,'duplicate_keys':0},
        'forbidden_files_read':0,'no_fitting':True,'no_paid_calls':True,'no_adjudication':True}
    payload['provenance.json']=encoded(provenance)
    for name,blob in payload.items():emit(name,blob,verify)
    # After all processing, recheck source preservation, including role records.
    for name,expected in HASHES.items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,'Input changed during preparation: '+name)
    print(json.dumps({k:v for k,v in summary.items() if k!='feature_null_counts'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    build(parser.parse_args().verify)
