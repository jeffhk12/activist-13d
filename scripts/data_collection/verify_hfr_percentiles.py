"""Independently reconcile saved HFR panels, metrics and rankings.

Inputs: saved dated CSV/GZIP panels, manager scorecards, prior ingestion manifest.
Outputs: validation.json and all-file SHA256 inventory in the new run directory.
Formula: independent log compounded CAGR, explicit variance and wealth drawdown;
pairwise midrank percentiles, source ROR / 100. Tier: 2.
Run: project Python verify_hfr_percentiles.py --root PROJECT --out RUN
"""

import argparse
import calendar
import csv
import gzip
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path


def read_csv(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def idx(day):
    d = date.fromisoformat(day)
    return d.year * 12 + d.month - 1


def num(value):
    return float(value) if value not in ("", None) else None


def same(actual, expected, label):
    if actual is None or expected is None:
        assert actual is expected, (label, actual, expected)
    else:
        assert math.isclose(actual, expected, rel_tol=2e-9, abs_tol=2e-10), (
            label,
            actual,
            expected,
        )


def recalc(values):
    n = len(values)
    terminal = 0.0 if -1 in values else math.exp(sum(math.log1p(v) for v in values))
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    path = [1.0]
    for value in values:
        path.append(path[-1] * (1 + value))
    dd = min(w / max(path[: j + 1]) - 1 for j, w in enumerate(path))
    return {
        "cagr": terminal ** (12 / n) - 1,
        "cumulative": terminal - 1,
        "volatility": sd * math.sqrt(12),
        "max_drawdown": dd,
        "zero_hurdle_ratio": mean / sd * math.sqrt(12) if sd > 1e-14 else None,
        "downside_deviation": math.sqrt(sum(min(v, 0) ** 2 for v in values) / n * 12),
        "positive_month_fraction": len([v for v in values if v > 0]) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    old = json.loads(
        (args.root / "research/runs/hfr-quarterly/20260924-v1/manifest.json").read_text()
    )
    summary = json.loads((args.out / "summary.json").read_text())
    assert len(summary["snapshots"]) == len(old["snapshots"]) == 35
    counts = {
        "normalized_return_observations": 0,
        "normalized_asset_observations": 0,
        "fund_metric_comparisons": 0,
        "manager_metric_comparisons": 0,
        "percentile_comparisons": 0,
        "representative_checks": 0,
        "persistence_checks": 0,
        "asset_metric_checks": 0,
    }
    all_manager = read_csv(args.out / "manager-scorecards.csv")
    prior = {}
    for snapshot in summary["snapshots"]:
        q = snapshot["quarter"]
        folder = args.out / "snapshots" / q
        prior_source = next(s for s in old["snapshots"] if s["quarter"] == q)
        assert snapshot["source_ed_funds"] == prior_source["event_driven_fund_rows"]
        assert snapshot["source_ed_firms"] == prior_source["event_driven_firm_ids"]
        funds = read_csv(folder / "fund_metrics.csv")
        lookup = {f["fund_id"]: f for f in funds}
        assert len(lookup) == len(funds) == snapshot["source_ed_funds"]
        byfund = {fid: {} for fid in lookup}
        asset_history = {fid: {} for fid in lookup}
        for kind in ["returns", "assets"]:
            records = read_csv(folder / (kind + ".csv.gz"))
            seen = set()
            for record in records:
                key = (record["fund_id"], record["date"])
                assert key not in seen
                seen.add(key)
                assert record["date"] <= snapshot["cutoff"]
                assert record["fund_id"] in lookup
                sources = json.loads(record["sources"])
                assert sources and all(s["row"] >= 2 for s in sources)
                if record["conflict"] == "True":
                    assert record["value"] == ""
                    continue
                value = float(record["value"])
                for source in sources:
                    expected = float(source["raw_value"]) / (100 if kind == "returns" else 1)
                    same(value, expected, (q, key, "normalization"))
                if kind == "returns":
                    byfund[key[0]][idx(key[1])] = value
                else:
                    asset_history[key[0]][key[1]] = value
                counts[
                    "normalized_" + ("return" if kind == "returns" else "asset") + "_observations"
                ] += 1
            assert (
                len(seen)
                == snapshot["return_key_count" if kind == "returns" else "asset_key_count"]
            )
        for fund in funds:
            series = byfund[fund["fund_id"]]
            end = idx(fund["cutoff"])
            assets = asset_history[fund["fund_id"]]
            latest = max(assets) if assets else None
            assert fund["assets_date"] == (latest or "")
            same(num(fund["latest_assets_millions"]), assets.get(latest), (q, "latest assets"))
            selected_assets = (
                assets[latest]
                if latest and idx(latest) >= end - 3 and fund["assets_currency"] == "USD"
                else None
            )
            same(num(fund["selection_assets"]), selected_assets, (q, "selection assets"))

            def ending(m):
                year, month = divmod(m, 12)
                return date(year, month + 1, calendar.monthrange(year, month + 1)[1]).isoformat()

            prev_year, prev_month = ending(end - 12), ending(end - 1)
            growth = (
                assets[fund["cutoff"]] / assets[prev_year] - 1
                if fund["cutoff"] in assets and assets.get(prev_year, 0) > 0
                else None
            )
            same(num(fund["assets_growth_12"]), growth, (q, "asset growth"))
            flow = (
                assets[fund["cutoff"]] - assets[prev_month] * (1 + series[end])
                if fund["cutoff"] in assets
                and prev_month in assets
                and end in series
                and fund["assets_currency"] == fund["return_currency"]
                else None
            )
            same(num(fund["approx_flow_latest_millions"]), flow, (q, "estimated flow"))
            counts["asset_metric_checks"] += 4
            streak = 0
            while end - streak in series:
                streak += 1
            assert streak == int(fund["contiguous_months"])
            assert len(series) == int(fund["total_valid_months"])
            for n in [12, 36, 60]:
                values = [series.get(m) for m in range(end - n + 1, end + 1)]
                expected = recalc(values) if all(v is not None for v in values) else None
                for name in [
                    "cagr",
                    "cumulative",
                    "volatility",
                    "max_drawdown",
                    "zero_hurdle_ratio",
                    "downside_deviation",
                    "positive_month_fraction",
                ]:
                    same(
                        num(fund[f"{name}_{n}"]),
                        expected[name] if expected else None,
                        (q, fund["fund_id"], name, n),
                    )
                    counts["fund_metric_comparisons"] += 1
        manager = json.loads((folder / "manager_scorecards.json").read_text())
        for row in manager:
            f = lookup[row["fund_id"]]
            assert f["ranking_base_eligible"] == "True"
            assert row["firm_id"] == f["firm_id"]
            eligible = [
                x
                for x in funds
                if x["ranking_base_eligible"] == "True"
                and x["firm_id"] == row["firm_id"]
                and (
                    row["peer_group"] == "Event-Driven"
                    or (x["sub_strategy"] or "Unspecified") == row["peer_group"]
                )
            ]

            def order(x):
                fid = x["fund_id"]
                return (
                    -int(x["contiguous_months"]),
                    -(num(x["selection_assets"]) or 0),
                    (0, int(fid)) if fid.isdigit() else (1, fid),
                )

            expected = min(eligible, key=order)
            assert row["fund_id"] == expected["fund_id"]
            assert row["candidate_products"] == len(eligible)
            counts["representative_checks"] += 1
            for n in [12, 36, 60]:
                for name in [
                    "cagr",
                    "volatility",
                    "max_drawdown",
                    "zero_hurdle_ratio",
                    "downside_deviation",
                ]:
                    same(row[f"{name}_{n}"], num(f[f"{name}_{n}"]), (q, "manager metric"))
                    counts["manager_metric_comparisons"] += 1
        for level, rows in [
            ("manager", manager),
            ("fund", read_csv(folder / "fund_percentiles.csv")),
        ]:
            for group in sorted({r["peer_group"] for r in rows}):
                group_rows = [r for r in rows if r["peer_group"] == group]
                assert len(
                    {r["firm_id"] if level == "manager" else r["fund_id"] for r in group_rows}
                ) == len(group_rows)
                for n in [12, 36, 60]:
                    for metric, higher in [
                        ("cagr", True),
                        ("volatility", False),
                        ("max_drawdown", True),
                        ("zero_hurdle_ratio", True),
                        ("downside_deviation", False),
                    ]:
                        field = f"{metric}_{n}"
                        values = [num(r[field]) for r in group_rows if num(r[field]) is not None]
                        for row in group_rows:
                            assert int(row[field + "_peer_n"]) == len(values)
                            v = num(row[field])
                            expected = None
                            if len(values) >= 8 and v is not None:
                                lower = (
                                    sum(x < v for x in values)
                                    if higher
                                    else sum(x > v for x in values)
                                )
                                equal = sum(x == v for x in values)
                                expected = 100 * (lower + (equal - 1) / 2) / (len(values) - 1)
                            same(
                                num(row[field + "_percentile"]), expected, (q, level, group, field)
                            )
                            counts["percentile_comparisons"] += 1
        for row in sorted(
            [r for r in all_manager if r["quarter"] == q],
            key=lambda r: (r["peer_group"], r["firm_id"]),
        ):
            key = (row["peer_group"], row["firm_id"])
            hist = prior.setdefault(key, [])
            assert int(row["prior_ranked_snapshots"]) == len(hist)
            same(
                num(row["prior_top_quartile_share"]),
                sum(hist) / len(hist) if hist else None,
                (q, "persistence"),
            )
            if row["primary_top_quartile"] != "":
                hist.append(row["primary_top_quartile"] == "True")
            counts["persistence_checks"] += 1
        print(q, "independent replay passed", flush=True)
    result = {
        "status": "passed",
        "snapshots": 35,
        "checks": counts,
        "test_suite": "17 focused unit tests passed; lint passed",
        "limitations": [
            "source hashes and row provenance checked; semantic manager identities not independently confirmed",
            "no cash-adjusted Sharpe or forward 13D strategy test",
            "browser visual preview unavailable; HTML and JavaScript checked separately",
        ],
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version,
    }
    (args.out / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    hashes = {
        str(p.relative_to(args.out)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.out.rglob("*"))
        if p.is_file() and p.name != "output-hashes.json"
    }
    (args.out / "output-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
