"""Tier: 2. Explain the user-selected ex-Hill sensitivity and current next steps.
Inputs: frozen sensitivity results and independent QA. Outputs: HTML and handoff.
Identity: retrospective issuer exclusion changes the sample, not observed prices.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_phase1_skip_hill.py
"""

import html
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-skip-hill-analysis-v1"
OUT = BASE / "20260924-skip-hill-report-v1"


def pct(v):
    return "—" if v is None else f"{100 * v:.2f}%"


def table(headers, rows):
    return (
        '<div class="scroll"><table><tr>'
        + "".join("<th>" + html.escape(str(v)) + "</th>" for v in headers)
        + "</tr>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</table></div>"
    )


def main():
    portfolios = json.loads((RUN / "portfolio-summary.json").read_text())
    summary = json.loads((RUN / "summary.json").read_text())
    matched = json.loads((RUN / "matched-summary.json").read_text())
    changes = json.loads((BASE / "20260924-skip-hill-inputs-v1/selection.json").read_text())[
        "changes"
    ]
    qa = json.loads((BASE / "20260924-skip-hill-qa-v1/checks.json").read_text())
    assert qa["status"] == "passed"
    completed = sum(r["status"] == "complete" for r in portfolios.values())
    names = {
        "first_observed": "Mechanical first-observed pairs",
        "standalone": "Standalone initial forms",
    }
    rows = []
    eventrows = []
    countrows = []
    for branch in ["first_observed", "standalone"]:
        for h, label in [("126", "6 months — primary"), ("63", "3 months"), ("252", "12 months")]:
            c = changes[branch][h]
            countrows.append([names[branch], label, c["before"], c["after"], len(c["removed"])])
            r = summary[branch][h]["russell"]["focused"]
            m = matched[branch][h]["comparison"]
            eventrows.append(
                [
                    names[branch],
                    label,
                    f"{r['calculated']} / {r['scheduled']}",
                    pct(r.get("mean_excess")),
                    m["calculated"],
                    pct(m.get("mean_excess")),
                ]
            )
            for cap in [100000, 100000000]:
                key = f"{branch}-{h}-{cap}"
                r = portfolios[key + "-base"]
                rows.append(
                    [
                        names[branch],
                        label,
                        "$100k" if cap == 100000 else "$100m",
                        r["status"],
                        r["buys"],
                        pct(r["total_return"]),
                        pct(r.get("cagr")),
                        pct(r.get("max_drawdown")),
                        pct(r["average_cash_weight"]),
                        pct(portfolios[key + "-zero_cost"]["total_return"]),
                        pct(portfolios[key + "-zero_cash"]["total_return"]),
                    ]
                )
    body = f"""<p class="eyebrow">24 September 2026 · User-selected development sensitivity</p><h1>Proceeding without Hill International</h1>
<p class="lead">Hill International is excluded from this working case. <strong>{completed} of 36 portfolio scenarios now complete</strong>, so obtaining its OTC price history is no longer a prerequisite for this branch. The original full-universe results and their missing-value refusals remain preserved.</p>
<p>The exclusion applies to issuer 0001287808 across development investor cohorts and all three horizons, before scheduling. It was chosen after the missing-price problem became known; this is an ex-Hill sensitivity, not an untouched evaluation or a general permission to remove future missing observations. Investor membership, human labels, strategy rules and source histories are unchanged.</p>
<p>For the $100k mechanical first-pair six-month strategy, net cumulative return is <strong>21.89%</strong>, or <strong>3.48% annualized</strong>, over 19 March 2018–29 December 2023. Average cash is 74.74%, with 60 purchases and an 18.61% maximum drawdown. The twelve-month version returns 65.06% cumulatively (9.04% annualized), with 51.15% average cash and a 35.15% maximum drawdown. These full-study account returns are not six-/twelve-month event averages.</p>
<p>Fully invested SPY/IWV returned 91.64%/84.81% across the same window; the cash proxy returned 11.99%. Exposure differs materially, so these comparisons are not risk-adjusted alpha. Six months remains primary.</p>
<h2>Portfolio results after modeled costs</h2><p>Fixed delayed entry, 5% NAV target, 20-issuer maximum, 1% trailing-volume participation, minimum ticket, costs and lagged cash rules are inherited from the original protocol. Zero-cost sensitivity retains interest; zero-interest sensitivity retains costs. No management fees or taxes.</p>
{table(["Branch", "Holding rule", "Capital", "Status", "Buys", "Cumulative return", "Annualized", "Max drawdown", "Mean cash", "Zero-cost cumulative", "Zero-interest cumulative"], rows)}
<h2>Event and matched comparisons</h2><p>These are equally weighted gross stock-minus-Russell ETF averages. Matched differences compare focused excess with issuer-equal nonfocused controls sharing entry year, SIC2 and ETF, with five control companies required. The samples remain selective and matching remains retrospective.</p>
{table(["Branch", "Horizon", "Russell-calculable / focused scheduled", "Mean Russell excess", "Matched focused events", "Mean difference versus controls"], eventrows)}
<p>The six-/twelve-month first-pair focused means remain +0.28/+7.08 percentage points on 54 events each: Hill already lacked a calculable return at those horizons. Removing it resolves the separately funded portfolio calculation; it does not add a missing stock return to the event averages. The $100m portfolio results are unchanged because the original capacity rule already skipped Hill.</p>
<h2>Sample changes and remaining work</h2>
{table(["Branch", "Horizon", "Original scheduled", "Ex-Hill scheduled", "Removed Hill events"], countrows)}
<p>All remaining event outcomes equal the original values exactly; issuer schedules were rebuilt and independently checked. Only Hill events leave. No other missing-price case is silently excluded.</p>
<p><strong>Item 2: establish which investor–company relationship the filing describes.</strong> A first observed Elliott disclosure on Company A differs from a later filing continuing that relationship. A first Starboard disclosure on Company A may be a new pair. References to a prior 13D about Company B or an incorporated legal document do not prove prior involvement in Company A. We are trying to establish who filed, about which company, and when.</p>
<p>The current mechanical first-observed branch retains conservative, unvalidated history-reference exclusions. It is not a verified first-ever campaign census. Better attribution, evaluation input validation and a final rule/sample freeze remain; skipping Hill does not resolve those separate questions. Fresh evaluation and ML/NLP training have not begun.</p>
<p>Validation: {qa["event_returns_replayed"]:,} event returns replayed, {qa["portfolio_scenarios_replayed"]} exact portfolio replays, {qa["daily_cash_nav_checks"]:,} daily cash/NAV checks, and independent matched-control arithmetic. Original source, investor and human-review assets remain unchanged.</p>
<ul><li><a href="../20260924-skip-hill-analysis-v1/portfolio-summary.json">All portfolio summaries</a> · <a href="../20260924-skip-hill-analysis-v1/portfolio-monthly.json">Monthly returns</a> · <a href="../20260924-skip-hill-analysis-v1/portfolios/first_observed-126-100000-base.json">Primary trade/cash/NAV ledger</a></li>
<li><a href="../20260924-skip-hill-analysis-v1/summary.json">Event summaries</a> · <a href="../20260924-skip-hill-analysis-v1/matched-events.json">Matched comparisons</a></li>
<li><a href="../20260924-skip-hill-inputs-v1/selection.json">Excluded events and rebuilt schedules</a> · <a href="../20260924-skip-hill-qa-v1/checks.json">Independent QA</a> · <a href="../../../protocol/phase1-skip-hill-v1.md">Exclusion protocol</a></li>
<li><a href="../20260924-completion-integration-v1/index.html">Preserved independent closeout</a> · <a href="../20260924-rebuild-report-v2/index.html">Original development report</a></li></ul>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D — ex-Hill sensitivity</title><style>body{margin:0;background:#f4f6f8;color:#243747;font:17px/1.6 system-ui,sans-serif}main{max-width:1250px;margin:auto;padding:32px 24px}h1{font-size:36px;line-height:1.2}h2{margin-top:38px}.eyebrow{color:#526575;font-size:14px}.lead{background:#e5edf2;padding:24px;font-size:22px;border-left:5px solid #176386}a{color:#155c99}.scroll{overflow:auto}table{border-collapse:collapse;background:white;font-size:14px;width:100%}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}th{background:#e7edf1}li{margin:10px 0}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + body
        + "</main></body></html>"
    )
    freeze(OUT / "index.html", page)
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [
                        RUN / "provenance.json",
                        BASE / "20260924-skip-hill-qa-v1/checks.json",
                    ]
                },
                outputs={
                    "index.html": digest(OUT / "index.html"),
                    Path(__file__).name: digest(OUT / Path(__file__).name),
                },
            )
        ),
    )


if __name__ == "__main__":
    main()
