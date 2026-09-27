"""Tier 0: Cache public Yahoo daily prices for ten explicit pilot candidates.
Inputs: frozen review inputs and candidate tickers. Outputs: separate dated raw responses.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/fetch_pilot_price_preview.py
No labels, WRDS credentials or existing caches are changed.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,requests,gzip,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'review/archive/13d-price-preview-20260922'
OUT.mkdir(exist_ok=True)
RAW=OUT/'raw';RAW.mkdir(exist_ok=True)
records=json.loads((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text())
tickers=['MOBX','TPL','EGRX','SQFT','EVTL','LILA','MYCB','ALDF','RHLD','ONAR']
def fetch(args):
    r,ticker=args
    date=datetime.fromisoformat(r['pilot']['index_filing_date']).replace(tzinfo=timezone.utc)
    params={'period1':int((date-timedelta(days=110)).timestamp()),'period2':int((date+timedelta(days=130)).timestamp()),'interval':'1d','events':'div,splits'}
    if ticker=='SPY':params.update(period1=1693526400,period2=1751328000)
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
    target=RAW/f'{ticker}-wide.json'
    if not target.exists():
        try:
            res=requests.get(url,params=params,headers={'User-Agent':'Mozilla/5.0'},timeout=25)
            target.write_bytes(res.content)
            (RAW/f'{ticker}-wide.meta.json').write_text(json.dumps({'url':res.url,'status':res.status_code,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(res.content).hexdigest()},indent=2))
        except Exception as e:return ticker,str(e)
    try:
        o=json.loads(target.read_bytes());v=o['chart']['result']
        return ticker, (v[0]['meta'].get('longName'),v[0]['meta'].get('currency'),len(v[0].get('timestamp',[]))) if v else o['chart']['error']
    except Exception:return ticker,target.read_text()[:120]
with ThreadPoolExecutor(max_workers=5) as pool:
    for result in pool.map(fetch,list(zip(records,tickers))+[(records[0],'SPY')]):print(result,flush=True)
if '--prices-only' in sys.argv:sys.exit(0)
matches=[]
cusips={r['pilot'].get('cusip','')[:8] for r in records if r['pilot'].get('cusip')}
for path in (ROOT/'data/raw/wrds/bulk-v1/crsp.stocknames').glob('*.json.gz'):
    for row in json.loads(gzip.decompress(path.read_bytes())).get('results',[]):
        if row.get('ncusip') in cusips or row.get('ticker') in tickers:
            if (row.get('nameenddt') or '')>='2023-01-01':matches.append({**row,'cache_path':str(path.relative_to(ROOT))})
unique={json.dumps(r,sort_keys=True):r for r in matches}
(OUT/'identifier-candidates.json').write_text(json.dumps(list(unique.values()),indent=2))
for r in unique.values():print('MATCH',r['ticker'],r['comnam'],r['ncusip'],r['namedt'],r['nameenddt'],r['permno'])
