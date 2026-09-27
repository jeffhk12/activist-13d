"""Tier: 2. Authorized limited historical validation and portfolio accounting.
Inputs: frozen 2024–2025 schedules, verified CRSP/FTSE panel and lagged DTB3.
Outputs: returns, matched controls and portfolios; no fresh-data evaluation.
Identity: issuer-equal matched controls; NAV=cash+positions; failed marks refuse.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_phase1_long_horizon.py
"""

import bisect
import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from run_phase1_development import INPUT, ROOT, calculate, digest, encode, freeze

from activist13d.expanded_hfr_returns import summarize_groups, tag_event
from activist13d.matched_controls import match_events
from activist13d.phase1_baseline import event_return, summarize
from activist13d.portfolio_accounting import bill_daily, portfolio
from activist13d.russell_benchmark import compare

REF = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-inputs-v1"
IN = REF
OUT = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-analysis-v1"
HFR = ROOT / "research/runs/hfr-all-managers/20260924-v1/accession-unions.json"
CASH_MANIFEST = (
    ROOT / "research/runs/phase1-baseline/20260924-evaluation-inputs-v2/cash-readiness.json"
)


def cash_inputs(sessions, start, end):
    source = json.loads(CASH_MANIFEST.read_text())
    path = ROOT / source["source"]
    assert digest(path) == source["source_sha256"]
    rows = {
        r["observation_date"]: float(r["DTB3"])
        for r in csv.DictReader(path.open())
        if r["DTB3"] not in {"", ".", "NA"}
    }
    dates = sorted(rows)
    factors = {}
    receipt = []
    for i, day in enumerate(sessions):
        if not start <= day <= end:
            continue
        prev = sessions[i - 1]
        cutoff = (date.fromisoformat(prev) - timedelta(days=2)).isoformat()
        observed = dates[bisect.bisect_right(dates, cutoff) - 1]
        assert (date.fromisoformat(day) - date.fromisoformat(observed)).days <= 10
        elapsed = (date.fromisoformat(day) - date.fromisoformat(prev)).days
        factors[day] = (1 + bill_daily(rows[observed])) ** elapsed - 1
        receipt.append(
            dict(
                day=day,
                previous=prev,
                observation=observed,
                discount_percent=rows[observed],
                factor=factors[day],
            )
        )
    return factors, receipt, path


def main():
    for p, sha in json.loads((REF / "provenance.json").read_text())["outputs"].items():
        assert digest(REF / p) == sha
    sources = [
        Path(__file__),
        ROOT / "src/activist13d/portfolio_accounting.py",
        ROOT / "src/activist13d/matched_controls.py",
        ROOT / "src/activist13d/phase1_baseline.py",
        ROOT / "src/activist13d/russell_benchmark.py",
        ROOT / "src/activist13d/expanded_hfr_returns.py",
        ROOT / "scripts/data_collection/run_phase1_development.py",
        ROOT / "tests/test_portfolio_accounting.py",
        ROOT / "tests/test_matched_controls.py",
        ROOT / "research/protocol/phase1-rebuild-v1.md",
        ROOT / "research/protocol/phase1-long-horizon-v1.md",
    ]
    for p in sources:
        freeze(OUT / "code" / p.name, p.read_bytes())
    prov = json.loads((IN / "provenance.json").read_text())
    for p, sha in prov["outputs"].items():
        assert digest(IN / p) == sha
    plans = json.loads((IN / "selection.json").read_text())["plans"]
    panel = {int(k): v for k, v in json.loads((REF / "panel.json").read_text()).items()}
    assignments = json.loads((REF / "assignments.json").read_text())
    unions = {k: set(v) for k, v in json.loads(HFR.read_text()).items()}
    outcomes = {}
    summaries = {}
    matches = {}
    matched_summary = {}
    for branch, pp in plans.items():
        spy, _ = calculate(pp, panel)
        outcomes[branch] = {}
        summaries[branch] = {}
        matches[branch] = {}
        matched_summary[branch] = {}
        for h, events in spy.items():
            spyrows = [tag_event(e, unions) for e in events]
            russell = []
            for e, plan in zip(spyrows, pp[h], strict=True):
                assert e["accession"] == plan["accession"]
                a = assignments[e["input_key"]]
                r = compare(e, a, plan["days"], panel)
                r.update(industry=a["industry"], siccd=a["siccd"])
                russell.append(r)
            outcomes[branch][h] = dict(spy=spyrows, russell=russell)
            summaries[branch][h] = dict(
                spy=summarize_groups(spyrows), russell=summarize_groups(russell)
            )
            matched = match_events(russell)
            matches[branch][h] = matched
            calc = [
                dict(
                    r,
                    stock_return=r["focused_excess"],
                    benchmark_return=r["control_mean"],
                    excess=r["difference"],
                )
                for r in matched
                if r["status"] == "matched"
            ]
            matched_summary[branch][h] = dict(
                statuses=dict(Counter(r["status"] for r in matched)), comparison=summarize(calc)
            )
            print(branch, h, "returns and matches", flush=True)
    common = {}
    for branch, pp in plans.items():
        keysets = [
            {(e["accession"], e["permno"], e["entry"]) for e in pp[h]}
            for h in ["252", "378", "504", "756"]
        ]
        keys = set.intersection(*keysets)
        common[branch] = {
            h: {
                benchmark: summarize_groups(
                    [
                        r
                        for r in outcomes[branch][h][benchmark]
                        if (r["accession"], r["permno"], r["entry"]) in keys
                    ]
                )
                for benchmark in ["spy", "russell"]
            }
            for h in ["252", "378", "504", "756"]
        }
        common[branch]["selection_keys"] = sorted(keys)
        common[branch]["selection_note"] = (
            "Calendar-mature 756-session events intersected with other fixed schedules; no return-availability screen."
        )
    freeze(OUT / "calendar-common-summary.json", encode(common))
    freeze(OUT / "outcomes.json", encode(outcomes))
    freeze(OUT / "summary.json", encode(summaries))
    freeze(OUT / "matched-events.json", encode(matches))
    freeze(OUT / "matched-summary.json", encode(matched_summary))
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    start = "2018-03-19"
    end = "2025-12-31"
    factors, receipt, cash_path = cash_inputs(sessions, start, end)
    freeze(OUT / "cash-factors.json", encode(receipt))
    portfolios = {}
    monthly = {}
    for branch, pp in plans.items():
        for h, events in pp.items():
            signals = [e for e in events if e["focused"]]
            for capital in [100000, 100000000]:
                for variant in ["base", "zero_cost", "zero_cash"]:
                    key = f"{branch}-{h}-{capital}-{variant}"
                    result = portfolio(
                        signals,
                        sessions,
                        panel,
                        factors,
                        capital,
                        start,
                        end,
                        zero_cost=variant == "zero_cost",
                        zero_cash=variant == "zero_cash",
                    )
                    portfolios[key] = result["summary"]
                    monthly[key] = []
                    month = None
                    firstnav = float(capital)
                    lastnav = firstnav
                    for r in result["daily"]:
                        m = r["day"][:7]
                        if month is not None and m != month:
                            monthly[key].append(
                                dict(month=month, return_=lastnav / firstnav - 1, end_nav=lastnav)
                            )
                            firstnav = lastnav
                        month = m
                        lastnav = r["nav"]
                    if month:
                        monthly[key].append(
                            dict(
                                month=month,
                                return_=lastnav / firstnav - 1,
                                end_nav=lastnav,
                                partial=result["summary"]["status"] != "complete",
                            )
                        )
                    freeze(OUT / "portfolios" / f"{key}.json", encode(result))
                    print(
                        key,
                        result["summary"]["status"],
                        result["summary"]["total_return"],
                        flush=True,
                    )
    freeze(OUT / "portfolio-summary.json", encode(portfolios))
    freeze(OUT / "portfolio-monthly.json", encode(monthly))
    days = [d for d in sessions if start <= d <= end]
    context = {
        symbol: dict(
            zip(["total_return", "status"], event_return(days, panel[permno]), strict=True)
        )
        for symbol, permno in [("SPY", 84398), ("IWV", 88223)]
    }
    cash = 1
    for d in days:
        cash *= 1 + factors[d]
    context["cash"] = dict(total_return=cash - 1, status="calculated_discount_yield_proxy")
    freeze(OUT / "portfolio-context.json", encode(context))
    inputs = [
        IN / "provenance.json",
        IN / "selection.json",
        REF / "panel.json",
        REF / "assignments.json",
        HFR,
        CASH_MANIFEST,
        cash_path,
        INPUT / "entry-calendar.json",
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in inputs},
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )


if __name__ == "__main__":
    main()
