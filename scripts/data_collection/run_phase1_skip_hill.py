"""Tier: 2. User-authorized ex-Hill development sensitivity and portfolio accounting.
Inputs: rebuilt eligibility schedules, verified CRSP/FTSE panel and lagged DTB3.
Outputs: returns, matched controls and portfolios; no fresh-data evaluation.
Identity: issuer-equal matched controls; NAV=cash+positions; failed marks refuse.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_phase1_skip_hill.py
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
from activist13d.phase1_baseline import event_return, schedule, summarize
from activist13d.portfolio_accounting import bill_daily, portfolio
from activist13d.russell_benchmark import compare

REF = ROOT / "research/runs/phase1-baseline/20260924-rebuilt-inputs-v2"
IN = ROOT / "research/runs/phase1-baseline/20260924-skip-hill-inputs-v1"
OUT = ROOT / "research/runs/phase1-baseline/20260924-skip-hill-analysis-v1"
HFR = ROOT / "research/runs/hfr-all-managers/20260924-v1/accession-unions.json"
CASH_MANIFEST = (
    ROOT / "research/runs/data-collection/public-series-20260914T010236Z-corrected-v2/manifest.json"
)


def cash_inputs(sessions, start, end):
    source = next(
        r for r in json.loads(CASH_MANIFEST.read_text())["sources"] if r["key"] == "fred_dtb3"
    )
    path = ROOT / source["stored_path"]
    assert digest(path) == source["sha256"]
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


def prepare():
    original = json.loads((REF / "selection.json").read_text())
    sessions = [
        d for d in json.loads((INPUT / "entry-calendar.json").read_text()) if d <= "2023-12-29"
    ]
    plans, removed, counts = {}, {}, {}
    for branch, selected in original["selected"].items():
        filtered = [e for e in selected if e["issuer"] != "0001287808"]
        removed[branch] = [e for e in selected if e["issuer"] == "0001287808"]
        plans[branch] = {}
        counts[branch] = {}
        for horizon in [63, 126, 252]:
            h = str(horizon)
            events, _ = schedule(filtered, sessions, horizon)
            prior = original["plans"][branch][h]
            assert events == [e for e in prior if e["issuer"] != "0001287808"]
            plans[branch][h] = events
            counts[branch][h] = dict(
                before=len(prior),
                after=len(events),
                removed=[
                    {k: v for k, v in e.items() if k != "days"}
                    for e in prior
                    if e["issuer"] == "0001287808"
                ],
            )
    freeze(
        IN / "selection.json",
        encode(
            dict(
                plans=plans,
                issuer_exclusion="0001287808",
                removed_candidates=removed,
                changes=counts,
            )
        ),
    )
    freeze(
        IN / "provenance.json",
        encode(
            dict(
                inputs={
                    str(p.relative_to(ROOT)): digest(p)
                    for p in [
                        REF / "selection.json",
                        REF / "provenance.json",
                        ROOT / "research/protocol/phase1-skip-hill-v1.md",
                    ]
                },
                outputs={"selection.json": digest(IN / "selection.json")},
            )
        ),
    )


def main():
    for p, sha in json.loads((REF / "provenance.json").read_text())["outputs"].items():
        assert digest(REF / p) == sha
    prepare()
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
        ROOT / "research/protocol/phase1-skip-hill-v1.md",
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
                a = assignments[e["accession"] + "|" + e["entry"]]
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
    freeze(OUT / "outcomes.json", encode(outcomes))
    freeze(OUT / "summary.json", encode(summaries))
    freeze(OUT / "matched-events.json", encode(matches))
    freeze(OUT / "matched-summary.json", encode(matched_summary))
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    start = "2018-03-19"
    end = "2023-12-29"
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
