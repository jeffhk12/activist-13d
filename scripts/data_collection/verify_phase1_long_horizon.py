"""Tier: 2. Independent joins/accounting checks and deterministic estimator replay.
Inputs: frozen rebuilt artifacts. Outputs: QA receipt; no changed research outputs.
Identity: source hashes, schedules, control means and cash ledgers must reconcile.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_phase1_long_horizon.py
"""

import json
import math
import platform
from collections import defaultdict
from pathlib import Path

from run_phase1_development import INPUT, ROOT, digest, encode, freeze
from run_phase1_long_horizon import IN, OUT, REF, cash_inputs

from activist13d.phase1_baseline import event_return, schedule
from activist13d.portfolio_accounting import portfolio


def main():
    qa = OUT.parent / "20260924-long-horizon-qa-v1"
    for directory in [IN, OUT]:
        prov = json.loads((directory / "provenance.json").read_text())
        for p, sha in prov["outputs"].items():
            assert digest(directory / p) == sha, (directory, p)
        for p, sha in prov["inputs"].items():
            assert digest(ROOT / p) == sha, p
    plans = json.loads((IN / "selection.json").read_text())["plans"]
    panel = {int(k): v for k, v in json.loads((REF / "panel.json").read_text()).items()}
    outcomes = json.loads((OUT / "outcomes.json").read_text())
    matches = json.loads((OUT / "matched-events.json").read_text())
    old = json.loads((IN / "selection.json").read_text())["plans"]
    assert plans == old
    saved_selection = json.loads((IN / "selection.json").read_text())
    calendar = [
        d for d in json.loads((INPUT / "entry-calendar.json").read_text()) if d <= "2025-12-31"
    ]
    for branch, pp in plans.items():
        for h, events in pp.items():
            replay, _ = schedule(saved_selection["selected"][branch], calendar, int(h))
            assert replay == [{k: v for k, v in e.items() if k != "input_key"} for e in events]

    eligibility = {
        r["accession"]: r
        for s in (OUT.parent / "20260924-universe-rebuild-v3/eligibility.jsonl")
        .read_text()
        .splitlines()
        if (r := json.loads(s))
    }
    protected = set(
        json.loads(
            (OUT.parent / "20260924-development-v4/human-review-protection.json").read_text()
        )["issuers"]
    )
    counts = {}
    replayed = 0
    matched = 0
    for branch, pp in plans.items():
        counts[branch] = {}
        for h, events in pp.items():
            last = {}
            for e, r in zip(events, outcomes[branch][h]["spy"], strict=True):
                assert e["entry"] > last.get(e["issuer"], "") and e["exit"] <= "2025-12-31"
                last[e["issuer"]] = e["exit"]
                assert e["issuer"] not in protected and e["issuer"] != "0001287808"
                for a in e["accessions"]:
                    assert eligibility[a]["status"] == "standalone_initial_candidate"
                    if branch == "first_observed":
                        assert eligibility[a]["campaign_status"] == "first_observed_pair"
                value, status = event_return(e["days"], panel.get(e["permno"], {}))
                assert value == r["stock_return"] and status == r["stock_status"]
                if value is not None:
                    rows = panel[e["permno"]]
                    wealth = float(rows[e["entry"]]["dlyclose"]) / float(
                        rows[e["entry"]]["dlyopen"]
                    )
                    for day in e["days"][1:]:
                        wealth *= 1 + float(rows[day]["dlyret"])
                        if rows[day]["dlydelflg"] == "Y":
                            break
                    assert math.isclose(wealth - 1, value, abs_tol=1e-12)
                replayed += 1
            original = {e["accession"] for e in old[branch][h]}
            current = {e["accession"] for e in events}
            counts[branch][h] = dict(
                scheduled=len(events),
                old_scheduled=len(original),
                newly_released=sorted(current - original),
                no_longer_scheduled=sorted(original - current),
            )
            by_acc = {r["accession"]: r for r in outcomes[branch][h]["russell"]}
            for m in matches[branch][h]:
                if m["status"] != "matched":
                    continue
                focal = by_acc[m["accession"]]
                issuers = defaultdict(list)
                for a in m["control_accessions"]:
                    r = by_acc[a]
                    assert not r["focused"] and r["issuer"] != focal["issuer"]
                    assert (r["entry"][:4], r["industry"], r["assigned_etf"]) == (
                        focal["entry"][:4],
                        focal["industry"],
                        focal["assigned_etf"],
                    )
                    issuers[r["issuer"]].append(r["excess"])
                assert len(issuers) >= 5 and len(issuers) == m["control_issuers"]
                mean = sum(sum(v) / len(v) for v in issuers.values()) / len(issuers)
                assert math.isclose(mean, m["control_mean"], abs_tol=1e-12)
                assert math.isclose(m["difference"], focal["excess"] - mean, abs_tol=1e-12)
                matched += 1
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    factors, _, _ = cash_inputs(sessions, "2018-03-19", "2025-12-31")
    scenarios = 0
    daily_count = 0
    for p in sorted((OUT / "portfolios").glob("*.json")):
        branch, h, capital, variant = p.stem.split("-")
        capital = int(capital)
        result = json.loads(p.read_text())
        again = portfolio(
            [e for e in plans[branch][h] if e["focused"]],
            sessions,
            panel,
            factors,
            capital,
            "2018-03-19",
            "2025-12-31",
            zero_cost=variant == "zero_cost",
            zero_cash=variant == "zero_cash",
        )
        assert again == result, p
        cash = float(capital)
        previous_nav = cash
        nav_product = cash
        trades = defaultdict(list)
        for t in result["trades"]:
            trades[t["day"]].append(t)
        for r in result["daily"]:
            cash += r["cash_interest"]
            for t in trades[r["day"]]:
                cash += (
                    -t["notional"] - t["cost"] if t["side"] == "buy" else t["notional"] - t["cost"]
                )
                if "adv" in t:
                    assert t["notional"] <= 0.01 * t["adv"] + 1e-6
                if t["side"] == "buy":
                    assert t["notional"] <= 0.05 * previous_nav + 1e-6
            nav_product *= 1 + r["return_"]
            assert math.isclose(cash, r["cash"], rel_tol=1e-10, abs_tol=1e-6)
            assert math.isclose(r["nav"], r["cash"] + r["invested"], rel_tol=1e-12)
            assert math.isclose(nav_product, r["nav"], rel_tol=1e-10)
            assert r["positions"] <= 20 and r["cash"] >= -1e-7
            previous_nav = r["nav"]
            daily_count += 1
        scenarios += 1
    receipt = dict(
        status="passed",
        event_returns_replayed=replayed,
        matched_arithmetic_checked=matched,
        portfolio_scenarios_replayed=scenarios,
        daily_cash_nav_checks=daily_count,
        python=platform.python_version(),
        platform=platform.platform(),
        event_changes=counts,
    )
    freeze(qa / "checks.json", encode(receipt))
    freeze(qa / "verify_phase1_long_horizon.py", Path(__file__).read_bytes())
    freeze(
        qa / "input-hashes.json",
        encode(
            {
                str(p.relative_to(ROOT)): digest(p)
                for p in [IN / "provenance.json", OUT / "provenance.json"]
            }
        ),
    )
    print({k: v for k, v in receipt.items() if k != "event_changes"})


if __name__ == "__main__":
    main()
