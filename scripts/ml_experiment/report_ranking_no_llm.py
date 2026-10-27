"""Explain the saved no-LLM ranking comparison and publish active navigation.

Inputs: verified prediction/evaluation snapshots; no fitting or new source data.
Outputs: HTML learning report, event rank changes, project-home/plan/index links.
Identity: every displayed statistic comes from saved evaluation; rank changes use
average ranks of forecast scores within each already-generated annual cohort.
Tier: 1. Run project Python scripts/ml_experiment/report_ranking_no_llm.py.
"""
import csv
import hashlib
import io
import json
import re
from html import escape
from pathlib import Path

from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research/runs/ranking-no-llm/20261026-v1'
LABELS = {'constant': 'Constant score', 'smaller_size': 'Smaller-size rule',
          'ridge_return': 'Ridge: return target', 'ridge_rank': 'Ridge: rank target',
          'tree_rank': 'Shallow tree: rank target'}


def load(name):
    return json.loads((RUN / name).read_text())


def fmt(value, digits=3):
    return 'undefined' if value is None else f'{value:+.{digits}f}'


def immutable(name, payload):
    path = RUN / name
    if path.exists():
        assert path.read_bytes() == payload, f'Preserve differing report artifact: {name}'
    else:
        path.write_bytes(payload)


def main():
    summary, evaluation, verification = [load(n) for n in ['summary.json', 'evaluation.json', 'verification.json']]
    assert verification['status'] == 'passed'
    metrics, quintiles = evaluation['metrics'], evaluation['quintiles']
    folds = load('folds.json')
    panels = load('inputs/panels.json')
    predictions = [json.loads(line) for line in (RUN / 'predictions.jsonl').read_text().splitlines()]
    lookup = {(int(h), r['row_id']): r for h, rows in panels.items() for r in rows}
    changes = []
    for h, year in sorted({(r['horizon_sessions'], r['prediction_year']) for r in predictions}):
        rows = [r for r in predictions if r['horizon_sessions'] == h and r['prediction_year'] == year]
        old = rankdata([r['scores']['ridge_return'] for r in rows])
        new = rankdata([r['scores']['ridge_rank'] for r in rows])
        for row, a, b in zip(rows, old, new, strict=True):
            meta = lookup[(h, row['row_id'])]
            changes.append({'horizon_sessions': h, 'prediction_year': year, 'row_id': row['row_id'],
                            'accession': meta['accession'], 'issuer_cik': meta['issuer'], 'entry': meta['entry'],
                            'annual_cohort_n': len(rows), 'return_model_rank_low_to_high': float(a),
                            'rank_model_rank_low_to_high': float(b),
                            'rank_change_positive_is_higher': float(b-a),
                            'realized_gross_excess_pp': 100*meta['excess']})
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(changes[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(changes)
    immutable('ranking-changes.csv', out.getvalue().encode())

    def ranking_table(horizon, sample='horizon_specific'):
        selected = [r for r in metrics if r['sample'] == sample and r['horizon_sessions'] == horizon]
        years = sorted({r['prediction_year'] for r in selected})
        cells = []
        for model, label in LABELS.items():
            vals = [next(r for r in selected if r['model'] == model and r['prediction_year'] == year) for year in years]
            t = next(r for r in summary['temporal_summary'] if r['sample'] == sample and r['horizon_sessions'] == horizon and r['model'] == model)
            cells.append('<tr><th>'+label+'</th>'+''.join(
                f'<td class="{"positive" if r["spearman"] is not None and r["spearman"] > 0 else "negative" if r["spearman"] is not None else ""}">{fmt(r["spearman"])}</td>' for r in vals)
                +f'<td>{fmt(t["median_year_spearman"])}</td><td>{t["positive_years"]}/{t["defined_spearman_years"] if model != "constant" else "0 defined"}</td></tr>')
        counts = [next(r['n'] for r in selected if r['prediction_year'] == year) for year in years]
        return '<div class="scroll"><table><thead><tr><th>Model</th>'+''.join(f'<th>{y}<br>n={n}</th>' for y,n in zip(years,counts,strict=True))+'<th>Median year</th><th>Positive years</th></tr></thead><tbody>'+''.join(cells)+'</tbody></table></div>'

    def quintile_table():
        rows = []
        selected = [r for r in metrics if r['sample'] == 'horizon_specific' and r['model'] == 'ridge_rank']
        for r in selected:
            groups = sorted([q for q in quintiles if q['sample'] == r['sample'] and q['model'] == r['model'] and q['prediction_year'] == r['prediction_year'] and q['horizon_sessions'] == r['horizon_sessions']], key=lambda q:q['quintile'])
            rows.append(f'<tr><td>{r["horizon_sessions"]//21} months</td><td>{r["prediction_year"]}</td><td>{r["n"]}</td>'+''.join(f'<td>{fmt(q["mean_excess_pp"],1)}</td>' for q in groups)+f'<td>{fmt(r["top_minus_bottom_pp"],1)}</td></tr>')
        return '<div class="scroll"><table><thead><tr><th>Horizon</th><th>Year</th><th>Events</th><th>Q1 lowest</th><th>Q2</th><th>Q3</th><th>Q4</th><th>Q5 highest</th><th>Q5−Q1</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'

    fold_table = ''.join(f'<tr><td>{f["horizon_sessions"]//21} months</td><td>{f["prediction_year"]}</td><td>{f["training_events"]}</td><td>{f["later_events"]}</td><td>{f["encoded_columns"]}</td><td>{f["latest_training_label_end"]}</td><td>{f["shared_issuers"]}</td></tr>' for f in folds)
    report = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D ranking without LLM extraction</title><style>
body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1160px;margin:28px auto;padding:28px;background:white}}h1,h2{{line-height:1.25}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d7dfe5;vertical-align:top}}thead th{{background:#edf3f7}}.scroll{{overflow:auto}}.positive{{color:#126145}}.negative{{color:#8c3342}}.callout{{background:#eef4f8;padding:18px;border-left:4px solid #306187}}a{{color:#155c99}}details{{margin:18px 0}}code{{overflow-wrap:anywhere}}</style></head><body><main>
<h1>Can we improve 13D investment rankings before adding LLM information?</h1>
<p>October 26, 2026 · Completed chronological development comparison · No LLM extraction or Bloomberg fundamentals used</p>
<p class="callout"><strong>The ranking-focused ridge gives a more encouraging 12-month pattern, but the 24-month evidence remains mixed.</strong> At 12 months its rank correlations are positive in three of four prediction years, versus one of four for return-target ridge. At 24 months it is positive in one of three years. The shallow rank-target tree does not supply a consistent alternative. These are descriptive results from previously examined history, not an established investment edge.</p>
<h2>What changed and why</h2>
<p>We retained the ten existing structured inputs and the saved return labels. We changed what two models learn: relative outcome position rather than the exact excess-return magnitude. This directly addresses Jeff's request to revisit rankings before proceeding with text extraction. The original 24-month return-ridge predictions reproduce exactly on all 302 later events, which anchors the before/after comparison.</p>
<p>The inputs are dated security market capitalization, industry, reported ownership percentage, ownership parsing coverage, reporting-person count, filing/event lag, header reporter count, prior submission count, prior other-issuer count and prior issuer/reporter history. Names and IDs identify records; investor cohort labels are diagnostics. No identity code is treated as a numerical investment signal.</p>
<p><strong>This is a structured-input baseline, not yet the conventional-financial baseline in the new project question.</strong> The nine Bloomberg fields are excluded because publication dates, revision vintage and historical mapping remain unresolved. There was no new financial download, source correction, return calculation or LLM interpretation.</p>
<h2>The method, from the beginning</h2>
<p>A <strong>training target</strong> is the answer the model tries to learn from earlier examples. The earlier ridge predicts the numerical cumulative excess return. The new ridge predicts the position of that return among all currently completed training outcomes. If five outcomes are −40%, −10%, 0%, +20% and +300%, their midpoint percentile targets are 0.1, 0.3, 0.5, 0.7 and 0.9. The 300% result still ranks highest, but its magnitude no longer dominates the target's squared-error loss. The tradeoff is losing information about distances between returns.</p>
<p><strong>Ridge</strong> fits a weighted combination of inputs while penalizing large coefficients. Both versions use the same fixed mean-loss penalty of 1 and an unpenalized intercept. <strong>The shallow tree</strong> learns at most two successive splits, with at least twenty training events in each leaf; it predicts training rank targets. This limits complexity but produces many tied scores. We also report a fixed smaller-size rule and a constant-score reference. Rank regression is a surrogate for ordering; it does not directly maximize Spearman, and its scores are not probabilities.</p>
<p>There are 21 learned model fits: three models at each of seven horizon/year origins. No parameter search, best-seed selection, score inversion, neural-network fit or extra model was added after seeing results.</p>
<h2>How to read the ranking statistic</h2>
<p><strong>Spearman correlation</strong> compares the order of model scores with the order of realized excess returns within each prediction year. +1 means identical ordering; −1 means reverse ordering; a value near zero means little overall monotonic association in that cohort. Constant scores have undefined correlation. We show every year rather than pooling scores from differently fitted models. The median and positive-year count summarize these few observed years; they are not confidence intervals.</p>
<h2>12-month results: 411 later events, 2020–2023</h2>{ranking_table(252)}
<p>Rank-target ridge improves on return-target ridge in each of the four years, with correlations of +0.039, −0.007, +0.088 and +0.206. The 2021 value is effectively near zero. This is a useful development lead, but three positive years do not establish a stable or statistically reliable effect.</p>
<h2>24-month results: 302 later events, 2021–2023</h2>{ranking_table(504)}
<p>The rank-target version is worse in 2021, improves to +0.074 in 2022, and is near zero in 2023. It does not deliver consistently positive two-year ranking evidence. Smaller-size ranking is negative in every observed year at both horizons. We did not reverse that rule after observing the signs.</p>
<h2>Do higher scores select better realized outcomes?</h2>
<p>The following table groups rank-ridge scores into five equal-weight groups within each annual cohort. Q5 contains the highest scores. Entries are mean cumulative stock-minus-assigned-Russell-ETF returns in <strong>percentage points</strong>. The last column is Q5 minus Q1; it is an event-level descriptive difference, not a funded long-short portfolio return.</p>{quintile_table()}
<p>A positive top-minus-bottom difference can coexist with negative mean excess returns in both groups. Spearman evaluates the whole ordering, while a quintile spread compares two tails and remains sensitive to extreme realized returns. For example, 2023's 12-month rank correlation is positive but the extreme-group spread is only about +1.5 percentage points.</p>
<p>Exact score ties receive identical fractional weights across quintile boundaries. A tree with three distinct scores cannot form five distinct conviction levels. Constant scores allocate every event equally across all five groups, giving no economic separation; tiny saved differences near 10⁻¹⁵ percentage points are floating-point noise.</p>
<h2>Which events changed position?</h2><p><a href="ranking-changes.csv">Every event's return-model versus rank-model position</a> is saved for all 713 event/horizon predictions. Higher rank means a higher model score; positive change means the rank-target model moved that event up. These ranks use all entries in a calendar year retrospectively for evaluation. They are not an annual list available for trading on January 1. No future returns enter the score itself.</p>
<h2>Sample, timing and fair comparisons</h2>
<p>The universe is anchored to the existing 667-event two-year feature panel, covering 641 issuer IDs and 639 stock IDs. Exact event/accession/issuer/security/entry joins find 662 twelve-month labels and all 667 two-year labels. Five twelve-month joins are unavailable under the independently formed horizon schedule; they are not assigned zero returns. Earlier rows without mature training history are retained in the panel but are not scored as later evaluation rows. This gives 411 twelve-month predictions across four years and 302 two-year predictions across three years. These samples overlap and must not be added as distinct investments.</p>
<p>Training at each January 1 uses only events whose entry and saved horizon endpoint both precede that date. Missing-value fills, numeric scaling and industry encodings are learned on those training inputs only. We inherit the saved endpoint and source conventions rather than independently certifying daily-price completeness.</p>
<div class="scroll"><table><thead><tr><th>Horizon</th><th>Prediction year</th><th>Completed training</th><th>Later events</th><th>Encoded inputs</th><th>Latest training endpoint</th><th>Shared issuers</th></tr></thead><tbody>{fold_table}</tbody></table></div>
<details><summary>Compare horizons on the same 297 later events in 2021–2023</summary><p>The tables below recompute evaluation on identical event IDs in each year (105, 109 and 83). Training remains horizon-specific because one-year outcomes mature sooner. The qualitative conclusion persists; this is an evaluation-sample check, not a new fit.</p><h3>12 months, matched events</h3>{ranking_table(252,'common_12_24')}<h3>24 months, matched events</h3>{ranking_table(504,'common_12_24')}</details>
<h2>What the return labels mean</h2>
<p>The horizons are 252 and 504 exchange sessions, approximating 12 and 24 months. The inherited entry convention is the opening of the second exchange session after public acceptance, with entry counted as session one. Outcomes are gross cumulative stock total return minus the assigned size-segment Russell ETF proxy (IWB, IWR or IWM), with saved dividend/delisting and missing-price rules. ETF proxy returns are not index returns. These are event-level observations with overlapping windows, not independent campaigns, after-cost performance, annualized returns or risk-adjusted alpha.</p>
<h2>Verification and limits</h2>
<p>The targeted tests passed locally, including hand-computed percentile/quintile examples, missing-input refusal, strict maturity, saved-tree threshold handling and exact replay. Independent checks reconcile 713 predictions, 65 annual model/sample metric rows and 325 quintile rows, reconstruct fourteen ridge coefficient vectors using augmented least squares, and verify tree leaf counts/means and all seven training cutoffs. SciPy independently agrees with the rank statistics. The old 24-month ridge is reproduced exactly. Source and prefit hashes are unchanged; protocol, code, fitted states, forecasts and environment are saved.</p>
<p>Previously inspected outcomes remain development evidence, even though each fit excludes its later outcomes. Repeated entities and overlapping return windows create dependence. With only three or four annual blocks, we do not attach an ordinary independent-row confidence interval or a significance claim. Annual dispersion is descriptive. Parser-derived ownership/identity summaries, historical vendor availability, selective coverage and inherited corporate-action/accounting exceptions remain limitations. A mechanically correct experiment cannot certify those source assumptions.</p>
<h2>What we should do next</h2>
<p>Keep the rank-target ridge as a predeclared candidate alongside the original baseline, without promoting it to a proven strategy. Resolve the minimum historical-availability and mapping issues in the Bloomberg inputs, then run financial-only comparisons on matched eligible events. LLM extraction can follow as a separate incremental-information experiment. The current run leaves the reserved extraction cases unexposed and provides a non-LLM reference for later comparison; it does not complete the financial-versus-LLM study.</p>
<details><summary>Learning checks</summary><p><strong>Does a score of 0.9 mean a 90% chance of outperforming?</strong> No. The training target describes relative rank among earlier outcomes, not a calibrated probability.</p><p><strong>Why not learn from every earlier entry?</strong> A two-year investment entered last year has not completed its outcome by this year's origin. Its future return cannot yet enter training.</p><p><strong>Does positive correlation imply positive returns?</strong> No. A model can order a weak set of investments relatively well while all groups underperform their benchmark.</p></details>
<h2>Reproducible evidence</h2><p><a href="inputs/protocol.json">Frozen experiment</a> · <a href="prefit-manifest.json">Prefit source/environment receipt</a> · <a href="summary.json">Summary</a> · <a href="metrics.csv">Every model/year metric</a> · <a href="quintiles.csv">Every quintile</a> · <a href="quintile-assignments.csv">Tie allocations</a> · <a href="predictions.jsonl">Saved scores</a> · <a href="fitted-states.json">Fitted states</a> · <a href="verification.json">Independent checks</a></p>
<p>Absolute report address: <code>{escape(str(RUN/'index.html'))}</code></p><p><a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p></main></body></html>'''
    immutable('index.html', report.encode())
    # Preserve the explanatory implementation separately from prefit model code.
    for filename in ['report_ranking_no_llm.py', 'verify_ranking_no_llm.py']:
        source = ROOT / 'scripts/ml_experiment' / filename
        target = RUN / 'code/scripts/ml_experiment' / filename
        if target.exists():
            assert target.read_bytes() == source.read_bytes()
        else:
            target.write_bytes(source.read_bytes())
    marker = '<!-- ranking-no-llm-v1-current -->'
    home = ROOT / 'START-HERE.html'
    content = home.read_text()
    if marker not in content:
        section = marker+'''<section><h2>Current: ranking analysis without LLM extraction — October 26</h2><p>The fixed comparison uses existing structured inputs and 12-/24-month outcomes. Rank-target ridge gives a more encouraging one-year pattern; two-year evidence remains mixed. Bloomberg fundamentals and LLM labels are excluded.</p><a class="button" href="research/runs/ranking-no-llm/20261026-v1/index.html">Ranking results without LLM</a><p>411 one-year and 302 two-year predictions; matched comparison on 297 events per horizon. Previously examined development evidence, not an established investment edge. Extraction results remain available below.</p></section>'''
        content = content.replace('</style></head><body><main>', '</style></head><body><main>\n'+section, 1)
        content = content.replace('<h2>Current: revised extraction tested — October 26</h2>', '<h2>Completed: revised extraction tested — October 26</h2>')
        assert marker in content
        home.write_text(content)
    checkpoints = ROOT / 'research/docs/ml-checkpoints.html'
    content = checkpoints.read_text()
    marker = '<!-- ranking-no-llm-v1-checkpoint -->'
    if marker not in content:
        content = re.sub(r'(<body><main><h1>13D machine learning learning checkpoints</h1>)<p>Updated.*?</p>', r'\1<p>Updated October 26, 2026 | Non-LLM chronological ranking comparison complete; 12-month development lead, mixed 24-month evidence</p>', content, count=1)
        content = content.replace('<section class="current">', '<section class="history">', 1)
        section = marker+'''<section class="current"><h2>Current checkpoint: predict ordering before adding text</h2><p>We compared return-target ridge, rank-target ridge and a shallow rank-target tree with constant and smaller-size references. Rank-target ridge improves all four observed one-year correlations; two-year results remain mixed. The report teaches rank targets, Spearman, tied quintiles, completed-outcome training and the limits of these few development years.</p><p><a href="../runs/ranking-no-llm/20261026-v1/index.html">Read the ranking results and worked lesson</a></p><p>411 one-year and 302 two-year predictions; no LLM or Bloomberg inputs. Financial timing/mapping still needs resolution before the financial-only versus combined study.</p></section>'''
        content = content.replace('<section class="history">', section+'\n<section class="history">', 1)
        checkpoints.write_text(content)
    plan = ROOT / 'research/docs/PROJECT-PLAN.md'
    content = plan.read_text()
    heading = '## Non-LLM ranking analysis completed — October 26, 2026'
    if heading not in content:
        section = f'''{heading}

Jeff requested proceeding with analysis before LLM extraction. The
[ranking report and learning checkpoint](../runs/ranking-no-llm/20261026-v1/index.html)
compare raw-return ridge, rank-target ridge and a shallow rank-target tree using
the existing ten structured inputs. Constant and smaller-size rules are fixed
references. Twenty-one fits produce 411 twelve-month and 302 twenty-four-month
later predictions; the matched horizon comparison contains 297 events per horizon.
The old 24-month ridge predictions reproduce exactly. Rank-target ridge improves
on raw-return ridge in all four observed twelve-month years (positive in three),
but twenty-four-month results remain mixed (positive in one of three years).
No hyperparameter search, LLM extraction, Bloomberg inputs or return recomputation
was performed. This is previously exposed chronological development evidence.
Resolve financial information timing/mapping before a matched financial-only
comparison; retain both ridge targets rather than selecting a winner from these
few years. Frozen experiment: ranking-no-llm-v1. Extraction pilots remain preserved.

'''
        content = content.replace('# Activist 13D Machine Learning Class Project Plan\n\n', '# Activist 13D Machine Learning Class Project Plan\n\n'+section, 1)
        assert heading in content
        plan.write_text(content)
    receipt = {'report_sha256': hashlib.sha256(report.encode()).hexdigest(),
               'rank_change_rows': len(changes), 'report': str(RUN/'index.html'),
               'verification': verification['status']}
    immutable('publication.json', (json.dumps(receipt, sort_keys=True, indent=2)+'\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
