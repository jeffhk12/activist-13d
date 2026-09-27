"""Tier: 2. Explain long-horizon exploratory results and unresolved accounting.
Inputs: frozen event, portfolio, diagnostic and independent QA artifacts.
Outputs: HTML and handoff, preserving all prior short-horizon research outputs.
Identity: cumulative excess, individual annualized return differences and account CAGR differ.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_phase1_long_horizon.py
"""

import html
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-long-horizon-analysis-v1"
OUT = BASE / "20260924-long-horizon-report-v1"
DOC = ROOT / "research/docs/PHASE1-LONG-HORIZON-RESULTS-20260924.md"


def pct(v):
    return "Unavailable" if v is None else f"{100 * v:+.2f}%"


def pp(v):
    return "Unavailable" if v is None else f"{100 * v:+.2f} pp"


def table(heads, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{html.escape(str(v))}</th>" for v in heads)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def main():
    paths = [
        RUN / "summary.json",
        RUN / "portfolio-summary.json",
        RUN / "matched-summary.json",
        RUN / "portfolio-context.json",
        BASE / "20260924-long-horizon-diagnostics-v1/diagnostics.json",
        BASE / "20260924-long-horizon-qa-v1/checks.json",
    ]
    summary, portfolios, matched, context, diagnostics, qa = [
        json.loads(p.read_text()) for p in paths
    ]
    f = summary["first_observed"]["504"]["russell"]["focused"]
    m = matched["first_observed"]["504"]["comparison"]
    assert qa["status"] == "passed" and f["scheduled"] == 67 and f["calculated"] == 56
    completed = sum(v["status"] == "complete" for v in portfolios.values())
    assert completed == 30 and len(portfolios) == 48
    eventrows, commonrows, portrows, matchrows, annualrows = [], [], [], [], []
    for branch in ["first_observed", "standalone"]:
        label = "First observed pair" if branch == "first_observed" else "Standalone initial"
        for h, months in [("252", 12), ("378", 18), ("504", 24), ("756", 36)]:
            s = summary[branch][h]["russell"]["focused"]
            d = diagnostics[branch][h]
            ci = s["issuer_bootstrap_95"]
            eventrows.append(
                [
                    label,
                    f"{months} months" + (" · primary" if months == 24 else ""),
                    f"{s['calculated']} / {s['scheduled']}",
                    pct(s["mean_stock"]),
                    pp(s["mean_excess"]),
                    pp(s["median_excess"]),
                    f"{100 * s['fraction_beating_benchmark']:.1f}%",
                    f"{pp(ci[0])} to {pp(ci[1])}",
                ]
            )
            if branch == "first_observed":
                commonrows.append(
                    [months, d["all_horizon_calculable_count"], pp(d["all_horizon_mean_excess"])]
                )
                annualrows.append(
                    [
                        months,
                        pct(d["mean_stock_annualized"]),
                        pct(d["mean_benchmark_annualized"]),
                        pp(d["mean_annualized_difference"]),
                        pp(d["same_sample_spy_excess"]),
                    ]
                )
            a = matched[branch][h]["comparison"]
            matchrows.append(
                [
                    label,
                    months,
                    a["calculated"],
                    pp(a.get("mean_stock")),
                    pp(a.get("mean_benchmark")),
                    pp(a.get("mean_excess")),
                ]
            )
            for capital in [100000, 100000000]:
                p = portfolios[f"{branch}-{h}-{capital}-base"]
                complete = p["status"] == "complete"
                portrows.append(
                    [
                        label,
                        months,
                        "$100k" if capital == 100000 else "$100m",
                        "Complete" if complete else "Stopped 2019-07-18",
                        pct(p["total_return"]),
                        pct(p.get("cagr")),
                        f"{100 * p['average_cash_weight']:.1f}%"
                        if complete
                        else "Partial only — not comparable",
                        pct(p.get("max_drawdown")),
                    ]
                )
    groups = []
    for key, label in [
        ("focused", "Focused activist candidates"),
        ("other_event_driven", "Other Event-Driven candidates"),
        ("new_other_hfr", "Other newly recognized HFR"),
        ("other_unresolved", "Other / unresolved filers"),
    ]:
        s = summary["first_observed"]["504"]["russell"][key]
        groups.append(
            [
                label,
                f"{s['calculated']} / {s['scheduled']}",
                pp(s.get("mean_excess")),
                pp(s.get("median_excess")),
            ]
        )
    body = f"""<p class="eyebrow">24 September 2026 · Exploratory revision · 2018–2025 research window</p>
<h1>Longer holding periods: positive averages, mixed evidence</h1>
<p class="lead">At the new <strong>24-month primary horizon</strong>, 56 focused events average <strong>{
        pp(f["mean_excess"])
    } over their Russell benchmarks</strong>. But the median is {
        pp(f["median_excess"])
    }, the uncertainty range includes underperformance, and the primary funded portfolio remains incomplete.</p>
<p>We expanded the research window to examine whether initial 13D opportunities need longer to develop. Entries start 19 March 2018; all follow-up ends 31 December 2025. Holding periods are 12, 18, 24 and 36 months, approximated by 252, 378, 504 and 756 exchange sessions. Only events with enough calendar follow-up enter each schedule.</p>
<p>This combines previously examined development and later historical companies. It is an exploratory revision requested after reviewing shorter-horizon outcomes, not independent confirmation. The earlier results remain preserved. Investor lists, human protections, the Hill exclusion and 5% position targets are unchanged.</p>
<h2>What changed in the investment conclusion?</h2>
{
        table(
            ["Finding", "What it means"],
            [
                [
                    "Two-year mean excess +8.66 pp; three-year +20.83 pp",
                    "Longer-horizon averages are more favorable, but the broader historical window also changes the companies and market environments being tested.",
                ],
                [
                    "Two-year median excess −14.91 pp; 41.1% beat Russell",
                    "The typical calculable focused event still lagged. Positive averages coexist with many losing relative outcomes.",
                ],
                [
                    "Two-year 95% interval −17.34 to +40.43 pp",
                    "The evidence remains too uncertain to establish a reliable excess-return advantage.",
                ],
                [
                    "Industry/year/size-matched two-year difference −8.08 pp; n=17",
                    "The favorable full-sample average does not carry through to the smaller matched comparison.",
                ],
                [
                    "Primary $100k two-year account incomplete",
                    "We cannot report a full-period investable return until the flagged Aratana delisting input is resolved under a supported rule.",
                ],
            ],
        )
    }
<h2>Focused event results</h2>
<p>Equally weighted gross cumulative stock returns, before portfolio costs. Historical Russell segment ETFs are assigned using the preceding month-end. “pp” means percentage points. Each row has its own calendar-eligible schedule; branches and horizons overlap and must not be added. First observed means relative to the archive, not a proven first-ever campaign.</p>
{
        table(
            [
                "Branch",
                "Holding period",
                "Calculable / scheduled",
                "Mean stock return",
                "Mean Russell excess",
                "Median Russell excess",
                "Beat Russell",
                "95% interval: mean excess",
            ],
            eventrows,
        )
    }
<p>Primary first-pair coverage: 2,107 scheduled events → 712 Russell assignments → 694 calculable common stock/SPY/Russell events. The initial losses are 217 missing historical-security records and 1,178 unmatched constituents; 18 assigned events then fail stock-return validation. Focused coverage is 67 → 58 → 56: one missing historical-security record, eight unmatched constituents and two return failures. Missing observations remain explicit; none are replaced using their outcomes.</p>
<h2>Does the same-company comparison improve with time?</h2>
{
        table(
            [
                "Months",
                "Same focused events calculable at every horizon",
                "Mean cumulative Russell excess",
            ],
            commonrows,
        )
    }
<p>These are the same 50 focused events with calendar maturity and calculable returns at all four horizons. Their cumulative mean excess rises with holding period. This helps separate horizon effects from sample composition, but it is a coverage-conditioned diagnostic, not a tradable rule that could know future data availability. The original schedules are unchanged.</p>
<h2>Annualized returns tell a more cautious story</h2>
{
        table(
            [
                "Months",
                "Mean individual stock annualized return",
                "Mean individual ETF annualized return",
                "Difference of those means",
                "Cumulative SPY excess, same sample",
            ],
            annualrows,
        )
    }
<p>Each event is annualized separately as (1 + total return)^(252 / holding sessions) − 1, then averaged. This differs from annualizing the average cumulative return or calculating a funded portfolio CAGR. Large cumulative winners have less influence after this transformation. At two years, mean individual annualized stock returns are 4.95% versus 8.38% for their ETFs: a −3.43 percentage-point difference. A positive cumulative average is therefore not a robust finding across these summaries.</p>
<h2>Industry, timing and size controls</h2>
<p>Controls share entry year, two-digit industry and assigned Russell ETF. Each control company has equal weight; five distinct control companies are required. No threshold was loosened. These are retrospective descriptive comparisons, not causal effects.</p>
{
        table(
            [
                "Branch",
                "Months",
                "Matched focused events",
                "Focused Russell excess, matched subset",
                "Control Russell excess",
                "Focused minus controls",
            ],
            matchrows,
        )
    }
<p>At 24 months, only 17 of 67 focused first-pair events match: their excess averages {
        pp(m["mean_stock"])
    }, compared with {pp(m["mean_benchmark"])} for their controls. The difference is {
        pp(m["mean_excess"])
    }, with a 95% interval of {pp(m["issuer_bootstrap_95"][0])} to {
        pp(m["issuer_bootstrap_95"][1])
    }. Another 39 calculable focal events lack enough controls; 11 focal observations are unresolved. This does not support a positive matched advantage.</p>
<h2>Broader manager comparisons at two years</h2>
{
        table(
            [
                "Disjoint group",
                "Calculable / scheduled",
                "Mean Russell excess",
                "Median Russell excess",
            ],
            groups,
        )
    }
<p>These groups are mutually exclusive. The overlapping HFR-plus-supplement aggregate contains 116 calculable of 170 scheduled events and averages +26.09 pp excess, with a negative median. Positive descriptive means in other HFR groups do not justify changing the investor list to recent winners. Unresolved filers are not validated passive investors.</p>
<h2>Funded portfolios and cash deployment</h2>
<p>Every account uses the fixed 19 March 2018–31 December 2025 window. The 5% target, 20-issuer maximum, liquidity participation, minimum tickets, modeled costs and lagged cash interest remain unchanged. This revision tests time horizons, not higher concentration.</p>
{
        table(
            [
                "Branch",
                "Months",
                "Capital",
                "Accounting status",
                "Full-period cumulative return",
                "Annualized account return",
                "Average cash, complete period only",
                "Max drawdown",
            ],
            portrows,
        )
    }
<p><strong>{
        completed
    } of 48 scenarios complete; 18 refuse a complete-account result.</strong> The $100k 18/24/36-month variants in both branches stop at Aratana Therapeutics (issuer 0001509190, security 13966) on 18 July 2019. The cached delisting row has a numerical return but the missing-value flag is MV rather than the required NA. The existing validator refuses it. We have not asserted zero proceeds, accepted the flagged value, or removed the company.</p>
<p>The completed $100k first-pair twelve-month account returned +57.41% cumulatively, +5.99% annualized, with 55.41% average cash and a −35.15% maximum drawdown. It illustrates how broader historical coverage increases deployment compared with the sparse 2024–2025 test; it does not isolate a holding-period effect. The larger-capital accounts are separate capacity scenarios and cannot substitute for the incomplete primary account.</p>
<p>Across the full account window, the cash proxy returned {
        pct(context["cash"]["total_return"])
    }, SPY {pct(context["SPY"]["total_return"])}, and IWV {
        pct(context["IWV"]["total_return"])
    }. Fully invested ETF context has different equity exposure and is not a risk-matched alpha test. Partial-period cash weights and returns are deliberately not presented as full-period results.</p>
<h2>Research conclusion and next action</h2>
<p><strong>The longer-horizon hypothesis remains worth investigating, but these results do not establish an investable edge.</strong> Average cumulative focused returns improve at two and three years; medians, individual annualized averages and matched comparisons remain unfavorable. Uncertainty and selective coverage are material. The primary portfolio needs a supported resolution of the Aratana delisting data before its full-period result can be claimed.</p>
<p>Preserve the investor list and earlier findings. Next investigate the flagged settlement and return evidence under a general rule, without adding an outcome-driven exclusion. Concentration tests, campaign-based exit rules and NLP remain separate extensions. No prospective collection or ML/NLP training has started, and this now-examined historical sample is not an untouched final evaluation.</p>
<details><summary>Evidence, implementation and verification</summary>
<p>Daily source preparation verified 1,990 cached dates; no daily source file was absent. Row availability still does not guarantee a usable return. Historical ETF identities were checked throughout all 1,959 account sessions. Vendor count disagreement, monthly membership publication timing and revised cash-vintage limitations remain. Reused known issuers are explicitly tagged; 1,902 of 2,107 primary events involve issuers previously selected in the recorded research runs. Human-protected issuers remain excluded.</p>
<p>Independent QA replayed {qa["event_returns_replayed"]:,} event returns, {
        qa["matched_arithmetic_checked"]
    } matched-control calculations, {qa["portfolio_scenarios_replayed"]} portfolio scenarios and {
        qa[
            "daily_cash_nav_checks"
        ]:,} daily accounting checks, including partial-run prefixes. All 180 non-network tests pass; 554 protected investor/human assets are unchanged. Annualization is pinned to a hand-computed two-year 21% total return becoming 10% annually.</p>
<ul><li><a href="../../../docs/{
        DOC.name
    }">Detailed continuation handoff</a> · <a href="../../../protocol/phase1-long-horizon-v1.md">Frozen revision protocol</a></li>
<li><a href="../20260924-long-horizon-inputs-v1/selection.json">Schedules, calendar and eligibility exclusions</a> · <a href="../20260924-long-horizon-inputs-v1/coverage.json">Input coverage</a></li>
<li><a href="../20260924-long-horizon-analysis-v1/summary.json">All event summaries</a> · <a href="../20260924-long-horizon-analysis-v1/outcomes.json">Event outcomes/refusals</a> · <a href="../20260924-long-horizon-analysis-v1/calendar-common-summary.json">Calendar-common samples</a></li>
<li><a href="../20260924-long-horizon-analysis-v1/matched-summary.json">Matched comparison summaries</a> · <a href="../20260924-long-horizon-analysis-v1/portfolio-summary.json">All portfolio statuses</a> · <a href="../20260924-long-horizon-analysis-v1/portfolios/first_observed-504-100000-base.json">Primary incomplete ledger</a></li>
<li><a href="../20260924-long-horizon-diagnostics-v1/diagnostics.json">Annualization, same-event and accounting diagnostics</a> · <a href="../20260924-long-horizon-qa-v1/checks.json">Independent QA</a> · <a href="../20260924-long-horizon-inputs-v1/outcome-access.json">Outcome-access record</a></li>
<li><a href="../20260924-historical-validation-report-v1/index.html">Preserved 2024–2025 short-horizon test</a> · <a href="provenance.json">Report provenance</a></li></ul></details>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D — long-horizon exploratory results</title><style>body{margin:0;background:#f4f6f8;color:#203448;font:17px/1.6 system-ui,sans-serif}main{max-width:1240px;margin:auto;padding:32px 24px 70px}h1{font-size:38px;line-height:1.2;max-width:1100px}h2{font-size:25px;margin-top:36px}.eyebrow{font-size:14px;color:#526575}.lead{font-size:22px;background:#e5edf2;border-left:5px solid #176386;padding:24px}a{color:#155c99}.scroll{overflow:auto}table{width:100%;background:white;border-collapse:collapse;font-size:14px}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}th{background:#e5ebf0}details{background:white;padding:20px;border:1px solid #dce3e9;margin-top:30px}summary{cursor:pointer;font-weight:650}li{margin:10px 0}@media(max-width:650px){h1{font-size:30px}main{padding:20px 16px}.lead{font-size:19px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + body
        + "</main></body></html>"
    )
    note = f"""# Phase 1 long-horizon results and handoff

24 September 2026. Revised exploratory analysis executed; primary longer-horizon portfolio incomplete.

## Investment finding

Expanded 2018–2025 history, with 24 months primary and 12/18/36 supporting. Focused first-pair cumulative Russell excess: −0.08 pp at 12 months (65 calculable), −1.81 pp at 18 (60), +8.66 pp at 24 (56), +20.83 pp at 36 (50). Two-year mean stock return +27.82%, assigned ETF +19.15%. Its median excess is −14.91 pp, 41.1% beat the benchmark, and the 95% interval is −17.34 to +40.43 pp. Positive longer-horizon averages do not establish a robust edge.

[Open the revised report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-long-horizon-report-v1/index.html).
Project: `/Users/jefflu/Projects/activist-13d`.

## Scope and evidence

Two-year schedule: 2,107 first-pair events, including 67 focused. Overall 712 benchmark assignments → 694 calculable; focused 58 assignments → 56 calculable. These are events, not manager counts. Fifty focused events are calculable across all four horizons; their cumulative excess means are +7.13/+8.97/+18.24/+20.83 pp. That common-successful-data table is only a coverage sensitivity and never changes the signal selection. Calendar-common schedules and horizon-specific denominators are preserved separately.

At two years, mean individual annualized stock/ETF returns are +4.95%/+8.38%, a −3.43 pp difference. Annualize each event first then average; this is not annualizing the mean or reporting an account CAGR. The sign difference from cumulative means reflects unequal outcomes and the nonlinear transformation. Keep this distinction explicit.

Industry/year/Russell controls yield only 17 two-year focal matches: focused excess −3.07 pp, controls +5.01 pp, difference −8.08 pp, interval −29.87 to +14.03 pp. Do not relax the five-distinct-control rule. Broader HFR-plus-supplement mean excess +26.09 pp across 116/170 observations has a negative median. No winner-driven list revision.

## Account limitation — next dependency

30/48 scenarios complete. All $100k 18/24/36-month variants in both branches stop on 2019-07-18 at Aratana Therapeutics, issuer 0001509190 / PERMNO 13966. Cached row: dlydelflg Y, dlyprevdt 2019-07-17, dlyret −0.011463, dlyretmissflg MV, dlyretdurflg DD, no close/open/volume. The inherited validator requires NA for the return-missing flag and refuses the row despite its numerical return. The code does not prove actual proceeds from that row.

Do not remove Aratana, accept its flagged value, bridge to another ticker, assume cash/stock consideration, or use zero proceeds without source-backed general treatment. Next investigate source definitions and dated corporate-action/settlement evidence; any accounting-policy correction gets a new protocol/code version and parity checks. No other issuer exclusion is authorized by the existing Hill decision. Partial accounts stop after 335 sessions on 2019-07-17 with 17 positions; their 42.14% average cash is a partial prefix and must not be compared with full-period averages.

Completed $100k first-pair 12-month account: +57.41% cumulative, +5.99% annualized, 55.41% average cash, −35.15% max drawdown; 75 buys. Full account window 2018-03-19–2025-12-31. Cash-only +22.87%, SPY +181.73%, IWV +166.93% over that window; differing exposures prevent alpha claims. Larger-capital completed accounts cannot replace the missing primary $100k result.

## Preserve research decisions

This revision is outcome-aware exploratory development requested by the user after shorter-horizon results. It intentionally includes previously examined issuers: 1,902 of 2,107 primary events have an issuer previously selected in the recorded runs. No claim of fresh confirmation. Keep all 207 human-protected issuers excluded, conservative body/header/history eligibility, Company B references as leads, Hill exclusion, fixed investor list and original 5% targets. First observed is archive-relative. Longer horizons and a broader sample changed together; use the common-event diagnostics and avoid attributing all changes to holding duration.

Rebuild issuer nonoverlap schedules at 252/378/504/756 exchange sessions. Entry still counts as session one. Same deterministic entry, liquidity, costs, cash, missing-data and terminal-position rules. No NLP/ML training, new semantic labels, actual trades, prospective launch or concentration sensitivity.

## Artifacts and reproduction

All run folders below are under `research/runs/phase1-baseline/`:

- `20260924-long-horizon-inputs-v1`: frozen selections, exposure tags, environment/code/access record, panel, historical Russell assignments and source inventories. All 1,990 required daily source files exist; row/return validity remains separate. Raw new constituent responses, where required, use `data/raw/wrds/long-horizon-20260924-v1/`; earlier raw caches are preserved.
- `20260924-long-horizon-analysis-v1`: event/group summaries, outcomes/refusals, matched comparisons, common-calendar samples, 48 portfolio ledgers, monthly returns and broad-market context.
- `20260924-long-horizon-qa-v1`: independent schedule reconstruction, {qa["event_returns_replayed"]:,} event-return replays, {qa["matched_arithmetic_checked"]} matched-control arithmetic checks, {qa["portfolio_scenarios_replayed"]} portfolio replays and {qa["daily_cash_nav_checks"]:,} daily cash/NAV checks including partial prefixes.
- `20260924-long-horizon-diagnostics-v1`: annualization hand pins, all-horizon calculable subset, accounting attribution, ETF identity checks over 1,959 sessions. Individual annualized event statistics are not portfolio CAGR.
- `20260924-long-horizon-report-v1`: user-facing results and provenance.

Protocol: `research/protocol/phase1-long-horizon-v1.md`. Scripts: `prepare_phase1_long_horizon.py`, `run_phase1_long_horizon.py`, `verify_phase1_long_horizon.py`, `diagnose_phase1_long_horizon.py`, `report_phase1_long_horizon.py` under `scripts/data_collection/`. Run using project `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. All input and output hashes must match; use a separate version for changes. Cached panel enables offline analysis replay. Full non-network suite: 180 passed, one deselected; protected guard checks 554 unchanged assets.

Vendor row-count disagreements, sparse benchmark matching, monthly membership timing and revised cash vintages remain limitations. No file-presence check certifies complete market coverage. Preserve earlier development, later historical and long-horizon outputs separately. The revised results support further research into the long-term thesis but do not establish an investable edge or justify changing the list to winners.
"""
    freeze(OUT / "index.html", page)
    freeze(DOC, note)
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                "outputs": {
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [OUT / "index.html", DOC, OUT / Path(__file__).name]
                },
            }
        ),
    )
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
