"""Publish the ten-case financial timing/identity/vintage audit and checkpoint.

Inputs: saved findings, comparison tables, summary and source-preservation receipt.
Outputs: HTML report and active project navigation. Identity: displayed totals
reconcile to per-event findings; issue counts describe a selected pilot only.
Tier: 1. No workbook edits, financial recollection or investment-model fitting.
Run: project Python scripts/ml_experiment/report_bloomberg_timing.py.
"""
import hashlib
import json
import re
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/bloomberg-timing/20261026-v1'
LABELS={'post_cutoff_results':'Selected annual results announced after filing',
        'historical_revision':'Original period public; workbook matches later recast',
        'historical_issuer_mismatch':'Financial figures match a different historical issuer',
        'field_definition_unresolved':'Cash/common-equity definitions unresolved',
        'older_annual_period':'Selected annual period is older than latest public annual filing'}


def main():
    findings=json.loads((RUN/'findings.json').read_text())
    summary=json.loads((RUN/'summary.json').read_text())
    comparisons=json.loads((RUN/'amount-comparisons.json').read_text())
    rows=[]
    details=[]
    for f in findings:
        status='; '.join(LABELS[k] for k in f['issue_flags']) if f['issue_flags'] else 'No material issue identified in bounded spotcheck'
        urls=' · '.join(f'<a href="{escape(s["url"],quote=True)}">{escape(s.get("title", "Primary source"))}</a>' for s in f['primary_sources'])
        rows.append(f'<tr><th><a href="#{f["case_id"]}">{escape(f["company"])}</a></th><td>{f["candidate_fiscal_year"]}<br>{f["period_end"]}</td><td>{f["filing_date"]}<br><small>cutoff {f["financial_cutoff_date"]}</small></td><td>{f["original_period_observed_date"]}</td><td>{escape(status)}</td></tr>')
        checks=[c for c in comparisons if c['case_id']==f['case_id']]
        checkrows=''.join(f'<tr><td>{escape(c["field"])}</td><td>{c["workbook_value"]:,.2f}</td><td>{c["source_usd"]:,.2f}</td><td>{c["difference_usd"]:,.2f}</td><td>{escape(c["status"].replace("_"," "))}</td></tr>' for c in checks)
        limits=' '.join(f['unresolved'])
        details.append(f'''<section id="{f['case_id']}"><h3>{f['case_id']} · {escape(f['company'])}</h3><p><strong>{escape(status)}.</strong> {escape(f['conclusion'])}</p><p>13D accepted {f['filing_accepted_et']} ET; stored financial cutoff {f['financial_cutoff_date']}; delayed entry {f['entry_date']}. Selected FY{f['candidate_fiscal_year']} ends {f['period_end']}. Observed original-period disclosure: {f['original_period_observed_date']} ({escape(f['original_period_date_kind'])}).</p><p>{escape(f['compatible_value_date_limit'])}</p><div class="scroll"><table><thead><tr><th>Field</th><th>Workbook USD</th><th>Compared primary-source USD</th><th>Workbook minus source USD</th><th>Numerical result</th></tr></thead><tbody>{checkrows}</tbody></table></div><p><strong>Action:</strong> {escape(f['next_action'])}</p><p><strong>Limits:</strong> {escape(limits)}</p><p>{urls}</p></section>''')
    issue_rows=''.join(f'<tr><td>{escape(LABELS[k])}</td><td>{n}/10</td></tr>' for k,n in summary['issue_counts'].items())
    report=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ten Bloomberg rows against their 13D dates</title><style>body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1180px;margin:28px auto;padding:28px;background:white}}h1,h2,h3{{line-height:1.3}}table{{width:100%;border-collapse:collapse;font-size:15px}}th,td{{text-align:left;padding:11px;border-bottom:1px solid #dce3e8;vertical-align:top}}thead th{{background:#edf3f7}}a{{color:#155c99}}.scroll{{overflow:auto}}.takeaway{{background:#fff4df;padding:18px;border-left:4px solid #a86a13}}section{{padding-top:12px}}small{{white-space:nowrap}}</style></head><body><main>
<h1>Were the Bloomberg figures usable when each 13D was filed?</h1><p>October 26, 2026 · Ten-event source check complete · Data preparation, not a ranking or investment result</p>
<p class="takeaway"><strong>Six of the ten selected rows need correction or definition work before they can support a financial-feature model.</strong> Two have selected annual results announced after the filing. One matches a different historical issuer, one matches later accounting recasts, one uses an older annual period, and one has unresolved cash/common-equity definitions. Four have no material issue identified in the bounded spotcheck, with a publication-metadata limitation for Geospace. None is certified across all nine fields and historical vendor vintage.</p>
<p>This is the existing ten-event financial-check pilot: the known Benchmark conflict control plus nine discovery-related events. It is deliberately selected and not a random sample. Six of ten is a diagnostic count, not an estimated error rate for the 667-event universe.</p>
<h2>What we checked</h2><p>We matched the workbook's saved raw and displayed rows to exact event IDs, issuer IDs, 13D acceptance timestamps, financial cutoffs and delayed entry dates. We then traced annual periods and selected numbers to original SEC filings and company-issued releases. The original XLSX was neither edited nor recalculated. No reserved text evidence, investment outcomes or LLM intention labels were read for this check.</p>
<p>The 90 raw-field slots are inventoried, but only {summary['primary_source_amount_comparisons']} amounts were compared directly with selected original-period source statements: {summary['amount_comparison_status']['match']} match numerically and {summary['amount_comparison_status']['difference_requires_reconciliation']} differ and require reconciliation. Matching a later release or an older period is not historical eligibility. Eight extra comparisons document the later recast and other-issuer matches. We did not independently authenticate Bloomberg field definitions, stable security IDs, query settings or revision-vintage controls for all ninety slots.</p>
<h2>Ten-case result</h2><p>The observed disclosure date below belongs to the correct issuer's original annual period. It is not a claim of the earliest public date of every field. For Catalyst and National Western especially, an early period-publication date does not validate the workbook's selected figures.</p><div class="scroll"><table><thead><tr><th>Company</th><th>Selected FY / period end</th><th>13D filing / financial cutoff</th><th>Observed original-period disclosure</th><th>Assessment</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Issues found in this selected pilot</h2><table><thead><tr><th>Issue</th><th>Selected rows</th></tr></thead><tbody>{issue_rows}</tbody></table>
<h2>The most consequential findings</h2>
<p><strong>Catalyst Biosciences: historical identity mismatch.</strong> The 2019 event is for Catalyst, CIK1124105. Its original FY2018 assets were $124.920 million, while the workbook has $214.839272 million. Five workbook amounts exactly equal original FY2018 GlycoMimetics financials, CIK1253689, which traded as GLYC. A June16,2025 SEC-hosted release says the combined Crescent/GlycoMimetics company would begin trading as CBIO. This establishes ticker reuse risk and a different-issuer numerical match. The precise Bloomberg lookup mechanism remains unverified; we do not attribute an unobserved query error to the vendor. See F06 sources below.</p>
<p><strong>National Western: a correct annual year can still contain later information.</strong> Original FY2022 earnings were $101.144 million and revenue $558.397 million. The workbook's $246.511 million and $560.034 million instead match later recasts under the new long-duration insurance accounting standard (LDTI). The selected assets also match the later recast. The original period was public before the April2023 cutoff; the exact recast values have not been shown to be public then. Later-report signature dates identify versions in the research notes but are not substituted for independently verified SEC publication timestamps. This row needs as-reported reconstruction or earlier field-specific disclosure proof.</p>
<p><strong>Benchmark and Continental: the selected full-year release follows the event.</strong> Benchmark's FY2018 results were released February7,2019, after its January4 filing and January8 entry. Continental's FY2021 results were released February14,2022 at16:15ET, after its February9 filing and February11 entry. Delayed entry does not cure either selected-release timing conflict. Earlier field-specific disclosures were not established in this bounded check.</p>
<p><strong>At Home: fiscal labels need actual dates.</strong> Workbook FY2020 is the year ended January25,2020. Company FY2021 ended January30,2021 and its10-K was filed March24,2021, before the May14 financial cutoff. The older figures are historical, but the rule failed to select the latest annual filing already available.</p>
<p><strong>TriState: definitions need reconciliation.</strong> Assets, liabilities and total net income match the January29,2020 release. Workbook cash of $0.357 million differs from reported cash and cash equivalents of $403.855 million. Common equity also differs. These are unresolved definition/coverage differences, not an automatic conclusion that the vendor amount is wrong. The bank's revenue and common-equity measures need sector-appropriate interpretation before ratios are engineered.</p>
<h2>The method to learn here</h2><p>A usable historical financial input needs four things: the correct company/security, the correct fiscal period, a public disclosure by the information cutoff, and the version and definition available at that time. A period-end date is not a publication date. A historical year in a current download does not guarantee an original as-reported value. A familiar ticker does not uniquely identify a historical company.</p>
<p>The saved cutoff is the prior exchange-session date in the original request. It is deliberately earlier than 13D acceptance and the later trading entry. This audit compares dates against all three and leaves same-day timestamp ambiguity unresolved when necessary. It does not silently change the trading or information-cutoff convention.</p>
<p>UroGen illustrates a useful distinction: its March16 preliminary release differed from the March24 original10-K. The workbook's checked values match that March24 version, which was already public well before the August cutoff. A revision is not automatically future information; its publication timing matters. Geospace's FY2017 release is dated November30,2017 and exact figures match the original company annual report, but the exact SEC index timestamp was not retrieved. Its December1 report signature is not treated as proof of publication.</p>
<h2>What to do next</h2><ol><li>Resolve historical company/security mappings with stable identifiers, beginning with Catalyst. Preserve original requested ticker seeds and explicit correction evidence.</li><li>Select each company's latest annual filing actually public by the fixed cutoff, retaining the exact fiscal-period end. Do not replace the rule with another blanket calendar-year offset.</li><li>Retrieve original as-reported versions or a demonstrably point-in-time financial series. Address National Western recasts and verify field definitions, units, preferred/noncontrolling interests and missing values.</li><li>Recheck these ten corrected rows before applying the procedure to all667 events. Then run the financial ranking experiment on an explicitly counted common eligible sample.</li></ol>
<p>No values have been corrected in the workbook and no financial-feature model was fitted here. The recent non-LLM ranking run excluded Bloomberg data, so these findings do not alter its saved predictions. They establish why the financial extension needs corrected inputs first.</p>
<details><summary>Per-company source evidence and amount comparisons</summary>{''.join(details)}</details>
<h2>Evidence and verification</h2><p><a href="summary.json">Counts and limits</a> · <a href="findings.json">Every event finding and primary source</a> · <a href="field-checks.csv">90-slot inventory</a> · <a href="amount-comparisons.json">36 original-period comparisons</a> · <a href="additional-version-checks.json">Eight recast/other-issuer comparisons</a> · <a href="correction-queue.csv">Ten-case correction queue</a> · <a href="selected-workbook-rows.json">Saved raw/displayed cells and formulas</a> · <a href="input-receipt.json">Unchanged-workbook receipt</a> · <a href="provenance.json">Evidence/output hashes</a></p>
<p>Six synthetic/replay checks cover unit conversion, missing-versus-zero values, invalid units, date boundaries, separate issue types and deterministic recalculation. Offline replay reproduces counts from frozen manually collected evidence; it does not rerun web research or prove every historical publication. Primary web excerpts are retained where available; some large/blocked originals were inspected through search extracts or issuer-hosted copies, with the limits recorded per case.</p>
<p><a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p></main></body></html>'''
    path=RUN/'index.html'
    if path.exists():
        assert path.read_text()==report
    else:
        path.write_text(report)
    home=ROOT/'START-HERE.html'
    text=home.read_text()
    marker='<!-- bloomberg-timing-v1-current -->'
    if marker not in text:
        section=marker+'''<section><h2>Current: ten Bloomberg rows checked against filing dates — October 26</h2><p>Six selected rows need correction or definition work: two later annual releases, a different historical issuer, later accounting recasts, an older annual period, and cash/equity definition differences. Four have no material issue identified in the bounded spotcheck; all-nine-field historical certification remains incomplete.</p><a class="button" href="research/runs/bloomberg-timing/20261026-v1/index.html">Bloomberg timing and identity findings</a><p>Original workbook unchanged. Correct historical IDs, public periods and as-reported versions before financial-model fitting. The selected pilot does not estimate the full-sample error rate.</p></section>'''
        text=text.replace('</style></head><body><main>','</style></head><body><main>\n'+section,1)
        text=text.replace('<h2>Current: ranking analysis without LLM extraction — October 26</h2>','<h2>Completed: ranking analysis without LLM extraction — October 26</h2>')
        assert marker in text
        home.write_text(text)
    index=ROOT/'research/docs/ml-checkpoints.html'
    text=index.read_text()
    marker='<!-- bloomberg-timing-v1-checkpoint -->'
    if marker not in text:
        text=re.sub(r'(<body><main><h1>13D machine learning learning checkpoints</h1>)<p>Updated.*?</p>',r'\1<p>Updated October 26, 2026 | Ten Bloomberg rows checked; timing, historical identity, revision and period-selection issues found</p>',text,count=1)
        text=text.replace('<section class="current">','<section class="history">',1)
        section=marker+'''<section class="current"><h2>Current checkpoint: financial dates, versions and identities</h2><p>The ten-case check found six rows needing correction or definition work. Learn why period end differs from publication date, why historical-year values may be recast, and why ticker reuse can attach the wrong company to a filing.</p><p><a href="../runs/bloomberg-timing/20261026-v1/index.html">Read all ten findings and the correction sequence</a></p><p>The workbook and previous ranking results are unchanged. Four rows have no material issue identified in the bounded checks; none is certified across all nine historical fields.</p></section>'''
        text=text.replace('<section class="history">',section+'\n<section class="history">',1)
        index.write_text(text)
    plan=ROOT/'research/docs/PROJECT-PLAN.md'
    text=plan.read_text()
    heading='## Ten-case Bloomberg timing check completed — October 26, 2026'
    if heading not in text:
        paragraph=f'''{heading}

The [financial timing/identity report](../runs/bloomberg-timing/20261026-v1/index.html)
checks the existing ten-event financial pilot against primary disclosures. Six
rows need correction or definition work: BHE/CLR selected annual releases after
filing, CBIO figures matching historical GlycoMimetics rather than Catalyst,
NWLI later LDTI recasts, HOME older annual-period selection and TSC cash/common
equity definitions. Four rows have no material issue identified in bounded checks;
Geospace exact publication metadata remains limited. There are 36 amount
comparisons, with 28 matches and 8 differences, plus eight recast/other-issuer
comparisons. A match alone is not historical eligibility. No row is fully
certified across all nine fields. The pilot is deliberately selected and includes
a known conflict, so these counts do not estimate a population error rate.
Original workbook and existing model outputs are preserved. Next correct stable
historical IDs, latest-public-period selection, original vintages and definitions,
then recheck these ten before extending the financial comparison to the full
sample. No new financial-feature fit or return calculation was performed.

'''
        text=text.replace('# Activist 13D Machine Learning Class Project Plan\n\n','# Activist 13D Machine Learning Class Project Plan\n\n'+paragraph,1)
        plan.write_text(text)
    print(json.dumps({'report':str(path),'selected_events':summary['selected_events'],
                      'events_with_issues':summary['events_with_identified_issues'],
                      'report_sha256':hashlib.sha256(report.encode()).hexdigest()},indent=2))


if __name__=='__main__':
    main()
