"""Tier: 2. Plain-English companion to frozen eligibility/matching/portfolio runs.
Inputs: immutable analysis, QA and eligibility artifacts. Outputs: HTML/Markdown.
Identity: every displayed statistic is read from or directly reconciled to artifacts.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_rebuilt_analysis.py
"""

import html
import json
import statistics
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-rebuild-report-v2"
AN = BASE / "20260924-rebuilt-analysis-v1"
IN = BASE / "20260924-rebuilt-inputs-v2"
EL = BASE / "20260924-universe-rebuild-v3"
QA = BASE / "20260924-rebuilt-qa-v1"
NAMES = {
    "standalone": "Standalone initial forms",
    "first_observed": "First observed manager–issuer pairs",
}
MONTHS = {"126": "6 months (primary)", "63": "3 months", "252": "12 months"}


def load(p):
    return json.loads(p.read_text())


def pct(v):
    return "—" if v is None else f"{v * 100:,.2f}%"


def pp(v):
    return "—" if v is None else f"{v * 100:+.2f}"


def interval(r):
    return " to ".join(pp(v) for v in r.get("issuer_bootstrap_95", [])) or "—"


def table(head, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join("<th>" + html.escape(str(x)) + "</th>" for x in head)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(x)) + "</td>" for x in r) + "</tr>"
            for r in rows
        )
        + "</tbody></table></div>"
    )


def main():
    s = load(AN / "summary.json")
    m = load(AN / "matched-summary.json")
    p = load(AN / "portfolio-summary.json")
    o = load(AN / "outcomes.json")
    q = load(QA / "checks.json")
    sel = load(IN / "selection.json")
    u = load(EL / "summary.json")
    context = load(AN / "portfolio-context.json")
    eventrows = []
    matchrows = []
    funnels = []
    portrows = []
    sensrows = []
    groups = []
    for b in ["standalone", "first_observed"]:
        for h in ["126", "63", "252"]:
            r = s[b][h]["russell"]["focused"]
            rs = [e for e in o[b][h]["russell"] if e["focused"] and e["excess"] is not None]
            eventrows.append(
                [
                    NAMES[b],
                    MONTHS[h],
                    f"{r['calculated']} / {r['scheduled']}",
                    pct(r["mean_stock"]),
                    pp(r["mean_excess"]),
                    pp(statistics.mean(e["spy_excess"] for e in rs)),
                    pp(r["median_excess"]),
                    interval(r),
                ]
            )
            c = m[b][h]["comparison"]
            matchrows.append(
                [
                    NAMES[b],
                    MONTHS[h],
                    f"{c['calculated']} / {r['calculated']}",
                    pp(c["mean_stock"]),
                    pp(c["mean_benchmark"]),
                    pp(c["mean_excess"]),
                    interval(c),
                ]
            )
            change = q["event_changes"][b][h]
            funnels.append(
                [
                    NAMES[b],
                    MONTHS[h],
                    len(sel["selected"][b]),
                    s[b][h]["spy"]["all"]["scheduled"],
                    s[b][h]["spy"]["all"]["calculated"],
                    s[b][h]["russell"]["all"]["calculated"],
                    len(change["newly_released"]),
                    len(change["no_longer_scheduled"]),
                ]
            )
            for capital in [100000, 100000000]:
                key = f"{b}-{h}-{capital}"
                r = p[key + "-base"]
                done = r["status"] == "complete"
                portrows.append(
                    [
                        NAMES[b],
                        MONTHS[h],
                        "$100k" if capital == 100000 else "$100m",
                        "Complete" if done else "Stops 14 Aug 2018",
                        r["buys"] if done else "—",
                        pct(r["total_return"]),
                        pct(r.get("cagr")),
                        pct(r.get("max_drawdown")),
                        pct(r["average_cash_weight"]) if done else "—",
                    ]
                )
                sensrows.append(
                    [
                        NAMES[b],
                        MONTHS[h],
                        "$100k" if capital == 100000 else "$100m",
                        pct(r["total_return"]),
                        pct(p[key + "-zero_cost"]["total_return"]),
                        pct(p[key + "-zero_cash"]["total_return"]),
                        f"${r['total_cost']:,.0f}" if done else "—",
                        f"{r['turnover']:.2f}x" if done else "—",
                    ]
                )
        for group, label in [
            ("all", "All eligible events"),
            ("expanded", "All HFR + supplement"),
            ("hfr_only", "HFR only"),
            ("focused", "Focused candidates"),
            ("other_event_driven", "Other Event-Driven"),
            ("new_other_hfr", "Other HFR"),
            ("other_unresolved", "Other/unresolved filers"),
        ]:
            r = s[b]["126"]["russell"][group]
            groups.append(
                [
                    NAMES[b],
                    label,
                    r["scheduled"],
                    r["calculated"],
                    pp(r.get("mean_excess")),
                    interval(r),
                ]
            )
    primary = s["first_observed"]["126"]["russell"]["focused"]
    twelve = s["first_observed"]["252"]["russell"]["focused"]
    intro = f"""<p class="eyebrow">Phase 1 · 24 September 2026 · Outcome-aware development research</p><h1>Does following a new 13D campaign still show an edge?</h1>
<p class="lead">The cleaner campaign definition substantially reduces the apparent advantage. First observed manager–issuer pairs average <strong>{pp(primary["mean_excess"])} percentage points</strong> over their Russell ETF at six months and <strong>{pp(twelve["mean_excess"])} points</strong> at twelve months, across 54 calculable focused events at each horizon. Neither uncertainty range rules out zero.</p>
<p>Industry/year-matched comparisons remain positive at six and twelve months, but cover only 19 focused events. The portfolio results do not yet establish an investable edge: small-account tests encounter an unresolved held-stock return, while the larger account holds very high cash under the fixed liquidity limits.</p>
<p>Six months remains primary; twelve months is supporting evidence. No investor was added or removed based on performance. Outcome-aware source reviews remain separate from human reference labels. Fresh-data evaluation has not started.</p>"""
    eligibility = f"""<h2>1. What now counts as an initial event?</h2>
<p><strong>Standalone initial form</strong> means the filing survives metadata, SEC header and document checks, including explicit amendment numbers in its body. <strong>First observed pair</strong> additionally requires no earlier occurrence of any current manager/reporting-party–issuer pair and no detected prior 13D or dissolved-group history. A new standalone form can therefore continue an existing campaign.</p>
{table(["Parsed-universe classification", "Filings"], [["Amendments", 58166], ["Standalone initial-form candidates", 17420], ["Unresolved 13G-to-13D conversion", 16], ["Unresolved source or primary document", 29], ["Total parsed universe", 75631]])}
<p>Of the 17,420 standalone candidates, <strong>16,278</strong> are first observed pairs, <strong>964</strong> have prior pair records, and <strong>178</strong> contain prior-history references. These sum to 17,420. There are 353 affirmative body-amendment flags despite initial metadata; two of those also receive the more conservative unresolved-conversion status. The 45 unresolved filings are excluded, not certified as initial.</p>
<p>“First observed” means within the supplied archive starting in 2013, not first ever. Reporting-party CIKs and existing HFR/supplement manager keys are identity proxies. Group overlap preserves history, but incomplete entity mapping and older activity can still misclassify economic campaigns. Text rules detect specific evidence; they are not a complete legal reading or an activism label.</p>
<h3>How the development sample changes</h3><p>The original 17,795 metadata-initial filings first pass the unchanged date, security, source and protected-issuer screen: 2,915 remain. Standalone eligibility excludes 46 (40 amendments, 3 source failures, 3 conversions), leaving 2,869 filings. The first-pair branch excludes another 135 (111 prior pairs, 24 text-history flags), leaving 2,734. Scheduling then combines simultaneous same-security filings and suppresses issuer overlap. Missing future returns never release replacement events.</p>
{table(["Branch", "Horizon", "Pre-schedule filings", "Scheduled events", "Stock + SPY calculable", "Russell common events", "Newly scheduled vs old", "No longer scheduled vs old"], funnels)}
<p>The six-month standalone schedule is rebuilt from 2,097 to 2,069 events: 30 previous events leave and 2 become eligible after the overlap schedule is recomputed. The first-pair schedule has 1,981 events: 125 previous events leave and 9 are newly scheduled. These are event changes, not counts of manager additions.</p>"""
    results = f"""<h2>2. Gross event returns: the definition matters</h2><p>Entries are 19 March 2018–30 December 2022, following the existing delayed-entry rule at the second trading-session open after publication. Follow-up ends in 2023. Three/six/twelve months mean 63/126/252 trading sessions. Each event receives equal weight; these averages are not portfolio returns. Costs are included only in the portfolio section.</p>
{table(["Branch", "Horizon", "Russell calculable / focused scheduled", "Mean stock return", "Mean Russell excess (pp)", "SPY excess, same events (pp)", "Median Russell excess (pp)", "Issuer-bootstrap 95% range (pp)"], eventrows)}
<p>The six-month first-pair sample has 62 focused scheduled events: 7 lack a supported Russell assignment and 1 lacks a calculable stock return, leaving 54. Half of those 54 beat the assigned ETF. Its uncertainty range is {interval(primary)} points. The twelve-month range is {interval(twelve)} points. The earlier +17.71-point twelve-month result used a less restrictive event definition.</p>
<p>Benchmarks use prior-month-end historical constituent evidence: IWM for Russell 2000, IWR for Russell Midcap, and IWB for other Russell 1000 members. These are ETF proxies, not exact index returns. SPY remains the broad-market reference. Russell 3000/IWV is broad market, not a microcap bucket.</p>
<h2>3. Similar industry, size segment and entry year</h2>
<p>Each focused event is compared with non-focused filings in the same branch, horizon, two-digit SIC industry, assigned ETF and entry calendar year. Its own company is excluded. At least five distinct control companies are required. We average each control company's excess returns first, then equally weight those companies.</p>
{table(["Branch", "Horizon", "Matched / Russell focal events", "Focused Russell excess on matched sample (pp)", "Control Russell excess (pp)", "Focused minus controls (pp)", "Focal-issuer bootstrap range (pp)"], matchrows)}
<p>At six months, first-pair matching covers <strong>19 of 54</strong> Russell-calculable focused events (35.2%); the other 35 have fewer than five control companies. The matched focused sample averages +6.70 points versus Russell and controls −3.91 points, a +10.61-point difference. This does not convert the full-sample +0.28 points into +10.61: the compared sample is much smaller and different.</p>
<p>These are coarse retrospective comparisons, not causal estimates or tradable signals. Controls can occur later within the same year, have overlapping windows, and be reused across focal events. The displayed bootstrap resamples focal issuers only; it does not fully account for shared controls, estimation of control means or market-time dependence. None of the matched six-/twelve-month ranges rules out zero. Unmatched filers are not verified non-activists.</p>"""
    portfolios = f"""<h2>4. What happens to actual portfolio capital?</h2>
<p>The simulation runs 19 March 2018–29 December 2023. Each new focused signal targets 5% of prior-close NAV, with at most 20 issuers, no leverage and a 1% cap on strictly prior 20-session average dollar volume. Orders below 0.1% of starting capital are skipped. Entries are filled once; exits can take multiple days. Costs are 10 basis points plus 50 basis points × square root of order/ADV, plus $1 per execution. These are fixed assumptions, not measured execution costs.</p>
{table(["Branch", "Horizon", "Starting capital", "Status", "Buys", "Cumulative net return", "Annualized return", "Max drawdown", "Average cash weight"], portrows)}
<p><strong>Portfolio opportunity cost matters.</strong> First-pair six-month accounting at $100m returns +12.36% cumulatively, or 2.03% annualized, with 96.52% average cash. The twelve-month version returns +23.52% cumulatively, or 3.72% annualized, with 93.22% cash. Fully invested SPY returns {pct(context["SPY"]["total_return"])} and IWV {pct(context["IWV"]["total_return"])}; the cash proxy returns {pct(context["cash"]["total_return"])}. These benchmarks have different equity exposure, so their differences are not risk-adjusted alpha.</p>
<p><strong>The $100k six- and twelve-month tests are incomplete in both branches.</strong> Hill International (filing 0001446114-18-000023; stock ID 91355) is bought on 18 April 2018. On 14 August 2018 the raw vendor record reports no trading, missing price and missing total return. The engine stops at the last valid NAV, 13 August. It does not delete the trade after seeing the missing outcome, carry a stale mark, or report the short prefix as a full-period return. The $100m run skips this signal under pre-entry capacity/minimum-order rules; that is not evidence that larger capital performs better.</p>
<p>Across 36 base/sensitivity scenarios, 24 complete and 12 stop on that missing held return. The completed scenarios end with no open positions. Daily cash plus marked positions reconciles to NAV. The shared issuer schedule is formed across the full eligible universe before selecting focused signals, retaining the original signal convention; it can suppress a later focused signal even if an earlier non-focused event was not held.</p>
<details><summary>Costs, cash and turnover sensitivities</summary><p>All returns below are cumulative over the same full period. A dash means the scenario is incomplete. Zero cost keeps interest; zero interest keeps costs. Turnover is total buy plus sell notional divided by average NAV over the full period, not annualized.</p>
{table(["Branch", "Horizon", "Capital", "Base return", "Zero-cost return", "Zero-interest return", "Total costs", "Two-way turnover"], sensrows)}
<p>Cash accrues from cached <a href="https://fred.stlouisfed.org/series/DTB3">FRED DTB3</a> discount yields: at least two calendar days before the preceding trading session, no more than ten days stale at valuation, compounded across elapsed calendar days. The 91-day discount-price conversion is a proxy, not actual bill trading; the 2026 historical vintage is not a verified contemporaneous release archive. Dividends remain inside synthetic total-return positions, with no separate double credit. No taxes or management fees.</p></details>"""
    end = f"""<h2>5. Decision before fresh evaluation</h2><p>The data still support investigating investor identity, but the first-campaign six-month baseline is now close to flat. A stronger twelve-month descriptive result and a small matched subsample are insufficient to claim a repeatable edge.</p>
<p>Next resolve the held-security missing-return/valuation treatment from source evidence under a separately frozen rule, validate remaining entity-history and form ambiguities, and address selective benchmark/matching coverage. Then freeze the research and portfolio rules and establish an exposure-clean fresh sample before evaluation. Do not change the investor list based on these returns or promote the outcome-aware reviews into human labels.</p>
<details><summary>All HFR and other-filer six-month comparisons</summary><p>All, HFR-only, expanded and focused rows overlap. Only focused, other Event-Driven, other HFR, and other/unresolved form disjoint groups.</p>{table(["Branch", "Group", "Scheduled", "Russell calculable", "Mean excess (pp)", "Issuer-bootstrap range (pp)"], groups)}</details>
<details><summary>Evidence, limitations and reproduction</summary><p>All 75,631 parsed records were source-audited; 75,602 yielded a usable canonical primary text. This is the supplied parsed universe, not proof of all SEC filings. Source hashes, canonical text hashes and exact evidence spans are retained. Early v1/v2 classifier outputs are diagnostic history; v3 is the final eligibility input. An initial preparation attempt stopped at the end-date guard before price processing; rebuilt-inputs-v2 is the completed input run.</p>
<p>Historical HFR membership uses the existing quarter-lag proxy; actual publication availability is unverified, and supplemental identity selection is retrospective. Russell constituent extracts retain vendor reported-count discrepancies in all 58 snapshots; downloaded slices do not certify complete constituent coverage. No match is an unresolved benchmark, not proof a stock was outside the index.</p>
<p>Validation passed: 53 targeted tests; {q["event_returns_replayed"]:,} event returns replayed; {q["matched_arithmetic_checked"]} matched comparisons checked independently; {q["portfolio_scenarios_replayed"]} portfolio scenarios replayed exactly; {q["daily_cash_nav_checks"]:,} daily cash/NAV checks. These validate implementation against the stated rules, not historical entity completeness or an investment edge.</p>
<ul><li><a href="../20260924-universe-rebuild-v3/summary.json">Universe counts</a> · <a href="../20260924-universe-rebuild-v3/eligibility.jsonl">All eligibility records and evidence</a></li>
<li><a href="../20260924-rebuilt-inputs-v2/selection.json">New schedules and every exclusion</a> · <a href="../20260924-rebuilt-inputs-v2/coverage.json">Input coverage</a></li>
<li><a href="../20260924-rebuilt-analysis-v1/outcomes.json">Event returns</a> · <a href="../20260924-rebuilt-analysis-v1/matched-events.json">Matched control members</a> · <a href="../20260924-rebuilt-analysis-v1/summary.json">All group summaries</a></li>
<li><a href="../20260924-rebuilt-analysis-v1/portfolio-summary.json">Portfolio summaries</a> · <a href="../20260924-rebuilt-analysis-v1/portfolio-monthly.json">Monthly returns</a> · <a href="../20260924-rebuilt-analysis-v1/portfolios/first_observed-126-100000-base.json">Incomplete $100k ledger</a> · <a href="../20260924-rebuilt-analysis-v1/portfolios/first_observed-126-100000000-base.json">Complete $100m ledger</a></li>
<li><a href="../20260924-rebuilt-qa-v1/checks.json">Replay and accounting QA</a> · <a href="../20260924-rebuilt-analysis-v1/provenance.json">Code/input/output hashes</a> · <a href="../../../protocol/phase1-rebuild-v1.md">Frozen method</a></li></ul>
<p>Reproduce with prepare_rebuilt_development.py, run_rebuilt_analysis.py, verify_rebuilt_analysis.py and report_rebuilt_analysis.py under the project virtual environment with PYTHONPATH=src, PYTHONNOUSERSITE=1 and PYTHONIOENCODING=utf-8. Eligibility source audit and finalization are rebuild_initial_universe.py and finalize_initial_universe_v3.py. The 207 protected issuers and human packets are unchanged. No model or paid API was used.</p></details>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D rebuilt eligibility and portfolio results</title><style>body{margin:0;background:#f4f6f8;color:#243747;font:17px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:35px 24px 70px}h1{font-size:36px;line-height:1.2}h2{margin-top:42px;color:#164c6a}h3{margin-top:28px}.eyebrow{color:#5b6b77;font-size:14px}.lead{font-size:22px;background:#e5edf2;padding:25px;border-left:5px solid #176386}a{color:#155c99}table{width:100%;border-collapse:collapse;background:white;font-size:14px;line-height:1.45}th,td{text-align:left;padding:12px;border-bottom:1px solid #dce3e9;vertical-align:top}th{background:#e7edf1}td:nth-child(n+3){font-variant-numeric:tabular-nums}.scroll{overflow-x:auto;margin:22px 0}details{background:white;border:1px solid #dce3e9;border-radius:8px;padding:20px;margin:22px 0}summary{cursor:pointer;font-weight:650}li{margin:8px 0}@media(max-width:600px){main{padding:20px 14px}h1{font-size:28px}.lead{font-size:19px;padding:18px}table{min-width:750px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + intro
        + eligibility
        + results
        + portfolios
        + end
        + "</main></body></html>"
    )
    freeze(OUT / "index.html", page)
    note = """# Rebuilt initial-event baseline, matched comparisons and portfolio accounting

24 September 2026 — outcome-aware development research; no fresh evaluation.

The stricter first-observed manager–issuer definition substantially reduces the apparent edge. Focused candidates average **+0.28 percentage points versus Russell at six months** and **+7.08 points at twelve months**, with 54 calculable events at each horizon. The respective issuer-bootstrap ranges are −7.31 to +8.59 and −6.32 to +22.61 points. Six months remains primary.

Standalone initial forms give +5.70/+16.17 points at six/twelve months (64 events each). These can include ongoing campaigns. First observed means first in the supplied archive, not first ever or a validated economic campaign.

The full 75,631-record audit yields 58,166 amendments, 17,420 standalone candidates, and 45 unresolved filings. Standalone candidates split into 16,278 first observed pairs, 964 previously observed pairs and 178 with prior-history text. v3 is the final reconciliation; earlier versions are preserved diagnostic artifacts.

The six-month first-pair industry/year/size comparison covers only 19 of 54 calculable focused events. Their +6.70-point Russell excess compares with −3.91 points for controls, a +10.61-point difference. Twelve months gives +12.38 points versus controls. Both uncertainty ranges include zero; controls can be reused and the bootstrap does not fully capture shared-control or calendar dependence. These selective results cannot replace the full-sample estimate.

At $100m, first-pair six-month portfolio accounting gives +12.36% cumulative (2.03% annualized), holding 96.52% cash on average. Twelve months gives +23.52% cumulative (3.72% annualized), with 93.22% cash. Full-period SPY/IWV returns are +91.64%/+84.81%; the cash proxy returns +11.99%. Different equity exposures prevent interpreting these differences as alpha.

The $100k six-/twelve-month portfolios in both branches stop on 14 August 2018 because the held Hill International position has no usable vendor return or price. No complete return is claimed and the trade is not dropped using hindsight. Across 36 scenarios, 24 complete and 12 stop. Detailed trade, skip, daily NAV and monthly-return ledgers are retained.

[Open the full report](../runs/phase1-baseline/20260924-rebuild-report-v2/index.html).

Next resolve the held-security valuation source issue under a separately frozen rule, validate remaining entity/form ambiguity and selective benchmark coverage, then establish and freeze an exposure-clean fresh evaluation sample. Do not tune investor membership to the winners or use outcome-aware review notes as human labels. Human packets and 207 protected issuers remain unchanged.

Reproduction: final eligibility `20260924-universe-rebuild-v3`; inputs `20260924-rebuilt-inputs-v2`; results `20260924-rebuilt-analysis-v1`; QA `20260924-rebuilt-qa-v1`. All are under `research/runs/phase1-baseline/`. The v1 input preparation stopped at the end-date guard before price processing and produced no return result. Protocol: `research/protocol/phase1-rebuild-v1.md`.

Validation: 53 targeted tests; 12,107 event returns replayed; 123 matched comparisons independently checked; 36 portfolio replays; 36,204 daily cash/NAV reconciliations. Tests establish rule implementation, not a repeatable investment edge.
"""
    freeze(ROOT / "research/docs/PHASE1-REBUILT-RESULTS-20260924-v2.md", note)
    freeze(OUT / "report_rebuilt_analysis.py", Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={
                    str(x.relative_to(ROOT)): digest(x)
                    for x in [
                        AN / "summary.json",
                        AN / "outcomes.json",
                        AN / "matched-summary.json",
                        AN / "portfolio-summary.json",
                        AN / "portfolio-context.json",
                        QA / "checks.json",
                        EL / "summary.json",
                        IN / "selection.json",
                    ]
                },
                outputs={
                    "index.html": digest(OUT / "index.html"),
                    "report_rebuilt_analysis.py": digest(OUT / "report_rebuilt_analysis.py"),
                },
            )
        ),
    )


if __name__ == "__main__":
    main()
