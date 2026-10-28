"""Reconcile ten Bloomberg rows against dated primary financial disclosures.

Inputs: immutable original-workbook snapshot and three sourced research JSONs.
Outputs: dated event findings, 90-slot field inventory, source comparisons,
correction queue and hashes. Identity: USD=source_value*source_multiplier;
publication-date comparison is separate from numerical/issuer/vintage agreement.
Tier: 1. No workbook edits, recalculation, downloads, fitting or outcome access.
Run: project Python scripts/ml_experiment/audit_bloomberg_timing.py [--verify].
"""
import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/bloomberg-timing/20261026-v1'
FIELD_MAP={'total_assets':'bs_tot_asset','revenue':'SALES_REV_TURN',
           'net_income':'NET_INCOME','net_income_loss':'NET_INCOME',
           'cash_and_cash_equivalents':'bs_cash_near_cash_item','cash':'bs_cash_near_cash_item',
           'total_liabilities':'BS_TOT_LIAB2','common_equity':'TOT_COMMON_EQY',
           'total_stockholders_equity':'TOT_COMMON_EQY'}
FIELDS=['bs_tot_asset','BS_TOT_LIAB2','TOT_DEBT_TO_TOT_ASSET','bs_cash_near_cash_item',
        'TOT_COMMON_EQY','SALES_REV_TURN','NET_INCOME','IS_OPER_INC','EBITDA']
ISSUES={'F01':['post_cutoff_results'],'F02':[],'F03':[],'F04':['historical_revision'],
        'F05':[],'F06':['historical_issuer_mismatch'],'F07':['post_cutoff_results'],
        'F08':[],'F09':['field_definition_unresolved'],'F10':['older_annual_period']}
DISPOSITIONS={
    'F01':'Replace selected FY2018 with the latest period actually public by cutoff; retain as-reported vintage.',
    'F02':'Three representative values match a pre-cutoff original release; other fields and Bloomberg vintage remain unverified.',
    'F03':'Original annual-report values match and FY2017 release predates cutoff; obtain exact filing metadata if exact-version publication proof is required.',
    'F04':'Replace recast values with original as-reported financials, or establish field-specific pre-cutoff evidence for the recast.',
    'F05':'Use the pre-cutoff March24 original10-K version for checked figures, rather than the differing March16 preliminary release.',
    'F06':'Remap to historical Catalyst CIK1124105/security; do not use the GlycoMimetics/Crescent CIK1253689 history. Requery all nine fields with stable historical vendor IDs.',
    'F07':'Replace selected FY2021 with an actually available period/vintage; FY2020 results were public February16,2021.',
    'F08':'Selected representative figures match original pre-cutoff statements; retain preferred-stock and net-income definitions.',
    'F09':'Reconcile cash and common-equity definitions to original bank statements; do not silently substitute a broader cash measure.',
    'F10':'Select latest annual filing actually public by cutoff: FY2021 endedJanuary30,2021, filedMarch24,2021; selected FY2020 is one annual period older.'}


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def amount_comparison(workbook_value, source_value, multiplier=1):
    if not finite(source_value) or not finite(multiplier) or multiplier<=0:
        raise ValueError('Invalid source amount or units')
    expected=source_value*multiplier
    if not finite(workbook_value):
        return {'status':'workbook_missing_or_error','source_usd':expected,'difference_usd':None}
    difference=workbook_value-expected
    return {'status':'match' if abs(difference)<=.01 else 'difference_requires_reconciliation',
            'source_usd':expected,'difference_usd':difference}


def date_position(observed, cutoff):
    if observed is None:
        return 'unknown'
    a,b=date.fromisoformat(observed),date.fromisoformat(cutoff)
    return 'before' if a<b else 'after' if a>b else 'same_day_time_unverified'


def encode(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def csv_bytes(rows):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def build():
    source_hashes={}

    def load(name):
        path=RUN/name
        source_hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())

    selected=load('selected-workbook-rows.json')
    receipt=load('input-receipt.json')
    a,b,own=[load(f'research/group-{g}.json') for g in ['a','b','root']]
    for name,expected in receipt['source_sha256'].items():
        path=Path(name) if name.startswith('/') else ROOT/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
    ac={r['case_id']:r for r in a['cases']}
    bc={r['case_id']:r for r in b['rows']}
    oc={r['case_id']:r for r in own['cases']}
    assert len(set(ac)|set(bc)|set(oc))==10
    sources={**{s['id']:s for s in a['sources']},**{s['id']:s for s in b['sources']}}
    findings,comparisons,additional=[],[],[]
    for row in selected:
        cid=row['case_id']
        raw=row['workbook_views']['BQL Raw Nine']['values']
        if cid in ac:
            evidence=ac[cid]
            period=evidence['period_end']
            original_date=evidence['original_period_release_date']
            original_type='company release'
            version_date=evidence['observed_publication_date']
            source_list=[sources[evidence['observed_publication_source']]]
            main=evidence['numeric_comparisons']
            conclusion=evidence['timing_conclusion_interpretation']
            limits=evidence['unresolved']
            for c in main:
                field=FIELD_MAP[c['field']]
                assert raw[field]==c['workbook_amount_usd']
                s=sources[c['source_id']]
                comparisons.append({'case_id':cid,'field':field,'workbook_value':raw[field],
                                    **amount_comparison(raw[field],c['source_amount'],c['source_multiplier']),
                                    'source_label':c['field'],'source_url':s['url'],
                                    'source_date':s.get('date'),'source_date_kind':s.get('date_type','document_date')})
            for c in evidence.get('later_recast_comparisons',[]):
                s=sources[c['source_id']]
                field=FIELD_MAP[c['field']]
                additional.append({'case_id':cid,'kind':'later_accounting_recast','field':field,
                                   'workbook_value':raw[field],**amount_comparison(raw[field],c['source_amount'],c['source_multiplier']),
                                   'source_url':s['url'],'source_date':s.get('date'),
                                   'date_kind':s.get('date_type'),'limit':'Report/signature date is not independently retrieved publication timestamp.'})
            if cid=='F04':
                source_list=[sources[k] for k in ['W1','W2','W3','W4','W5']]
            elif cid=='F03':
                source_list=[sources[k] for k in ['G1','G2','G3']]
            elif cid=='F05':
                source_list=[sources[k] for k in ['U1','U2','U3']]
        elif cid in bc:
            evidence=bc[cid]
            period=evidence['exact_fiscal_year_end']
            original_date=evidence['observed_annual_release_date'] or evidence['observed_10k_filing_date']
            original_type='company release' if evidence['observed_annual_release_date'] else '10-K filing'
            version_date=evidence['observed_10k_filing_date'] if cid=='F10' else original_date
            source_list=[sources[k] for k in dict.fromkeys(evidence['date_source_ids']+evidence['identity_source_ids'])]
            conclusion=evidence['timing_conclusion']
            limits=evidence['unresolved']
            for c in evidence['comparisons']+evidence.get('additional_definition_mismatches',[]):
                field=FIELD_MAP[c['field']]
                assert math.isclose(raw[field],c['workbook_usd'],abs_tol=.01)
                s=sources[c['source_id']]
                comparisons.append({'case_id':cid,'field':field,'workbook_value':raw[field],
                                    **amount_comparison(raw[field],c['published_usd']),
                                    'source_label':c.get('note',c['field']),'source_url':s['url'],
                                    'source_date':s['document_date'],'source_date_kind':s['date_basis']})
            if cid=='F06':
                alt=evidence['alternative_exact_match']
                for name,value in alt['figures_usd'].items():
                    field=FIELD_MAP[name]
                    additional.append({'case_id':cid,'kind':'different_historical_issuer_exact_match',
                                       'field':field,'workbook_value':raw[field],**amount_comparison(raw[field],value),
                                       'source_url':sources['glyc_2018_10k']['url'],
                                       'source_date':alt['observed_release_date'],'historical_cik':alt['cik'],
                                       'historical_ticker':alt['historical_ticker']})
                source_list += [sources[k] for k in ['glyc_2018_10k','glyc_2018_release','crescent_2025_release']]
            if cid=='F10':
                source_list += [sources[k] for k in evidence['latest_annual_by_cutoff']['source_ids']]
        else:
            evidence=oc[cid]
            period=evidence['period_end']
            original_date=evidence['original_period_publication_date']
            original_type=evidence['publication_kind']
            version_date=evidence['compatible_values_observed_publication_date']
            source_list=[{'title':evidence['primary_title'],'url':evidence['primary_url'],'date':original_date}]+evidence.get('additional_sources',[])
            conclusion=evidence['interpretation']
            limits=['Observed release is not a proven earliest date for each individual field; all nine Bloomberg definitions and vintage remain unverified.']
            for c in evidence['comparisons']:
                comparisons.append({'case_id':cid,'field':c['field'],'workbook_value':raw[c['field']],
                                    **amount_comparison(raw[c['field']],c['source_value'],c['source_multiplier']),
                                    'source_label':c['source_label'],'source_url':evidence['primary_url'],
                                    'source_date':original_date,'source_date_kind':'company results release'})
        assert row['candidate_fiscal_year']==date.fromisoformat(period).year or cid=='F10'
        details={'F04':'Original period released March10,2023. Exact workbook figures equal later LDTI recasts; their earliest public dates were not established.',
                 'F03':'FY2017 release November30,2017; exact values match original annual report, but exact SEC publication timestamp not retrieved.',
                 'F05':'Initial March16,2023 release differs; March24 original10-K matches before cutoff.',
                 'F06':'Correct Catalyst annual period predates cutoff, but selected values match another issuer.',
                 'F10':'FY2020 ends January25,2020; FY2021 endedJanuary30,2021 was already public.'}.get(cid,'')
        findings.append({**{k:row[k] for k in ['case_id','row_id','company','issuer_cik','filing_accepted_et','filing_date','entry_date','financial_cutoff_date','candidate_fiscal_year']},
                         'period_end':period,'original_period_observed_date':original_date,
                         'original_period_date_kind':original_type,
                         'period_date_vs_cutoff':date_position(original_date,row['financial_cutoff_date']),
                         'period_date_vs_filing':date_position(original_date,row['filing_date']),
                         'period_date_vs_entry':date_position(original_date,row['entry_date']),
                         'compatible_value_version_date':version_date,
                         'compatible_value_date_limit':details,
                         'issue_flags':ISSUES[cid],
                         'assessment':'correction_or_definition_work_needed' if ISSUES[cid] else 'no_material_issue_identified_in_bounded_spotcheck',
                         'conclusion':conclusion,'next_action':DISPOSITIONS[cid],
                         'unresolved':limits,'primary_sources':source_list,
                         'all_nine_fields_historically_certified':False})
    # A slot means one of nine selected raw fields, not a completed validation.
    by_field={(r['case_id'],r['field']):r for r in comparisons}
    assert len(by_field)==len(comparisons)
    field_rows=[]
    for row in selected:
        values=row['workbook_views']['BQL Raw Nine']['values']
        excel_row=row['workbook_views']['BQL Raw Nine']['excel_row']
        for field in FIELDS:
            comparison=by_field.get((row['case_id'],field))
            field_rows.append({'case_id':row['case_id'],'company':row['company'],'field':field,
                               'raw_cell':f'{chr(70+FIELDS.index(field))}{excel_row}',
                               'workbook_value':values[field],
                               'comparison_status':comparison['status'] if comparison else 'not_externally_compared_in_this_check',
                               'source_usd':comparison['source_usd'] if comparison else None,
                               'difference_usd':comparison['difference_usd'] if comparison else None,
                               'source_url':comparison['source_url'] if comparison else None,
                               'historical_vintage_certified':False})
    counts=Counter(flag for f in findings for flag in f['issue_flags'])
    summary={'selected_events':len(findings),'selected_raw_field_slots':len(field_rows),
             'period_dates_before_cutoff':sum(f['period_date_vs_cutoff']=='before' for f in findings),
             'period_dates_after_cutoff':sum(f['period_date_vs_cutoff']=='after' for f in findings),
             'events_with_identified_issues':sum(bool(f['issue_flags']) for f in findings),
             'events_without_identified_material_issue_in_spotcheck':sum(not f['issue_flags'] for f in findings),
             'issue_counts':dict(counts),'primary_source_amount_comparisons':len(comparisons),
             'amount_comparison_status':dict(Counter(r['status'] for r in comparisons)),
             'additional_recast_or_other_issuer_comparisons':len(additional),
             'all_nine_historical_field_certifications':0,
             'sample_limitation':'Deliberately selected ten-event pilot includes a known-conflict control; counts do not estimate full-sample error rates.',
             'workbook_unchanged':True,'model_fitted':False,'new_return_calculation':False,
             'original_workbook_sha256':receipt['workbook_sha256']}
    assert summary['selected_events']==10 and summary['selected_raw_field_slots']==90
    queue=[{k:f[k] for k in ['case_id','company','filing_date','financial_cutoff_date','period_end','original_period_observed_date','assessment','next_action']} for f in findings]
    payloads={'findings.json':encode(findings),'summary.json':encode(summary),
              'amount-comparisons.json':encode(comparisons),'additional-version-checks.json':encode(additional),
              'field-checks.csv':csv_bytes(field_rows),'correction-queue.csv':csv_bytes(queue)}
    source_hashes['scripts/ml_experiment/audit_bloomberg_timing.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    payloads['provenance.json']=encode({'evidence_sha256':source_hashes,
                                       'outputs_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in payloads.items()},
                                       'replay':'Offline recalculation from frozen manually gathered evidence; does not rerun web research or authenticate Bloomberg query settings.'})
    return payloads,summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    artifacts,summary=build()
    for name,payload in artifacts.items():
        target=RUN/name
        if args.verify or target.exists():
            assert target.read_bytes()==payload,name
        else:
            target.write_bytes(payload)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
