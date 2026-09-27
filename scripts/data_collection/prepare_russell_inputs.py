"""Tier: 2. Prepare dated Russell membership joins and ETF daily panel.
Inputs: frozen schedules/registry, monthly vendor records, historical CRSP pages.
Outputs: immutable assignments, ETF panel, identity evidence and provenance.
Identity: exact historical CUSIP8 match at prior month end, never later membership.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/prepare_russell_inputs.py
"""
import bisect
import json
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path
from run_phase1_development import ROOT, INPUT, RAW, FIELDS, freeze, encode, digest, read_page, build_panel
from collect_russell_membership import snapshot_date, OUT, BASE
from activist13d.russell_benchmark import ETFS, assign

PROTOCOL=ROOT/'research/protocol/phase1-russell-v1.md'
MEMBERSHIP_FIELDS=['cusip','date','name','russell1000','russell2000','russellmc','r1000_wt','r2000_wt','rmidc_wt']


def main():
    baseline=json.loads((BASE/'provenance.json').read_text())
    assert digest(BASE/'selection.json')==baseline['files']['selection.json']
    assert digest(INPUT/'event-candidates.jsonl')==baseline['registry_sha256']
    assert digest(INPUT/'entry-calendar.json')==baseline['calendar_sha256']
    freeze(OUT/'protocol.md',PROTOCOL.read_bytes())
    plans=json.loads((BASE/'selection.json').read_text())['plans']
    registry={r['accession']:r for line in (INPUT/'event-candidates.jsonl').read_text().splitlines() if (r:=json.loads(line))}
    sessions=json.loads((INPUT/'entry-calendar.json').read_text())
    inventory={}
    days=sorted({d for events in plans.values() for e in events for d in e['days']})
    assert days[-1]<='2023-12-29'
    panel_path=OUT/'etf-panel.json'
    if panel_path.exists():
        panel=json.loads(panel_path.read_text())
        inventory=json.loads((OUT/'panel-source-inventory.json').read_text())
    else:
        panel,missing=build_panel({'etfs':[dict(permno=p,days=days) for p in ETFS.values()]},inventory)
        assert not missing
        panel={str(k):v for k,v in panel.items()}
        freeze(panel_path,encode(panel))
        freeze(OUT/'panel-source-inventory.json',encode(inventory))
    identities=[]
    for p in sorted((RAW/'crsp.stocknames_v2').glob('*.json.gz')):
        payload,meta=read_page(p,inventory)
        if meta['request']['method']!='GET':
            continue
        for r in payload.get('results',[]):
            if r.get('permno') in ETFS.values() and r.get('ticker') in ETFS and ETFS[r['ticker']]==r['permno'] and r.get('securitysubtype')=='ETF' and r['namedt']<=days[0] and r['nameenddt']>=days[-1]:
                identities.append(dict(source=str(p.relative_to(ROOT)),row=r))
    assert {r['row']['permno'] for r in identities}==set(ETFS.values())
    targets=defaultdict(set)
    event_info={}
    for events in plans.values():
        for e in events:
            public=min(registry[a]['acceptance_datetime_et'][:10] for a in e['accessions'])
            snap=snapshot_date(public,sessions)
            assert snap<public and 0<(date.fromisoformat(public)-date.fromisoformat(snap)).days<=35
            pre=sessions[bisect.bisect_left(sessions,public)-1]
            targets[snap].add(e['permno'])
            targets[pre].add(e['permno'])
            event_info[(e['accession'],e['entry'])]=(public,snap,pre)
    pages={}
    for p in sorted((RAW/'crsp.dsf_v2').glob('*.meta.json')):
        m=json.loads(p.read_text())
        params=m['request'].get('params',{})
        d=params.get('dlycaldt')
        if d in targets and m['request']['method']=='GET' and params=={'dlycaldt':d,'limit':50000,'offset':0}:
            assert d not in pages
            pages[d]=p.with_name(p.name.replace('.meta.json','.gz'))
    historic={}
    for i,(d,securities) in enumerate(sorted(targets.items())):
        if d not in pages:
            continue
        payload,_=read_page(pages[d],inventory)
        rows=payload.get('results',[])
        assert len(rows)<50000 and not payload.get('next')
        assert all(r['dlycaldt']==d for r in rows) and len({r['permno'] for r in rows})==len(rows)
        for r in rows:
            if r['permno'] in securities:
                historic[(d,r['permno'])]={k:r.get(k) for k in ['cusip','permco','dlycap','usincflg','securitytype','securitysubtype','issuertype']}
        if i%100==0:
            print('Historical identifiers',i+1,len(targets),flush=True)
    memberships={}
    receipts=json.loads((OUT/'membership-receipt.json').read_text())
    for rec in receipts:
        payload,_=read_page(ROOT/rec['source'],inventory)
        by_cusip=defaultdict(list)
        for r in payload['results']:
            c=r.get('cusip')
            if isinstance(c,str) and len(c)==9:
                by_cusip[c[:8]].append({k:r.get(k) for k in MEMBERSHIP_FIELDS})
        memberships[rec['date']]=by_cusip
    assignments={}
    for (accession,entry),(public,snap,pre) in sorted(event_info.items()):
        e=next(e for events in plans.values() for e in events if e['accession']==accession and e['entry']==entry)
        old=historic.get((snap,e['permno']))
        current=historic.get((pre,e['permno']))
        symbol=None
        hits=[]
        if not old or not current:
            status='missing_historical_security'
        elif old.get('permco') is None or old['permco']!=current.get('permco'):
            status='changed_or_missing_company_identity'
        elif not isinstance(old.get('cusip'),str) or len(old['cusip'])!=8:
            status='invalid_historical_cusip'
        else:
            hits=memberships[snap].get(old['cusip'],[])
            symbol,status=assign(hits)
        assignments[accession+'|'+entry]=dict(accession=accession,entry=entry,permno=e['permno'],public_date=public,snapshot_date=snap,
            pre_disclosure_date=pre,snapshot_security=old,pre_disclosure_security=current,matched_rows=hits,etf=symbol,status=status)
    freeze(OUT/'assignments.json',encode(assignments))
    freeze(OUT/'etf-identities.json',encode(identities))
    freeze(OUT/'source-inventory.json',encode(inventory))
    for p in [Path(__file__),ROOT/'scripts/data_collection/collect_russell_membership.py',ROOT/'src/activist13d/russell_benchmark.py']:
        freeze(OUT/'code'/p.name,p.read_bytes())
    freeze(OUT/'provenance.json',encode(dict(inputs={str(p.relative_to(ROOT)):digest(p) for p in [BASE/'selection.json',INPUT/'event-candidates.jsonl',INPUT/'entry-calendar.json',PROTOCOL]},outputs={str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='provenance.json'})))
    print(encode(dict(assignment_statuses=dict(Counter(r['status'] for r in assignments.values())),etfs=dict(Counter(r['etf'] or 'unmatched' for r in assignments.values())))))


if __name__=='__main__':
    main()
