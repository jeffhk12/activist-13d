"""Build a portable corrected ten-event Bloomberg handoff, with empty results.

Inputs: frozen timing-audit rows/findings and a text handoff template. Outputs:
self-contained TXT, keyed CSV inputs/scaffolds, diagnostic JSON, manifest and ZIP.
Identity: 10 exact event IDs x 9 annual field candidates = 90 unique requests.
Tier: 1. No Bloomberg calls, source workbook edits, returns or live Excel authoring.
Run: project Python scripts/ml_experiment/build_bloomberg_remediation_handoff.py
 [--verify]. Downloads copies are created only after package validation.
"""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'research/runs/bloomberg-timing/20261026-v1'
RUN=ROOT/'research/runs/bloomberg-remediation-handoff/20261027-v1'
HANDOFF='13D_Bloomberg_Extraction_20261027.handoff.txt'
ARCHIVE='13D_Bloomberg_Pilot_20261027.zip'
FIELDS=[
 ('bs_tot_asset','Total assets','annual balance sheet','Consolidated assets; endpoint, entity, currency and scale'),
 ('BS_TOT_LIAB2','Total liabilities','annual balance sheet','Confirm components and scope; not equivalent to interest-bearing debt'),
 ('TOT_DEBT_TO_TOT_ASSET','Debt to assets','annual endpoint ratio','Confirm percentage/fraction, debt definition and leases; no assumed divisor'),
 ('bs_cash_near_cash_item','Cash measure','annual balance sheet','Verify cash/equivalents/deposits/investments/restricted-cash inclusions'),
 ('TOT_COMMON_EQY','Common book equity','annual balance sheet','Preferred carrying/liquidation basis, noncontrolling interests and negative equity'),
 ('SALES_REV_TURN','Revenue','annual actual flow','Record sales/financial-sector revenue definition; no TTM or estimates'),
 ('NET_INCOME','Net income','annual actual flow','Total/parent/common attribution; preferred dividends and noncontrolling interests'),
 ('IS_OPER_INC','Operating income','annual actual flow','Preserve definition; do not silently equate to EBIT'),
 ('EBITDA','EBITDA','annual actual flow','Reported/computed/adjusted basis; preserve missing/not-applicable states'),
]
RESULT_COLUMNS=['request_id','row_id','case_id','field_id','as_of_date','cutoff_timezone',
 'bloomberg_security_id','bloomberg_company_id','returned_company_name','returned_security_name',
 'returned_cik','returned_cusip','returned_share_class','historical_mapping_evidence',
 'raw_value','value','original_currency','unit','scale_multiplier','converted_currency',
 'fx_rate','fx_date','fx_source','period_start','period_end','issuer_fiscal_label','period_basis',
 'publication_datetime','publication_precision','publication_source_url','vendor_available_datetime',
 'revision_vintage','historical_version_method','vendor_field_definition','query_or_formula',
 'pull_datetime','status','raw_error','notes']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(data):
    return (json.dumps(data,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()


def csv_text(rows,columns):
    out=io.StringIO(newline='')
    writer=csv.DictWriter(out,fieldnames=columns,lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def request_rows(events):
    ids=[e['row_id'] for e in events]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate event IDs')
    return [{'request_id':e['row_id']+'|'+field[0],'row_id':e['row_id'],
             'case_id':e['case_id'],'field_id':field[0],'as_of_date':e['as_of_date'],
             'cutoff_timezone':'America/New_York','status':'not_requested'}
            for e in events for field in FIELDS]


def build():
    sources={}
    def read(path):
        raw=path.read_bytes()
        sources[str(path.relative_to(ROOT))]=sha(raw)
        return raw
    rows=json.loads(read(AUDIT/'selected-workbook-rows.json'))
    findings=json.loads(read(AUDIT/'findings.json'))
    summary=json.loads(read(AUDIT/'summary.json'))
    comparisons=json.loads(read(AUDIT/'amount-comparisons.json'))
    template=read(Path(__file__).with_name('bloomberg_remediation_handoff_template.txt')).decode()
    sources[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__).read_bytes())
    events=[]
    for r in rows:
        h=r['historical_identity']
        events.append({'case_id':r['case_id'],'row_id':r['row_id'],'accession':r['accession'],
                       'issuer_name_sec':r['company'],'issuer_cik':r['issuer_cik'],
                       'accepted_et':r['filing_accepted_et'],'entry_date':r['entry_date'],
                       'as_of_date':r['financial_cutoff_date'],'cutoff_timezone':'America/New_York',
                       'cutoff_rule':'end of supplied prior-session date',
                       'permno':h['permno'],'historical_company_name':h['historical_company_name'],
                       'historical_ticker':h['historical_ticker'],'historical_share_class':h['historical_share_class'],
                       'historical_cusip8':h['historical_cusip8'],
                       'filing_cusip9_candidate':h['filing_cusip9_candidate'],
                       'historical_name_start':h['historical_name_start'],'historical_name_end':h['historical_name_end'],
                       'ticker_seed_unverified':h['bloomberg_ticker_seed_unverified'],
                       'old_fy_label_diagnostic_only':r['candidate_fiscal_year']})
    assert len(events)==10 and len({e['row_id'] for e in events})==10
    requests=request_rows(events)
    assert len(requests)==len({r['request_id'] for r in requests})==90
    fields=[{'field_id':f[0],'candidate_vendor_mnemonic':f[0],'requested_measure':f[1],
             'basis':f[2],'definition_to_confirm':f[3],'vendor_confirmation':'not_yet_confirmed'} for f in FIELDS]
    controls=[]
    for f in findings:
        refs='\n'.join('  Source: '+s.get('title','Primary disclosure')+'\n  '+s['url'] for s in f['primary_sources'])
        controls.append(f'{f["case_id"]} {f["company"]}\n'
                        f'  13D: {f["filing_date"]}; financial cutoff: {f["financial_cutoff_date"]}; old FY endpoint: {f["period_end"]}.\n'
                        f'  Finding: {f["conclusion"]}\n  Action: {f["next_action"]}\n'+refs)
    event_csv=csv_text(events,list(events[0]))
    field_csv=csv_text(fields,list(fields[0]))
    text=(template.replace('{{EVENT_CSV}}',event_csv.rstrip()).replace('{{FIELD_CSV}}',field_csv.rstrip())
          .replace('{{CASE_CONTROLS}}','\n\n'.join(controls)).replace('{{RESULT_COLUMNS}}',', '.join(RESULT_COLUMNS)))
    assert '{{' not in text
    results=[{c:r.get(c,'') for c in RESULT_COLUMNS} for r in requests]
    assert all(r['value']==r['raw_value']==r['query_or_formula']=='' and r['status']=='not_requested' for r in results)
    queries=[{'field_id':f[0],'candidate_vendor_mnemonic':f[0],
              'confirmed_definition':'','confirmed_query_syntax':'','fiscal_period_control':'',
              'information_asof_control':'','revision_vintage_control':'','help_or_documentation_evidence':'',
              'tested_request_id':'','terminal_capability_status':'pending_validation'} for f in FIELDS]
    prompt='Read 13D_Bloomberg_Extraction_20261027.handoff.txt completely. Prepare the corrected ten-event/nine-annual-field pilot on this Bloomberg computer. Preserve exact IDs/cutoffs, verify historical identities and as-of versions, and keep unverified results explicit. Use the self-contained appendices if companion CSVs are absent. Do not invent Bloomberg query syntax, IDs or values. Do not run all667 until pilot review.\n'
    artifacts={HANDOFF:text.encode(),'chatgpt_prompt.txt':prompt.encode(),
               'pilot_events.csv':event_csv.encode(),'field_dictionary.csv':field_csv.encode(),
               'pilot_requests.csv':csv_text(requests,list(requests[0])).encode(),
               'result_template.csv':csv_text(results,RESULT_COLUMNS).encode(),
               'query_validation_template.csv':csv_text(queries,list(queries[0])).encode(),
               'diagnostic_controls.json':dump({'findings':findings,'amount_comparisons':comparisons,'summary':summary,
                                               'use':'Diagnostic source controls only; do not copy into purported Bloomberg results.'})}
    package={'prepared_on':'2026-10-27','scope':'corrected ten-event annual pilot only',
             'events':10,'fields':9,'requests':90,'live_queries_executed':0,
             'actual_results_populated':0,'source_workbook_modified':False,
             'old_667_event_handoff_superseded_for_this_pilot':True,
             'source_sha256':sources,'output_sha256':{n:sha(v) for n,v in artifacts.items()}}
    artifacts['package_manifest.json']=dump(package)
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in artifacts.items():
            item=zipfile.ZipInfo(name,date_time=(2026,10,27,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o644<<16
            z.writestr(item,data)
    artifacts[ARCHIVE]=archive.getvalue()
    return artifacts,package


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    artifacts,summary=build()
    RUN.mkdir(parents=True,exist_ok=True)
    for name,data in artifacts.items():
        p=RUN/name
        if args.verify or p.exists():
            assert p.read_bytes()==data,name
        else:
            p.write_bytes(data)
    print(json.dumps({k:summary[k] for k in ['events','fields','requests','live_queries_executed','actual_results_populated']},indent=2))


if __name__=='__main__':
    main()
