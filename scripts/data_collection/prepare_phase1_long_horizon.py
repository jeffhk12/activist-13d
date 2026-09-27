"""Tier: 2. Expand authorized exploratory schedules to 12/18/24/36 months through 2025.
Inputs: full-universe reconciled eligibility, old basic security screen, raw CRSP.
Outputs: two new schedules, full required panel, historical assignments/liquidity.
Identity: eligibility precedes scheduling and returns; no replacement on failure.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/prepare_phase1_long_horizon.py
"""

import bisect
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import wrds_collect
from collect_russell_membership import snapshot_date
from prepare_phase1_evaluation_inputs_v2 import locate_pages
from run_phase1_development import (
    FIELDS,
    INPUT,
    ROOT,
    digest,
    encode,
    freeze,
    read_page,
)
from wrds_collect import FrozenClient
from wrds_daily import archive_daily

from activist13d.evaluation_input_checks import daily_keys
from activist13d.phase1_baseline import number, schedule
from activist13d.phase1_evaluation_readiness_selection import candidates
from activist13d.russell_benchmark import ETFS, assign

OUT = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-inputs-v1"
ELIG = ROOT / "research/runs/phase1-baseline/20260924-universe-rebuild-v3"
OLD = ROOT / "research/runs/phase1-baseline/20260924-development-v4"
RUSSELL = ROOT / "research/runs/phase1-baseline/20260924-russell-inputs-v1"


def main():
    for p in [Path(__file__), ROOT / "research/protocol/phase1-long-horizon-v1.md"]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    registry = {
        r["accession"]: r
        for line in (INPUT / "event-candidates.jsonl").read_text().splitlines()
        if (r := json.loads(line))
    }
    eligibility = {
        r["accession"]: r
        for line in (ELIG / "eligibility.jsonl").read_text().splitlines()
        if (r := json.loads(line))
    }
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    protection = json.loads((OLD / "human-review-protection.json").read_text())
    result = candidates(
        list(registry.values()),
        eligibility,
        sessions,
        set(protection["issuers"]) | {"0001287808"},
        set(),
        set(),
        start="2018-03-19",
        asof="2025-12-31",
    )
    base_candidates, base_exclusions = result["selected"], result["exclusions"]
    prior_issuers = set()
    for folder in ["20260924-rebuilt-inputs-v2", "20260924-historical-execution-inputs-v2"]:
        prior = json.loads((OUT.parent / folder / "selection.json").read_text())
        prior_issuers.update(
            e["issuer"] for pp in prior["plans"].values() for events in pp.values() for e in events
        )
    for e in base_candidates:
        e["previously_selected_issuer"] = e["issuer"] in prior_issuers
    for rel, sha in json.loads(
        (OUT.parent / "20260924-completion-integration-v1/protected-assets.json").read_text()
    ).items():
        assert digest(ROOT / rel) == sha, rel
    plans = {}
    exclusions = {}
    selected = {}
    for branch in ["standalone", "first_observed"]:
        usable = []
        drop = []
        for r in base_candidates:
            a = eligibility[r["accession"]]
            reason = None
            if a["status"] != "standalone_initial_candidate":
                reason = a["status"]
            elif branch == "first_observed" and a["campaign_status"] != "first_observed_pair":
                reason = a["campaign_status"]
            if reason:
                drop.append(dict(accession=r["accession"], reason=reason))
            else:
                usable.append(r)
        selected[branch] = usable
        plans[branch] = {}
        exclusions[branch] = dict(eligibility=drop, schedule={})
        for h in [252, 378, 504, 756]:
            events, dropped = schedule(usable, [d for d in sessions if d <= "2025-12-31"], h)
            assert all(
                e["exit"] <= "2025-12-31" and e["issuer"] not in protection["issuers"]
                for e in events
            )
            for e in events:
                public = min(registry[a]["acceptance_datetime_et"][:10] for a in e["accessions"])
                e["input_key"] = e["accession"] + "|" + e["entry"] + "|" + public
            plans[branch][str(h)] = events
            exclusions[branch]["schedule"][str(h)] = dropped
    freeze(
        OUT / "selection.json",
        encode(
            dict(
                plans=plans,
                selected=selected,
                base_exclusions=base_exclusions,
                exclusions=exclusions,
            )
        ),
    )
    wanted = defaultdict(set)
    metadata_days = defaultdict(set)
    event_metadata = {}
    focused = set()
    for branches in plans.values():
        for events in branches.values():
            for e in events:
                if e["focused"]:
                    focused.add(e["permno"])
                for day in e["days"]:
                    wanted[day].add(e["permno"])
                public = min(registry[a]["acceptance_datetime_et"][:10] for a in e["accessions"])
                pre = sessions[bisect.bisect_left(sessions, public) - 1]
                snap = snapshot_date(public, sessions)
                assert snap < public and pre < public
                metadata_days[pre].add(e["permno"])
                metadata_days[snap].add(e["permno"])
                event_metadata[e["input_key"]] = dict(
                    permno=e["permno"], public=public, pre=pre, snapshot=snap
                )
    # Full focused panel supports strictly lagged ADV and portfolio exit wind-down.
    portfolio_days = [d for d in sessions if "2018-02-01" <= d <= "2025-12-31"]
    for day in portfolio_days:
        wanted[day].update(focused | set(ETFS.values()) | {84398})
    for day, nums in metadata_days.items():
        wanted[day].update(nums)
    pages = locate_pages(wanted)
    client = FrozenClient(online=True, cache=ROOT / "data/raw/wrds/long-horizon-20260924-v1")
    for day in sorted(set(wanted) - set(pages)):
        archive_daily(client, day, partition_check=True)
    pages = locate_pages(wanted)
    code = [
        Path(__file__),
        ROOT / "scripts/data_collection/run_phase1_long_horizon.py",
        ROOT / "scripts/data_collection/run_phase1_development.py",
        ROOT / "scripts/data_collection/collect_russell_membership.py",
    ] + sorted((ROOT / "src/activist13d").glob("*.py"))
    for p in code:
        freeze(OUT / "code" / p.relative_to(ROOT), p.read_bytes())
    freeze(
        OUT / "environment.json",
        encode(
            {
                "python": platform.python_version(),
                "packages": json.loads(
                    subprocess.check_output(
                        [sys.executable, "-m", "pip", "list", "--format=json"], text=True
                    )
                ),
            }
        ),
    )
    access = OUT / "outcome-access.json"
    if not access.exists():
        freeze(
            access,
            encode(
                {
                    "actual_utc": datetime.now(timezone.utc).isoformat(),
                    "purpose": "User-authorized long-horizon exploratory revision; previously seen outcomes included",
                    "sample_sha256": digest(OUT / "selection.json"),
                    "protocol_sha256": digest(ROOT / "research/protocol/phase1-long-horizon-v1.md"),
                    "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in code},
                }
            ),
        )
    else:
        for rel, sha in json.loads(access.read_text())["code_hashes"].items():
            assert digest(ROOT / rel) == sha
    panel = defaultdict(dict)
    historical = {}
    inventory = {}
    missing = []
    extra = [
        "dlycap",
        "siccd",
        "permco",
        "cusip",
        "securitytype",
        "securitysubtype",
        "issuertype",
        "usincflg",
    ]
    for i, (day, nums) in enumerate(sorted(wanted.items())):
        if day not in pages:
            missing.append(day)
            continue
        payload, _ = read_page(pages[day][0][1], inventory)
        rows = list(daily_keys(payload, day).values())
        assert (
            len(rows) < 50000
            and not payload.get("next")
            and len(rows) == len({r["permno"] for r in rows})
        )
        for r in rows:
            assert r["dlycaldt"] == day
            if r["permno"] in nums:
                panel[r["permno"]][day] = {k: r.get(k) for k in FIELDS}
            if r["permno"] in metadata_days.get(day, set()):
                historical[day + "|" + str(r["permno"])] = {k: r.get(k) for k in extra}
        if i % 100 == 0:
            print("Required daily inputs", i + 1, len(wanted), flush=True)
    memberships = {}
    member_pages = defaultdict(list)
    for p in sorted((ROOT / "data/raw/wrds").rglob("*.meta.json")):
        if p.parent.name != "ftse.idx_holdings_us":
            continue
        m = json.loads(p.read_text())
        params = m["request"].get("params", {})
        day = params.get("date")
        if (
            day
            and m["request"]["method"] == "GET"
            and params == {"date": day, "limit": 10000, "offset": 0}
        ):
            member_pages[day].append(
                (m.get("retrieved_at", ""), p.with_name(p.name.replace(".meta.json", ".gz")))
            )
    wrds_collect.TABLES = (*wrds_collect.TABLES, "ftse.idx_holdings_us")
    membership_receipts = []
    for day in sorted({v["snapshot"] for v in event_metadata.values()}):
        if day in member_pages:
            source = sorted(member_pages[day])[0][1]
            payload, meta = read_page(source, inventory)
        else:
            payload, meta = client.request(
                "ftse.idx_holdings_us", "GET", {"date": day, "limit": 10000, "offset": 0}
            )
            source = ROOT / meta["cache_path"]
            payload, meta = read_page(source, inventory)
        rows = payload.get("results", [])
        assert rows and len(rows) < 10000 and not payload.get("next")
        assert all(r["date"] == day for r in rows) and len(rows) == len({r["cusip"] for r in rows})
        membership_receipts.append(
            dict(
                date=day,
                source=str(source.relative_to(ROOT)),
                rows=len(rows),
                reported_count=payload.get("count"),
                count_discrepancy=payload.get("count") != len(rows),
            )
        )
        lookup = defaultdict(list)
        for r in payload["results"]:
            c = r.get("cusip")
            if isinstance(c, str) and len(c) == 9:
                lookup[c[:8]].append(
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
        memberships[day] = lookup
    freeze(OUT / "membership-receipt.json", encode(membership_receipts))
    assignments = {}
    for key, info in event_metadata.items():
        snap = historical.get(info["snapshot"] + "|" + str(info["permno"]))
        pre = historical.get(info["pre"] + "|" + str(info["permno"]))
        etf = None
        hits = []
        if not snap or not pre:
            status = "missing_historical_security"
        elif snap["permco"] is None or snap["permco"] != pre["permco"]:
            status = "changed_or_missing_company_identity"
        elif not isinstance(snap["cusip"], str) or len(snap["cusip"]) != 8:
            status = "invalid_historical_cusip"
        elif info["snapshot"] not in memberships:
            status = "missing_membership_snapshot"
        else:
            hits = memberships[info["snapshot"]].get(snap["cusip"], [])
            etf, status = assign(hits)
        sic = pre.get("siccd") if pre else None
        industry = str(int(sic)).zfill(4)[:2] if number(sic) and 100 <= int(sic) < 9999 else None
        assignments[key] = dict(
            info,
            etf=etf,
            status=status,
            industry=industry,
            siccd=sic,
            historical_security=snap,
            matched_rows=hits,
        )
    freeze(OUT / "panel.json", encode(panel))
    freeze(OUT / "assignments.json", encode(assignments))
    freeze(OUT / "source-inventory.json", encode(inventory))
    freeze(
        OUT / "coverage.json",
        encode(
            dict(
                missing_daily_pages=missing,
                focused_securities=len(focused),
                assignment_statuses=dict(Counter(r["status"] for r in assignments.values())),
            )
        ),
    )
    sources = [
        ELIG / "eligibility.jsonl",
        INPUT / "event-candidates.jsonl",
        INPUT / "entry-calendar.json",
        OLD / "human-review-protection.json",
        ROOT / "research/protocol/phase1-long-horizon-v1.md",
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
    print({b: {h: len(e) for h, e in pp.items()} for b, pp in plans.items()})


if __name__ == "__main__":
    main()
