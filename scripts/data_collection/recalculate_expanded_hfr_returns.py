"""Tier: 2. Recalculate existing event returns and expanded HFR group statistics.

Inputs: frozen development-v4 panel/schedules, all-HFR candidates and accession sets.
Outputs: new dated return ledger, 63/126/252-session summaries, provenance and HTML.
Formula: unchanged open-to-close gross event return; excess = stock minus SPY.
Require exact event-return parity and unchanged old cohort statistics. No Russell
membership inference, holdout exposure, new price downloads, portfolio or ML run.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/recalculate_expanded_hfr_returns.py
"""
import html
import json
import platform
from collections import Counter
from pathlib import Path

from run_phase1_development import ROOT, calculate, digest, encode, freeze

from activist13d.expanded_hfr_returns import DISJOINT, LABELS, summarize_groups, tag_event
from activist13d.phase1_baseline import summarize

BASE = ROOT / 'research/runs/phase1-baseline/20260924-development-v4'
HFR = ROOT / 'research/runs/hfr-all-managers/20260924-v1'
OUT = ROOT / 'research/runs/phase1-baseline/20260924-expanded-hfr-returns-v1'
PROTOCOL = ROOT / 'research/protocol/phase1-expanded-hfr-v1.md'


def checked(path, expected):
    if digest(path) != expected:
        raise ValueError(f'Input hash mismatch: {path.name}')
    return json.loads(path.read_text())


def percent(value, points=False):
    return '—' if value is None else f'{value * 100:+.2f}' + (' pp' if points else '%')


def table(summary, keys):
    rows = []
    for key in keys:
        s = summary[key]
        interval = s.get('issuer_bootstrap_95')
        cells = [LABELS[key], f'{s["calculated"]} / {s["scheduled"]}',
                 str(s.get('unique_issuers', 0)), percent(s.get('mean_stock')),
                 percent(s.get('mean_benchmark')), percent(s.get('mean_excess'), True),
                 percent(s.get('median_excess'), True),
                 ' to '.join(percent(v, True) for v in interval) if interval else '—']
        rows.append('<tr>' + ''.join(f'<td>{html.escape(c)}</td>' for c in cells) + '</tr>')
    return '<div class="scroll"><table><tr><th>Group</th><th>Calculated / scheduled events</th><th>Companies</th><th>Mean stock return</th><th>Mean SPY return</th><th>Mean excess</th><th>Median excess</th><th>95% issuer-resampling interval</th></tr>' + ''.join(rows) + '</table></div>'


def render(summaries, strategies, bridge):
    primary = summaries['126']
    expanded, added, focused = (primary[k] for k in ['expanded', 'new_other_hfr', 'focused'])
    body = f'''<nav><a href="../../../../START-HERE.html">Project home</a> · <a href="../../../protocol/phase1-expanded-hfr-v1.md">Calculation rules</a> · <a href="../../hfr-all-managers/20260924-v1/index.html">Expanded manager matching</a></nav>
<h1>Following a broader set of HFR managers: recalculated returns</h1>
<p>24 September 2026 · Development entries March 2018–December 2022 · Gross event returns versus SPY</p>
<section class="notice"><h2>What changed—and what the result means</h2>
<p>Across {expanded['calculated']} calculable six-month events linked to HFR or the seven supplemental groups, the average stock return was {percent(expanded.get('mean_stock'))}, versus {percent(expanded.get('mean_benchmark'))} for SPY over the same dates. The average excess return was <strong>{percent(expanded.get('mean_excess'), True)}</strong>.</p>
<p>The newly recognized other HFR group contributes {added['calculated']} calculable events, averaging {percent(added.get('mean_excess'), True)} versus SPY. The focused activist candidates still average {percent(focused.get('mean_excess'), True)} across {focused['calculated']} events: that group's membership and results are unchanged.</p>
<p><strong>This is the updated high-level SPY comparison, not the proposed Russell size-matched test.</strong> Historical Russell assignment remains unfinished. Positive gross excess returns here are a development pattern, not established alpha or funded portfolio performance.</p></section>
<section><h2>Six months: the primary comparison</h2>{table(primary, ['all', 'expanded', 'hfr_only', 'previous_broad'])}
<p>The expanded group includes the external supplement. HFR-only isolates matches from the supplied HFR database. These rows overlap; do not add them. SPY returns differ between groups because the events occur on different dates.</p>
<h2>Breakdown without double-counting</h2>{table(primary, list(DISJOINT))}
<p>These four groups partition the entire sample. “Other or unresolved” is not a verified non-hedge-fund or non-activist control group. HFR strategy offerings describe the manager, not the intent of each investment.</p></section>
<section><h2>How to read these numbers</h2><p>Excess return is the stock's return minus SPY's return over the same purchase and sale dates. “pp” means percentage points. The median is the middle event. The interval shows uncertainty when companies are resampled; it does not account for shared market shocks or manager dependence.</p>
<p>The initial all-filings study already contained the newly recognized HFR events. This run recalculates returns from the saved price panel and changes their group classification. Total events, individual returns and prior focused-group statistics must reproduce exactly. The change is not a fresh out-of-sample test.</p></section>
<section><h2>From the matching universe to the return sample</h2><p>The expanded historical universe contains {bridge['initial_filings']} initial filings, of which {bridge['basic_ready_initials']} pass the earlier basic data checks across all dates. For the fixed development analysis, {bridge['screen_surviving_initial_filings']} of those filings survive the original date, human-review protection and entry screens. After the shared event-scheduling rules, there are {expanded['scheduled']} scheduled six-month events and {expanded['calculated']} calculable outcomes.</p>
<p>Filings and events are different units: simultaneous disclosures can merge into one event, while overlapping issuer entries are suppressed. Earlier years, later years and protected review companies remain outside this development calculation. Missing outcomes are not filled with zero.</p>
<p>Six-month expanded-group outcome statuses: {html.escape(json.dumps(expanded['statuses'], sort_keys=True))}. Fund-of-funds-only matches account for {primary['fund_of_funds_only']['calculated']} calculable events within the expanded sample and remain separately flagged.</p></section>
<section><h2>Three- and twelve-month supporting comparisons</h2><h3>63 trading sessions — approximately three months</h3>{table(summaries['63'], ['expanded', *DISJOINT])}<h3>252 trading sessions — approximately twelve months</h3>{table(summaries['252'], ['expanded', *DISJOINT])}
<p>These horizons were selected before the initial comparison. Their event counts differ because overlapping-entry exclusions and follow-up requirements depend on the holding period. Six months remains primary even if a supporting horizon looks better.</p></section>
<section><h2>Limits and the next decision</h2><p>Names and historical HFR availability remain unverified candidates. The seven supplemental manager groups were selected retrospectively. Fund-of-funds and diversified managers remain visible. The company/security screen does not fully resolve operating-company eligibility or related-party disclosures.</p>
<p>These are equally weighted gross event averages, not a portfolio with capital, position limits, cash drag and trading costs. The shared schedule is not a separate executable portfolio for each manager group. Usable delisting returns are included once and subsequent proceeds earn zero in this diagnostic.</p>
<p>The next benchmark comparison should assign a historically appropriate Russell size segment, retaining SPY as the high-level reference and comparing both benchmarks on the same matched events. Later evaluation outcomes remain untouched. Industry controls and portfolio accounting are still needed before judging a repeatable investment edge.</p></section>
<section><details><summary>Strategy views and supporting evidence</summary><p>Strategy views overlap because one manager can offer several strategies; they are secondary descriptive comparisons.</p>'''
    strategy_rows = []
    for strategy, s in strategies['126'].items():
        strategy_rows.append('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in [strategy,
            f'{s["calculated"]}/{s["scheduled"]}', percent(s.get('mean_stock')), percent(s.get('mean_excess'), True)]) + '</tr>')
    body += '<div class="scroll"><table><tr><th>Manager offers strategy</th><th>Calculated/scheduled</th><th>Mean stock return</th><th>Mean excess versus SPY</th></tr>' + ''.join(strategy_rows) + '</table></div>'
    body += '''<p><a href="summary.json">Exact group statistics</a> · <a href="strategy-summary.json">Overlapping strategy statistics</a> · <a href="outcomes.json">Event ledger</a> · <a href="bridge.json">Sample counts and exclusions</a> · <a href="verification.json">Parity and protection checks</a> · <a href="provenance.json">Source and output hashes</a> · <a href="../20260924-development-v4/index.html">Preserved earlier result</a></p>
<p>Entry: second exchange session after public acceptance date, at the open. Exit: scheduled closing trade. Return: entry-day close/open multiplied by subsequent total-return multipliers, minus one. The original return engine and source panel are unchanged. No new market-data download, paid model API, NLP labeling or ML fitting occurred.</p></details></section>'''
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expanded HFR return comparison</title><style>body{margin:0;background:#f4f6f8;color:#23394b;font:17px/1.65 system-ui,sans-serif}main{max-width:1250px;margin:32px auto;padding:0 24px}section{background:white;border:1px solid #dce3e8;padding:26px;margin:24px 0;border-radius:8px}h1{line-height:1.25}h2{font-size:23px}a{color:#155d94}.notice{border-left:5px solid #b6852c}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e8}th{background:#edf3f7}summary{cursor:pointer;font-weight:600}nav{display:flex;gap:15px;flex-wrap:wrap}@media print{body{background:white}section{border:0;padding:0}}</style></head><body><main>''' + body + '</main></body></html>'


def main():
    freeze(OUT / 'protocol.md', PROTOCOL.read_bytes())
    provenance = json.loads((BASE / 'provenance.json').read_text())['files']
    hfr_provenance = json.loads((HFR / 'provenance.json').read_text())
    selection = checked(BASE / 'selection.json', provenance['selection.json'])
    protection = checked(BASE / 'human-review-protection.json', provenance['human-review-protection.json'])
    unions = {k: set(v) for k, v in checked(HFR / 'accession-unions.json', hfr_provenance['accession-unions.json']).items()}
    candidates = checked(HFR / 'candidates.json', hfr_provenance['candidates.json'])
    hfr_summary = checked(HFR / 'summary.json', hfr_provenance['summary.json'])
    if digest(ROOT / 'src/activist13d/phase1_baseline.py') != provenance['code/phase1_baseline.py']:
        raise ValueError('Original return estimator changed')
    for path in [Path(__file__), ROOT / 'src/activist13d/expanded_hfr_returns.py',
                 ROOT / 'src/activist13d/phase1_baseline.py', ROOT / 'tests/test_expanded_hfr_returns.py',
                 ROOT / 'scripts/data_collection/run_phase1_development.py']:
        freeze(OUT / 'code' / path.name, path.read_bytes())
    saved = checked(BASE / 'daily-panel.json', provenance['daily-panel.json'])
    panel = {int(k): v for k, v in saved['panel'].items()}
    recalculated, old_summaries = calculate(selection['plans'], panel)
    original = checked(BASE / 'outcomes.json', provenance['outcomes.json'])
    assert recalculated == original, 'Individual returns or statuses changed'
    assert old_summaries == checked(BASE / 'summary.json', provenance['summary.json'])
    strategies_by_accession = {r['accession']: {s for h in r['matches'] for s in h['strategies']} for r in candidates}
    strategy_names = sorted({s for values in strategies_by_accession.values() for s in values})
    outcomes, summaries, strategies = {}, {}, {}
    protected = set(protection['issuers'])
    for horizon, records in recalculated.items():
        tagged = [tag_event(r, unions) for r in records]
        for row in tagged:
            assert row['issuer'] not in protected and '2018-03-19' <= row['entry'] <= '2022-12-30'
            assert row['exit'] <= '2023-12-29'
            row['hfr_strategy_offerings'] = sorted(set().union(*(strategies_by_accession.get(a, set()) for a in row['accessions'])))
        outcomes[horizon] = tagged
        s = summarize_groups(tagged)
        assert s['all'] == old_summaries[horizon]['all']
        assert s['previous_broad'] == old_summaries[horizon]['broad']
        assert s['focused'] == old_summaries[horizon]['focused']
        for field in ['scheduled', 'calculated']:
            assert sum(s[k][field] for k in DISJOINT) == s['all'][field]
            assert sum(s[k][field] for k in DISJOINT[:3]) == s['expanded'][field]
        summaries[horizon] = s
        strategies[horizon] = {key: summarize([r for r in tagged if key in r['hfr_strategy_offerings']]) for key in strategy_names}
    overlay_path = ROOT / 'research/runs/hfr-all-managers/20260924-verification-v1/initial-filings-overlay.json'
    overlay = json.loads(overlay_path.read_text())
    expanded_initials = {r['accession'] for r in overlay}
    assert len(expanded_initials) == hfr_summary['cohorts']['all_hfr_plus_supplement']['initials']
    excluded = [r for r in selection['entry_exclusions'] if r['accession'] in expanded_initials]
    bridge = dict(initial_filings=len(expanded_initials), basic_ready_initials=sum(r['basic_data_ready'] for r in overlay),
        screen_surviving_initial_filings=len(expanded_initials - {r['accession'] for r in excluded}),
        entry_exclusion_reasons=dict(Counter(r['reason'] for r in excluded)),
        scheduled_events_by_horizon={h: s['expanded']['scheduled'] for h, s in summaries.items()},
        protected_issuer_count=protection['protected_issuer_count'])
    assert bridge['initial_filings'] == 688 and bridge['basic_ready_initials'] == 389
    freeze(OUT / 'outcomes.json', encode(outcomes))
    freeze(OUT / 'summary.json', encode(summaries))
    freeze(OUT / 'strategy-summary.json', encode(strategies))
    freeze(OUT / 'bridge.json', encode(bridge))
    freeze(OUT / 'verification.json', encode(dict(individual_returns_recomputed_and_identical=True,
        all_event_and_old_group_statistics_identical=True, focused_group_unchanged=True,
        disjoint_group_counts_reconciled=True, protected_issuers_excluded=True,
        no_2024_or_later_outcomes=True, benchmark='SPY', russell_adjusted=False)))
    freeze(OUT / 'index.html', render(summaries, strategies, bridge))
    freeze(OUT / 'provenance.json', encode(dict(protocol_sha256=digest(PROTOCOL), python=platform.python_version(),
        inputs={str(path.relative_to(ROOT)): digest(path) for path in [BASE / 'provenance.json', BASE / 'daily-panel.json',
            BASE / 'selection.json', BASE / 'outcomes.json', BASE / 'summary.json', BASE / 'human-review-protection.json',
            HFR / 'provenance.json', HFR / 'accession-unions.json', HFR / 'candidates.json', overlay_path]},
        outputs={str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*'))
                 if p.is_file() and p.name != 'provenance.json'})))
    print(encode(summaries['126']))
    print(f'Wrote {OUT / "index.html"}')


if __name__ == '__main__':
    main()
