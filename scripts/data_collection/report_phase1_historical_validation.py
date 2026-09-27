"""Tier: 2. Explain frozen historical validation results in investment terms.
Inputs: verified historical summaries, diagnostics and accounting QA.
Outputs: self-contained HTML report, continuation handoff and provenance.
Identity: stock-minus-benchmark percentage points differ from total account return.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_phase1_historical_validation.py
"""

import html
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-historical-validation-v2"
OUT = BASE / "20260924-historical-validation-report-v1"
DOC = ROOT / "research/docs/PHASE1-HISTORICAL-VALIDATION-20260924.md"


def pct(v):
    return "—" if v is None else f"{100 * v:+.2f}%"


def pp(v):
    return "—" if v is None else f"{100 * v:+.2f} pp"


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{html.escape(str(v))}</th>" for v in headers)
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
        RUN / "portfolio-context.json",
        RUN / "matched-summary.json",
        BASE / "20260924-historical-diagnostics-v1/diagnostics.json",
        BASE / "20260924-historical-validation-qa-v2/checks.json",
    ]
    s, portfolios, context, matches, diag, qa = [json.loads(p.read_text()) for p in paths]
    p = portfolios["first_observed-126-100000-base"]
    f = s["first_observed"]["126"]["russell"]["focused"]
    d = diag["first_observed"]["126"]
    assert qa["status"] == "passed" and all(v["status"] == "complete" for v in portfolios.values())
    assert f["scheduled"] == 6 and f["calculated"] == 5
    assert 50 + 315 + 1 + 137 == s["first_observed"]["126"]["russell"]["all"]["scheduled"]
    eventrows, portrows = [], []
    for branch in ["first_observed", "standalone"]:
        for h, horizon in [("126", "6 months · primary"), ("63", "3 months"), ("252", "12 months")]:
            v = s[branch][h]["russell"]["focused"]
            dt = diag[branch][h]
            ci = v["issuer_bootstrap_95"]
            eventrows.append(
                [
                    "First observed pair" if branch == "first_observed" else "Standalone form",
                    horizon,
                    f"{v['calculated']} / {v['scheduled']}",
                    pct(v["mean_stock"]),
                    pp(v["mean_excess"]),
                    pp(dt["focused_same_sample_spy_mean"]),
                    f"{pp(ci[0])} to {pp(ci[1])}",
                ]
            )
            for cap in [100000, 100000000]:
                v = portfolios[f"{branch}-{h}-{cap}-base"]
                portrows.append(
                    [
                        "First observed pair" if branch == "first_observed" else "Standalone form",
                        horizon,
                        "$100k" if cap == 100000 else "$100m",
                        v["buys"],
                        pct(v["total_return"]),
                        pct(v["cagr"]),
                        pct(v["max_drawdown"]),
                        f"{100 * v['average_cash_weight']:.2f}%",
                        pp(v["total_return"] - context["cash"]["total_return"]),
                    ]
                )
    groups = []
    labels = [
        ("focused", "Focused activist candidates"),
        ("other_event_driven", "Other Event-Driven candidates"),
        ("new_other_hfr", "Other newly recognized HFR candidates"),
        ("other_unresolved", "Other / unresolved filers"),
    ]
    for key, label in labels:
        v = s["first_observed"]["126"]["russell"][key]
        groups.append(
            [
                label,
                f"{v['calculated']} / {v['scheduled']}",
                pct(v.get("mean_stock")),
                pp(v.get("mean_excess")),
                pp(v.get("median_excess")),
            ]
        )
    body = f"""<p class="eyebrow">24 September 2026 · Phase 1 historical validation · Entries in 2024–2025</p>
<h1>The later sample does not confirm a focused-activist edge</h1>
<p class="lead">Following the focused candidates produced <strong>{
        pp(f["mean_excess"])
    } versus Russell over six months</strong>, across five benchmark-matched events. The $100,000 portfolio returned <strong>{
        pct(p["total_return"])
    } over 2024–2025</strong>, below the cash proxy’s {pct(context["cash"]["total_return"])}.</p>
<p>We asked whether buying after an initial 13D adds value when we identify the investor. This limited later-period historical test gives negative evidence for the fixed focused rule. It does not establish that activist investing never works: the sample is small, benchmark coverage is selective, and prior exposure to historical outcomes cannot be fully ruled out.</p>
<h2>What the primary result means</h2>
{
        table(
            ["What we measured", "Result", "Investment meaning"],
            [
                [
                    "Six-month stock selection",
                    f"{pct(f['mean_stock'])} stock return versus {pct(f['mean_benchmark'])} assigned Russell ETF return; n=5",
                    "The focused stocks underperformed their size-segment benchmarks on average.",
                ],
                [
                    "Uncertainty",
                    f"{pp(f['issuer_bootstrap_95'][0])} to {pp(f['issuer_bootstrap_95'][1])}",
                    "The 95% issuer-resampling interval includes both underperformance and outperformance. Five observations cannot support a strong general conclusion.",
                ],
                [
                    "Funded account, 2 Jan 2024–31 Dec 2025",
                    f"{pct(p['total_return'])} cumulative; {pct(p['cagr'])} annualized; {p['buys']} purchases",
                    "This is the whole two-year account using six-month holdings, not a six-month portfolio return.",
                ],
                [
                    "Cash and deployment",
                    f"{100 * p['average_cash_weight']:.2f}% average cash; {pp(d['primary_account_minus_cash'])} versus cash-only",
                    "Most of the account gain came from cash interest. The strategy did not improve on holding the cash proxy.",
                ],
                [
                    "Industry/time controls",
                    "No qualifying focused matches",
                    "Every calculable focal event had fewer than five matching control companies. No matched-comparison estimate can be reported.",
                ],
            ],
        )
    }
<p>The primary account gained ${d["account_pnl_dollars"]:,.2f}: ${
        d["cash_interest_dollars"]:,.2f} of cash interest, ${
        d["gross_stock_pnl_dollars"]:,.2f} of gross stock profit/loss, less ${
        d["costs_dollars"]:,.2f} of modeled costs. These reconcile to its ending value of ${
        p[
            "terminal_nav"
        ]:,.2f}. One of the six signals was skipped because its prior 20-session liquidity history was unavailable. All positions were closed by the fixed endpoint.</p>
<h2>Why is so much of the account in cash?</h2>
<p>The broader primary schedule has 503 events, but the focused strategy has only six qualifying signals and makes five purchases. Each targets 5% of the account, and their six-month holding periods do not all overlap. Five half-year positions at approximately 5% each spread over a two-year account imply roughly 6% average exposure before price changes and exact trading dates—close to the observed 5.78%. The rule has room for 20 companies but never receives enough qualifying signals to fill that capacity.</p>
<p>Higher concentration could deploy more cash, subject to liquidity limits, while increasing company-specific risk. It would not repair weak stock selection: the purchased stocks collectively lost money before costs in this test. A comparison of 10% and 20% targets with identical signals, dates and liquidity limits is a proposed exploratory sensitivity, not an activated change to this 5% baseline. Because the idea arose after inspecting these results, it cannot be presented as a prespecified independent test.</p>
<h2>How the sample gets smaller</h2>
<p>The frozen primary schedule contains <strong>503 events</strong>. Historical benchmark matching leaves 138: 50 lack the required historical security evidence and 315 have no constituent match. One of the 138 then fails stock-return validation, leaving <strong>137 common stock/SPY/Russell observations</strong>. Separately, 492 of 503 stock-only return histories are calculable; seven fail total-return validation and four lack a usable scheduled exit trade.</p>
<p>The focused subset is inside those totals: <strong>6 scheduled → 5 benchmark-matched → 5 calculable</strong>. All six stock-only histories are calculable. The unmatched event stays in the selection and accounting records. Missing benchmark membership is not a negative investment outcome.</p>
<h2>Focused results across holding periods</h2>
<p>Gross, equally weighted event returns. Entry is the second exchange session after disclosure acceptance, at the modeled opening price. Russell uses preceding-month membership and IWB/IWR/IWM ETF proxies. SPY excess is shown on exactly the same calculable observations. “pp” means percentage points. Rows overlap and must not be added.</p>
{
        table(
            [
                "Branch",
                "Holding period",
                "Calculable / scheduled focused",
                "Stock return",
                "Russell excess",
                "SPY excess, same sample",
                "95% interval for Russell excess",
            ],
            eventrows,
        )
    }
<p>The twelve-month first-pair estimate is based on only three companies. Its negative resampling interval does not overcome the tiny sample or incomplete exposure history. Holding-period samples differ. On the same three first-pair companies common to all horizons, Russell excess is {
        pp(diag["first_observed"]["63"]["common_calendar_focused_russell_mean"])
    }, {pp(d["common_calendar_focused_russell_mean"])} and {
        pp(diag["first_observed"]["252"]["common_calendar_focused_russell_mean"])
    } at three, six and twelve months respectively. Longer holding did not rescue the pattern in this common sample.</p>
<h2>What about the rest of HFR?</h2>
{
        table(
            [
                "Disjoint group · first pair, six months",
                "Calculable / scheduled",
                "Mean stock return",
                "Mean Russell excess",
                "Median Russell excess",
            ],
            groups,
        )
    }
<p>These four groups are mutually exclusive. The broader HFR-plus-supplement aggregate overlaps them: its 14 calculable events average +16.24 percentage points versus Russell, with a wide interval spanning zero. The eight newly recognized other-HFR events look stronger here, but that is a small descriptive result. We will not redefine the focused investor list around this period’s winners. Other/unresolved filers are not a validated passive-investor control group.</p>
<h2>Portfolio accounting after modeled costs</h2>
<p>Every account runs from 2 January 2024 to 31 December 2025. Rules retain a 5% target allocation per issuer, a 20-issuer limit, orders capped at 1% of preceding 20-session dollar volume, minimum tickets, modeled friction and lagged cash interest. Sparse signals and capacity restrictions leave large cash balances. There are no taxes or management fees. All 36 base/cost/cash scenarios complete; base cases are below.</p>
{
        table(
            [
                "Branch",
                "Holding rule",
                "Capital",
                "Buys",
                "Cumulative account return",
                "Annualized",
                "Max drawdown",
                "Average cash",
                "Account minus cash",
            ],
            portrows,
        )
    }
<p>Fully invested SPY returned {pct(context["SPY"]["total_return"])} and IWV {
        pct(context["IWV"]["total_return"])
    } over the same account window. Their equity exposure is very different from these mostly-cash accounts; the difference is not risk-adjusted alpha.</p>
<h2>Conclusion and next research step</h2>
<p><strong>The earlier development pattern did not replicate in this later sample under the frozen rule.</strong> Phase 1 supplies a reproducible simple-following baseline, including an unfavorable later result. It does not currently support an allocation claim. No industry/time-matched conclusion is available because the minimum control coverage was not met.</p>
<p>Keep these results and the investor list fixed. The next step is to review this baseline and prepare the prospective registration and collection process. Structured-data ML can later test whether disclosure-time attributes improve selection; NLP must then demonstrate additional value. Neither should use this now-examined historical sample as an untouched final test. Prospective collection has not started.</p>
<details><summary>Methods, verification and source evidence</summary>
<p>Return chains require usable entry and exit observations, consecutive daily total returns and recognized delisting flags. Supported delisting returns are applied once; event proceeds earn zero thereafter while portfolio proceeds enter the cash account. Refusals remain in denominators. Industry controls use entry calendar year, two-digit SIC and Russell ETF, with five distinct control issuers required.</p>
<p>Source preparation verified 522 cached daily files and recorded numerical access after protocol/sample/code snapshots. Vendor count discrepancies, monthly membership timing and revised cash-vintage limitations remain. An adapter error mapping invalid SIC 0/9999 into usable industries was corrected in separate v2 inputs: 37 specifications changed to missing, with identical selection, prices, analytical summaries, matched results and portfolios. Original versions remain preserved.</p>
<p>Verification replayed {qa["event_returns_replayed"]:,} event returns, {
        qa["portfolio_scenarios_replayed"]
    } portfolio scenarios and {
        qa[
            "daily_cash_nav_checks"
        ]:,} daily cash/NAV identities. The full non-network suite passes 180 tests; 554 protected investor/human assets are unchanged. No investor-list tuning or human-label changes occurred.</p>
<ul><li><a href="../../../docs/{
        DOC.name
    }">Detailed findings and continuation handoff</a> · <a href="../../../protocol/phase1-historical-validation-v1.md">Frozen historical protocol</a></li>
<li><a href="../20260924-historical-validation-v2/summary.json">All group summaries</a> · <a href="../20260924-historical-validation-v2/outcomes.json">Event outcomes and refusals</a> · <a href="../20260924-historical-validation-v2/calendar-common-summary.json">Common-calendar comparisons</a></li>
<li><a href="../20260924-historical-validation-v2/portfolio-summary.json">All portfolio scenarios</a> · <a href="../20260924-historical-validation-v2/portfolios/first_observed-126-100000-base.json">Primary account ledger</a> · <a href="../20260924-historical-validation-v2/portfolio-monthly.json">Monthly account returns</a></li>
<li><a href="../20260924-historical-validation-v2/matched-events.json">Unavailable matched comparisons</a> · <a href="../20260924-historical-diagnostics-v1/diagnostics.json">Cash/P&amp;L reconciliation and sample diagnostics</a></li>
<li><a href="../20260924-historical-validation-qa-v2/checks.json">Independent QA</a> · <a href="../20260924-historical-execution-inputs-v1/outcome-access-0001.json">First numerical-access record</a> · <a href="../20260924-historical-diagnostics-v1/correction-parity.json">Correction parity</a> · <a href="provenance.json">Report provenance</a></li></ul></details>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D — historical validation results</title><style>body{margin:0;background:#f4f6f8;color:#203448;font:17px/1.6 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:32px 24px 70px}h1{font-size:38px;line-height:1.2;max-width:1000px}h2{font-size:25px;margin-top:36px}.eyebrow{font-size:14px;color:#526575}.lead{font-size:22px;background:#e7edf1;border-left:5px solid #9c6343;padding:24px}a{color:#155c99}.scroll{overflow:auto}table{width:100%;background:white;border-collapse:collapse;font-size:14px}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #dce3e9}th{background:#e5ebf0}details{background:white;border:1px solid #dce3e9;padding:20px;margin-top:32px}summary{cursor:pointer;font-weight:650}li{margin:9px 0}@media(max-width:650px){h1{font-size:30px}main{padding:20px 16px}.lead{font-size:19px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + body
        + "</main></body></html>"
    )
    handoff = f"""# Phase 1 historical validation — findings and continuation

24 September 2026. Status: authorized historical evaluation completed; no fresh confirmation.

## Investment finding

The later sample does not confirm a focused-activist edge. Five six-month first-observed events average {pp(f["mean_excess"])} versus assigned Russell ETFs (mean stock {pct(f["mean_stock"])}, benchmark {pct(f["mean_benchmark"])}). The issuer-resampling 95% interval is {pp(f["issuer_bootstrap_95"][0])} to {pp(f["issuer_bootstrap_95"][1])}. This is negative observed evidence with substantial uncertainty, not proof that all activist investing fails.

The $100,000 primary account earns {pct(p["total_return"])} cumulatively ({pct(p["cagr"])} annualized) over 2 January 2024–31 December 2025, versus {pct(context["cash"]["total_return"])} cash-only. Mean cash weight is {100 * p["average_cash_weight"]:.2f}%. Five buys; one prior-liquidity skip; no terminal positions. Gain ${d["account_pnl_dollars"]:,.2f} = cash interest ${d["cash_interest_dollars"]:,.2f} + gross stock P&L ${d["gross_stock_pnl_dollars"]:,.2f} − costs ${d["costs_dollars"]:,.2f}. Full-period account returns differ from six-month event averages.

[Open the full report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-historical-validation-report-v1/index.html).
Project: `/Users/jefflu/Projects/activist-13d`.

## Samples and comparisons

Frozen primary schedule: 503 events, including six focused. Fifty have missing historical identity evidence and 315 no constituent match, leaving 138 assignments; one return-validation failure leaves 137 common benchmark observations. Stock-only: 492 calculable, seven invalid/missing total returns, four unusable exits. All six focused stock histories calculate; five have Russell assignments. Coverage is selective. No missing event was replaced.

First-pair focused Russell excess: three months −7.85 pp (6 calculable / 7 scheduled), six months −6.18 pp (5/6), twelve months −29.39 pp (3/4). On the same three common companies, respective means are −10.12/−14.39/−29.39 pp. Six months remains primary. All-horizon/branch tables, SPY on identical samples and common-calendar selection keys are in the report and run.

No focused event qualifies for the frozen industry/year/Russell comparison requiring five distinct control issuers. This analysis is unavailable, not estimated as zero and not relaxed after results. Broader HFR-plus-supplement six-month excess is +16.24 pp across 14 calculable of 22 scheduled events, with an interval spanning zero. Newly recognized other HFR has eight calculable events and a positive descriptive mean. Do not tune the investor list to these winners.

## Rules preserved

First-observed pairs are archive-relative candidates, not first-ever campaigns. Preserve standalone initial forms separately; fixed six-month primary and three/twelve-month supporting horizons; $100k primary and $100m capacity accounts; existing 5% targets, 20-issuer limit, liquidity/fee/cash rules. Missing marks refuse a complete account; delisting settlement uses supported CIZ total-return flags once. Hill remains excluded under the retrospective user decision. Company B references remain unconfirmed research leads for later NLP. Human labels and all investor memberships are unchanged.

## Source and implementation record

- Decision freeze: `20260924-historical-decision-freeze-v1`, governed by `research/protocol/phase1-historical-validation-v1.md`.
- Input access/preparation: `20260924-historical-execution-inputs-v1` records code/environment and first numerical access before reading numeric fields. It verifies 522 cached date sources. Required-key and raw-source inventories are retained.
- Corrected execution inputs: `20260924-historical-execution-inputs-v2`. Restore inherited SIC rule 100 <= code < 9999: 32 specifications with 9999 and five with 0 were initially given a false industry category. Correction sets them to missing. Original panel, selection and access receipt preserved exactly.
- Current analysis: `20260924-historical-validation-v2`; original v1 retained. Seven analytical artifacts, including summaries, matched comparisons and portfolio results, are byte-identical across versions. Event records differ only in corrected industry metadata.
- Independent QA: `20260924-historical-validation-qa-v2`: {qa["event_returns_replayed"]:,} event-return replays, {qa["portfolio_scenarios_replayed"]} exact portfolio replays and {qa["daily_cash_nav_checks"]:,} cash/NAV checks. All 36 portfolio scenarios complete; zero qualifying matched estimates.
- Diagnostics: `20260924-historical-diagnostics-v1`, including independent cash/P&L identity, industry-range contract and correction parity.
- Current report: `20260924-historical-validation-report-v1`.

All run names above are below `research/runs/phase1-baseline/`. Full non-network suite: 180 passed, one deselected. Protected guard: 554 unchanged assets. Source count disagreements, monthly membership publication timing and cash revision-vintage limitations remain. This is a limited historical validation with incomplete exposure provenance. These outcomes are now examined and must never be represented as an untouched final test.

## Reproduce

From project root, use `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. Scripts under `scripts/data_collection/`:

1. `prepare_phase1_historical_execution.py` — original cached numerical source preparation and access receipt; no new network calls.
2. `repair_phase1_historical_industry.py` — separate v2 input correction, no selection or price changes.
3. `run_phase1_historical_validation_v2.py` — current event, matched and portfolio execution.
4. `verify_phase1_historical_validation.py` — independent joins, return arithmetic and accounting replay.
5. `summarize_phase1_historical_validation.py` — correction parity and investment diagnostics.
6. `report_phase1_historical_validation.py` — report and this handoff.

Frozen artifacts refuse changed bytes. New implementation changes require a new version with reason and appropriate parity checks. The copied first-access receipt in v2 is provenance from original v1, not a claim that v2 was the first access.

## Position-sizing discussion after results

User asked whether sparse opportunities explain high cash and whether concentration should rise. Five purchases at 5% target weights with roughly six-month holdings across a two-year account explain the approximately 6% average exposure. This reflects few qualifying focused signals, not absence of the broader 503-event universe. The 20-position maximum is capacity, not a requirement to hold 20 names.

Recommendation: preserve the 5% baseline and consider 10%/20% targets on exactly the same signals, dates and liquidity rules as a separately labeled exploratory sensitivity. Larger positions raise company risk and may still hit capacity limits. Purchased stocks collectively lost money before costs here; more exposure is not evidence of a better signal. No concentration sensitivity has been executed or adopted in this run. Any later execution must disclose that this sizing question was raised after seeing outcomes.

## Next work

Review the unfavorable later result without changing the fixed investor list. Phase 1 now has a completed simple-following historical baseline and a later-period test, but no demonstrated investable edge and no fresh confirmation. Industry/time robustness remains coverage-limited.

Prepare the actual prospective registration and operating collection controls using the separate prospective plan; collection has not been launched. Freeze dates and any general implementation changes before prospective signals arrive. A twelve-month collection window is still a planning recommendation, not an activated schedule. Keep append-only signal and outcome-access records and preserve quarantine rules.

Structured-data ML may next investigate whether investor/company/filing attributes improve the baseline. NLP must demonstrate additional value beyond that model. The now-examined historical period may be diagnostic/development evidence with explicit disclosure, but cannot be recycled as independent final evaluation. No ML/NLP training or human-label changes have occurred in this task.
"""
    freeze(OUT / "index.html", page)
    freeze(DOC, handoff)
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
