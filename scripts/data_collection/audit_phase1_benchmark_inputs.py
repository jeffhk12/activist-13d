"""Tier: 1. Audit pre-disclosure size/industry inputs for relative benchmarks.

Inputs: frozen development-v4 selections; feasibility registry/calendar; CRSP pages.
Outputs: dated characteristics and group coverage, source hashes, HTML report.
Identity: matching date is last exchange session strictly before the earliest
merged disclosure's acceptance date; cap dollars = CRSP dlycap * 1000. Size bins
are descriptive dollar bands, not historical Russell or S&P index membership.
No peer returns or new strategy outcomes are calculated.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/audit_phase1_benchmark_inputs.py
"""
import bisect
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

from run_phase1_development import INPUT, RAW, ROOT, digest, encode, freeze, read_page

from activist13d.phase1_baseline import number

BASE = ROOT / 'research/runs/phase1-baseline/20260924-development-v4'
OUT = ROOT / 'research/runs/phase1-baseline/20260924-benchmark-inputs-v1'


def size_band(cap_thousands):
    value = number(cap_thousands)
    if value is None or value <= 0:
        return 'unavailable'
    if value < 2_000_000:
        return 'below_$2bn'
    if value < 10_000_000:
        return '$2bn_to_$10bn'
    return '$10bn_or_more'


def industry(value):
    try:
        value = int(str(value))
    except (TypeError, ValueError):
        return None
    return str(value).zfill(4)[:2] if 100 <= value < 10000 and value != 9999 else None


def previous_session(public_day, sessions):
    index = bisect.bisect_left(sessions, public_day)
    return sessions[index - 1] if index else None


def main():
    # Hand-pinned units/boundaries and date convention, plus refusal paths.
    assert size_band(1_000_000) == 'below_$2bn'  # $1m in thousands = $1bn.
    assert size_band(2_000_000) == '$2bn_to_$10bn'
    assert size_band(10_000_000) == '$10bn_or_more'
    assert size_band(None) == size_band(-1) == 'unavailable'
    assert industry(3571) == '35' and industry('0100') == '01' and industry(9999) is None
    assert previous_session('2020-01-06', ['2020-01-02', '2020-01-03', '2020-01-06']) == '2020-01-03'
    sessions = json.loads((INPUT / 'entry-calendar.json').read_text())
    baseline_provenance = json.loads((BASE / 'provenance.json').read_text())
    assert digest(INPUT / 'event-candidates.jsonl') == baseline_provenance['registry_sha256']
    assert digest(INPUT / 'entry-calendar.json') == baseline_provenance['calendar_sha256']
    registry = {r['accession']: r for line in (INPUT / 'event-candidates.jsonl').read_text().splitlines()
                if (r := json.loads(line))}
    events = json.loads((BASE / 'selection.json').read_text())['plans']['126']
    expected = json.loads((BASE / 'provenance.json').read_text())['files']['selection.json']
    assert digest(BASE / 'selection.json') == expected
    requests = defaultdict(list)
    for event in events:
        public_day = min(registry[a]['acceptance_datetime_et'][:10] for a in event['accessions'])
        day = previous_session(public_day, sessions)
        assert day < public_day and day < '2023-01-01'
        requests[day].append(event)
    pages = {}
    for path in sorted((RAW / 'crsp.dsf_v2').glob('*.meta.json')):
        meta = json.loads(path.read_text())
        params = meta['request'].get('params', {})
        day = params.get('dlycaldt')
        if day in requests and meta['request']['method'] == 'GET' and params == {'dlycaldt': day, 'limit': 50000, 'offset': 0}:
            assert day not in pages
            pages[day] = path.with_name(path.name.replace('.meta.json', '.gz'))
    inventory, observations = {}, []
    for i, (day, group) in enumerate(sorted(requests.items())):
        rows = {}
        if day in pages:
            payload, _ = read_page(pages[day], inventory)
            raw_rows = payload.get('results', [])
            assert len(raw_rows) < 50000 and not payload.get('next')
            assert all(r['dlycaldt'] == day for r in raw_rows)
            assert len(raw_rows) == len({r['permno'] for r in raw_rows})
            rows = {r['permno']: r for r in raw_rows}
        for event in group:
            raw = rows.get(event['permno'], {})
            observations.append(dict(accession=event['accession'], issuer=event['issuer'],
                permno=event['permno'], entry=event['entry'], characteristics_date=day,
                broad=event['broad'], focused=event['focused'],
                size_band=size_band(raw.get('dlycap')), industry_2digit=industry(raw.get('siccd')),
                source=str(pages[day].relative_to(ROOT)) if day in pages else None,
                fields={k: raw.get(k) for k in ['dlycap', 'siccd', 'permco', 'usincflg', 'primaryexch', 'ticker']},
                status='observed' if raw else 'missing_security_or_page'))
        if i % 100 == 0:
            print(f'Historical benchmark inputs: {i + 1}/{len(requests)} dates', flush=True)
    groups = {'all': observations, 'broad': [r for r in observations if r['broad']],
              'focused': [r for r in observations if r['focused']],
              'other': [r for r in observations if not r['broad']]}
    summary = {key: dict(scheduled_events=len(rows),
        size_bands=dict(sorted(Counter(r['size_band'] for r in rows).items())),
        with_size_and_industry=sum(r['size_band'] != 'unavailable' and r['industry_2digit'] is not None for r in rows),
        industry_groups=len({r['industry_2digit'] for r in rows if r['industry_2digit'] is not None}))
        for key, rows in groups.items()}
    assert summary['all']['scheduled_events'] == 2097
    assert summary['focused']['scheduled_events'] == 75
    for stats in summary.values():
        assert sum(stats['size_bands'].values()) == stats['scheduled_events']
    freeze(OUT / 'observations.json', encode(observations))
    freeze(OUT / 'summary.json', encode(summary))
    freeze(OUT / 'source-inventory.json', encode(inventory))
    freeze(OUT / 'provenance.json', encode(dict(selection_sha256=expected,
        registry_sha256=digest(INPUT / 'event-candidates.jsonl'), calendar_sha256=digest(INPUT / 'entry-calendar.json'),
        source_inventory_sha256=digest(OUT / 'source-inventory.json'), script_sha256=digest(Path(__file__)),
        new_return_comparisons_calculated=False)))
    table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(x))}</td>' for x in [key,
        s['scheduled_events'], s['size_bands'].get('below_$2bn', 0), s['size_bands'].get('$2bn_to_$10bn', 0),
        s['size_bands'].get('$10bn_or_more', 0), s['size_bands'].get('unavailable', 0), s['with_size_and_industry']]) + '</tr>'
        for key, s in summary.items())
    freeze(OUT / 'index.html', f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Choosing a fair benchmark for each stock</title><style>body{{font:17px/1.65 system-ui;color:#263a4c;background:#f5f7f9}}main{{max-width:1100px;margin:35px auto;padding:24px}}section{{background:white;padding:24px;margin:20px 0;border:1px solid #dae1e6}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse;width:100%}}.scroll{{overflow:auto}}a{{color:#165c92}}</style></head><body><main>
<nav><a href="../../../../START-HERE.html">Project home</a> · <a href="../../../docs/PHASE1-BENCHMARK-REVISION-20260924.md">Benchmark revision and interpretation</a></nav>
<h1>Did the investment beat comparable stocks?</h1><p>24 September 2026 · Benchmark input audit · New benchmark returns not yet calculated</p>
<section><h2>Why we are changing the comparison</h2><p>SPY remains a useful large-cap reference, but it does not tell us whether a smaller industrial or technology company beat comparable investments. Our primary comparison will use a stock-appropriate benchmark, with size and industry determined before disclosure. We will retain SPY as context.</p>
<p>The earlier focused activist-candidate sample averaged 3.98 percentage points above SPY over six months across 74 calculable events. That is observed outperformance against SPY, not yet evidence that the group beats its appropriate benchmark or delivers reliable alpha. Its issuer-resampling interval was -5.76 to +15.35 points.</p></section>
<section><h2>What historical data is available?</h2><p>These counts cover all 2,097 scheduled six-month events, before excluding events with incomplete outcomes. Characteristics come from the last trading day strictly before the earliest associated disclosure date. Focused is inside broad; neither is additive to all.</p>
<div class="scroll"><table><tr><th>Group</th><th>Scheduled events</th><th>Below $2bn</th><th>$2bn–$10bn</th><th>$10bn or more</th><th>Size missing</th><th>Size and industry available</th></tr>{table}</table></div>
<p>Size is the CRSP security's market capitalization, not necessarily the entire company's capitalization across share classes. These dollar bands describe the sample; they do not establish historical small/mid/large-cap index membership. Industry is a two-digit SIC grouping, not a verified GICS sector or a finished peer group. Present-day classifications are not substituted.</p></section>
<section><h2>How the revised result should be presented</h2><p>Show absolute stock return, return of its size/industry-appropriate benchmark, and the difference over identical holding dates. Compare old and new benchmarks on the same successfully matched events, so a change in sample composition is visible. Include match quality, exclusions and uncertainty.</p><p>A size-matched index is the first investable reference; an industry-and-size matched peer basket is the more specific research comparison. Exact assignment and peer rules must be recorded before computing the new comparison. SPY remains a secondary reference. The revision follows inspection of the first development result; later evaluation outcomes remain untouched.</p></section>
<section><h2>Evidence and next step</h2><p><a href="summary.json">Exact coverage counts</a> · <a href="observations.json">Historical characteristics and source links</a> · <a href="source-inventory.json">Verified source inventory</a> · <a href="../20260924-development-v4/index.html">Preserved SPY comparison</a></p><p>The next calculation needs a fixed benchmark-assignment rule and historical coverage checks, including treatment of multiple share classes and foreign companies. No new excess-return estimate or claim of alpha is produced by this audit.</p></section></main></body></html>''')
    print(encode(summary))


if __name__ == '__main__':
    main()
