"""Tier: 2. Summarize annualized event and cash/stock accounting diagnostics.
Inputs: frozen long-horizon outcomes, portfolio ledgers and input evidence.
Outputs: common-sample, annualization, income attribution and ETF identity receipt.
Identity: annualized event return=(1+total_return)^(252/h)-1; NAV gain=interest+stock P&L-costs.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/diagnose_phase1_long_horizon.py
"""

import json
import math
import statistics
from collections import Counter
from pathlib import Path

from run_phase1_development import INPUT, ROOT, digest, encode, freeze, read_page

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-long-horizon-analysis-v1"
OUT = BASE / "20260924-long-horizon-diagnostics-v1"


def annualize(value, horizon):
    if value is None or value < -1 or horizon <= 0:
        raise ValueError("Invalid annualization input")
    return (1 + value) ** (252 / horizon) - 1


def main():
    # Hand-computed compound return contract and refusal.
    assert math.isclose(annualize(0.21, 504), 0.1, abs_tol=1e-12)
    assert annualize(-1, 756) == -1
    try:
        annualize(-1.1, 252)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid return accepted")
    plans = json.loads((BASE / "20260924-long-horizon-inputs-v1/selection.json").read_text())[
        "plans"
    ]
    events = json.loads((RUN / "outcomes.json").read_text())
    context = json.loads((RUN / "portfolio-context.json").read_text())
    common = json.loads((RUN / "calendar-common-summary.json").read_text())
    diagnostics = {}
    for branch, pp in events.items():
        diagnostics[branch] = {}
        calendar_keys = {tuple(k) for k in common[branch]["selection_keys"]}
        valid_keys = set.intersection(
            *[
                {
                    (r["accession"], r["permno"], r["entry"])
                    for r in pp[h]["russell"]
                    if r["focused"]
                    and r["excess"] is not None
                    and (r["accession"], r["permno"], r["entry"]) in calendar_keys
                }
                for h in ["252", "378", "504", "756"]
            ]
        )
        for h, block in pp.items():
            valid = [r for r in block["russell"] if r["focused"] and r["excess"] is not None]
            same = [r for r in valid if (r["accession"], r["permno"], r["entry"]) in valid_keys]
            ledger = json.loads((RUN / "portfolios" / f"{branch}-{h}-100000-base.json").read_text())
            summary = ledger["summary"]
            income = sum(r["cash_interest"] for r in ledger["daily"])
            stock_pnl = sum(
                t["notional"] if t["side"] != "buy" else -t["notional"] for t in ledger["trades"]
            ) + sum(v["value"] for v in ledger["terminal_positions"].values())
            if summary["status"] == "complete":
                assert math.isclose(
                    summary["terminal_nav"] - 100000,
                    income + stock_pnl - summary["total_cost"],
                    abs_tol=1e-5,
                )

            def mean(rows, fn):
                return statistics.mean(fn(r) for r in rows) if rows else None

            diagnostics[branch][h] = dict(
                focused_calculable=len(valid),
                mean_stock_annualized=mean(
                    valid, lambda r, h=h: annualize(r["stock_return"], int(h))
                ),
                mean_benchmark_annualized=mean(
                    valid, lambda r, h=h: annualize(r["benchmark_return"], int(h))
                ),
                mean_annualized_difference=mean(
                    valid,
                    lambda r, h=h: (
                        annualize(r["stock_return"], int(h))
                        - annualize(r["benchmark_return"], int(h))
                    ),
                ),
                same_sample_spy_excess=mean(valid, lambda r: r["spy_excess"]),
                all_horizon_calculable_count=len(same),
                all_horizon_calculable_keys=sorted(valid_keys),
                all_horizon_mean_excess=mean(same, lambda r: r["excess"]),
                common_subset_is_coverage_sensitivity_not_signal_selection=True,
                cash_interest_dollars=income,
                gross_stock_pnl_dollars=stock_pnl,
                pnl_scope="full_period" if summary["status"] == "complete" else "partial_prefix",
                account_minus_cash=summary["total_return"] - context["cash"]["total_return"]
                if summary["status"] == "complete"
                else None,
                skips=dict(Counter(t["reason"] for t in ledger["skips"])),
                all_stock_statuses=dict(Counter(r["stock_status"] for r in block["spy"])),
                prior_selected_issuer_events=sum(
                    e["previously_selected_issuer"] for e in plans[branch][h]
                ),
            )
    # Verify ETF identities across the full extended account window from exact raw source.
    sessions = [
        d
        for d in json.loads((INPUT / "entry-calendar.json").read_text())
        if "2018-03-19" <= d <= "2025-12-31"
    ]
    refs = json.loads(
        (BASE / "20260924-evaluation-inputs-etf-v1/identity-coverage.json").read_text()
    )
    inventory = {}
    identities = []
    for ref in refs:
        payload, _ = read_page(ROOT / ref["source"], inventory)
        rows = [
            r
            for r in payload["results"]
            if r.get("permno") == ref["permno"]
            and r.get("ticker") == ref["symbol"]
            and r.get("securitysubtype") == "ETF"
        ]
        missing = [d for d in sessions if not any(r["namedt"] <= d <= r["nameenddt"] for r in rows)]
        assert not missing, (ref["symbol"], missing[:3])
        identities.append(
            {"symbol": ref["symbol"], "sessions_verified": len(sessions), "source": ref["source"]}
        )
    freeze(OUT / "diagnostics.json", encode(diagnostics))
    freeze(OUT / "etf-identities.json", encode(identities))
    freeze(OUT / "source-inventory.json", encode(inventory))
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    paths = [
        RUN / "provenance.json",
        BASE / "20260924-long-horizon-inputs-v1/provenance.json",
        BASE / "20260924-evaluation-inputs-etf-v1/identity-coverage.json",
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
    print(encode(diagnostics["first_observed"]["504"]))


if __name__ == "__main__":
    main()
