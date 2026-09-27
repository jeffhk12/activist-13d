"""Tier: 2. Compare frozen 13D events with lagged-membership Russell ETF returns.
Inputs: saved assignments/panel, expanded-HFR event ledger and original schedules.
Outputs: new immutable common-sample outcomes, summaries, HTML and provenance.
Identity: excess=stock return-assigned ETF return on identical event dates.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_russell_returns.py
"""

import html
import json
import platform
from collections import Counter
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.expanded_hfr_returns import DISJOINT, LABELS
from activist13d.phase1_baseline import summarize
from activist13d.russell_benchmark import compare

INPUT = ROOT / "research/runs/phase1-baseline/20260924-russell-inputs-v1"
BASE = ROOT / "research/runs/phase1-baseline/20260924-development-v4"
EXPANDED = ROOT / "research/runs/phase1-baseline/20260924-expanded-hfr-returns-v1"
OUT = ROOT / "research/runs/phase1-baseline/20260924-russell-returns-v1"
PROTOCOL = ROOT / "research/protocol/phase1-russell-v1.md"


def groups(rows):
    return dict(
        all=rows,
        expanded=[r for r in rows if r["expanded_manager"]],
        hfr_only=[r for r in rows if r["hfr_only"]],
        **{k: [r for r in rows if r["disjoint_cohort"] == k] for k in DISJOINT},
    )


def stats(rows):
    common = [r for r in rows if r["excess"] is not None]
    excluded = [
        dict(
            r, benchmark_return=r["spy_return"], excess=r["spy_excess"], status=r["original_status"]
        )
        for r in rows
        if r["excess"] is None
    ]
    spy = [dict(r, benchmark_return=r["spy_return"], excess=r["spy_excess"]) for r in common]
    broad = [
        dict(
            r,
            benchmark_return=r["broad_russell_return"],
            excess=r["stock_return"] - r["broad_russell_return"],
        )
        for r in common
    ]
    return dict(
        russell=summarize(rows),
        spy_common=summarize(spy),
        iwv_common=summarize(broad),
        excluded_spy=summarize(excluded),
        assigned_etfs=dict(Counter(r["assigned_etf"] for r in common)),
    )


def pct(v, pp=False):
    return "—" if v is None else f"{v * 100:+.2f}" + (" pp" if pp else "%")


def table(summaries):
    rows = []
    for key, value in summaries.items():
        s = value["russell"]
        spy = value["spy_common"]
        ci = s.get("issuer_bootstrap_95")
        cells = [
            LABELS[key],
            f"{s['calculated']} / {s['scheduled']}",
            pct(s.get("mean_stock")),
            pct(s.get("mean_benchmark")),
            pct(s.get("mean_excess"), True),
            pct(spy.get("mean_benchmark")),
            pct(spy.get("mean_excess"), True),
            " to ".join(pct(x, True) for x in ci) if ci else "—",
        ]
        rows.append("<tr>" + "".join("<td>" + html.escape(c) + "</td>" for c in cells) + "</tr>")
    return (
        '<div class="scroll"><table><tr><th>Group</th><th>Common / scheduled events</th><th>Stock</th><th>Assigned Russell ETF</th><th>Stock minus Russell ETF</th><th>SPY, same sample</th><th>Stock minus SPY</th><th>95% company-resampling interval, Russell excess</th></tr>'
        + "".join(rows)
        + "</table></div>"
    )


def report(summary, old, receipt):
    main = summary["126"]
    f = main["focused"]
    a = main["expanded"]
    body = f"""<nav><a href="../../../../START-HERE.html">Project home</a> · <a href="../../../protocol/phase1-russell-v1.md">Frozen calculation rules</a></nav>
<h1>Did the stock beat its Russell size benchmark?</h1>
<p>24 September 2026 · Development entries March 2018–December 2022 · Six months primary</p>
<section><h2>What we found</h2><p>Among {a["russell"]["calculated"]} matched events in the expanded HFR-plus-supplement group, the mean six-month stock-minus-Russell ETF return was <strong>{pct(a["russell"].get("mean_excess"), True)}</strong>. For {f["russell"]["calculated"]} focused activist-candidate events it was <strong>{pct(f["russell"].get("mean_excess"), True)}</strong>, compared with {pct(f["spy_common"].get("mean_excess"), True)} against SPY on those same events.</p>
<p>This is a <strong>historical monthly-membership comparison using Russell ETF proxies</strong>. It is not a dollar-cap approximation, exact index return, daily membership reconstruction or demonstrated investment edge. The sample differs from the original SPY-only study; exclusions are shown below.</p></section>
<section><h2>Six-month primary result</h2>{table(main)}<p>Stock and benchmarks use identical opening-entry and closing-exit dates. These are equally weighted gross event averages, not annualized portfolio returns. ETF fees and tracking differences are embedded; strategy transaction costs are not. Positive excess means the stock outperformed its assigned ETF. “pp” means percentage points.</p><p>All/expanded/HFR-only are overlapping totals. Focused, other Event-Driven, newly recognized HFR and other/unresolved are mutually exclusive. Other/unresolved is not a verified non-hedge-fund control group.</p></section>
<section><h2>How each benchmark was selected</h2><p>Use the last month-end snapshot before the disclosure month. Exact historical security identifiers connect each stock to FTSE Russell's recorded constituents. Midcap members use IWR; other Russell 1000 members use IWB; Russell 2000 members use IWM. The assignment remains fixed throughout the investment. IWV, the Russell 3000 ETF, is broad-market context and is never used as a microcap category.</p><p>Membership may have changed between the prior month end and disclosure. Historical vendor publication timestamps and revisions remain unverified. Missing or conflicting matches are excluded, including stocks for which this dataset cannot establish an appropriate US segment. We do not force an assignment from current membership or arbitrary cap cutoffs.</p></section>
<section><h2>Separate benchmark effects from sample changes</h2><div class="scroll"><table><tr><th>Group</th><th>Original SPY events / excess</th><th>Common events / SPY excess</th><th>Excluded events with stock/SPY returns / SPY excess</th><th>Common ETF composition</th></tr>"""
    for key, s in main.items():
        o = old["126"][key]
        c = s["spy_common"]
        e = s["excluded_spy"]
        cells = [
            LABELS[key],
            f"{o['calculated']} / {pct(o.get('mean_excess'), True)}",
            f"{c['calculated']} / {pct(c.get('mean_excess'), True)}",
            f"{e['calculated']} / {pct(e.get('mean_excess'), True)}",
            str(s["assigned_etfs"]),
        ]
        body += "<tr>" + "".join("<td>" + html.escape(x) + "</td>" for x in cells) + "</tr>"
    body += "</table></div><p>The original SPY estimate and common-sample SPY estimate can differ because different stocks are included. Only the two benchmark comparisons on the common sample isolate the benchmark change.</p><h3>Sequential reasons events leave the comparison</h3><ul>"
    for status, n in main["all"]["russell"]["statuses"].items():
        body += f"<li>{html.escape(status.replace('_', ' '))}: {n} events</li>"
    body += "</ul><p>Assignment is checked first, then original stock/SPY availability, then ETF availability. Each event has one final status. Failure does not mean the investment lost money. Detailed per-group reasons are in the statistics file.</p></section>"
    body += f"<section><h2>Three- and twelve-month supporting results</h2><h3>Three months / 63 sessions</h3>{table(summary['63'])}<h3>Twelve months / 252 sessions</h3>{table(summary['252'])}<p>Six months remains primary. Counts change with overlap exclusions and follow-up requirements. We do not choose the best-looking horizon after seeing returns.</p></section>"
    body += "<section><h2>Russell 3000 broad-market context, same six-month sample</h2><table><tr><th>Group</th><th>Mean IWV return</th><th>Stock minus IWV</th></tr>"
    for key, s in main.items():
        body += f"<tr><td>{html.escape(LABELS[key])}</td><td>{pct(s['iwv_common'].get('mean_benchmark'))}</td><td>{pct(s['iwv_common'].get('mean_excess'), True)}</td></tr>"
    discrepancies = sum(r["count_discrepancy"] for r in receipt)
    body += f"""</table></section><section><h2>What this means for the research</h2><p>This is a more relevant size comparison for successfully matched stocks. It still does not control for industry, valuation, leverage, manager selection or event timing. The company-resampling interval reflects sampling uncertainty, not every shared market or manager risk. Manager identities remain candidates and the supplemental manager list was chosen retrospectively.</p><p>Coverage is selective: unmatched stocks may be smaller, newly listed, foreign or missing from the downloaded data. A match-based result cannot be generalized to all 13D filings. The vendor's reported total differs from returned row counts in {discrepancies} of {len(receipt)} monthly snapshots. Dates and unique identifiers are checked, but vendor completeness is not certified; a nonmatch does not prove nonmembership.</p><p>The next steps are to examine concentration by manager/company/year, industry controls and portfolio returns with costs and capital constraints. The benchmark refinement follows inspection of development results. Later outcomes remain reserved, and human-review companies remain excluded. No NLP or predictive ML is involved.</p></section>
<section><details><summary>Methods, sources and reproducibility</summary><p>Entry: second exchange session after acceptance, at the open. Exit: 126/63/252-session scheduled close. Entry-day close/open is compounded with subsequent daily total returns. Original stock delisting treatment is retained: valid delisting return once, then zero return on proceeds. Shared issuer schedules suppress overlapping entries before return calculations. Follow-up ends by 29 December 2023.</p>
<p><a href="summary.json">Exact statistics and exclusions</a> · <a href="outcomes.json">Event ledger</a> · <a href="../20260924-russell-inputs-v1/assignments.json">Historical membership evidence</a> · <a href="../20260924-russell-inputs-v1/membership-receipt.json">Snapshot coverage</a> · <a href="provenance.json">Hashes and environment</a> · <a href="../20260924-expanded-hfr-returns-v1/index.html">Preserved SPY-only result</a></p>
<p>Source definitions: <a href="https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/lseg-mergent/">WRDS FTSE Russell data</a>; <a href="https://www.lseg.com/en/ftse-russell/indices/russell-us">FTSE Russell index family</a>; iShares <a href="https://www.ishares.com/us/products/239707/">IWB</a>, <a href="https://www.ishares.com/us/products/239718/IWR">IWR</a>, <a href="https://www.blackrock.com/us/individual/products/239710/ishares-russell-2000-etf">IWM</a>. Historical identity and returns use the cached CRSP sources, not current web-page performance.</p></details></section>"""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D Russell size comparison</title><style>body{font:17px/1.65 system-ui;color:#243b50;background:#f3f6f8;margin:0}main{max-width:1350px;margin:30px auto;padding:0 24px}section{background:white;padding:25px;margin:22px 0;border:1px solid #dce3e9;border-radius:8px}h1{line-height:1.3}h2{font-size:24px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #ddd}th{background:#eaf0f5}a{color:#155b91}summary{cursor:pointer;font-weight:bold}</style></head><body><main>'
        + body
        + "</main></body></html>"
    )


def main():
    for directory, key in [(INPUT, "outputs"), (EXPANDED, "outputs")]:
        p = json.loads((directory / "provenance.json").read_text())
        for name, expected in p[key].items():
            assert digest(directory / name) == expected, name
    baseline = json.loads((BASE / "provenance.json").read_text())["files"]
    for name in ["selection.json", "human-review-protection.json"]:
        assert digest(BASE / name) == baseline[name]
    assert (
        digest(ROOT / "src/activist13d/phase1_baseline.py") == baseline["code/phase1_baseline.py"]
    )
    assert digest(PROTOCOL) == digest(INPUT / "protocol.md")
    for p in [
        Path(__file__),
        ROOT / "src/activist13d/russell_benchmark.py",
        ROOT / "src/activist13d/phase1_baseline.py",
        ROOT / "tests/test_russell_benchmark.py",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    freeze(OUT / "protocol.md", PROTOCOL.read_bytes())
    plans = json.loads((BASE / "selection.json").read_text())["plans"]
    protected = set(json.loads((BASE / "human-review-protection.json").read_text())["issuers"])
    old = json.loads((EXPANDED / "outcomes.json").read_text())
    old_summary = json.loads((EXPANDED / "summary.json").read_text())
    assignments = json.loads((INPUT / "assignments.json").read_text())
    panel = {int(k): v for k, v in json.loads((INPUT / "etf-panel.json").read_text()).items()}
    receipt = json.loads((INPUT / "membership-receipt.json").read_text())
    outcomes = {}
    summaries = {}
    for horizon, events in plans.items():
        assert len(events) == len(old[horizon])
        rows = []
        for e, r in zip(events, old[horizon], strict=True):
            assert e["accession"] == r["accession"] and e["entry"] == r["entry"]
            assert r["issuer"] not in protected and r["exit"] <= "2023-12-29"
            rows.append(
                compare(r, assignments[e["accession"] + "|" + e["entry"]], e["days"], panel)
            )
        outcomes[horizon] = rows
        summaries[horizon] = {k: stats(v) for k, v in groups(rows).items()}
        assert (
            sum(summaries[horizon][k]["russell"]["calculated"] for k in DISJOINT)
            == summaries[horizon]["all"]["russell"]["calculated"]
        )
        for k, s in summaries[horizon].items():
            assert (
                s["russell"]["calculated"]
                == s["spy_common"]["calculated"]
                == s["iwv_common"]["calculated"]
            )
            assert (
                s["russell"]["calculated"] + s["excluded_spy"]["calculated"]
                == old_summary[horizon][k]["calculated"]
            )
    freeze(OUT / "outcomes.json", encode(outcomes))
    freeze(OUT / "summary.json", encode(summaries))
    freeze(OUT / "index.html", report(summaries, old_summary, receipt))
    sources = [
        INPUT / "provenance.json",
        INPUT / "assignments.json",
        INPUT / "etf-panel.json",
        INPUT / "membership-receipt.json",
        EXPANDED / "provenance.json",
        EXPANDED / "outcomes.json",
        EXPANDED / "summary.json",
        BASE / "selection.json",
        BASE / "human-review-protection.json",
        PROTOCOL,
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in sources},
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
                python=platform.python_version(),
            )
        ),
    )
    print(encode(summaries["126"]))


if __name__ == "__main__":
    main()
