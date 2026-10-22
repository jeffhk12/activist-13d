"""Create the October 21 ML professor progress report from preserved evidence.

Inputs: frozen feature, preprocessing, baseline and Windows nonlinear runs.
Outputs: an eight-page PDF, self-contained HTML, source snapshots and a manifest.
Identities: error=prediction-target; MAE=mean(abs(error)); RMSE=sqrt(mean(error^2));
network parameter count=4*p+9. No new fit, tuning, extraction or trading.
Tier: 2 presentation of previously audited calculations, with numerical assertions,
source hashes, independent metric parity, extraction checks and rendered visual QA.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 <PDF-runtime-python> build_report.py
"""

import csv
import hashlib
import json
import math
import shutil
from html import escape
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PDF = HERE / '13D_ML_Project_and_Progress_Report_20261021.pdf'
RUN = ROOT / 'research/runs/ml-nonlinear/20261019-windows-v1'
SOURCES = {
    'E1 feature coverage': ROOT / 'research/runs/ml-feature-preview/20261012-v1/summary.json',
    'E2 preprocessing': ROOT / 'research/runs/ml-preprocessing/20261012-v1/summary.json',
    'E3 baseline protocol': ROOT / 'research/protocol/ml-baselines-v1.json',
    'E4 nonlinear protocol': ROOT / 'research/protocol/ml-nonlinear-v1.json',
    'E5 completed results': RUN / 'evaluation.json',
    'E6 training diagnostics': RUN / 'training-diagnostics.json',
    'E7 independent audit': ROOT / 'research/runs/ml-nonlinear-verification/20261019-windows-v1/verification.json',
    'E8 sample construction': ROOT / 'research/docs/professor-update-20261015/source-snapshots-v2/sample-bridge.json',
    'E9 Bloomberg audit': ROOT / 'research/runs/bloomberg-return-audit/20261018-v1/index.html',
    'E10 extraction workflow': ROOT / 'research/protocol/extraction-workflow-v1.md',
    'E11 scored events': RUN / 'scored-events.csv',
    'E12 Windows receipt': ROOT / 'research/runs/ml-nonlinear-verification/20261019-windows-v1/windows-execution.json',
}

def load(key):
    return json.loads(SOURCES[key].read_text())

E = load('E5 completed results')
F = load('E1 feature coverage')
P = load('E2 preprocessing')
N = load('E4 nonlinear protocol')
A = load('E7 independent audit')
B = load('E8 sample construction')
MODELS = [
    ('zero_excess', 'Zero excess reference'),
    ('training_mean', 'Earlier training mean'),
    ('ridge', 'Fixed ridge regression'),
    ('neural_ensemble', 'Neural network: five-start average'),
    ('tree', 'Shallow decision tree'),
    ('forest', 'Random forest'),
    ('boosting', 'Gradient boosting'),
]

# Independent arithmetic over the saved event errors; no estimator is fitted.
scored = list(csv.DictReader(SOURCES['E11 scored events'].open(newline='')))
for key, _ in MODELS:
    rows = [r for r in scored if r['model'] == key]
    assert len(rows) == 302 and len({r['row_id'] for r in rows}) == 302
    errors = [float(r['prediction']) - float(r['target']) for r in rows]
    assert all(math.isclose(e, float(r['error']), abs_tol=1e-12)
               for e, r in zip(errors, rows))
    assert math.isclose(math.fsum(abs(e) for e in errors)/302, E['pooled'][key]['mae'], abs_tol=1e-12)
    assert math.isclose(math.sqrt(math.fsum(e*e for e in errors)/302), E['pooled'][key]['rmse'], abs_tol=1e-12)
assert F['joined_events'] == 667 and sum(F['cohort_counts'].values()) == 667
assert [(f['prediction_year'], f['training_events'], f['later_events'], f['encoded_input_columns'])
        for f in P['folds']] == [(2021,118,106,51),(2022,254,110,63),(2023,365,86,69)]
assert sum(f['later_events'] for f in P['folds']) == 302
assert [4*f['encoded_input_columns']+9 for f in P['folds']] == [213,261,285]
assert all(E['pooled'][k]['rmse'] > E['pooled']['training_mean']['rmse'] for k, _ in MODELS[2:])
assert all(E['by_prediction_year'][str(y)]['neural_ensemble']['spearman'] < 0 for y in (2021,2022,2023))
assert A['events'] == 302 and A['reference_predictions_unchanged']
assert len(scored) == A['csv_event_model_rows_checked'] == 3624
assert math.isclose((10+10+30)/3, 50/3)
assert math.isclose(math.sqrt((100+100+900)/3), 19.148542155126762)
bridge = B['phase1_sample_bridge']
assert bridge['metadata_initial_registry'] - sum(bridge['base_exclusions'].values()) == 4673
assert 4673 - sum(bridge['history_exclusions'].values()) == 4440
assert 4440 - sum(bridge['schedule_exclusions'].values()) - bridge['merged_record_reduction'] == 2107

NAVY = colors.HexColor('#15334b')
TEAL = colors.HexColor('#087f83')
GRAY = colors.HexColor('#506275')
PALE = colors.HexColor('#edf4f7')
LINE = colors.HexColor('#d3dee6')
AMBER = colors.HexColor('#a25c16')
WIDTH = 524
styles = {
    'title': ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=NAVY, spaceAfter=13),
    'subtitle': ParagraphStyle('Subtitle', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=NAVY, spaceAfter=13),
    'body': ParagraphStyle('Body', fontName='Helvetica', fontSize=10.2, leading=13.6, textColor=NAVY, spaceAfter=8),
    'small': ParagraphStyle('Small', fontName='Helvetica', fontSize=8.6, leading=11.3, textColor=GRAY, spaceAfter=6),
    'meta': ParagraphStyle('Meta', fontName='Helvetica', fontSize=9, leading=12, textColor=TEAL, spaceAfter=13),
    'h': ParagraphStyle('Heading', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=TEAL, spaceBefore=7, spaceAfter=7, keepWithNext=True),
    'cell': ParagraphStyle('Cell', fontName='Helvetica', fontSize=9, leading=12, textColor=NAVY),
    'head': ParagraphStyle('Head', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white),
}
story, html_pages = [], []
page_html = []

def para(text, kind='body'):
    story.append(Paragraph(text, styles[kind]))
    tag = {'title':'h1','subtitle':'h2','h':'h3'}.get(kind,'p')
    page_html.append(f'<{tag} class="{kind}">{text}</{tag}>')

def page(title, first=False):
    global page_html
    if not first:
        html_pages.append(''.join(page_html))
        page_html = []
        story.append(PageBreak())
    para(title, 'title' if first else 'subtitle')

def table(rows, widths):
    cells = [[Paragraph(str(t), styles['head' if i == 0 else 'cell']) for t in row]
             for i, row in enumerate(rows)]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),5.5),('BOTTOMPADDING',(0,0),(-1,-1),5.5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
        ('LINEBELOW',(0,-1),(-1,-1),.5,LINE),
    ]))
    story.extend([t,Spacer(1,10)])
    page_html.append('<table>'+''.join('<tr>'+''.join(f'<{"th" if i == 0 else "td"}>{v}</{"th" if i == 0 else "td"}>' for v in row)+'</tr>' for i,row in enumerate(rows))+'</table>')

def box(text):
    t=Table([[Paragraph(text,styles['body'])]],colWidths=[WIDTH])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,LINE),
                          ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
                          ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([t,Spacer(1,11)])
    page_html.append('<aside>'+text+'</aside>')

class Network(Flowable):
    def __init__(self):
        super().__init__(); self.width=WIDTH; self.height=128
    def draw(self):
        c=self.canv
        c.setStrokeColor(LINE)
        for y in (105,78,51,24):
            c.line(142,65,255,y); c.line(277,y,400,65)
        for x,w,label,detail in [(0,142,'Prepared inputs','51, 63 or 69 columns'),(400,124,'Linear output','Two-year excess return')]:
            c.setFillColor(PALE); c.roundRect(x,41,w,48,5,fill=1,stroke=1)
            c.setFillColor(NAVY); c.setFont('Helvetica-Bold',10); c.drawCentredString(x+w/2,70,label)
            c.setFont('Helvetica',8.5); c.drawCentredString(x+w/2,54,detail)
        for j,y in enumerate((105,78,51,24),1):
            c.setFillColor(PALE); c.circle(266,y,11,fill=1,stroke=1)
            c.setFillColor(TEAL); c.setFont('Helvetica-Bold',9); c.drawCentredString(266,y-3,f'h{j}')
        c.setFillColor(GRAY); c.setFont('Helvetica',8)
        c.drawCentredString(262,5,'Each hidden neuron receives every input; all weights and biases are learned.')

page('Machine learning for 13D investment selection',True)
para('Jeff Lu | ML professor project and progress report | 21 October 2026','meta')
para('<b>Research question:</b> can information available after an initial Schedule 13D disclosure improve predictions of subsequent stock performance relative to a size-appropriate benchmark? Does separately validated information extracted from filing text improve the same models?')
box('<b>Current finding.</b> The first small neural network and tree comparisons have been trained and evaluated. None improves pooled return-prediction error over the simple references on the same 302 later events. The neural network also has negative within-year rank correlations in all three years. This is a negative development result, with useful next diagnostic questions; no investment edge is established.')
para('The neural network remains the central class method. Ridge regression and tree methods provide comparisons. LLM extraction is a planned feature-construction extension, rather than the core prediction model.','body')
table([['Method','Evaluated n','RMSE (pp)','MAE (pp)'], *[
    [name,str(E['pooled'][k]['n']),f"{100*E['pooled'][k]['rmse']:.2f}",f"{100*E['pooled'][k]['mae']:.2f}"] for k,name in MODELS
]], [254,72,99,99])
para('<b>How to read the table:</b> lower is better. MAE is the average absolute forecast miss; RMSE gives large misses more weight. Units are percentage points of cumulative two-year stock-minus-benchmark return. These are prediction errors, not portfolio returns. [E5]','small')
para('Progress since the October 15 report','h')
para('The network has moved from an untrained proposal to a completed Windows experiment. A shallow tree, random forest and gradient boosting were added using the same prepared inputs and evaluation events. The returned results passed independent checks and exact replay. A Bloomberg export was received and reviewed, but historical-availability issues prevent its inclusion. No LLM features have been evaluated.')
para('<b>Next decision:</b> diagnose optimization, target tails and feature limitations before increasing model complexity. Agree on a limited, chronologically validated follow-up experiment and how to reserve an unexposed final evaluation.','body')

page('Data, observation rules and sample coverage')
para('One observation is an eligible initial-disclosure issuer-entry event with a historical stock match, an entry date and a subsequent return label. It is not automatically an independent activist campaign. The current 667-row feature panel has entry years 2018-2023. The 302 scored events enter in 2021-2023. [E1-E3]')
para('How the current prediction sample was formed','h')
table([
    ['Stage','Count','Meaning of the reduction'],
    ['Metadata initial registry','17,795','Older initial-record registry; a different selection path from factual staging.'],
    ['Basic screened records','4,673','Entry-window, source/security, trading-readiness and protected-review screens.'],
    ['First-observed pair records','4,440','233 removed for observed prior investor-issuer history. First in this archive is not necessarily first ever.'],
    ['Two-year scheduled events','2,107','1,995 records removed for overlap, multiple securities or calendar limits; merging reduces records by another 338.'],
    ['Calculable common labels','694','2,107 minus 1,395 without benchmark assignment, minus 18 return refusals.'],
    ['Single-filing feature panel','667','27 merged events deferred pending a feature-aggregation rule.'],
    ['Later events evaluated','302','106 in 2021, 110 in 2022 and 86 in 2023; remaining panel rows enter earlier.'],
],[139,51,334])
para('The separate archive preparation contains 75,631 filing records accepted from January 2013 to September 2026 and factual processing of 15,813 selected initial candidates through 2025. Those counts are not successive steps in the return-sample funnel above. [E8]','small')
table([
    ['Disjoint diagnostic investor group','Panel n','Evaluated n'],
    ['Focused activist candidates','55','18'],['Other Event-Driven candidates','12','4'],
    ['Other HFR candidates','44','25'],['Other / unresolved','556','255'],['Total','667','302'],
],[340,92,92])
para('<b>HFR classification:</b> retained for diagnostics, excluded from predictors. Historical availability and fund/firm-to-filing attribution still require validation; a strategy offering does not establish the purpose of a particular filing. Unmatched investors remain unknown, rather than being classified as passive or non-hedge-fund.')
para('Coverage and inherited issuer non-overlap rules restrict the population. Outcome windows overlap across issuers and reporter identities recur. Neither 667 nor 302 is a count of independent trials. [E3-E4]','small')

page('Actual model inputs and preprocessing')
para('The experiment uses ten structured source fields describing size, industry, reported ownership and prior disclosure activity. The source evidence is preserved separately from future outcomes and diagnostic identities. Deterministic construction makes a rule reproducible; it does not certify semantic accuracy. [E1]')
fields=[
('Security size','snapshot_security_market_cap_usd','Dated CRSP security-level market cap; not consolidated company value.'),
('Industry','pre_disclosure_industry_sic2','Pre-disclosure two-digit SIC; a category, not a numerical magnitude.'),
('Reporting-person count','parsed_reporting_person_count','Parsed cover-page persons; not independent investors.'),
('Reported ownership','reported_ownership_pct_max','Largest valid percentage for the matched security; overlapping stakes are not summed.'),
('Ownership coverage','ownership_pct_valid_fraction','Valid percentages divided by extracted ownership rows for that security.'),
('Event-to-filing lag','filing_event_lag_calendar_days','Calendar days from disclosed event date to filing date; not a deadline assessment.'),
('Header reporter count','header_reporter_count','Distinct observed header CIK identifiers; not validated managers.'),
('Prior submissions','prior_header_submission_count_max','Maximum strictly prior submission count among header reporters.'),
('Prior other issuers','prior_header_other_issuer_count_max','Maximum strictly prior other-issuer count among header reporters.'),
("Issuer's prior reporters",'prior_issuer_other_reporter_count','Prior reporters at the issuer outside the current header group.'),
]
table([['Source field','Construction / interpretation','Present / 667'],*[
    [label,desc,str(F['feature_coverage'][key]['present'])] for label,key,desc in fields
]], [125,315,84])
para('Ownership is missing in 110 events, including 14 with unresolved security attribution. The valid-percentage fraction is missing in 21 events and filing lag in 18. Missing source values are not silently replaced with economic zero. [E1-E2]','small')
para('What the network receives','h')
para('Within each year, learn transformations on training inputs only: declared log(1+x) transforms; median replacement for missing numerical values; missing-value indicators; numerical centering and scaling; industry indicator columns; and removal of training-constant columns. Reuse those fitted transformations on later entries. Unseen later industries use an all-zero industry vector and are separately flagged in diagnostics.')
para('The ten fields become <b>51, 63 and 69 retained input columns</b> for 2021, 2022 and 2023. In 2023 these are eight varying numerical columns, three missingness columns and 58 industry indicators. The header reporter count is constant in training and drops out. [E2]')
para('Excluded from inputs: raw issuer/reporter IDs, HFR labels, future returns or amendments, Bloomberg financials and LLM interpretations. Momentum, volatility and liquidity predictors are not assembled in this version. Prior-disclosure histories begin with the supplied archive in 2013.','small')

page('The small neural network: what was trained')
para('The network learns four intermediate combinations of the prepared inputs, then combines them into one continuous return forecast. It has one hidden layer of width four and a linear output, allowing positive and negative predictions. [E4]')
story.append(Network())
page_html.append('<aside><b>Architecture:</b> prepared inputs (51 / 63 / 69) &rarr; four fully connected ReLU hidden neurons &rarr; one linear return output.</aside>')
para('For neuron j: <b>z_j = sum_k(W_jk x_k) + b_j</b>; activation <b>h_j = max(0, z_j)</b>.<br/>Final forecast: <b>yhat = c + sum_j(v_j h_j)</b>. Weights W and v determine sensitivity; biases b and c shift the responses. Training learns them jointly.')
para('<b>Why ReLU?</b> It introduces bends into the prediction rule. Without a nonlinear activation, successive affine layers collapse to another affine rule. For an invented ownership example, max(0, ownership - 8) is inactive below 8% and increases above it. Our actual thresholds and input combinations are learned, not set to 8%. A neuron is not assumed to have an economic interpretation.')
table([['Prediction year','Input columns p','Parameters: 4p + 9','Training events'],
       *[[str(f['prediction_year']),str(f['encoded_input_columns']),str(4*f['encoded_input_columns']+9),str(f['training_events'])] for f in P['folds']]], [116,116,176,116])
para('How learning updates the weights','h')
para('A forward pass computes forecasts. The training objective measures mean squared error plus a penalty on large weights. Backpropagation computes how that objective changes with each parameter; Adam uses those gradients to update the parameters. More parameters increase flexibility, rather than guaranteeing better prediction.')
box('<b>Fixed training objective:</b> mean((yhat - y)^2) + 0.01 x (sum(W^2) + sum(v^2)). Both biases are unpenalized. Targets stay in decimal return units without clipping, scaling or transformation.')
para('Initialization: hidden weights use a normal distribution with standard deviation sqrt(2/p), hidden biases start at zero, output weights have standard deviation 0.01, and the output bias starts at the training-target mean. Training uses 500 full-batch Adam updates at learning rate 0.001; the final update is always used. No later-year early stopping. [E4]','small')
para('Five fixed seeds (11, 23, 37, 51, 71) give five starting-weight choices. All five forecasts are averaged for the main network result; each seed remains reported. PyTorch CPU float64 fitting ran on Windows. A fixed 500-update budget does not prove convergence.','small')

page('Comparison methods and chronological evaluation')
para('All methods receive identical prepared inputs and are scored on identical later events. Configurations are fixed starting choices, with no hyperparameter search. This compares these implementations; it is not an optimized ranking of algorithm families. [E3-E4]')
table([
    ['Method','Learning rule / fixed configuration'],
    ['Zero excess / training mean','Predict zero, or the mean completed earlier outcome, for every later event. No feature-based selection.'],
    ['Ridge regression','Linear prediction with a squared-weight penalty; mean squared training error + 1 x sum(beta^2); intercept unpenalized.'],
    ['Shallow tree','Learn threshold splits; depth at most 2, at least 20 training events in each leaf.'],
    ['Random forest','Average 200 varied bootstrap trees; depth at most 3, minimum leaf 20, 70% of input columns considered per split.'],
    ['Gradient boosting','Add sequential corrections from 100 depth-2 trees, learning rate 0.05, minimum leaf 20; squared-error loss, all training rows per stage.'],
],[142,382])
para('Target and information timing','h')
para('Target y is the cumulative stock total return minus its assigned Russell size-segment ETF-proxy cumulative return over <b>504 exchange sessions</b>. Entry is the opening of the second exchange session after public acceptance, with entry counted as session one. This is an event-level gross return difference, not annualized or risk-adjusted alpha. Historical index/size assignment and ETF-proxy returns are distinct concepts. [E3]')
table([['Prediction year','Completed training n','Later events n','Encoded inputs'],
       *[[str(f['prediction_year']),str(f['training_events']),str(f['later_events']),str(f['encoded_input_columns'])] for f in P['folds']]], [116,160,132,116])
para('At each January 1 cutoff, training requires both entry and the scheduled two-year outcome end to be strictly earlier. A 2020 entry cannot train the 2021 forecast merely because its filing is in the past: its two-year outcome is not yet known. Training sets overlap across years and should not be added as unique observations.')
para('How forecast errors are calculated','h')
para('<b>e_i = prediction_i - actual_i</b>; <b>MAE = sum(abs(e_i))/n</b>; <b>RMSE = sqrt(sum(e_i^2)/n)</b>. Pool all 302 event errors with equal event weights. Do not average yearly RMSE. Multiply decimal error measures by 100 to report percentage points. Weight penalties are excluded from evaluation errors.')
para('<b>Invented arithmetic:</b> errors of +10, -10 and +30 points give MAE = 50/3 = 16.67 points and RMSE = sqrt(1,100/3) = 19.15 points. Opposite signs cannot cancel in either measure; squaring makes a 30-point miss count nine times as much as a 10-point miss.','small')
para('All outcome history was already examined in earlier project work. These are chronological development evaluations, not an untouched final test. Neither chronological separation nor reproducibility creates independent observations.','small')

page('Results: forecast accuracy, ranking and stability')
para('No tested feature-based model beats the earlier-training mean or zero-excess reference on pooled RMSE. The same is true for pooled MAE. The forest improves RMSE modestly over ridge (92.42 vs 93.68 points), but remains worse than both constants. This does not demonstrate useful incremental prediction. [E5]')
table([['Entry year / n','Zero RMSE','Mean RMSE','NN RMSE','Forest RMSE'],*[
    [f'{y} / {E["by_prediction_year"][str(y)]["neural_ensemble"]["n"]}',
     *[f'{100*E["by_prediction_year"][str(y)][k]["rmse"]:.2f}' for k in ('zero_excess','training_mean','neural_ensemble','forest')]] for y in (2021,2022,2023)
]], [112,103,103,103,103])
para('All table errors above are percentage points. The neural ensemble is worse than the earlier-training mean in each evaluation year, rather than only in the pooled result.','small')
para('Can the model rank opportunities despite inaccurate magnitudes?','h')
para('Spearman correlation compares the ordering of predictions with the ordering of actual returns within each year. +1 means identical ordering, 0 means zero rank correlation, and -1 means reversed ordering. Constant references have no within-year ranking. This descriptive measure does not establish an investable portfolio.')
table([['Method','2021: n=106','2022: n=110','2023: n=86'],*[
    [name,*[f'{E["by_prediction_year"][str(y)][key]["spearman"]:.3f}' for y in (2021,2022,2023)]]
    for key,name in MODELS[2:]
]], [215,103,103,103])
para('The neural ensemble has negative rank correlations in all three years. Boosting correlations are small: +0.029, -0.001 and +0.042. These figures provide no demonstrated stable positive ranking benefit. They do not justify reversing the signal or choosing a method after observing outcomes. No dependence-adjusted significance test is claimed.','small')
para('Sensitivity to starting weights and extreme misses','h')
table([['Neural seed','11','23','37','51','71'],
       ['Pooled RMSE (pp)',*[f'{100*E["pooled"][f"neural_seed_{s}"]["rmse"]:.2f}' for s in N['seeds']]]], [139,77,77,77,77,77])
para(f'All five seed results are retained; their ensemble RMSE is 108.96 points. Seed spread measures sensitivity in this fixed design, not a confidence interval. The five largest event misses account for {100*E["largest_five_share_of_sse"]["neural_ensemble"]:.1f}% of neural squared error and {100*E["largest_five_share_of_sse"]["zero_excess"]:.1f}% for zero excess. All events remain included. [E5]','small')
box('<b>Interpretation:</b> current inputs and fixed specifications have not demonstrated better forecasts or stable positive ranking. The evidence does not establish that 13D information is intrinsically uninformative, or identify the cause of the failure. Optimization, target tails, limited data and information quality require separate diagnosis.')

page('Feature extensions, limitations and research controls')
para('Structured-data learning is the completed first comparison. The next information sets should be added in separately specified experiments on comparable events, keeping the current negative result visible.')
para('Bloomberg fundamentals: received, not yet model-ready','h')
para('The returned workbook matches all 667 requested events: 587 have all nine numeric raw fields, 57 are partial and 23 have none. These counts assess completeness and internal consistency, not point-in-time correctness. [E9]')
para('The annual-period rule uses the calendar year before the cutoff. A January 3, 2019 BHE row selects FY2018 figures announced on February 7, 2019, after the cutoff. This is a concrete information-availability conflict. Prior-year revenue, operating cash flow and company market cap are absent, and annual flows differ from the requested actual trailing-twelve-month measures. Historical mapping, publication dates, revisions, currency and scale need validation. No Bloomberg fields entered the completed models.')
para('LLM extraction: secondary information contribution','h')
para('The proposed role is to convert filing passages into structured inputs, such as stated governance objectives, capital-allocation demands and ownership relationships. Deterministic processing supplies explicit dates, identifiers and source rows; LLM interpretation addresses language and attribution that fixed parsing may miss. No incremental LLM performance result exists. [E10]')
table([
    ['Required step','What it establishes'],
    ['Human reference before model labels','Bounded development examples with source passages and uncertainty; preserve an unexposed evaluation sample.'],
    ['Fixed extraction protocol','Version input text, schema, model/settings and prompt; retain evidence spans and permit abstention.'],
    ['Repeated interpretation checks','Measure label and downstream forecast variation. Agreement is stability, not proof of truth; repeated-label frequencies are not calibrated truth probabilities.'],
    ['Matched feature ablation','Compare the same methods with structured inputs alone versus structured plus validated text inputs, using the same events and dates.'],
],[163,361])
para('Limits that matter for interpretation','h')
para('<b>Data:</b> return/benchmark coverage selects the population; ownership and investor identity remain uncertain; dated vendor history does not certify original availability. The inherited non-overlap rule can remove informative ML examples and requires a separate design decision.')
para('<b>Statistics:</b> 118-365 training events are small relative to 213-285 neural parameters. Return windows overlap and identities recur. Squared error emphasizes extreme targets. No confidence intervals, causal findings or independent-event significance claims are reported.')
para('<b>Decision scope:</b> the current outcome is a two-year return forecast. Invest/not-invest, entry timing, holding horizon and position sizing remain separate policy choices requiring capital, cost and risk assumptions. No funded portfolio, after-cost alpha or live trading is evaluated.','small')

page('Progress, next experiment and professor feedback')
table([
    ['Workstream','Status as of 21 October 2026'],
    ['Observation and features','Completed candidate panel and source-backed ten-field preparation; semantic and coverage qualifications remain.'],
    ['Chronological inputs','Completed training-only preprocessing and matured-label annual folds.'],
    ['Simple prediction references','Completed zero, mean and fixed ridge comparisons on 302 later events.'],
    ['Nonlinear methods','Completed neural, tree, forest and boosting comparison on Windows; returned results independently audited.'],
    ['Diagnosis and controlled follow-up','Next: inspect saved loss/gradient curves, neuron activity, seed differences and influential targets before a new specification.'],
    ['Richer data and LLM inputs','Planned; Bloomberg availability checks and human-first extraction validation are prerequisites.'],
],[166,358])
para('Proposed next experiment - for discussion','h')
para('First diagnose the current model without changing it: distinguish optimization behavior from poor later prediction and identify whether target tails or sparse inputs warrant a follow-up. Then freeze a small set of candidate changes, such as regularization or a robust training loss, using only chronologically matured inner validation folds. Do not choose settings on the displayed later-year outcomes.')
para('Report the unchanged baseline alongside the follow-up, including MAE, RMSE, within-year ranking and training diagnostics. Any overlap-rule change, validated HFR predictor or richer feature set needs a new protocol and matched-sample comparison. Reserve an evaluation set not previously exposed; if none is available, label all subsequent comparisons as development evidence.')
para('Questions for the ML professor','h')
para('1. Is a four-neuron network with explicit regularization an appropriate central method for this sample size, or should capacity be reduced further?<br/>2. Should the main task remain continuous-return prediction, with ranking and a separately defined classification task as secondary analyses?<br/>3. What restricted tuning and chronological validation design would be sufficient for the course?<br/>4. How much of the project should focus on model diagnosis versus an incremental, validated text-feature experiment?')
para('Reproducibility and evidence','h')
para('The completed run used Windows Python 3.13.12 on CPU. All 43 relevant checks passed on Windows and Mac; 15 run artifacts replay exactly in the recorded Windows environment. An independent Mac audit checked 2,416 saved-state forecasts, 96 metric sets and 3,624 event/model rows without fitting models. These are calculation checks, not evidence of predictive success. [E7, E12]','small')
para('The first attempt stopped before scoring because a serialized forest disagreed at a floating-point split boundary. A minimal reproducer and regression test fixed the comparison precision. The failed evidence was preserved and a new corrected run retained the same statistical settings. No outcome-based exclusions, tuning or seed selection were introduced.','small')
para('Evidence key: E1 features; E2 preprocessing; E3 baseline protocol; E4 nonlinear protocol; E5 results; E6 diagnostics; E7 independent audit; E8 sample construction; E9 Bloomberg audit; E10 extraction workflow; E11 event errors; E12 Windows receipt. Source paths, copies and SHA-256 hashes accompany the report in index.html and evidence.json. No new models were run. AI-assisted code and report preparation; extraction interpretations remain unvalidated.','small')

html_pages.append(''.join(page_html))
assert len(html_pages) == 8

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE); canvas.line(44,40,568,40)
    canvas.setFont('Helvetica',8); canvas.setFillColor(GRAY)
    canvas.drawString(44,27,'Jeff Lu | 13D machine learning | Development research | 21 Oct 2026')
    canvas.drawRightString(568,27,f'{doc.page} / 8')
    canvas.restoreState()

HERE.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(PDF),pagesize=(612,792),rightMargin=44,leftMargin=44,
                      topMargin=43,bottomMargin=53,title='13D Machine Learning: Project and Progress Report',
                      author='Jeff Lu',subject='Completed neural and tree comparisons, limitations and next research steps')
def stable_canvas(*args, **kwargs):
    kwargs['invariant'] = 1
    return Canvas(*args, **kwargs)

doc.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=stable_canvas)
reader=PdfReader(PDF)
assert len(reader.pages) == 8, f'Unexpected overflow: {len(reader.pages)} pages'
for i,p in enumerate(reader.pages,1):
    text=p.extract_text()
    assert len(text)>500, (i,'empty or sparse page')
    assert f'{i} / 8' in text
alltext='\n'.join(p.extract_text() for p in reader.pages)
for required in ['108.96','87.08','89.90','302','667','213','261','285','16.67','19.15','-0.193','43','2,416']:
    assert required in alltext, required

snapshots=HERE/'source-snapshots'
snapshots.mkdir(exist_ok=True)
evidence=[]
for label,path in SOURCES.items():
    dest=snapshots/(label.split()[0]+'-'+path.name)
    shutil.copyfile(path,dest)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
    evidence.append({'id':label,'path':str(path.relative_to(ROOT)),'snapshot':str(dest.relative_to(HERE)),'sha256':digest})

css='''body{margin:0;background:#eef3f6;color:#15334b;font:17px/1.65 system-ui,sans-serif}main{max-width:940px;margin:28px auto}section{background:white;padding:36px;margin:24px 0}h1{font-size:34px;line-height:1.2}h2{font-size:27px;line-height:1.25}h3{font-size:21px;color:#087f83}table{border-collapse:collapse;width:100%;font-size:15px;margin:20px 0}td,th{padding:11px;text-align:left;vertical-align:top;border-bottom:1px solid #d3dee6}th{background:#15334b;color:white}tr:nth-child(even){background:#edf4f7}aside{background:#edf4f7;border-left:4px solid #087f83;padding:20px}a{color:#087f83}.meta{color:#087f83}.small{font-size:14px;color:#506275}code{overflow-wrap:anywhere}@media print{body{background:white}section{page-break-after:always;padding:0}main{max-width:none}}'''
evidence_html='<h2>Source evidence</h2><p>The PDF is self-contained; the links below open preserved project records locally.</p><ol>'+''.join(f'<li><a href="../../../{escape(e["path"])}">{escape(e["id"])}</a> - <a href="{escape(e["snapshot"])}">report snapshot</a></li>' for e in evidence)+'</ol>'
html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D ML professor update - 21 October 2026</title><style>'+css+'</style><main><section><p><a href="../../../START-HERE.html">Project home</a> | <a href="../ml-checkpoints.html">Learning checkpoints</a></p><p><a href="'+PDF.name+'">Download the eight-page PDF</a></p><p>Updated from completed October 19 experiments. No new fitting or extraction.</p></section>'+''.join('<section>'+s+'</section>' for s in html_pages)+'<section>'+evidence_html+'</section></main></html>'
(HERE/'index.html').write_text(html)
manifest={'report_date':'2026-10-21','research_status':'development evaluation; no new fitting',
          'pages':8,'source_evidence':evidence,'models':{k:E['pooled'][k] for k,_ in MODELS},
          'checks':{'same_events_per_model':302,'event_error_rows':len(scored),'pooled_metrics_recomputed':True,
                    'source_snapshots_hash_match':True,'toy_metrics_pinned':True,'page_text_checks_passed':True},
          'pdf_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
          'html_sha256':hashlib.sha256((HERE/'index.html').read_bytes()).hexdigest(),
          'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE/'evidence.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'pdf':str(PDF),'pages':len(reader.pages),'characters':len(alltext),'sources':len(evidence)},indent=2))
