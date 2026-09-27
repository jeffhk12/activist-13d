"""Tier: 2. Publish the final Phase 1 synthesis without changing research outcomes.
Inputs: frozen short/long-horizon summaries and documented acquisition source.
Outputs: final HTML/Markdown conclusion, evidence manifest and source note.
Identity: a positive event mean does not establish complete account performance.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/write_phase1_final_conclusion.py
"""

import html
import json
import re
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-phase1-final-conclusion-v1"
DOC = ROOT / "research/docs/PHASE1-FINAL-CONCLUSION-20260924.md"
SEC = "https://www.sec.gov/Archives/edgar/data/1739104/000110465919040878/a19-12937_28k.htm"


def inline(text):
    result = html.escape(text)
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', result)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", result)


def main():
    paths = [
        BASE / "20260924-long-horizon-analysis-v1/summary.json",
        BASE / "20260924-long-horizon-analysis-v1/matched-summary.json",
        BASE / "20260924-long-horizon-analysis-v1/portfolio-summary.json",
        BASE / "20260924-historical-validation-v2/summary.json",
        BASE / "20260924-historical-validation-v2/portfolio-summary.json",
        BASE / "20260924-long-horizon-diagnostics-v1/diagnostics.json",
    ]
    long, match, portfolio, short, shortp, diagnostic = [json.loads(p.read_text()) for p in paths]
    assert long["first_observed"]["504"]["russell"]["focused"]["calculated"] == 56
    assert short["first_observed"]["126"]["russell"]["focused"]["calculated"] == 5
    assert match["first_observed"]["504"]["comparison"]["calculated"] == 17
    assert sum(v["status"] == "complete" for v in portfolio.values()) == 30
    assert portfolio["first_observed-504-100000-base"]["total_return"] is None
    assert shortp["first_observed-126-100000-base"]["status"] == "complete"
    blocks = []

    def add(kind, content):
        blocks.append((kind, content))

    add("h1", "Phase 1 final conclusion: initial 13D following")
    add(
        "p", "24 September 2026 · Historical baseline conclusion · Portfolio exceptions remain open"
    )
    add(
        "lead",
        "**Phase 1 does not establish a reliable, investable edge from mechanically following initial 13D disclosures, even when we restrict the strategy to the current focused activist candidates.** Longer holding periods produce more favorable average cumulative returns, but the typical event, matched comparisons and portfolio evidence do not consistently support that result.",
    )
    add("h2", "The investment question")
    add(
        "p",
        "Can an investor improve returns by buying after an initial 13D becomes public, particularly when the filer can be linked to a hedge fund or focused activist candidate? Phase 1 tests that simple rule. It does not predict which campaigns succeed, interpret intentions with NLP, or adjust positions using later amendments.",
    )
    add("h2", "What we completed")
    add(
        "p",
        "We built a reproducible historical baseline covering filing eligibility, candidate investor matching, historical security links, benchmark-relative event returns and funded portfolio accounting. We distinguished standalone initial forms from first observed manager–company pairs, resolved affirmative amendment evidence conservatively, and retained uncertain history references. First observed is relative to our archive, not proof of a first-ever campaign; manager links remain candidates rather than universally validated identities.",
    )
    add(
        "p",
        "The analysis includes the broader HFR manager universe and the fixed focused subset, historical Russell size-segment ETF proxies, SPY context, industry/year/size controls, and modeled trading costs, liquidity limits and cash interest. Initial short-horizon work was followed by a 2024–2025 historical test and a broader 2018–2025 exploratory revision with 24 months primary and 12, 18 and 36 months supporting. Earlier results and protocols remain preserved.",
    )
    add("h2", "The evidence")
    headers = ["Test", "Sample and result", "Investment interpretation"]
    rows = [
        [
            "Later historical test: six months",
            "2024–2025; 5 focused benchmark-matched events; −6.18 percentage points versus Russell",
            "The shorter-horizon development pattern did not replicate in this small later sample.",
        ],
        [
            "Longer-horizon revision: 24 months",
            "2018–2025 research window; 56 focused events; +8.66 points mean Russell excess",
            "A favorable average, with a 95% interval of −17.34 to +40.43 points.",
        ],
        [
            "Typical two-year event",
            "Median excess −14.91 points; 41.1% beat Russell",
            "The positive mean does not describe the typical investment.",
        ],
        [
            "Longer-horizon revision: 36 months",
            "50 focused events; +20.83 points mean Russell excess",
            "More favorable cumulative mean, but median excess remains negative and the interval includes underperformance.",
        ],
        [
            "Two-year industry/year/size comparison",
            "17 matched focused events; −8.08 points versus controls",
            "The broader positive mean does not carry through to this smaller matched comparison.",
        ],
        [
            "Later-period funded account",
            "Six-month holding rule; $100k account returned 8.73% over 2024–2025 versus 9.72% cash-only",
            "Five purchases at 5% targets left 94.22% average cash. Cash interest explains most of the gain.",
        ],
        [
            "Longer-horizon funded accounts",
            "30 of 48 scenarios complete; primary $100k 18/24/36-month accounts incomplete",
            "No full-period primary long-horizon account return can be claimed.",
        ],
    ]
    add("table", (headers, rows))
    add(
        "p",
        "These samples overlap and differ in dates and eligibility; their counts must not be added or treated as one experiment. Event figures are gross, equally weighted stock-minus-benchmark cumulative returns. Portfolio figures include modeled costs and cash over the whole account window. Neither measure is automatically risk-adjusted alpha.",
    )
    add(
        "p",
        "On the same 50 focused events calculable at all four long horizons, mean cumulative Russell excess is +7.13, +8.97, +18.24 and +20.83 points at 12, 18, 24 and 36 months. This supports further investigation of a longer-term thesis, but the common-data subset is a diagnostic rather than a selection rule available in real time. Annualizing each event separately also gives a more cautious result: the two-year mean stock/ETF annualized returns are 4.95%/8.38%. Those averages are different from annualizing a mean cumulative return or measuring a funded account CAGR.",
    )
    add("h2", "What limits the conclusion")
    add(
        "list",
        [
            "**Selective coverage:** the two-year first-pair schedule has 2,107 events, but only 694 calculable common benchmark observations. The focused subset has 56 calculable of 67 scheduled events. Results may not generalize to the unmatched or unresolved observations.",
            "**Uncertainty and unequal outcomes:** positive means coexist with negative medians and wide intervals. We have not established a repeatable selection advantage.",
            "**Incomplete independence:** the long-horizon expansion was requested after shorter-horizon results were examined and reuses previously studied companies. It is exploratory, not untouched confirmation.",
            "**Accounting exceptions:** unresolved settlement evidence prevents a complete primary long-horizon portfolio result. Completed larger-capital scenarios cannot substitute for that missing primary result.",
            "**Implementation assumptions:** delayed opening-price entries, 5% targets, capacity limits, modeled friction, monthly benchmark membership and a cash proxy are research conventions, not guaranteed execution or verified historical cash-trading returns.",
        ],
    )
    add("h2", "Does delisting mean we exit?")
    add(
        "p",
        "**Delisting is a corporate-action event, not a guaranteed sale at the last quoted price.** A cash acquisition can replace the shares with cash proceeds; a share exchange can leave us holding another security. Some delisted stocks may continue trading elsewhere. An automatic-exit strategy would need an explicit, observable trigger and an executable sale convention; it cannot assume that a past final quote was available after the delisting became known. [Investor.gov merger explanation](https://www.investor.gov/introduction-investing/investing-basics/glossary/mergers) · [Investor.gov on possible OTC trading after delisting](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/reverse).",
    )
    add(
        "p",
        f"For Aratana, Elanco’s July 18, 2019 filing documents an exchange of each eligible Aratana share for **0.1481 Elanco shares plus one contingent value right**, with cash for fractional shares. The contingent right was not guaranteed immediate cash. [Elanco acquisition-completion 8-K]({SEC}).",
    )
    add(
        "p",
        "For our model, the original position must be reconciled to the securities and rights actually received, followed by a supported valuation and holding or liquidation rule. The cached Aratana delisting return carries a missing-value flag and is refused by our current validator. The merger terms clarify the event, but they do not by themselves complete share conversion, fractional-share, execution and contingent-right accounting. No proceeds have been invented and Aratana has not been removed from the sample.",
    )
    add("h2", "Final Phase 1 assessment")
    add(
        "lead",
        "**The historical baseline is established; an investable edge is not.** Phase 1 supports continuing the research into which investor, company and disclosure characteristics distinguish better opportunities. It does not support claiming that identifying a focused activist and holding for a fixed period is sufficient to generate reliable alpha.",
    )
    add(
        "p",
        "We can conclude the historical research phase with these qualifications recorded. This is a final synthesis of the evidence available today, not certification that every portfolio calculation is complete. The Aratana settlement remains an explicit open accounting exception. Future source-backed resolution should be published as a separate addendum, preserving these results.",
    )
    add("h2", "What comes next")
    add(
        "list",
        [
            "**Accounting addendum:** establish a general, source-supported treatment for replacement shares and contingent rights, resolve Aratana if possible, and rerun affected portfolios without excluding inconvenient observations.",
            "**Structured-data ML:** test whether information available at disclosure—investor identity/type, company characteristics, stake information and correctly attributed prior involvement—improves selection beyond this baseline. Model development must not recycle this examined sample as an untouched final test.",
            "**Incremental NLP:** test whether stated intentions and correctly attributed historical references add value beyond structured data. Company B references remain leads until evidence supports a position; assistant reviews are not human labels.",
            "**Amendment-driven position management:** evaluate separately whether publicly disclosed stake increases, reductions or changed intentions should trigger trades. This is a strategy extension, not unfinished work in the original fixed-holding baseline.",
            "**Prospective validation:** register the final rules and collection period before new signals arrive. No prospective collection has started. Investor lists must not be tuned to historical winners.",
        ],
    )
    add("h2", "Evidence and preserved records")
    add(
        "p",
        f"[Long-horizon report]({BASE / '20260924-long-horizon-report-v1/index.html'}) · [Later historical report]({BASE / '20260924-historical-validation-report-v1/index.html'}) · [Long-horizon continuation handoff]({ROOT / 'research/docs/PHASE1-LONG-HORIZON-RESULTS-20260924.md'}) · [Frozen long-horizon protocol]({ROOT / 'research/protocol/phase1-long-horizon-v1.md'}).",
    )
    add(
        "p",
        "This conclusion changes no returns, portfolio rules, investor lists or human reference labels. Hill remains the earlier user-selected retrospective exclusion. Historical code and outputs retain their source and calculation receipts. The conclusion is a synthesis; it does not initiate ML, NLP, trading, new issuer exclusions or a new exit policy.",
    )
    markdown = []
    rendered = []
    for kind, content in blocks:
        if kind in {"h1", "h2"}:
            markdown.append(("# " if kind == "h1" else "## ") + content)
            rendered.append(f"<{kind}>{inline(content)}</{kind}>")
        elif kind in {"p", "lead"}:
            markdown.append(content)
            rendered.append(
                "<p" + (' class="lead"' if kind == "lead" else "") + ">" + inline(content) + "</p>"
            )
        elif kind == "list":
            markdown.append("\n".join("- " + v for v in content))
            rendered.append(
                "<ul>" + "".join("<li>" + inline(v) + "</li>" for v in content) + "</ul>"
            )
        else:
            heads, values = content
            markdown.append(
                "| "
                + " | ".join(heads)
                + " |\n| "
                + " | ".join(["---"] * len(heads))
                + " |\n"
                + "\n".join("| " + " | ".join(row) + " |" for row in values)
            )
            rendered.append(
                '<div class="scroll"><table><thead><tr>'
                + "".join("<th>" + inline(v) + "</th>" for v in heads)
                + "</tr></thead><tbody>"
                + "".join(
                    "<tr>" + "".join("<td>" + inline(v) + "</td>" for v in row) + "</tr>"
                    for row in values
                )
                + "</tbody></table></div>"
            )
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D — final Phase 1 conclusion</title><style>body{margin:0;background:#f4f6f8;color:#203448;font:17px/1.65 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:32px 24px 70px}h1{font-size:38px;line-height:1.2}h2{font-size:25px;margin-top:36px}.lead{background:#e5edf2;border-left:5px solid #176386;padding:24px;font-size:21px}a{color:#155c99}.scroll{overflow:auto}table{width:100%;background:white;border-collapse:collapse;font-size:15px}th,td{padding:13px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}th{background:#e5ebf0}li{margin:12px 0}@media(max-width:650px){h1{font-size:30px}main{padding:20px 16px}.lead{font-size:19px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + "".join(rendered)
        + "</main></body></html>"
    )
    freeze(DOC, "\n\n".join(markdown) + "\n")
    freeze(OUT / "index.html", page)
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "external-source-note.json",
        encode(
            {
                "accessed_date": "2026-09-24",
                "source_url": SEC,
                "accession": "0001104659-19-040878",
                "section": "Item 8.01",
                "source_fact": "Merger completed 2019-07-18; 0.1481 Elanco shares and one contingent value right per eligible Aratana share, cash for fractional shares.",
                "accounting_status": "Terms identified, no valuation or liquidation assumption implemented; original refusal preserved.",
            }
        ),
    )
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                "outputs": {
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [
                        DOC,
                        OUT / "index.html",
                        OUT / Path(__file__).name,
                        OUT / "external-source-note.json",
                    ]
                },
                "research_returns_changed": False,
            }
        ),
    )
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
