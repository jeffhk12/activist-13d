"""Tier: 2. Prepare later candidate inputs without calculating future performance.
Inputs: frozen candidate schedules, dated CRSP/FTSE/FRED sources and fixed rules.
Outputs: source receipts, historical assignments, lagged ADV and key coverage.
Identity: fixed requested keys partition into present/absent; outcomes never select.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/prepare_phase1_evaluation_inputs_v2.py
"""

import bisect
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
import wrds_collect
from collect_russell_membership import snapshot_date
from run_phase1_development import INPUT, ROOT, digest, encode, freeze, read_page
from wrds_collect import FrozenClient, Refusal
from wrds_daily import archive_daily

from activist13d.evaluation_input_checks import daily_keys, lagged_adv, presence
from activist13d.russell_benchmark import ETFS, assign

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-evaluation-inputs-v2"
ORIGINAL = BASE / "20260924-evaluation-inputs-v1"
READY = BASE / "20260924-evaluation-readiness-v1"
CACHE = ROOT / "data/raw/wrds/evaluation-inputs-20260924-v1"
PROTOCOL = ROOT / "research/protocol/phase1-evaluation-inputs-v1.md"
END = "2026-09-23"
ETF_IDS = dict(ETFS, SPY=84398)


def requirements():
    manifest = json.loads((READY / "manifest.json").read_text())
    expected = manifest["outputs"]["candidate-selection.json"]
    expected = expected["sha256"] if isinstance(expected, dict) else expected
    assert digest(READY / "candidate-selection.json") == expected
    original = json.loads((READY / "candidate-selection.json").read_text())
    registry = {
        r["accession"]: r
        for line in (INPUT / "event-candidates.jsonl").read_text().splitlines()
        if (r := json.loads(line))
    }
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    plans = {}
    specs = {}
    wanted = defaultdict(set)
    historical = defaultdict(set)
    liquidity = defaultdict(set)
    for branch, pp in original["plans"].items():
        plans[branch] = {}
        for h, block in pp.items():
            events = [e for e in block["events"] if e["issuer"] != "0001287808"]
            plans[branch][h] = events
            for e in events:
                public = min(registry[a]["acceptance_datetime_et"][:10] for a in e["accessions"])
                pre_i = bisect.bisect_left(sessions, public)
                entry_i = bisect.bisect_left(sessions, e["entry"])
                assert sessions[entry_i] == e["entry"]
                snap = snapshot_date(public, sessions)
                advdays = sessions[entry_i - 20 : entry_i]
                key = e["accession"] + "|" + e["entry"] + "|" + public
                specs[key] = dict(
                    accession=e["accession"],
                    permno=e["permno"],
                    issuer=e["issuer"],
                    entry=e["entry"],
                    public=public,
                    pre=sessions[pre_i - 1],
                    snapshot=snap,
                    advdays=advdays,
                )
                e["input_key"] = key
                for d in e["days"]:
                    wanted[d].add(e["permno"])
                for d in [snap, sessions[pre_i - 1]]:
                    historical[d].add(e["permno"])
                for d in advdays:
                    liquidity[d].add(e["permno"])
    start = min(e["entry"] for pp in plans.values() for events in pp.values() for e in events)
    accountdays = [d for d in sessions if start <= d <= END]
    focused = {
        e["permno"]
        for pp in plans.values()
        for events in pp.values()
        for e in events
        if e["focused"]
    }
    # Fixed holding scope, not a survival filter. Post-delisting absent rows stay explicit.
    for d in accountdays:
        wanted[d].update(focused | set(ETF_IDS.values()))
    for d, nums in historical.items():
        wanted[d].update(nums)
    for d, nums in liquidity.items():
        wanted[d].update(nums)
    result = dict(
        plans=plans,
        specs=specs,
        start=start,
        end=END,
        accountdays=accountdays,
        focused_permnos=sorted(focused),
        wanted={d: sorted(v) for d, v in sorted(wanted.items())},
        historical={d: sorted(v) for d, v in sorted(historical.items())},
        liquidity={d: sorted(v) for d, v in sorted(liquidity.items())},
        hill_excluded=True,
        selection_modified_by_data_coverage=False,
    )
    freeze(OUT / "requirements.json", encode(result))
    return result, sessions


def locate_pages(needed):
    found = defaultdict(list)
    for p in sorted((ROOT / "data/raw/wrds").rglob("*.meta.json")):
        if p.parent.name != "crsp.dsf_v2":
            continue
        m = json.loads(p.read_text())
        request = m.get("request", {})
        params = request.get("params", {})
        day = params.get("dlycaldt")
        if (
            request.get("method") == "GET"
            and day in needed
            and params == {"dlycaldt": day, "limit": 50000, "offset": 0}
        ):
            raw = p.with_name(p.name.replace(".meta.json", ".gz"))
            if raw.exists():
                found[day].append((m.get("retrieved_at", ""), raw))
    # Earliest archived vintage preferred; all candidates retained in receipt.
    return {d: sorted(v, key=lambda x: (x[0], str(x[1]))) for d, v in found.items()}


def cash_readiness(days, sessions):
    old = ROOT / "data/raw/public-series/20260914T010236Z/fred_dtb3.csv"
    receipt = next(
        r
        for r in json.loads(
            (
                ROOT
                / "research/runs/data-collection/public-series-20260914T010236Z-corrected-v2/manifest.json"
            ).read_text()
        )["sources"]
        if r["key"] == "fred_dtb3"
    )
    assert digest(old) == receipt["sha256"]

    def read(path):
        return {
            r["observation_date"]: r["DTB3"]
            for r in csv.DictReader(path.open())
            if r["DTB3"] not in {"", ".", "NA"}
        }

    rows = read(old)
    source = old
    refresh_error = None
    if max(rows) < (date.fromisoformat(days[-1]) - timedelta(days=6)).isoformat():
        source = ROOT / "data/raw/public-series/evaluation-inputs-20260924-v1/fred_dtb3.csv"
        if not source.exists():
            try:
                url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"
                response = requests.get(url, timeout=(10, 45), allow_redirects=False)
                if response.status_code != 200:
                    raise ValueError("FRED_http_" + str(response.status_code))
                if not response.content.startswith(b"observation_date,DTB3"):
                    raise ValueError("FRED_unexpected_csv")
                freeze(source, response.content)
                freeze(
                    source.with_suffix(".meta.json"),
                    encode(
                        dict(
                            url=url,
                            retrieved_at=wrds_collect.utc(),
                            sha256=hashlib.sha256(response.content).hexdigest(),
                            bytes=len(response.content),
                        )
                    ),
                )
            except (requests.RequestException, ValueError):
                source = old
                refresh_error = "cash_refresh_failed; existing_source_retained"
        if source != old:
            meta = json.loads(source.with_suffix(".meta.json").read_text())
            assert digest(source) == meta["sha256"]
            rows = read(source)
    observed = sorted(rows)
    positions = {d: i for i, d in enumerate(sessions)}
    checks = []
    for d in days:
        previous = sessions[positions[d] - 1]
        cutoff = (date.fromisoformat(previous) - timedelta(days=2)).isoformat()
        i = bisect.bisect_right(observed, cutoff) - 1
        obs = observed[i] if i >= 0 else None
        age = (date.fromisoformat(d) - date.fromisoformat(obs)).days if obs else None
        valid = bool(obs and age <= 10 and -5 < float(rows[obs]) < 50)
        checks.append(
            dict(
                day=d,
                observation=obs,
                age_days=age,
                status="available" if valid else "missing_or_stale",
            )
        )
    return dict(
        source=str(source.relative_to(ROOT)),
        source_sha256=digest(source),
        latest_observation=max(rows),
        refresh_error=refresh_error,
        statuses=dict(Counter(r["status"] for r in checks)),
        days=checks,
        account_returns_calculated=False,
    )


def main():
    for p in [
        Path(__file__),
        PROTOCOL,
        ROOT / "src/activist13d/evaluation_input_checks.py",
        ROOT / "src/activist13d/russell_benchmark.py",
        ROOT / "tests/test_evaluation_input_checks.py",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    req, sessions = requirements()
    print(
        "Frozen requirements",
        len(req["specs"]),
        "entry specifications",
        len(req["wanted"]),
        "source dates",
        flush=True,
    )
    pages = locate_pages(req["wanted"])
    client = FrozenClient(online=True, cache=CACHE)
    # Preserve the original acquisition history after the cache becomes warm.
    # This is source-replay bookkeeping only; input requirements and checks agree.
    previous_acquisition = json.loads((ORIGINAL / "daily-acquisition.json").read_text())
    repairs = previous_acquisition["repairs"]
    failed = previous_acquisition["failures"]
    for day in sorted(set(req["wanted"]) - set(pages)):
        try:
            r = archive_daily(
                client,
                "crsp.dsf_v2",
                {"dlycaldt": day},
                50000,
                lambda _: None,
                partition_check=True,
            )
            repairs.append(r)
            p = ROOT / r["pages"][0]["source"]["cache_path"]
            pages[day] = [("", p)]
            print("Repaired daily date", day, r["n"], flush=True)
        except Refusal as error:
            failed[day] = str(error)
            print("Daily source unresolved", day, str(error), flush=True)
    freeze(OUT / "daily-acquisition.json", encode(dict(repairs=repairs, failures=failed)))
    inventory = {}
    historic = {}
    liq = defaultdict(dict)
    observed = defaultdict(set)
    daily = []
    for i, (day, nums) in enumerate(req["wanted"].items()):
        try:
            if day not in pages:
                raise ValueError("no_daily_source")
            p = pages[day][0][1]
            payload, meta = read_page(p, inventory)
            keyed = daily_keys(payload, day)
            cover = presence(nums, keyed)
            for n in set(nums) & set(keyed):
                observed[n].add(day)
            for n in req["historical"].get(day, []):
                if n in keyed:
                    historic[day + "|" + str(n)] = {
                        k: keyed[n].get(k)
                        for k in [
                            "cusip",
                            "permco",
                            "siccd",
                            "securitytype",
                            "securitysubtype",
                            "issuertype",
                        ]
                    }
            for n in req["liquidity"].get(day, []):
                if n in keyed:
                    liq[n][day] = {k: keyed[n].get(k) for k in ["dlyclose", "dlyvol"]}
            daily.append(
                dict(
                    day=day,
                    status="source_verified",
                    source=str(p.relative_to(ROOT)),
                    source_candidates=[str(x[1].relative_to(ROOT)) for x in pages[day]],
                    page_rows=len(keyed),
                    reported_count=payload.get("count"),
                    count_discrepancy=payload.get("count") != len(keyed),
                    **cover,
                )
            )
        except (ValueError, FileNotFoundError) as error:
            daily.append(
                dict(
                    day=day,
                    status="unresolved_source",
                    reason=str(error),
                    required=len(nums),
                    present=0,
                    missing=nums,
                )
            )
        if i % 75 == 0:
            print("Verified source dates", i + 1, len(req["wanted"]), flush=True)
    freeze(OUT / "daily-source-coverage.json", encode(daily))
    wrds_collect.TABLES = (*wrds_collect.TABLES, "ftse.idx_holdings_us")
    members = {}
    receipts = []
    for d in sorted({s["snapshot"] for s in req["specs"].values()}):
        try:
            payload, meta = client.request(
                "ftse.idx_holdings_us", "GET", {"date": d, "limit": 10000, "offset": 0}
            )
            rows = payload.get("results")
            if not isinstance(rows, list) or not rows or len(rows) >= 10000 or payload.get("next"):
                raise ValueError("missing_or_truncated_membership")
            if any(r.get("date") != d for r in rows) or len({r.get("cusip") for r in rows}) != len(
                rows
            ):
                raise ValueError("membership_date_or_key_failure")
            bycusip = defaultdict(list)
            for r in rows:
                if isinstance(r.get("cusip"), str) and len(r["cusip"]) == 9:
                    bycusip[r["cusip"][:8]].append(
                        {
                            k: r.get(k)
                            for k in [
                                "cusip",
                                "russell1000",
                                "russell2000",
                                "russellmc",
                                "r1000_wt",
                                "r2000_wt",
                                "rmidc_wt",
                            ]
                        }
                    )
            members[d] = bycusip
            receipts.append(
                dict(
                    date=d,
                    status="source_verified",
                    rows=len(rows),
                    reported_count=payload.get("count"),
                    count_discrepancy=payload.get("count") != len(rows),
                    source=meta["cache_path"],
                    sha256=meta["sha256"],
                )
            )
            print("Membership date", d, len(rows), flush=True)
        except (Refusal, ValueError) as error:
            receipts.append(dict(date=d, status="unresolved_source", reason=str(error)))
    freeze(OUT / "membership-receipt.json", encode(receipts))
    assignments = {}
    for key, s in req["specs"].items():
        old = historic.get(s["snapshot"] + "|" + str(s["permno"]))
        pre = historic.get(s["pre"] + "|" + str(s["permno"]))
        etf = None
        hits = []
        if not old or not pre:
            status = "missing_historical_security"
        elif old["permco"] is None or old["permco"] != pre["permco"]:
            status = "changed_or_missing_company_identity"
        elif not isinstance(old["cusip"], str) or len(old["cusip"]) != 8:
            status = "invalid_historical_cusip"
        elif s["snapshot"] not in members:
            status = "missing_membership_snapshot"
        else:
            hits = members[s["snapshot"]].get(old["cusip"], [])
            etf, status = assign(hits)
        # ADV is strictly pre-entry, not a post-entry capacity screen.
        adv = lagged_adv(s["entry"], s["advdays"], liq.get(s["permno"], {}))
        assignments[key] = dict(
            s,
            status=status,
            etf=etf,
            siccd=pre.get("siccd") if pre else None,
            matched_rows=hits,
            historical_security=old,
            prior_20_session_adv=adv,
            liquidity_status="available"
            if adv is not None
            else "missing_or_invalid_prior_liquidity",
        )
    freeze(OUT / "assignments.json", encode(assignments))
    events = {}
    for branch, pp in req["plans"].items():
        events[branch] = {}
        for h, evs in pp.items():
            records = []
            for e in evs:
                missing = [d for d in e["days"] if d not in observed[e["permno"]]]
                a = assignments[e["input_key"]]
                records.append(
                    dict(
                        accession=e["accession"],
                        issuer=e["issuer"],
                        permno=e["permno"],
                        entry=e["entry"],
                        exit=e["exit"],
                        focused=e["focused"],
                        input_key=e["input_key"],
                        requested_sessions=len(e["days"]),
                        observed_key_sessions=len(e["days"]) - len(missing),
                        absent_dates=missing,
                        benchmark_status=a["status"],
                        etf=a["etf"],
                        liquidity_status=a["liquidity_status"],
                    )
                )
            events[branch][h] = records
    freeze(OUT / "event-input-coverage.json", encode(events))
    identities = []
    for p in sorted((ROOT / "data/raw/wrds/bulk-v1/crsp.stocknames_v2").glob("*.json.gz")):
        payload, meta = read_page(p, inventory)
        if meta["request"]["method"] != "GET":
            continue
        for r in payload.get("results", []):
            if (
                r.get("ticker") in ETF_IDS
                and ETF_IDS[r["ticker"]] == r.get("permno")
                and r.get("securitysubtype") == "ETF"
                and r["namedt"] <= req["start"]
                and r["nameenddt"] >= END
            ):
                identities.append(dict(source=str(p.relative_to(ROOT)), row=r))
    freeze(OUT / "etf-identities.json", encode(identities))
    cash = cash_readiness(req["accountdays"], sessions)
    freeze(OUT / "cash-readiness.json", encode(cash))
    summary = dict(
        status="inputs_prepared_not_performance_evaluated",
        overall_evaluation_ready=False,
        selection_changed_by_coverage=False,
        performance_calculated=False,
        future_price_return_values_reported=False,
        unique_entry_specs=len(req["specs"]),
        required_source_dates=len(daily),
        daily_statuses=dict(Counter(r["status"] for r in daily)),
        daily_count_discrepancies=sum(r.get("count_discrepancy", False) for r in daily),
        membership_statuses=dict(Counter(r["status"] for r in receipts)),
        membership_count_discrepancies=sum(r.get("count_discrepancy", False) for r in receipts),
        assignment_statuses=dict(Counter(a["status"] for a in assignments.values())),
        cash_statuses=cash["statuses"],
        etf_identity_symbols=sorted({r["row"]["ticker"] for r in identities}),
        branches={
            b: {
                h: dict(
                    scheduled=len(rows),
                    focused=sum(r["focused"] for r in rows),
                    all_requested_stock_keys_present=sum(not r["absent_dates"] for r in rows),
                    benchmark_assigned=sum(r["benchmark_status"] == "matched" for r in rows),
                    focused_benchmark_assigned=sum(
                        r["focused"] and r["benchmark_status"] == "matched" for r in rows
                    ),
                    lagged_liquidity_available=sum(
                        r["liquidity_status"] == "available" for r in rows
                    ),
                )
                for h, rows in pp.items()
            }
            for b, pp in events.items()
        },
    )
    freeze(OUT / "summary.json", encode(summary))
    freeze(OUT / "source-inventory.json", encode(inventory))
    sources = [
        READY / "candidate-selection.json",
        READY / "manifest.json",
        INPUT / "event-candidates.jsonl",
        INPUT / "entry-calendar.json",
        PROTOCOL,
        ROOT / cash["source"],
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in sources},
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    print(encode(summary))


if __name__ == "__main__":
    main()
