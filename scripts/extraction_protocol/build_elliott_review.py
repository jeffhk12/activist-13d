"""Build a factual Elliott identity discovery page, Tier: 1.
Inputs: cached local filing candidates and dated official-source notes.
Outputs: separate draft HTML and verified-CIK filing inventory.
Identity: select reporting-party CIK 0001791786; never merge by name.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/build_elliott_review.py
"""
import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research/runs/investor-identity/20260923-elliott'
PACK = ROOT / 'review/drafts/investor-identity-elliott-20260923'

def selected(record):
    return any(f.get('cik') == '0001791786' for f in record.get('filers', []))

def build():
    candidates = json.loads((RUN / 'local-filing-candidates.json').read_text())
    records = [r for r in candidates if selected(r)]
    assert selected({'filers': [{'cik': '0001791786', 'name': 'different spelling'}]})
    assert not selected({'filers': [{'cik': '0000000001', 'name': 'Elliott Investment Management'}]})
    assert not selected({'filers': []})
    assert len({r['accession'] for r in records}) == len(records)
    sources = json.loads((RUN / 'external-sources.json').read_text())
    for source in sources:
        if source.get('local_cache'):
            assert hashlib.sha256((RUN / source['local_cache']).read_bytes()).hexdigest() == source['sha256']
    PACK.mkdir(parents=True, exist_ok=True)
    e = html.escape
    def link(path, label):
        return f'<a href="{e(os.path.relpath(path, PACK))}">{e(label)}</a>'
    rows = []
    inventory = []
    for r in records:
        path = ROOT / r['source_path']
        assert path.is_file(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r['source_sha256'], path
        issuer = '; '.join(s['name'] for s in r['subjects'])
        rows.append(f'<tr><td>{e(r["filing_date"])}</td><td>{e(r["form"])}</td><td>{e(issuer)}</td><td>{link(path,r["accession"])}</td></tr>')
        inventory.append({k:r[k] for k in ('accession','filing_date','form','filers','subjects','source_path','source_sha256')})
    facts = [
        ('Adviser / reporting entity', 'Elliott Investment Management L.P.', 'CRD 307151; SEC 801-119969; CIK 1791786. ADV Item 1.'),
        ('Adviser’s general partner', 'Elliott Investment Management GP LLC', 'ADV Schedule A. Do not assign it as GP of every fund.'),
        ('Controller in the adviser chain', 'Paul E. Singer', 'ADV Schedule B: managing member and president of the GP; ownership band 75% or more. This is not ownership of a portfolio company.'),
        ('Co-CEOs / co-CIOs', 'Paul Singer and Jonathan Pollock', 'ADV Schedule A and official leadership page. Firm roles do not identify the PM responsible for a specific stock.'),
        ('Separate relying adviser', 'Elliott Management Corporation', 'CRD 156601; ADV Schedule R. Preserve as a separate legal entity.'),
        ('Underlying fund vehicles', 'Requires filing-specific review', 'Read Item 2, Item 5 and signatures; do not substitute the adviser’s name for the owning funds.'),
        ('Issuer-specific portfolio manager', 'Unresolved', 'Current leadership disclosures do not establish who managed a particular position.'),
    ]
    factrows = ''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in row)+'</tr>' for row in facts)
    sourcelinks = ''.join(f'<li><a href="{e(s["url"])}">{e(s["url"])}</a> — source date: {e(s["source_date"] or "undated")}; accessed {e(s["accessed_on"])}</li>' for s in sources)
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Elliott — identity discovery</title>
<style>body{font:16px/1.55 system-ui;color:#233747;background:#f3f6f8;margin:30px auto;max-width:1200px;padding:20px}section{background:white;padding:24px;margin:20px 0;border-radius:10px}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #ddd}a{color:#176699}code{overflow-wrap:anywhere}li{overflow-wrap:anywhere}</style>
<h1>Elliott: identify the investor before reviewing the event</h1><p>Exploratory factual research • 23 September 2026 • historical roles and event review pending</p>
<p>''' + link(ROOT/'START-HERE.html','Project home') + '''</p><section><h2>What we can identify now</h2><p>Elliott is the user-selected known-activist example. This page records identities, not investment quality or campaign outcomes. The facts below are assistant-transcribed from current official sources; they are not human reference labels or historical filing-date features.</p>
<p>The regulatory source is dated <b>24 July 2026</b>. Do not carry its relationships backwards into older filings without dated evidence.</p><table><tr><th>Attribute</th><th>Value</th><th>Evidence / boundary</th></tr>''' + factrows + '''</table></section>
<section><h2>Local filings for the verified adviser CIK</h2><p>''' + str(len(records)) + ''' cached records match reporting-party CIK <b>0001791786</b>. This is local archive coverage, not a complete SEC filing history or a count of independent campaigns. Initial filings and amendments remain separate. Historical Elliott Associates records are not included in this identifier-only subset.</p><table><tr><th>Filing date</th><th>Form</th><th>Issuer</th><th>Accession / full raw source</th></tr>''' + ''.join(rows) + '''</table></section>
<section><h2>HFR and next evidence</h2><p>No Elliot/Elliott name match was found in the Fund and Firm columns of the supplied HFR Fund snapshot dated 8 September 2026. This does not prove absence under an alias or in other HFR products. HFR coverage is not an eligibility requirement.</p><p>Next: map fund vehicles and disclosed relationships in a selected initial 13D, then trace its amendments. Store activist-manager identity separately from filing-specific demands, beneficial ownership and issuer control. Keep an issuer-specific PM blank unless a dated source explicitly establishes the role.</p></section>
<section><h2>Sources and audit files</h2><ul>''' + sourcelinks + '</ul><p>' + link(RUN/'EXTERNAL-SOURCES.md','Detailed source notes') + ' · ' + link(RUN/'verified-cik-filings.json','Verified-CIK inventory') + '''</p><p>Full project address: <code>/Users/jefflu/Projects/activist-13d</code></p></section></html>''', inventory

if __name__ == '__main__':
    page, inventory = build()
    page2, inventory2 = build()
    assert page == page2 and inventory == inventory2
    (RUN/'verified-cik-filings.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (PACK/'index.html').write_text(page)
    print(f'Validated {len(inventory)} cached raw-source hashes; reproducible page: {PACK / "index.html"}')
