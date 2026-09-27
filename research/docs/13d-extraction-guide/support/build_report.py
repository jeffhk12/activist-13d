"""Render an explanatory Schedule 13D guide from authored HTML and exposed pilot text.

Inputs: report-body.html, frozen ten-pilot bundles and inspected inventory.
Output: report.html and exact quotation provenance in evidence.json.
Tier 1: evidence locations are [start,end) Unicode offsets; text[start:end]=quote.
No estimators, model calls, classifications of protected cases or protocol edits.
Run with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 project .venv/bin/python.
"""
from pathlib import Path
from html import escape
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
bundles = json.loads((ROOT/'review/archive/13d-structured-review-20260922/review-inputs.json').read_text())
inventory = json.loads((HERE/'pilot-inventory.json').read_text())
examples = [
('0001104659-24-000323', 'Chavant / Mobix', 'Chavant Capital expects to distribute to its members', 'Sponsor distribution and board relationships matter. Preserve the SEC-header name Chavant Capital Acquisition Corp. separately from the cover issuer Mobix Labs, Inc.; resolve the historical identity before joining prices.'),
('0001398344-24-000853', 'Bulldog / Texas Pacific Land', 'The stockholders urge the Board to seek stockholder approval', 'The specific proposal is in Exhibit B. Item 4 alone merely points to the letter. Resolve the roles of Bulldog and Special Opportunities Fund before naming a campaign entity; the pilot parser did not recover a CUSIP.'),
('0001104659-24-024047', 'Michael Graves / Eagle Pharmaceuticals', 'his position as Interim Principal Executive Officer', 'The passage concerns an issuer executive. Record role and acquisition context before interpreting a holding as an outsider campaign. Incorporated Item 6 needs review.'),
('0001493152-24-008748', 'Gary Katz / Presidio Property Trust', 'investment purposes only', 'This passage does not establish a specific current demand. Read the full evidence before recording not_stated; it is not proof of permanent passivity.'),
('0001193125-24-081594', 'Stephen Fitzpatrick / Vertical Aerospace', 'lock-up period as part of the Transaction', 'The transaction and incorporated Items 3 and 6 govern interpretation. Record agreement restrictions and unresolved references rather than infer an activist objective.'),
('0000807249-25-000003', 'GAMCO / Liberty Latin America', 'may suggest or take a position', 'General investment philosophy or conditional engagement is different from a specific current demand. A familiar manager name cannot supply missing intent evidence.'),
('0001640334-25-000152', 'Frank Gillen / My City Builders', 'conversion of debt by PreCheck', 'Preserve the named entity PreCheck and its relationship as unresolved. Do not silently substitute the header issuer or equate influence language with a concrete governance request.'),
('0001104659-25-014424', 'Aldel Investors II / Aldel Financial II', 'Founder Shares', 'Sponsor shares and blank-check-company context can explain merger language. A business-combination description alone is not an outsider sale demand.'),
('0000950142-25-000685', 'Resolute Compo / Resolute Holdings Management', 'completed a spin-off', 'Distinguish completed corporate events from current investor requests. Review the executive/director relationships and overlapping beneficial ownership in Annex A.'),
('0001477932-25-002177', 'Claude Zdanow / Onar', 'sole director of the Issuer', 'An existing control relationship is economically different from an outside fund seeking change. Read incorporated Item 3 before final event eligibility.')]
assert len(inventory) == len(examples) == 10
assert len({x['accession'] for x in inventory}) == 10
evidence, cards = [], []
for accession, title, quote, interpretation in examples:
    record = next(x for x in inventory if x['accession'] == accession)
    bundle = next(x for x in bundles if x['accession'] == accession)
    matches = [d for d in bundle['documents'] if quote in d.get('text','')]
    if not matches:
        raise ValueError(f'Quotation not found: {accession}: {quote}')
    doc = matches[0]
    start = doc['text'].index(quote)
    assert doc['text'][start:start+len(quote)] == quote
    assert hashlib.sha256(doc['text'].encode()).hexdigest() == doc['text_sha256']
    evidence.append(dict(accession=accession, document_id=doc['document_id'], filename=doc['filename'], quote=quote, start=start, end=start+len(quote), text_sha256=doc['text_sha256'], source_sha256=record['source_sha256'], source_url=record['source_url']))
    cards.append(f'<article class="example"><h3>{escape(title)}</h3><p class="meta">{accession} · Filed {record["filing_date"]} · {escape(doc["filename"])}</p><blockquote>{escape(quote)}</blockquote><p><b>Illustrative interpretation—not a validated label:</b> {escape(interpretation)}</p><p><a href="{escape(record["source_url"],quote=True)}">SEC source</a> · <a href="../../../review/archive/13d-structured-review-20260922/index.html">Existing ten-filing review pack</a></p></article>')
    full_text = ''.join('<h4>'+escape(d['filename'])+'</h4><p style="white-space:pre-wrap">'+escape(d.get('text') or 'Text unavailable')+'</p>' for d in bundle['documents'])
    cards[-1] = cards[-1].replace(' · <a href="../../../review/archive/13d-structured-review-20260922/index.html">Existing ten-filing review pack</a>', '')
    cards[-1] = cards[-1].replace('</article>', '<details><summary>Read the full supplied source packet</summary>'+full_text+'</details></article>')
body = (HERE/'report-body.html').read_text().replace('<!-- EXAMPLES -->', '\n'.join(cards))
body = body.replace('Open the <a href="../../../review/archive/13d-structured-review-20260922/index.html">existing full ten-filing review pack</a> for longer source text.', 'Expand “Read the full supplied source packet” beneath each example for the full canonical text of its locally supplied documents. Incorporated documents not supplied in that packet remain a limitation.')
plan = json.loads((HERE/'pipeline-plan.json').read_text())
assert plan['primary_event'] == 'initial_13D'
assert [s['priority'] for s in plan['stages']] == [1, 2, 3, 4, 5]
assert plan['stages'][0]['id'] == '13d_core'
stage_html = []
for stage in plan['stages']:
    stage_html.append('<article class="example"><h3>'+str(stage['priority'])+'. '+escape(stage['label'])+'</h3><p><b>Status:</b> '+escape(stage['implementation_status'])+'</p><p><b>Scope:</b> '+escape(stage['scope'])+'</p><p><b>Extract:</b> '+escape('; '.join(stage['fields']))+'.</p><p><b>Next step:</b> '+escape(stage['next_action'])+'</p><p><b>Gate:</b> '+escape(stage['gate'])+'</p></article>')
pipeline = '<section id="pipeline"><p class="tag">Scope update agreed September 23, 2026</p><h2>Expanded filing pipeline — 13D first</h2><p>The additional filing families are now in the staged project plan. Initial 13D remains the primary event and first implementation/review priority. This registry renders the roadmap below; it is not connected to a collection scheduler. Other filing adapters remain to be implemented.</p>'+''.join(stage_html)+'<h3>Shared requirements</h3><p>Every family preserves source hashes, exact supporting text, reporting parties, security identity, publication time and the separately reported ownership/event date. Links need evidence and an explicit unresolved state. Earlier public filings can supply initial context; later filings belong in follow-up records and cannot be backfilled into the initial signal.</p><p>The current 13D collector and frozen manifests are unchanged. No downloads or model jobs were started by this update. Each new collection stage needs a bounded manifest and storage estimate under the existing resource guards.</p><p><a href="support/pipeline-plan.json">Machine-readable scope and stage registry</a> · <a href="../PROJECT-PLAN.md">Project plan and current addendum</a></p><p>Source references: <a href="https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/exchange-act-sections-13d-13g-regulation-13d-g-beneficial-ownership-reporting">SEC beneficial-ownership guidance</a>; <a href="https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f">13F FAQ</a>; <a href="https://www.investor.gov/introduction-investing/getting-started/researching-investments/using-edgar-research-investments">SEC EDGAR research guide</a>; <a href="https://www.sec.gov/files/form8-k.pdf">Form 8-K</a>. The stages are project decisions; field contracts and current form versions require verification before implementation.</p></section>'
body = body.replace('<section id="meaning">', pipeline+'<section id="meaning">')
body = body.replace('<nav><ol>', '<nav><ol><li><a href="#pipeline">Expanded filing pipeline — 13D first</a></li>')
css = '''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f6f8;color:#203448;font:17px/1.65 system-ui,sans-serif}header,main,footer{max-width:1180px;margin:auto;padding:30px}header{padding-top:52px}h1{font-size:42px;line-height:1.15;max-width:900px}h2{font-size:29px;line-height:1.25;margin-top:0}h3{font-size:21px}a{color:#135f91}section{background:white;border:1px solid #d9e2e9;border-radius:10px;margin:25px 0;padding:30px;scroll-margin-top:20px}table{border-collapse:collapse;width:100%;font-size:15px;line-height:1.5;margin:20px 0}td,th{padding:13px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #dce4ea}th{background:#eaf1f6}tr:nth-child(even){background:#f8fafb}.table-wrap{overflow-x:auto}blockquote{border-left:4px solid #16827c;background:#edf7f5;margin:15px 0;padding:15px}.note{background:#fff5df;border-left:4px solid #be8626;padding:18px}.lead{font-size:21px}.meta,small{font-size:14px;color:#526779}.path{overflow-wrap:anywhere;font:14px/1.6 ui-monospace,monospace}.example{border-top:1px solid #dce4ea;margin-top:25px;padding-top:10px}nav ol{columns:2;gap:35px}li{margin:8px 0}code{font-size:.9em;overflow-wrap:anywhere}.tag{color:#12655f;font-weight:700;text-transform:uppercase;letter-spacing:.07em;font-size:13px}@media(max-width:700px){header,main,footer{padding:18px}section{padding:18px}h1{font-size:32px}nav ol{columns:1}td,th{min-width:140px}}@media print{body{background:white;font-size:11pt}header,main,footer{padding:0;max-width:none}section{border:0;padding:10px 0;break-inside:auto}h2,h3{break-after:avoid}tr,blockquote{break-inside:avoid}nav{display:none}a{color:inherit}table{font-size:9pt}.example{break-inside:avoid}}'''
html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Understanding 13D filings and useful extraction attributes</title><style>'+css+'</style></head><body>'+body+'</body></html>'
assert '<!-- EXAMPLES -->' not in html
assert len(evidence) == 10 and all(x['end'] > x['start'] for x in evidence)
(HERE.parent/'report.html').write_text(html)
(HERE/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('Rendered report; ten exact quotations validated against hashed canonical source documents.')
