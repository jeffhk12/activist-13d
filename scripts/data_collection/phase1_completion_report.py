"""Tier: 2. Integrate independent closeout evidence without claiming fresh results.
Inputs: agent receipts, unchanged analytical JSON, protected-asset checks and tests.
Outputs: plain-English HTML/Markdown and final completion-status manifest.
Identity: investigation completed does not imply valuation or evaluation completed.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_completion_report.py
"""

import html
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-completion-integration-v1"


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join("<th>" + html.escape(str(x)) + "</th>" for x in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(x)) + "</td>" for x in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def main():
    val = BASE / "20260924-valuation-resolution-v1"
    elig = BASE / "20260924-eligibility-closeout-v1"
    ready = BASE / "20260924-evaluation-readiness-v1"
    summary = json.loads((elig / "summary.json").read_text())
    capacity = json.loads((val / "capacity-attribution.json").read_text())[
        "first_observed-126-100000000-base"
    ]
    candidates = json.loads((ready / "summary.json").read_text())
    assert summary["unresolved_records"] == 45
    assert (
        candidates["plans"]["first_observed"]["126"]["counts"]["focused"] == 8
        if "counts" in candidates["plans"]["first_observed"]["126"]
        else candidates["plans"]["first_observed"]["126"]["focused"] == 8
    )
    # Roots of all links are frozen agent artifacts; code-cleanup receipts are supplementary.
    receipts = []
    for pattern in [
        "20260924-valuation-resolution-v*",
        "20260924-eligibility-closeout-v*",
        "20260924-evaluation-readiness-v*",
    ]:
        for folder in sorted(BASE.glob(pattern)):
            for p in sorted(folder.rglob("*")):
                if p.is_file() and p.suffix in {".json", ".md"}:
                    receipts.append(p)
    rows = [
        [
            "Valuation and portfolio",
            "Diagnosed Hill’s OTC interval; checked 12,107 schedules and replayed all 36 portfolios.",
            "Complete daily OTC prices, corporate actions and execution liquidity are still unavailable. Twelve portfolios remain incomplete.",
        ],
        [
            "Eligibility and identity",
            "Reviewed 45 unresolved records, a deterministic 35-filing sample and all 24 development text-history exclusions; quantified coverage.",
            "Text references can concern another issuer or a different form. Retained exclusions are conservative, unvalidated history-reference exclusions.",
        ],
        [
            "Evaluation readiness",
            "Built outcome-blind candidate selection, exposure inventory, draft strategy specification and executable gates.",
            "Only 8 focused first-pair six-month candidates survive conservative quarantine; historical exposure and required inputs remain unverified.",
        ],
    ]
    body = """<p class="eyebrow">24 September 2026 · Independent agent closeout · Development research</p>
<h1>Phase 1: what the fresh review established</h1>
<p class="lead">The three independent workstreams are complete, but <strong>Phase 1 is not ready for fresh confirmation</strong>. They sharpened the reasons: incomplete OTC valuation data, unresolved campaign-history attribution, selective comparison coverage, and a small later candidate sample whose exposure history is not fully documented.</p>
<p>The investment question remains whether buying after an identifiable investor’s initial 13D improves returns under executable rules. The prior development estimates remain unchanged: focused first-observed candidates average +0.28 percentage points above Russell ETFs at six months and +7.08 at twelve months, 54 calculable events each. Both uncertainty ranges include zero. These are gross event averages, not complete portfolio results or established alpha.</p>"""
    body += table(["Workstream", "Completed", "Still prevents completion"], rows)
    body += f"""<h2>What changed our understanding?</h2>
<p><strong>Missing data did not mean the stock stopped trading everywhere.</strong> Hill’s contemporaneous <a href="https://www.sec.gov/Archives/edgar/data/1287808/000110465918051640/a18-18281_38k.htm">8-K</a> described NYSE suspension and expected OTC Pink trading from 14 August 2018. <a href="https://www.crsp.org/wp-content/uploads/appendix/FlagType_CT.html">CRSP defines NT as Not Tracked</a>; <a href="https://www.crsp.org/wp-content/uploads/appendix/FlagType_TS.html">X means Unknown or Unavailable</a>. This corrects the earlier report’s “no trading” interpretation. It does not repair the missing daily marks.</p>
<p>The six-month scheduled sale was inside the OTC interval. A later exchange price or one endpoint quote cannot reconstruct daily NAV, sale liquidity or execution. The agent therefore retained the complete-return refusal and supplied clearly labeled hypothetical position-mark scenarios. Those scenarios are not observed returns or bounds on terminal strategy performance.</p>
<p><strong>Cash explains most of the large-account result.</strong> The $100m first-pair six-month strategy bought {capacity["buys"]} of {capacity["signals"]} signals. For {capacity["liquidity_cap_below_target_buys"]} purchases, the liquidity cap was below the target position size. Cash interest was ${capacity["cash_interest_dollars"] / 1e6:.3f}m out of ${capacity["nav_change_dollars"] / 1e6:.3f}m total NAV gain over 19 March 2018–29 December 2023. Changing sizing after seeing that result would define a different strategy; the fixed baseline is preserved.</p>
<p><strong>A prior-filing reference is not necessarily prior involvement in this company.</strong> Independent source checks found references to other issuers, incorporated powers of attorney and 13G-to-13D narrative transitions. All 24 development exclusions caused solely by text-history flags were inspected: the assistant’s evidence review judged 14 supportive of reporting history, eight non-supporting lexical matches, and two ambiguous. These are research interpretations, not validated labels. All remain excluded conservatively, with no accession-specific restoration. The operational “first-observed” branch is not a fully validated campaign census. These source interpretations are outcome-aware research notes, never human reference labels.</p>
<h2>Coverage is part of the investment conclusion</h2>
<p>Before looking at returns, Russell assignments exist for 709 of 1,981 first-pair six-month scheduled events (35.8%). Coverage is 55 of 62 focused events (88.7%), versus 639 of 1,892 other/unresolved events (33.8%). One assigned focused event later lacks a usable return, leaving the previously reported 54-event result. The benchmark sample is therefore selective; the omitted observations are not shown to be random.</p>
<p>Only 19 of 62 focused scheduled events have five potential control companies using the fixed industry/year/size rules; 13 of those 19 are in SIC 73. This is a narrow comparison subset, not a broad validation of activism.</p>
<p>The 45 unresolved filings comprise 18 intact raw files with missing retrieval sidecars, 11 missing raw submissions, and 16 conversion cases needing reporting-history adjudication. Intact text can support diagnosis; it does not restore missing retrieval provenance. Exact CIK overlap supports most prior-pair links, but candidate investor identities are still not automatically verified economic managers.</p>
<h2>What can be evaluated next?</h2>
<p>The outcome-blind later candidate schedule contains <strong>700 first-pair six-month events across 653 companies, including only 8 focused events</strong>. Actual screened entries span January 2024–December 2025; calendar maturity is assessed through 23 September 2026. Ten previously previewed companies needed separate exclusion from the 207 protected human-review issuers.</p>
<p>The conservative quarantine also excludes companies present in prior development selections. This changes the question toward new-to-development companies; it is more restrictive than a simple later-date split. The date-only comparator has 925 first-pair events and 12 focused events. Neither count is a performance result or proof that the remaining observations are untouched.</p>
<p>A metadata-only cache check found full-date CRSP requests and payload files for 172 of the 174 dates absent from the earlier feasibility inventory. Only 8 April and 17 December 2025 lack such requests in the scanned cache. This closes a misleading impression of widespread absent files, but does not certify valid security rows or usable marks. No return rows were opened for that check.</p>
<p>The prepared candidate protocol fixes six months as primary, three/twelve supporting, both event definitions, investor membership, accounting and inference conventions. It is a <strong>draft candidate specification</strong>, not the final production freeze. No new candidate future returns were opened. Historical temporal validation with explicit exposure limitations is distinct from prospective confirmation beginning after the actual final freeze.</p>
<h2>Exact remaining dependencies</h2>
<ol><li><strong>Valuation:</strong> obtain an auditable HILI/HIL daily OTC series for 14 August–17 October 2018 with boundary identity, distributions/adjustments and trading liquidity. Apply a documented general rule across all affected holdings, then rerun the development accounts.</li>
<li><strong>Eligibility:</strong> establish current-issuer/current-reporter attribution for history references under a tested rule, or explicitly freeze a narrower conservative exclusion-based estimand. A mechanical replay cannot establish semantic correctness.</li>
<li><strong>Evaluation inputs:</strong> prepare dated Russell membership and price/cash/volume inventories for the chosen cohort. Cached request presence is not valid row coverage, integrity or historical availability. See the readiness receipts for the bounded inventory findings.</li>
<li><strong>Evaluation boundary:</strong> complete the rule/sample freeze and choose explicitly between limited historical temporal validation and a prospectively registered cohort. The latter must accumulate future holding-period observations; it cannot be made mature today.</li></ol>
<p>No investor-list tuning, human-label changes, strategy-return revisions or fresh confirmation claims resulted from this review. The investor and human-review assets are checked against the 554-file before/after hash manifest.</p>
<h2>Handoffs and reproducible evidence</h2>
<ul><li><a href="../../../docs/PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md">Detailed team handoff: scope, sources, assignments and completion criteria</a></li>
<li><a href="../20260924-valuation-resolution-v1/phase1_valuation_report.md">Valuation investigation, source links, capacity attribution and scenarios</a></li>
<li><a href="../../../docs/phase1_eligibility_closeout_report_20260924.md">Eligibility source-review report</a> · <a href="../20260924-eligibility-closeout-v1/summary.json">Eligibility and coverage counts</a> · <a href="../20260924-eligibility-closeout-v1/development-history-contexts.json">All 24 development history contexts</a> · <a href="../20260924-eligibility-closeout-v1/unresolved-dispositions.json">45 unresolved-file dispositions</a></li>
<li><a href="../20260924-evaluation-readiness-v1/HANDOFF.md">Evaluation readiness handoff</a> · <a href="../../../protocol/phase1-evaluation-candidate-v1.md">Draft candidate protocol</a> · <a href="../20260924-evaluation-readiness-v1/gates.json">Readiness gates</a> · <a href="../20260924-evaluation-readiness-v1/receipts/cache-metadata-supplement.json">Cache-metadata check</a></li>
<li><a href="../20260924-rebuild-report-v2/index.html">Preserved development return report</a> · <a href="protected-assets.json">Protected-asset hashes</a> · <a href="final-status.json">Integrated status and validation receipt</a></li></ul>
<p>Fresh agents began from the written handoff without inheriting the earlier conversation. Root reviewed their findings, independently checked source definitions and reran the non-network tests. Passing tests validates calculations and preservation; it does not supply the missing market history or certify an untouched sample.</p>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 1 independent closeout</title><style>body{margin:0;background:#f4f6f8;color:#243747;font:17px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:36px 24px 70px}h1{font-size:36px;line-height:1.2}h2{margin-top:38px;color:#164c6a}.eyebrow{font-size:14px;color:#5b6b77}.lead{font-size:22px;background:#e5edf2;padding:24px;border-left:5px solid #176386}table{width:100%;border-collapse:collapse;background:white;font-size:15px}td,th{text-align:left;vertical-align:top;padding:14px;border-bottom:1px solid #dce3e9}th{background:#e7edf1}a{color:#155c99}li{margin:12px 0}.scroll{overflow-x:auto}@media(max-width:650px){h1{font-size:28px}table{min-width:700px}.lead{font-size:19px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + body
        + "</main></body></html>"
    )
    freeze(OUT / "index.html", page)
    freeze(OUT / "phase1_completion_report.py", Path(__file__).read_bytes())
    guardlog = Path("/tmp/phase1-completion-protected.log").read_text()
    assert "Verified unchanged protected assets: 554" in guardlog
    freeze(OUT / "protected-verification.txt", guardlog)
    testlog = Path("/tmp/phase1-completion-final-tests.log").read_text()
    freeze(OUT / "final-tests.txt", testlog)
    status = dict(
        status="independent_closeout_complete_phase1_confirmation_not_ready",
        phase1_complete=False,
        fresh_outcomes_opened=False,
        investor_membership_changed=False,
        human_labels_changed=False,
        development_return_estimates_changed=False,
        remaining=[
            "OTC daily valuation and execution evidence",
            "current-issuer history attribution or explicit conservative estimand",
            "candidate benchmark/price/cash input validation",
            "final rule/sample/exposure freeze and mature confirmation data",
        ],
        validation_log="final-tests.txt",
        protected_asset_count=554,
        inputs={
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                val / "capacity-attribution.json",
                elig / "summary.json",
                ready / "summary.json",
                OUT / "protected-assets.json",
                *receipts,
            ]
        },
        outputs={
            "index.html": digest(OUT / "index.html"),
            "phase1_completion_report.py": digest(OUT / "phase1_completion_report.py"),
            "final-tests.txt": digest(OUT / "final-tests.txt"),
        },
    )
    freeze(OUT / "final-status.json", encode(status))


if __name__ == "__main__":
    main()
