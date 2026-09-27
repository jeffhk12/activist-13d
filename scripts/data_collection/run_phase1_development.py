"""Tier: 2. Run the frozen Phase 1 gross event-return development diagnostic.

Inputs: feasibility-v2 registry/calendar; frozen CRSP CIZ pages; human review paths.
Outputs: dated selections/refusals, daily panel, gross results, provenance and HTML.
Formula: see activist13d.phase1_baseline and phase1-development-v1.md. No ML,
capital allocation, cost estimates or final holdout outcome evaluation.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_phase1_development.py
"""
import gzip
import hashlib
import html
import json
import platform
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from activist13d.phase1_baseline import event_return, number, schedule, summarize

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'research/runs/phase1-baseline/20260924-feasibility-v2'
OUT = ROOT / 'research/runs/phase1-baseline/20260924-development-v4'
RAW = ROOT / 'data/raw/wrds/bulk-v1'
PROTOCOL = ROOT / 'research/protocol/phase1-development-v1.md'
FIELDS = ['dlyopen', 'dlyclose', 'dlyvol', 'conditionaltype', 'tradingstatusflg',
          'dlydelflg', 'dlyret', 'dlyprevdt', 'dlyretmissflg', 'dlyretdurflg']


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n'


def freeze(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode() if isinstance(content, str) else content
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Refusing changed frozen output: {path}')
    else:
        path.write_bytes(data)


def read_page(path, inventory):
    meta_path = path.with_suffix('.meta.json')
    meta = json.loads(meta_path.read_text())
    raw = gzip.decompress(path.read_bytes())
    if hashlib.sha256(raw).hexdigest() != meta['sha256'] or len(raw) != meta['raw_bytes']:
        raise ValueError(f'Raw integrity failure: {path}')
    if not meta['request']['url'].rstrip('/').endswith('/' + path.parent.name):
        raise ValueError('Source table mismatch')
    inventory[str(path.relative_to(ROOT))] = dict(sha256=meta['sha256'],
        sidecar_sha256=digest(meta_path), request=meta['request'], retrieved_at=meta.get('retrieved_at'))
    return json.loads(raw), meta


def select_events(records, protected):
    selected, excluded = [], []
    for r in records:
        issuers = sorted({s['cik'] for s in r.get('subjects', []) if s.get('cik')})
        entry = r.get('entry_date_audit_proxy')
        reason = None
        if not entry or not '2018-03-19' <= entry <= '2022-12-30':
            reason = 'outside_development_entry_dates'
        elif set(issuers) & protected:
            reason = 'protected_human_review_issuer'
        elif (r['source_status'] != 'hash_and_size_verified'
              or r['security_screen'] != 'corporate_common_candidate'
              or r['entry_price_status'] != 'positive_open_observed'
              or r['amendment_flag_conflict'] or r['publication_date_disagrees']
              or r['cusip_check_digit_valid'] is False or not r['candidate_group_key']
              or r['issuer_also_filing_party'] or len(issuers) != 1):
            reason = 'fails_prior_basic_readiness'
        else:
            price = r.get('entry_price_evidence', {}).get('row', {})
            volume = number(price.get('dlyvol'))
            if (price.get('conditionaltype') != 'RW' or price.get('tradingstatusflg') != 'A'
                    or volume is None or volume <= 0):
                reason = 'entry_trading_conditions'
        if reason:
            excluded.append({'accession': r['accession'], 'reason': reason})
        else:
            selected.append(dict(accession=r['accession'], entry=entry,
                issuer=issuers[0], permno=r['security_link']['permno'],
                broad=r['broad_manager_subset'], focused=r['focused_activist_subset']))
    return selected, excluded


def verify_benchmark(inventory):
    matches = []
    for path in sorted((RAW / 'crsp.stocknames_v2').glob('*.json.gz')):
        payload, meta = read_page(path, inventory)
        if meta['request']['method'] != 'GET':
            continue
        for row in payload.get('results', []):
            if (row.get('permno') == 84398 and row.get('cusip') == '78462F10'
                    and row.get('ticker') == 'SPY' and row.get('securitysubtype') == 'ETF'
                    and row['namedt'] <= '2018-03-19' and row['nameenddt'] >= '2023-12-29'):
                matches.append(dict(source=str(path.relative_to(ROOT)), row=row))
    if not matches:
        raise ValueError('Historical SPY benchmark identity not verified')
    return matches


def build_panel(plans, inventory):
    wanted = defaultdict(set)
    for events in plans.values():
        for event in events:
            for day in event['days']:
                if day > '2023-12-29':
                    raise ValueError('Protected period cannot be evaluated')
                wanted[day].update([event['permno'], 84398])
    pages = {}
    daily_meta = list((RAW / 'crsp.dsf_v2').glob('*.meta.json'))
    daily_meta += list((ROOT / 'data/raw/wrds/phase1-gap-20260924/crsp.dsf_v2').glob('*.meta.json'))
    for meta_path in sorted(daily_meta):
        meta = json.loads(meta_path.read_text())
        params = meta['request'].get('params', {})
        day = params.get('dlycaldt')
        if (day in wanted and meta['request']['method'] == 'GET'
                and params == {'dlycaldt': day, 'limit': 50000, 'offset': 0}):
            if day in pages:
                raise ValueError('Duplicate full daily source')
            pages[day] = meta_path.with_name(meta_path.name.replace('.meta.json', '.gz'))
    panel = defaultdict(dict)
    missing_pages = []
    for i, (day, securities) in enumerate(sorted(wanted.items())):
        if day not in pages:
            missing_pages.append(day)
            continue
        payload, meta = read_page(pages[day], inventory)
        rows = payload.get('results', [])
        if len(rows) >= 50000 or payload.get('next'):
            raise ValueError('Possibly truncated full daily source')
        seen = set()
        for row in rows:
            if row['dlycaldt'] != day or row['permno'] in seen:
                raise ValueError('Invalid date or repeated daily key')
            seen.add(row['permno'])
            if row['permno'] in securities:
                panel[row['permno']][day] = {k: row.get(k) for k in FIELDS}
        if i % 100 == 0:
            print(f'Checked holding-period data: {i + 1}/{len(wanted)} dates', flush=True)
    return panel, missing_pages


def calculate(plans, panel):
    outcomes, summaries = {}, {}
    for horizon, events in plans.items():
        results = []
        for event in events:
            value, status = event_return(event['days'], panel.get(event['permno'], {}))
            benchmark, benchmark_status = event_return(event['days'], panel.get(84398, {}))
            if value is None:
                combined = 'stock:' + status
            elif benchmark is None:
                combined = 'benchmark:' + benchmark_status
            else:
                combined = status
            result = {k: v for k, v in event.items() if k != 'days'}
            result.update(stock_return=value, benchmark_return=benchmark,
                          excess=value - benchmark if value is not None and benchmark is not None else None,
                          status=combined, stock_status=status, benchmark_status=benchmark_status)
            results.append(result)
        outcomes[horizon] = results
        groups = {'all': results, 'broad': [r for r in results if r['broad']],
                  'focused': [r for r in results if r['focused']],
                  'other': [r for r in results if not r['broad']]}
        summaries[horizon] = {key: summarize(group) for key, group in groups.items()}
    return outcomes, summaries


def pct(value):
    return '—' if value is None else f'{100 * value:.2f}%'


def report(summary, exclusions, missing, protection):
    rows = []
    names = {'all': 'All screened initial disclosures', 'broad': 'Broad manager candidates',
             'focused': 'Focused activist candidates (inside broad)', 'other': 'Other or unresolved managers'}
    for horizon in ['126', '63', '252']:
        for group, stats in summary[horizon].items():
            interval = stats.get('issuer_bootstrap_95')
            interval_text = '—' if interval is None else ' to '.join(pct(v) for v in interval)
            cells = [str(int(horizon)), names[group], f'{stats["calculated"]} / {stats["scheduled"]}',
                     pct(stats.get('mean_stock')), pct(stats.get('mean_benchmark')),
                     pct(stats.get('mean_excess')), pct(stats.get('median_excess')), interval_text]
            rows.append('<tr>' + ''.join('<td>' + html.escape(c) + '</td>' for c in cells) + '</tr>')
    primary = summary['126']['all']
    findings = (f'Among {primary["calculated"]} calculable six-month events, the average stock return was '
                f'{pct(primary.get("mean_stock"))}, compared with {pct(primary.get("mean_benchmark"))} '
                f'for SPY over the same event dates. The average difference was '
                f'{pct(primary.get("mean_excess"))} (percentage-point difference).')
    refusal_rows = ''.join(f'<li>{html.escape(k)}: {v}</li>' for k, v in primary['statuses'].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 1 — first development return calculation</title><style>
body{{font:17px/1.65 system-ui;color:#25384a;background:#f4f6f8;margin:0}}main{{max-width:1200px;margin:35px auto;padding:0 24px}}section{{background:white;padding:25px;margin:22px 0;border:1px solid #dce3e8;border-radius:8px}}h1{{line-height:1.25}}h2{{font-size:23px}}a{{color:#155e94}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:12px;border-bottom:1px solid #dce3e8;text-align:left;vertical-align:top}}th{{background:#edf3f7}}li{{margin:9px 0}}.status{{border-left:5px solid #b5842d}}summary{{cursor:pointer;font-weight:bold}}</style></head><body><main>
<nav><a href="../../../../START-HERE.html">Project home</a> · <a href="../../../protocol/phase1-development-v1.md">Rules recorded before calculation</a></nav>
<h1>Does buying after an initial 13D improve returns?</h1><p>24 September 2026 · First development diagnostic · Gross event returns, not portfolio performance</p>
<section class="status"><h2>What this first calculation tells us</h2><p>{findings}</p>
<p><strong>This does not yet establish an investable edge.</strong> The sample uses provisional stock/manager classifications, excludes protected review companies, and omits events whose return histories cannot yet be calculated. Costs, portfolio cash and capital constraints are not included. The first result is a development comparison to investigate, not a final strategy finding.</p></section>
<section><h2>What we tested</h2><p>Purchase at the second trading-session open after the disclosure date, allowing a full intervening session. Hold for 126 sessions (about six months). Compare the stock with buying SPY at the same opening and holding to the same exit. Three and twelve months—63 and 252 sessions—were declared as supporting comparisons before viewing results.</p>
<p>Entries run from 19 March 2018 through 30 December 2022, with follow-up limited to 2023. The 2024-and-later years were not evaluated in this run. Earlier price-preview examples still need exclusion from a globally clean final holdout. Same-issuer overlapping entries are suppressed before outcomes are examined; simultaneous disclosures of the same security are combined.</p>
<p>These are equally weighted event averages. They answer what happened after the sampled disclosures. They do not show the return on a funded portfolio, since events start on different dates and capital may be idle or committed elsewhere.</p></section>
<section><h2>Results and their meaning</h2><div class="scroll"><table><tr><th>Sessions held</th><th>Group</th><th>Calculated / scheduled events</th><th>Mean stock return</th><th>Mean SPY return</th><th>Mean difference</th><th>Median difference</th><th>95% issuer-resampling range for mean difference</th></tr>{''.join(rows)}</table></div>
<p>A positive difference means the stock beat SPY over the same period; a negative difference means SPY did better. Differences and interval endpoints are percentage points. The median describes the middle event and helps show whether a few large winners drive the average. The range measures uncertainty when companies are resampled, but does not account for shared market shocks or manager dependence.</p>
<p>The focused activist group is contained in the broad group. “Other” includes managers we have not identified; it is not a verified non-activist control group. SPY is a large-cap benchmark and does not remove size, sector or other risk differences. Smaller groups provide hypotheses rather than firm conclusions.</p></section>
<section><h2>What still limits the answer</h2><p>{protection['protected_issuer_count']} issuer identities associated with human review material were protected from this calculation. They were excluded before return inspection. There are {len(missing)} missing daily source dates within requested holding windows; other missing or invalid observations are also refused rather than filled with zero.</p>
<p>Missing histories can change the answer systematically—for example, if disappearing stocks are more difficult to calculate. Available one-session delisting returns are included once, with proceeds held at zero return afterward; unresolved terminal values remain exclusions. The vendor's overall daily coverage is not independently certified.</p>
<p>The supplemental manager list was selected retrospectively and HFR historical availability is still based on unverified delivery dates. The classifications are useful research candidates, not proof that the same list could have been traded historically.</p></section>
<section><h2>Next work</h2><ol><li>Resolve incomplete histories and verify company and manager eligibility, then test whether those corrections change the conclusion.</li><li>Compare like-for-like stocks and periods, and check whether a few managers, companies or market periods dominate the result.</li><li>Build the funded portfolio with position limits, cash returns and trading costs at the two proposed capital levels. Keep later evaluation data reserved while these choices are developed.</li></ol></section>
<section><details><summary>Evidence, exclusions and calculation details</summary><p>Six-month outcome statuses:</p><ul>{refusal_rows}</ul><p>Entry-screen exclusions: {html.escape(json.dumps(exclusions, sort_keys=True))}.</p>
<p><a href="summary.json">Exact statistics</a> · <a href="outcomes.json">Event ledger and refusal reasons</a> · <a href="selection.json">Selections fixed before return calculation</a> · <a href="source-inventory.json">Hashed vendor sources</a> · <a href="provenance.json">Inputs, code and output hashes</a> · <a href="HANDOFF.md">Research handoff</a></p>
<p>Gross wealth = entry-day close/open × subsequent daily total-return multipliers. Entry-day close-to-close return is not used, because part of it occurred before purchase. SPY is calculated identically. Missing outcomes have no zero-return substitution. The source panel is saved separately for offline replay. No paid models, NLP labels or ML fitting were used.</p></details></section></main></body></html>'''


def main():
    # Freeze choices and code before opening any holding-period return pages.
    freeze(OUT / 'protocol.md', PROTOCOL.read_bytes())
    for path in [Path(__file__), ROOT / 'src/activist13d/phase1_baseline.py',
                 ROOT / 'tests/test_phase1_baseline.py']:
        freeze(OUT / 'code' / path.name, path.read_bytes())
    registry_path = INPUT / 'event-candidates.jsonl'
    prior = json.loads((INPUT / 'provenance.json').read_text())
    if digest(registry_path) != prior['event_candidates_sha256']:
        raise ValueError('Feasibility registry integrity failure')
    records = [json.loads(line) for line in registry_path.read_text().splitlines()]
    protected_paths = []
    accessions = set()
    for folder in [ROOT / 'review/current', ROOT / 'review/drafts']:
        for path in sorted(folder.rglob('*')):
            found = re.findall(r'\d{10}-\d{2}-\d{6}', path.name)
            if found:
                protected_paths.append(str(path.relative_to(ROOT)))
                accessions.update(found)
    # Review packets include amendments: resolve their issuers from all archived
    # metadata, not only the initial-filing registry being evaluated.
    database = ROOT / 'research/runs/phase1-overnight/full-20260915/sec.sqlite'
    protected, resolved = set(), set()
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as db:
        for raw, in db.execute('SELECT record_json FROM records'):
            record = json.loads(raw)
            if record['accession'] in accessions:
                issuers = {s['cik'] for s in record.get('subjects', []) if s.get('cik')}
                if issuers:
                    protected.update(issuers)
                    resolved.add(record['accession'])
    if accessions - resolved:
        raise ValueError(f'Unresolved human-review issuer identities: {sorted(accessions - resolved)}')
    protection = dict(accessions=sorted(accessions), issuers=sorted(protected),
                      protected_issuer_count=len(protected), source_paths=protected_paths)
    freeze(OUT / 'human-review-protection.json', encode(protection))
    events, excluded = select_events(records, protected)
    sessions = [d for d in json.loads((INPUT / 'entry-calendar.json').read_text())
                if d <= '2023-12-29']
    plans, overlap = {}, {}
    for horizon in [126, 63, 252]:
        plans[str(horizon)], overlap[str(horizon)] = schedule(events, sessions, horizon)
    selection = dict(plans=plans, overlap_exclusions=overlap, entry_exclusions=excluded)
    freeze(OUT / 'selection.json', encode(selection))
    inventory = {}
    benchmark = verify_benchmark(inventory)
    panel_path = OUT / 'daily-panel.json'
    if panel_path.exists():
        receipt = json.loads((OUT / 'panel-receipt.json').read_text())
        if digest(panel_path) != receipt['sha256']:
            raise ValueError('Panel replay integrity failure')
        saved = json.loads(panel_path.read_text())
        panel = {int(k): v for k, v in saved['panel'].items()}
        missing = saved['missing_daily_pages']
        inventory = json.loads((OUT / 'source-inventory.json').read_text())
    else:
        panel, missing = build_panel(plans, inventory)
        freeze(panel_path, encode(dict(panel=panel, missing_daily_pages=missing)))
        freeze(OUT / 'source-inventory.json', encode(inventory))
        freeze(OUT / 'panel-receipt.json', encode(dict(sha256=digest(panel_path))))
    outcomes, summary = calculate(plans, panel)
    freeze(OUT / 'outcomes.json', encode(outcomes))
    freeze(OUT / 'summary.json', encode(summary))
    exclusions = dict(Counter(e['reason'] for e in excluded))
    freeze(OUT / 'coverage.json', encode(dict(entry_exclusions=exclusions,
        screened_events=len(events), missing_daily_pages=missing, benchmark_evidence=benchmark,
        overlap_exclusion_counts={k: len(v) for k, v in overlap.items()})))
    freeze(OUT / 'index.html', report(summary, exclusions, missing, protection))
    freeze(OUT / 'HANDOFF.md', '''# First development event-return calculation

Read [the plain-English report](index.html) first. This is a gross event diagnostic,
not the final baseline portfolio or a demonstrated investment edge. The primary
horizon is six months; three and twelve months are supporting comparisons.

Selection and protocol were saved before holding-period returns were loaded.
Use summary.json for calculated/scheduled denominators; outcomes.json retains
refusals and same-window benchmark results. Human-review issuer exclusions are
recorded separately. No outcome is written to human-labeling packets.

The return engine handles a usable one-session delisting return exactly once;
unresolved terminal values and missing observations are refused. CIZ total returns
are not combined with legacy delisting returns. Post-delisting proceeds earn zero
in this diagnostic. Real portfolio cash/cost/capacity accounting remains open.

Re-run scripts/data_collection/run_phase1_development.py with PYTHONPATH=src and
the project interpreter. Saved panel replay verifies its hash, reproduces output
bytes and refuses changed evidence. First extraction verifies raw page hashes;
panel replay does not re-read every original vendor page. Source inventory retains
requests, pull dates and checksums. Final eligibility/identity, daily coverage and
selection bias remain unresolved gates. Preserve this run and protocol unchanged.
''')
    provenance = dict(protocol_sha256=digest(PROTOCOL), registry_sha256=digest(registry_path),
        protected_identity_database_sha256=digest(database),
        calendar_sha256=digest(INPUT / 'entry-calendar.json'), python=platform.python_version(),
        files={str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*'))
               if p.is_file() and p.name != 'provenance.json'})
    freeze(OUT / 'provenance.json', encode(provenance))
    print(encode(summary['126']), flush=True)
    print(f'Wrote {OUT / "index.html"}', flush=True)


if __name__ == '__main__':
    main()
