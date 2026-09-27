"""Tier: 2. Report-support diagnostics without changing historical selection.
Inputs: frozen outcomes, assignments, cash/portfolio ledgers and QA. Outputs: receipt.
Identity: invested-account value = total account return minus same-window cash return.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/summarize_phase1_historical_validation.py
"""

import json
import math
import statistics
from collections import Counter
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-historical-validation-v2"
OUT = BASE / "20260924-historical-diagnostics-v1"


def main():
    old = BASE / "20260924-historical-validation-v1"
    comparisons = {}
    for name in [
        "portfolio-summary.json",
        "portfolio-monthly.json",
        "portfolio-context.json",
        "cash-factors.json",
        "matched-events.json",
        "matched-summary.json",
        "summary.json",
    ]:
        comparisons[name] = digest(old / name) == digest(RUN / name)
    assert all(comparisons.values()), (
        "Industry correction changed analytical results; inspect explicitly"
    )
    assignments = json.loads(
        (BASE / "20260924-historical-execution-inputs-v2/assignments.json").read_text()
    )
    assert all(
        a["industry"] is None
        for a in assignments.values()
        if a["siccd"] is None or not 100 <= int(a["siccd"]) < 9999
    )
    outcomes = json.loads((RUN / "outcomes.json").read_text())
    context = json.loads((RUN / "portfolio-context.json").read_text())
    common = json.loads((RUN / "calendar-common-summary.json").read_text())
    result = {}
    for branch, pp in outcomes.items():
        result[branch] = {}
        keys = {tuple(k) for k in common[branch]["selection_keys"]}
        for h, events in pp.items():
            valid = [r for r in events["russell"] if r["focused"] and r["excess"] is not None]
            ledger = json.loads((RUN / "portfolios" / f"{branch}-{h}-100000-base.json").read_text())
            total_interest = sum(d["cash_interest"] for d in ledger["daily"])
            pnl = sum(
                t["notional"] if t["side"] != "buy" else -t["notional"] for t in ledger["trades"]
            ) + sum(v["value"] for v in ledger["terminal_positions"].values())
            fees = ledger["summary"]["total_cost"]
            assert math.isclose(
                ledger["summary"]["terminal_nav"] - 100000,
                total_interest + pnl - fees,
                abs_tol=1e-6,
            )
            focused = [r for r in events["spy"] if r["focused"]]
            common_rows = [r for r in valid if (r["accession"], r["permno"], r["entry"]) in keys]
            result[branch][h] = dict(
                focused_same_sample_spy_mean=statistics.mean(r["spy_excess"] for r in valid)
                if valid
                else None,
                focused_same_sample_count=len(valid),
                focused_stock_statuses=dict(Counter(r["stock_status"] for r in focused)),
                all_stock_statuses=dict(Counter(r["stock_status"] for r in events["spy"])),
                primary_account_minus_cash=ledger["summary"]["total_return"]
                - context["cash"]["total_return"],
                account_pnl_dollars=ledger["summary"]["terminal_nav"] - 100000,
                cash_interest_dollars=total_interest,
                gross_stock_pnl_dollars=pnl,
                costs_dollars=fees,
                skip_reasons=dict(Counter(t["reason"] for t in ledger["skips"])),
                common_calendar_focused_calculable=len(common_rows),
                common_calendar_focused_russell_mean=statistics.mean(
                    r["excess"] for r in common_rows
                )
                if common_rows
                else None,
                common_calendar_focused_keys=[
                    (r["accession"], r["permno"], r["entry"]) for r in common_rows
                ],
            )
    freeze(OUT / "diagnostics.json", encode(result))
    freeze(
        OUT / "correction-parity.json",
        encode(
            {
                "exact_analytical_parity": comparisons,
                "note": "37 input specifications had invalid SIC restored to missing; analytical summaries, matched comparisons and portfolios unchanged.",
            }
        ),
    )
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    paths = [
        RUN / "provenance.json",
        BASE / "20260924-historical-validation-qa-v2/checks.json",
        BASE / "20260924-historical-execution-inputs-v2/provenance.json",
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                "outputs": {
                    p.name: digest(p)
                    for p in OUT.iterdir()
                    if p.is_file() and p.name != "provenance.json"
                },
            }
        ),
    )
    print(encode(result["first_observed"]))


if __name__ == "__main__":
    main()
