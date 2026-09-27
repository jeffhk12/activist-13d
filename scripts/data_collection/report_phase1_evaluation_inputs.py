"""Tier: 2. Explain later-period input readiness without evaluating investments.
Inputs: frozen preparation, QA, ETF and date-scope receipts. Outputs: HTML/handoff.
Identity: coverage counts describe available inputs, never investment performance.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_phase1_evaluation_inputs.py
"""

import html
import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-evaluation-inputs-report-v1"
DOC = ROOT / "research/docs/PHASE1-EVALUATION-INPUTS-HANDOFF-20260924.md"
INPUTS = {
    "prep": BASE / "20260924-evaluation-inputs-v2/summary.json",
    "qa": BASE / "20260924-evaluation-inputs-qa-v1/summary.json",
    "etf": BASE / "20260924-evaluation-inputs-etf-v1/identity-coverage.json",
    "scope": BASE / "20260924-evaluation-calendar-support-v1/summary.json",
    "replay": BASE / "20260924-evaluation-inputs-replay-v1/receipt.json",
}


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
    data = {k: json.loads(p.read_text()) for k, p in INPUTS.items()}
    prep, qa, scope = data["prep"], data["qa"], data["scope"]
    assert not prep["performance_calculated"] and not prep["overall_evaluation_ready"]
    assert not scope["changes_original_sample"]
    assert qa["selection_equal_to_frozen_candidate_excluding_hill"]
    assert all(e["covered_sessions"] == 502 for e in data["etf"])
    p = prep["branches"]["first_observed"]["126"]
    q = qa["branches"]["first_observed"]["126"]
    s = scope["counts"]["first_observed"]["126"]
    assert p["scheduled"] == q["scheduled"] == s["original_scheduled"] == 700
    assert (
        q["all_keys_present"] + q["with_empty_market_dates"] + q["with_post_delisting_absences"]
        == 700
    )
    rows = []
    for branch in ["first_observed", "standalone"]:
        for horizon, label in [
            ("126", "6 months · primary"),
            ("63", "3 months"),
            ("252", "12 months"),
        ]:
            a = prep["branches"][branch][horizon]
            rows.append(
                [
                    "First observed pair"
                    if branch == "first_observed"
                    else "Standalone initial form",
                    label,
                    a["scheduled"],
                    a["focused"],
                    a["benchmark_assigned"],
                    f"{a['focused_benchmark_assigned']} / {a['focused']}",
                    a["all_requested_stock_keys_present"],
                    a["lagged_liquidity_available"],
                ]
            )
    findings = [
        [
            "Market-data cutoff",
            f"{qa['last_nonempty_date']}; {qa['empty_source_dates']} empty 2026 trading dates",
            "The planned account through 23 September 2026 cannot yet be evaluated from this extract.",
        ],
        [
            "Primary candidate schedule",
            f"{p['scheduled']} first-observed events, including {p['focused']} focused events",
            "The focused subset is small. An event is a scheduled filing opportunity, not a unique manager or validated campaign.",
        ],
        [
            "Russell benchmark assignments",
            f"{p['benchmark_assigned']} / {p['scheduled']} overall; {p['focused_benchmark_assigned']} / {p['focused']} focused",
            "Matching covers the focused group much better than the comparison universe; a matched-sample result may not generalize.",
        ],
        [
            "Stock records",
            f"{q['all_keys_present']} / 700 have every requested daily key; 187 encounter empty-market dates; 40 have post-delisting absences",
            "A record’s presence does not prove a valid return. Delisting settlement still needs validation.",
        ],
        [
            "Trading capacity inputs",
            f"{p['lagged_liquidity_available']} / 700 have the required prior 20-session liquidity history",
            "We can prepare the participation limit for these events; this does not guarantee trade execution.",
        ],
        [
            "Cash and benchmark identities",
            "Cash observations available for 684 / 684 sessions; each of five ETF identities covers 502 / 684",
            "Cash inputs are ready. ETF identity records also stop at year-end 2025.",
        ],
    ]
    body = f"""<p class="eyebrow">24 September 2026 · Phase 1, item 3 · Data preparation</p>
<h1>Can we test the strategy on a later period?</h1>
<p class="lead"><strong>The inputs are prepared, but the full planned evaluation is not ready.</strong> The available market-data extract ends on 31 December 2025. No new investment returns were calculated.</p>
<p>Our investment question remains whether buying after an initial 13D disclosure improves returns, especially when we can identify the investor. Six months is primary; three and twelve months support it. This step checks whether we have the stock, benchmark, liquidity and cash inputs to test that question outside the development period.</p>
<h2>What we found—and what it means</h2>{table(["Check", "What we found", "Investment meaning"], findings)}
<p>We recovered the missing 8 April and 17 December 2025 market-data downloads, prepared 25 historical Russell membership snapshots, and refreshed the cash-rate source. The 182 requested 2026 market dates still contain no records. This finding describes this extract; it does not establish that other sources lack those dates.</p>
<h2>Coverage across the fixed schedules</h2>
<p>Entries are in 2024–2025, with planned maturity assessed through 23 September 2026. The two branches and three horizons overlap and must not be added together. Coverage columns are parallel checks, not successive sample reductions. No event was removed or replaced because of these checks.</p>
{table(["Branch", "Holding period", "Scheduled events", "Focused events", "Russell assigned", "Focused Russell assigned", "All stock keys present", "Prior liquidity available"], rows)}
<p>“Standalone initial form” describes the filing itself. “First observed pair” means the manager–issuer relationship is first observed under the archive’s conservative rules; it does not prove the investor’s first-ever involvement. Historical Russell assignments use the preceding calendar month-end: IWR for Midcap, IWB for other Russell 1000 members, and IWM for Russell 2000. IWV and SPY provide broad-market context. These are ETF proxies, not direct index returns.</p>
<h2>A narrower historical option, not yet activated</h2>
<p>If we required planned exits by 31 December 2025, the six-month first-observed schedule would shrink from <strong>{s["original_scheduled"]} to {s["calendar_supported"]} events</strong>. It would include <strong>{s["focused"]} focused events, of which {s["focused_benchmark_assigned"]} have Russell assignments</strong>; overall, {s["benchmark_assigned"]} of {s["calendar_supported"]} have assignments. This count uses dates alone, not investment outcomes. It does not establish that all remaining returns are usable or that the sample is untouched.</p>
<p>With only five benchmark-matched focused opportunities under that alternative, the result would be a limited additional check of the hypothesis. We have preserved the original schedule and documented the alternative separately.</p>
<h2>What still prevents confirmation</h2>
<ul><li><strong>Data coverage:</strong> obtain later market and ETF identity coverage for the full scope, or explicitly freeze a narrower historical endpoint before outcomes are inspected.</li>
<li><strong>Return and settlement validity:</strong> future numerical prices, total-return chains and delisting settlements remain unchecked. A delisting flag alone does not establish sale proceeds.</li>
<li><strong>Selective matching:</strong> only 191 of 700 primary events have assigned Russell benchmarks. Missing matches are not evidence of poor investments or passive investors.</li>
<li><strong>Source limitations:</strong> reported vendor counts disagree with returned records for all 705 daily requests and all 25 membership requests. Hash, date and identifier checks pass; vendor-universe completeness is not certified.</li>
<li><strong>Research design:</strong> finalize strategy rules, scope and an exposure record. Prior screens and incomplete exposure history prevent calling this later cohort a certified untouched sample.</li></ul>
<h2>Next: freeze the evaluation design</h2>
<p>Carry forward the fixed investor list, six-month primary period and conservative history interpretation. Keep Hill excluded from the user-selected branch. Use NLP later to attribute references to the correct company: a Company B reference can be a research lead without proving a position in B or earlier involvement in Company A. Outcome-aware reviews remain separate from human labels.</p>
<p>The next deliverable is the final rule, sample and exposure decision record. Only after the applicable gates are satisfied should we calculate later-period industry/time-matched comparisons and portfolio returns. The earlier development work remains exploratory evidence of a possible signal, not a demonstrated repeatable edge.</p>
<details><summary>Supporting methods, evidence and reproducibility</summary>
<p>Automated checks examined source hashes, dates, security identifiers and delisting flags. Numerical price/volume processing was restricted to pre-entry liquidity windows. No future numerical price or return values were inspected or reported. Cash uses lagged observations from <a href="https://fred.stlouisfed.org/series/DTB3">FRED DTB3</a>; historical revisions are not certified contemporary releases.</p>
<p>Independent verification replayed {qa["daily_sources_replayed"]} daily sources and {qa["required_daily_key_checks"]:,} required stock/date keys. All 180 non-network tests pass (one network test deselected); 554 protected investor and human-review assets are unchanged. The v2 cache-replay repair preserves the original acquisition receipt: all {data["replay"]["analytical_json_count"]} analytical JSON files are byte-identical to v1. Thirty new membership/ETF raw-source hashes were independently checked.</p>
<ul><li><a href="../../../docs/{DOC.name}">Detailed continuation handoff</a> · <a href="../../../protocol/phase1-evaluation-inputs-v1.md">Frozen preparation protocol</a></li>
<li><a href="../20260924-evaluation-inputs-v2/summary.json">Preparation summary</a> · <a href="../20260924-evaluation-inputs-v2/requirements.json">Fixed requirements</a> · <a href="../20260924-evaluation-inputs-v2/assignments.json">Historical benchmark and liquidity assignments</a></li>
<li><a href="../20260924-evaluation-inputs-v2/daily-acquisition.json">Acquisition history</a> · <a href="../20260924-evaluation-inputs-v2/cash-readiness.json">Cash availability</a> · <a href="../20260924-evaluation-inputs-etf-v1/identity-coverage.json">ETF identity supplement</a></li>
<li><a href="../20260924-evaluation-inputs-qa-v1/summary.json">Independent coverage QA</a> · <a href="../20260924-evaluation-calendar-support-v1/summary.json">Unactivated date-only alternative</a> · <a href="../20260924-evaluation-inputs-replay-v1/receipt.json">Replay receipt</a></li>
<li><a href="../20260924-skip-hill-report-v1/index.html">Preserved development performance</a> · <a href="provenance.json">Report provenance</a></li></ul></details>"""
    page = (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D — later-period input readiness</title><style>body{margin:0;background:#f4f6f8;color:#203448;font:17px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:32px 24px 70px}h1{font-size:38px;line-height:1.2;max-width:850px}h2{margin-top:36px;font-size:25px}.eyebrow{font-size:14px;color:#526575}.lead{background:#e5edf2;border-left:5px solid #176386;padding:22px;font-size:22px}a{color:#155c99}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;background:white;font-size:15px}td,th{padding:13px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}th{background:#e5ebf0}li{margin:10px 0}details{background:white;border:1px solid #dce3e9;padding:20px;margin-top:30px}summary{cursor:pointer;font-weight:650}@media(max-width:650px){main{padding:20px 16px}h1{font-size:30px}.lead{font-size:19px}}</style></head><body><main><a href="../../../../START-HERE.html">← Project home</a>"""
        + body
        + "</main></body></html>"
    )
    handoff = f"""# Phase 1 item 3 — evaluation-input handoff

24 September 2026. Status: input preparation completed; full evaluation NOT READY.

## Investment meaning

We are preparing a later-period test of simple following after an initial 13D. The extract ends on 31 December 2025, while the requested account ends on 23 September 2026. All 182 requested 2026 market sessions are empty. No new performance result exists. Six months remains primary; three and twelve months supporting. Investor membership and human labels are unchanged.

[Open the report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-evaluation-inputs-report-v1/index.html).
Absolute project: `/Users/jefflu/Projects/activist-13d`.

## Decisions to preserve

- Hill International (issuer 0001287808) stays excluded in the user-selected branch. Preserve original full-universe refusals and the retrospective exclusion history; do not resume the OTC search.
- User deferred nuanced cross-company history attribution to future NLP. A prior reference to Company B does not establish prior Company A involvement. Keep B as a research lead; do not assert a B position without sufficient evidence. Existing conservative history-reference exclusions remain until a separately specified, validated change. Do not promote assistant interpretations into human labels.
- First observed manager–issuer pairs are archive-relative mechanical candidates, not proven first-ever campaigns. Preserve standalone initial-form and first-observed branches separately.
- Do not tune the investor list to winners, drop missing-price events opportunistically, or call the later cohort untouched without an exposure audit. No ML/NLP training occurred.

## Completed work and limits

The immutable protocol is `research/protocol/phase1-evaluation-inputs-v1.md`. Fixed candidate requirements were saved before input checks. Unique entry specifications: 758; required daily sources: 705, including 684 account sessions and historical/pre-entry inputs. Two known 2025 holes (8 April and 17 December) were acquired; nonempty repair slices passed partition equality. Twenty-five month-end Russell snapshots were acquired. Refreshed cash data pass lag/staleness availability for 684/684 sessions. Each of SPY/IWB/IWM/IWR/IWV has dated identity coverage for 502/684 sessions, ending 2025-12-31.

Primary first-observed schedule: 700 events, including 8 focused. Russell assignments: 191/700 overall and 7/8 focused. All requested stock keys: 473/700; empty-market dates affect 187; post-delisting absences affect 40. No unexplained missing security keys remain under that status partition, but delisting settlement and numerical return validity remain unchecked. Prior 20-session liquidity inputs: 556/700. These are parallel coverage checks, not a sequential funnel.

All 705 daily requests and 25 membership requests retain vendor count discrepancies. Verified source bytes/date/unique keys do not certify vendor completeness. Monthly membership and revised cash histories do not prove contemporaneous publication timing. Future numeric prices, returns, signs, NAV and settlement amounts were not inspected or calculated. Only strictly pre-entry prices/volumes were used to prepare liquidity; automated later-window inspection used keys and delisting status.

## Unactivated calendar alternative

A planned-exit cutoff of 2025-12-31 gives 503 primary first-observed events, including 6 focused and 5 focused Russell assignments (138 overall). Twelve months gives 312 events, 4 focused, 3 focused assignments. Three months gives 612, 7 and 6 respectively. This is date-only feasibility; it does not change the original sample, guarantee valid returns or certify freshness. Five primary focused benchmark matches would support only a limited hypothesis check.

## Exact continuation order

1. Prepare the final rule/sample/exposure decision record (item 4). Reconcile the desired 2026 endpoint with demonstrated 2025 data coverage. Keep the original scope and calendar-only alternative separate until an explicit design decision is frozen; do not automatically activate the narrower sample.
2. For the full scope, obtain source coverage beyond 2025 with ETF identity support. For a narrower historical scope, freeze the endpoint and calendar eligibility before outcome access. Preserve all unmatched/uncalculable cases and denominators.
3. Complete the exposure audit and state what is known versus unprovable across prior chats/machines/previews. The later cohort is not certified untouched. A genuinely prospective cohort starts after the final freeze and must mature.
4. After final outcome-access gates, validate numerical total-return chains, marks, exit execution and delisting settlements under unchanged refusal rules. Row presence alone cannot authorize a portfolio result.
5. Then run the frozen later-period event/industry-time matched comparisons and portfolio accounting, with Russell ETF and SPY on the same common sample, costs, cash, capacity and uncertainty. Report excluded/unresolved observations separately. No winner-driven changes or human-label contamination.

## Run map

All names below are under `research/runs/phase1-baseline/`:

- `20260924-evaluation-inputs-v1/`: original acquisition history, requirements, source inventory, assignment and coverage files, frozen code/provenance.
- `20260924-evaluation-inputs-v2/`: current cache replay; all 10 analytical JSON files exactly match v1. Only receipt bookkeeping changed so original acquisition records survive warm-cache runs. Do not edit v1 to fix its rerun refusal.
- `20260924-evaluation-inputs-etf-v1/`: refreshed ETF identity source supplement. The base summary’s empty full-scope identity list means no 2026-wide coverage; this supplement establishes partial coverage through 2025.
- `20260924-evaluation-inputs-qa-v1/`: independent raw key/status replay, absence diagnostics, calendar cutoff.
- `20260924-evaluation-calendar-support-v1/`: unactivated date-only alternative and candidate metadata.
- `20260924-evaluation-inputs-replay-v1/`: v1/v2 parity, source hash checks and shared dependency snapshots.
- `20260924-evaluation-inputs-report-v1/`: this report, frozen generator and provenance.

New raw cache: `data/raw/wrds/evaluation-inputs-20260924-v1/`; official refreshed cash bytes: `data/raw/public-series/evaluation-inputs-20260924-v1/`. Old raw evidence remains unchanged. Existing raw pages may contain outcome fields; do not print/decode them into model-facing output when doing coverage work.

## Reproduction and verification

Use project `.venv/bin/python`, `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`, from the project root. Main scripts are under `scripts/data_collection/`:

- `prepare_phase1_evaluation_inputs_v2.py` — repeated preparation using the existing cache; v1 preserved original acquisition history.
- `verify_evaluation_etf_identities.py` — ETF supplement, cached responses.
- `verify_phase1_evaluation_inputs.py` — independent key/status/source checks.
- `describe_evaluation_calendar_support.py` — date-only counts, no activation.
- `verify_evaluation_input_replay.py` — source/output parity and dependency snapshot receipt.
- `report_phase1_evaluation_inputs.py` — report and handoff.
- `phase1_completion_guard.py` — verifies 554 protected assets unchanged.

Tests: `tests/test_evaluation_input_checks.py` pins pre-entry liquidity by hand, refuses missing/bad input, and proves key checks ignore changes to future numeric values. Full non-network suite: 180 passed, 1 deselected. QA independently replayed 705 daily sources and 184,522 requested keys; 30 membership/ETF raw hashes verified. Ten analytical JSONs reproduce byte-for-byte between v1/v2. Report generator asserts denominators/coverage contracts and supports identical reruns. All outcome-input limitations remain explicit rather than converted to assumed zero returns.

Earlier handoffs remain preserved: `PHASE1-SKIP-HILL-20260924.md`, `PHASE1-COMPLETION-STATUS-20260924.md`, and `PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md` in `research/docs/`.
"""
    freeze(OUT / "index.html", page)
    freeze(DOC, handoff)
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in INPUTS.values()},
                "outputs": {
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [OUT / "index.html", DOC, OUT / Path(__file__).name]
                },
                "performance_calculated": False,
            }
        ),
    )
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
