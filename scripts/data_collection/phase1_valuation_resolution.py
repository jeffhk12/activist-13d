"""Tier: 2. Offline valuation-gap inventory, exact replay and capacity attribution.
Inputs: frozen rebuilt development schedules/panel/portfolios; optional public sources.
Outputs: separate valuation-resolution-v1 evidence and receipts.
Identity: NAV change = cash interest + stock P&L - costs; isolated sensitivity only.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_valuation_resolution.py [--fetch-sources]
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from activist13d.phase1_valuation_audit import first_gap, isolated_sensitivity
from activist13d.portfolio_accounting import portfolio

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/runs/phase1-baseline"
INPUT = BASE / "20260924-rebuilt-inputs-v2"
OLD = BASE / "20260924-rebuilt-analysis-v1"
OUT = BASE / "20260924-valuation-resolution-v2"
SOURCES = {
    "nyse-suspension": "https://ir.theice.com/press/news-details/2018/NYSE-to-Suspend-Trading-in-Hill-International-Inc-HIL-and-Commence-Delisting-Proceedings/default.aspx",
    "hill-8k": "https://www.sec.gov/Archives/edgar/data/1287808/000110465918051640/a18-18281_38k.htm",
    "hill-resumption": "https://www.globenewswire.com/news-release/2018/10/16/1622034/0/en/Hill-International-to-Resume-Trading-on-the-NYSE-on-October-18-2018.html",
    "crsp-conditional": "https://www.crsp.org/wp-content/uploads/appendix/FlagType_CT.html",
    "crsp-return-missing": "https://www.crsp.org/wp-content/uploads/appendix/FlagType_RM.html",
    "crsp-trading": "https://www.crsp.org/wp-content/uploads/appendix/FlagType_TS.html",
}


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, obj):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == content, f"Immutable output differs: {path}"
    else:
        path.write_bytes(content)


def fetch_sources():
    import requests
    cache = ROOT / "data/raw/public/phase1-valuation-20260924-v1"
    cache.mkdir(parents=True, exist_ok=True)
    receipt = []
    for key, url in SOURCES.items():
        meta = cache / (key + ".json")
        if meta.exists():
            r = read(meta)
            assert digest(ROOT / r["path"]) == r["sha256"]
        else:
            response = requests.get(url, timeout=45, headers={"User-Agent": "Activist13DResearch/1.0 public evidence audit"})
            p = cache / (key + ".html")
            p.write_bytes(response.content)
            r = dict(url=url, final_url=response.url, status=response.status_code,
                     retrieved_utc=datetime.now(timezone.utc).isoformat(),
                     path=str(p.relative_to(ROOT)), sha256=digest(p))
            meta.write_text(json.dumps(r, indent=2) + "\n")
        receipt.append(r)
    write("http-source-receipts.json", receipt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-sources", action="store_true")
    args = parser.parse_args()
    if args.fetch_sources:
        fetch_sources()
    cache = ROOT / "data/raw/public/phase1-valuation-20260924-v1"
    write("source-receipts.json", {"urls": SOURCES, "cached_files": {
        str(p.relative_to(ROOT)): digest(p) for p in sorted(cache.glob("*")) if p.is_file()},
        "limitation": "Direct GlobeNewswire HTTP timed out; web-retrieval.json preserves web.run extracted sources. HTTP errors are diagnostic only."})
    plans = read(INPUT / "selection.json")["plans"]
    panel = {int(k): v for k, v in read(INPUT / "panel.json").items()}
    sessions = read(BASE / "20260924-feasibility-v2/entry-calendar.json")
    factors = {r["day"]: r["factor"] for r in read(OLD / "cash-factors.json")}
    gaps = []
    coverage = []
    for branch, horizons in plans.items():
        for horizon, events in horizons.items():
            count = focused_count = 0
            for e in events:
                gap = first_gap(e, panel.get(e["permno"], {}))
                if gap:
                    count += 1
                    focused_count += bool(e["focused"])
                    gaps.append(dict(branch=branch, horizon=horizon, accession=e["accession"],
                                     issuer=e["issuer"], permno=e["permno"], focused=e["focused"],
                                     entry=e["entry"], exit=e["exit"], **gap))
            coverage.append(dict(branch=branch, horizon=horizon, schedules=len(events),
                                 focused_schedules=sum(bool(e["focused"]) for e in events),
                                 potential_gap_schedules=count, focused_potential_gap_schedules=focused_count))
    write("potential-window-gaps.json", gaps)
    write("coverage.json", coverage)
    hill = panel[91355]
    write("hill-daily-evidence.json", {d: r for d, r in hill.items() if "2018-08-10" <= d <= "2018-11-20"})
    capacities = {}
    failures = []
    receipts = []
    for path in sorted((OLD / "portfolios").glob("*.json")):
        key = path.stem
        branch, horizon, capital, variant = key.split("-")
        events = [e for e in plans[branch][horizon] if e["focused"]]
        original = read(path)
        replay = portfolio(events, sessions, panel, factors, int(capital), "2018-03-19", "2023-12-29",
                           zero_cash=variant == "zero_cash", zero_cost=variant == "zero_cost")
        assert replay == original, key
        receipts.append(dict(scenario=key, exact_replay=True, status=replay["summary"]["status"]))
        buys = [r for r in replay["trades"] if r["side"] == "buy"]
        daily = replay["daily"]
        interest = sum(r["cash_interest"] for r in daily)
        costs = sum(r["cost"] for r in daily)
        nav_change = daily[-1]["nav"] - int(capital)
        capacities[key] = dict(status=replay["summary"]["status"], start="2018-03-19",
                              last_valued_day=daily[-1]["day"], signals=len(events), buys=len(buys),
                              skips=dict(Counter(r["reason"] for r in replay["skips"])),
                              liquidity_cap_below_target_buys=sum(.01*r["adv"] < r["target"] for r in buys),
                              total_buy_notional=sum(r["notional"] for r in buys),
                              cash_interest_dollars=interest, costs_dollars=costs,
                              stock_pnl_before_cost_dollars=nav_change-interest+costs,
                              nav_change_dollars=nav_change,
                              average_cash_weight=replay["summary"]["average_cash_weight"])
        if replay["summary"]["failure"]:
            failure = replay["summary"]["failure"]
            issuer = failure["reason"].split(":")[1]
            position = replay["terminal_positions"][issuer]
            nav = daily[-1]["nav"]
            failures.append(dict(scenario=key, failure=failure, last_valued_day=daily[-1]["day"],
                                 last_observed_nav=nav, position=position,
                                 weight_at_last_observed_nav=position["value"]/nav,
                                 isolated_lower_nav=nav-position["value"], finite_upper_nav=None,
                                 sensitivities=[isolated_sensitivity(nav, position["value"], int(capital), m)
                                                for m in [0, .5, 1, 1.5, 2]]))
    write("capacity-attribution.json", capacities)
    write("refusals-and-isolated-sensitivity.json", failures)
    write("replay-receipt.json", receipts)
    source_paths = [Path(__file__), ROOT / "src/activist13d/phase1_valuation_audit.py",
                    ROOT / "tests/test_phase1_valuation_audit.py", INPUT / "selection.json", INPUT / "panel.json",
                    OLD / "cash-factors.json", BASE / "20260924-feasibility-v2/entry-calendar.json",
                    ROOT / "src/activist13d/portfolio_accounting.py"] + sorted((OLD / "portfolios").glob("*.json"))
    write("provenance.json", {"inputs": {str(p.relative_to(ROOT)): digest(p) for p in source_paths},
                              "outputs": {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.glob("*.json")) if p.name not in {"provenance.json", "verification-receipt.json"}}})
    print(json.dumps(dict(schedules=sum(r["schedules"] for r in coverage), potential_gaps=len(gaps),
                          replayed=len(receipts), refused=len(failures), sources_cached=(OUT / "source-receipts.json").exists())))


if __name__ == "__main__":
    main()
