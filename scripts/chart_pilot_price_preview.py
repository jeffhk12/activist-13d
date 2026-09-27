"""Tier 1 exploratory preview: ten price paths around public 13D acceptance.
Inputs: frozen filing snapshot and cached Yahoo daily chart responses.
Outputs: PNG charts, daily CSV, checkpoints and reproducibility manifest.
Formula: index_t = 100 * vendor_split_adjusted_close_t / last_close_before_release.
T0 is filing calendar date (empty for holidays); +/-k counts US market sessions.
No dividends, trading strategy, inference or label updates. SPY is a price baseline.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/chart_pilot_price_preview.py
"""
from pathlib import Path
from datetime import datetime,time
from zoneinfo import ZoneInfo
import csv,json,hashlib,math,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review/archive/13d-price-preview-20260922';RAW=OUT/'raw'
records=json.loads((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text())
tickers=['MOBX','TPL','EGRX','SQFT','EVTL','LILA','MYCB','ALDF','RHLD','ONAR']
names=['Mobix Labs','Texas Pacific Land','Eagle Pharmaceuticals','Presidio Property Trust','Vertical Aerospace','Liberty Latin America — Class A','My City Builders','Aldel Financial II','Resolute Holdings','Onar Holding']
tz=ZoneInfo('America/New_York')
def load(ticker):
    obj=json.loads((RAW/f'{ticker}-wide.json').read_text())['chart']['result'][0]
    q=obj['indicators']['quote'][0];result={}
    assert obj['meta']['symbol']==ticker and obj['meta']['currency']=='USD'
    for i,ts in enumerate(obj['timestamp']):
        d=datetime.fromtimestamp(ts,tz).date().isoformat()
        p=q['close'][i];result[d]={'close':float(p) if p is not None and p>0 else None,'volume':q['volume'][i]}
    return result,obj
def index(p,base):return 100*p/base
assert index(55,50)==110 and index(40,50)==80
spy,_=load('SPY');sessions=sorted(spy)
allrows=[];summaries=[];series=[]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(5,2,figsize=(16,21));fig.subplots_adjust(top=.915,bottom=.10,hspace=.60,wspace=.22)
for r,ticker,name,ax in zip(records,tickers,names,axes.flat):
    p,obj=load(ticker);accept=datetime.fromisoformat(r['pilot']['acceptance_datetime_et']).replace(tzinfo=tz);date=accept.date().isoformat()
    pre=[d for d in sessions if d<date][-60:];post=[d for d in sessions if d>date][:60]
    dates=[(i-len(pre),d) for i,d in enumerate(pre)]+[(0,date)]+[(i+1,d) for i,d in enumerate(post)]
    # All filing days here are regular full sessions or a holiday; none is an early close.
    baseline_candidates=[d for d in sessions if datetime.combine(datetime.fromisoformat(d).date(),time(16),tz)<accept]
    base_date=baseline_candidates[-1];base=p.get(base_date,{}).get('close')
    assert base and base>0,f'No reliable last pre-release close: {ticker}'
    react=0 if date in sessions and accept.time()<time(16) else 1
    xs=[];ys=[];bs=[];rawprices=[];vol=[]
    for day,d in dates:
        close=p.get(d,{}).get('close') if d in sessions else None
        x=index(close,base) if close is not None else None
        b=index(spy[d]['close'],spy[base_date]['close']) if d in sessions else None
        row={'accession':r['accession'],'ticker':ticker,'filing_acceptance_et':accept.isoformat(),'event_day':day,'date':d,'vendor_split_adjusted_close_usd':close,'volume':p.get(d,{}).get('volume'),'price_index':x,'spy_price_index':b,'baseline_date':base_date,'baseline_vendor_close':base}
        allrows.append(row);xs.append(day);ys.append(x if x is not None else np.nan);bs.append(b if b is not None else np.nan);rawprices.append(close);vol.append(row['volume'])
    assert xs==list(range(-60,61)) and len(set(d for _,d in dates))==121
    baseline_i=[day for day,d in dates if d==base_date][0];assert abs(ys[xs.index(baseline_i)]-100)<1e-9
    color='#1864ab' if ticker not in ['MYCB','ONAR'] else '#a05619'
    ax.axvspan(-60,0,color='#eaf0f7',alpha=.75);ax.axvline(0,color='#243b53',lw=1.2)
    ax.axhline(100,color='#94a3b8',lw=.8);ax.plot(xs,bs,color='#9299a3',lw=1.2,ls='--',label='SPY price')
    ax.plot(xs,ys,color=color,lw=1.9,label=ticker)
    if react==1:ax.axvline(1,color='#cc7a00',lw=.8,ls=':')
    notes=[]
    if ticker=='MOBX':
        notes.append('Pre-Dec 22, 2023 history spans SPAC predecessor')
        transition=next((day for day,d in dates if d=='2023-12-22'),None)
        if transition is not None:ax.axvline(transition,color='#8b5cf6',lw=.9,ls=':')
    if ticker=='RHLD':notes.append('Short pre-filing history; no backfill')
    if ticker in ['MYCB','ONAR']:notes.append('OTC: stale/zero-volume closes may occur')
    zero=sum(v==0 for v,y in zip(vol,ys) if math.isfinite(y));missing=sum(not math.isfinite(y) for y in ys)
    before=sum(math.isfinite(y) for x,y in zip(xs,ys) if x<0);after=sum(math.isfinite(y) for x,y in zip(xs,ys) if x>0)
    timing='after close' if accept.time()>=time(16) else ('market holiday' if date not in sessions else 'during session')
    note='; '.join(notes) or 'Daily closes; split-adjusted, dividends excluded'
    ax.set_title(f'{ticker} | {name}\nFiled {date} {accept:%H:%M} ET · {timing}',loc='left',fontsize=11,fontweight='bold',pad=9)
    ax.text(0,-.25,note,transform=ax.transAxes,fontsize=8,color='#475569',wrap=True)
    ax.set_xlim(-60,60);ax.set_xticks([-60,-40,-20,0,20,40,60]);ax.grid(axis='y',alpha=.18)
    ax.set_ylabel('Price index');ax.set_xlabel('Trading sessions relative to filing date');ax.legend(loc='best',fontsize=8,frameon=False)
    checkpoints={str(k):None if not math.isfinite(ys[xs.index(k)]) else ys[xs.index(k)]-100 for k in [-60,-20,-5,-1,0,1,5,20,60]}
    summary={'ticker':ticker,'name':name,'accession':r['accession'],'filing_date':date,'acceptance_et':accept.isoformat(),'baseline_date':base_date,'baseline_close':base,'first_reaction_event_day':react,'available_pre_sessions':before,'available_post_sessions':after,'missing_points':missing,'zero_volume_points':zero,'changes_pct_from_last_pre_release_close':checkpoints,'note':note,'vendor_name':obj['meta'].get('longName'),'source_url':json.loads((RAW/f'{ticker}-wide.meta.json').read_text())['url']}
    summaries.append(summary);series.append((ticker,name,xs,ys,bs))
fig.suptitle('Ten 13D filings | 60 trading sessions before and after',x=.06,ha='left',fontsize=23,fontweight='bold',color='#243b53')
fig.text(.06,.951,'100 = last close before public SEC acceptance. T0 = filing date; holiday T0 is blank. Each panel has its own vertical scale.',fontsize=11,color='#475569')
fig.text(.06,.023,'Blue shading: pre-filing · Solid vertical line: filing date · Orange dotted line: first reaction session for after-hours/holiday filings\nSource: Yahoo Finance cached daily prices; SEC acceptance timestamps. Price-only preview, not causal evidence or an executable strategy.\nTickers matched to issuer names/share classes for preview; a complete historical identifier/corporate-action audit remains outstanding.',fontsize=10,color='#475569')
fig.savefig(OUT/'13D-pre-post-prices.png',dpi=150,facecolor='white');plt.close(fig)
fig,ax=plt.subplots(figsize=(14,7))
for ticker,name,x,y,b in series:ax.plot(x,y,lw=1.5,label=ticker)
ax.set_yscale('log');ax.axvline(0,color='#243b53',lw=1);ax.axhline(100,color='#94a3b8',lw=1,ls='--');ax.axvspan(-60,0,color='#eaf0f7',alpha=.5)
ax.set(xlim=(-60,60),xlabel='Trading sessions relative to filing date',ylabel='Price index (log scale)',title='13D price preview | all ten filings aligned');ax.legend(ncol=5,loc='upper center');ax.grid(alpha=.15)
fig.text(.1,.01,'100 = last close before release. Gaps retained. Price-only; no dividend reinvestment. Different issuers and events, n = 10.',fontsize=9)
fig.tight_layout(rect=(0,.035,1,1));fig.savefig(OUT/'13D-overlay.png',dpi=150,facecolor='white');plt.close(fig)
with (OUT/'daily-prices.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=allrows[0]);w.writeheader();w.writerows(allrows)
payload=json.dumps(summaries,indent=2)+'\n';target=OUT/'summary.json'
if target.exists():assert target.read_text()==payload,'Cached rerun changed summary'
else:target.write_text(payload)
manifest={'purpose':'Exploratory preview, not strategy evaluation','n_filings':10,'n_vendor_name_matches':10,'historical_identifier_validation':'Partial; not a validated historical security crosswalk','event_convention':'T0 filing calendar date; preceding/following SPY sessions numbered -1/+1; missing holiday T0 remains blank','normalization':'100 * vendor close / last regular close strictly before SEC acceptance','price_convention':'Yahoo vendor split-adjusted close; excludes cash dividends; not contemporaneous unadjusted dollars','raw_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.glob('*-wide.json'))},'python':sys.version,'matplotlib':matplotlib.__version__,'source_snapshot_sha256':hashlib.sha256((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
for s in summaries:print(s['ticker'],'pre',s['available_pre_sessions'],'post',s['available_post_sessions'],'zero-volume',s['zero_volume_points'],'T+1/20/60',*[round(s['changes_pct_from_last_pre_release_close'][str(k)],2) if s['changes_pct_from_last_pre_release_close'][str(k)] is not None else None for k in [1,20,60]])
