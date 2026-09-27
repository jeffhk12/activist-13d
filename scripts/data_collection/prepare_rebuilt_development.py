"""Tier: 2. Rebuild development schedules and dated price/benchmark inputs.
Inputs: full-universe reconciled eligibility, old basic security screen, raw CRSP.
Outputs: two new schedules, full required panel, historical assignments/liquidity.
Identity: eligibility precedes scheduling and returns; no replacement on failure.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/prepare_rebuilt_development.py
"""

import bisect
import json
from collections import Counter, defaultdict
from pathlib import Path

from collect_russell_membership import snapshot_date
from run_phase1_development import (
    FIELDS,
    INPUT,
    RAW,
    ROOT,
    digest,
    encode,
    freeze,
    read_page,
    select_events,
)

from activist13d.phase1_baseline import number, schedule
from activist13d.russell_benchmark import ETFS, assign

OUT = ROOT / "research/runs/phase1-baseline/20260924-rebuilt-inputs-v2"
ELIG = ROOT / "research/runs/phase1-baseline/20260924-universe-rebuild-v3"
OLD = ROOT / "research/runs/phase1-baseline/20260924-development-v4"
RUSSELL = ROOT / "research/runs/phase1-baseline/20260924-russell-inputs-v1"


def main():
    for p in [Path(__file__), ROOT / "research/protocol/phase1-rebuild-v1.md"]:
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
    candidates, base_exclusions = select_events(list(registry.values()), set(protection["issuers"]))
    plans = {}
    exclusions = {}
    selected = {}
    for branch in ["standalone", "first_observed"]:
        usable = []
        drop = []
        for r in candidates:
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
        for h in [63, 126, 252]:
            events, dropped = schedule(usable, [d for d in sessions if d <= "2023-12-29"], h)
            assert all(
                e["exit"] <= "2023-12-29" and e["issuer"] not in protection["issuers"]
                for e in events
            )
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
                event_metadata[e["accession"] + "|" + e["entry"]] = dict(
                    permno=e["permno"], public=public, pre=pre, snapshot=snap
                )
    # Full focused panel supports strictly lagged ADV and portfolio exit wind-down.
    portfolio_days = [d for d in sessions if "2018-02-01" <= d <= "2023-12-29"]
    for day in portfolio_days:
        wanted[day].update(focused | set(ETFS.values()) | {84398})
    for day, nums in metadata_days.items():
        wanted[day].update(nums)
    pages = {}
    folders = [RAW / "crsp.dsf_v2", ROOT / "data/raw/wrds/phase1-gap-20260924/crsp.dsf_v2"]
    for folder in folders:
        for p in sorted(folder.glob("*.meta.json")):
            m = json.loads(p.read_text())
            params = m["request"].get("params", {})
            day = params.get("dlycaldt")
            if (
                day in wanted
                and m["request"]["method"] == "GET"
                and params == {"dlycaldt": day, "limit": 50000, "offset": 0}
            ):
                assert day not in pages
                pages[day] = p.with_name(p.name.replace(".meta.json", ".gz"))
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
        payload, _ = read_page(pages[day], inventory)
        rows = payload.get("results", [])
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
    for rec in json.loads((RUSSELL / "membership-receipt.json").read_text()):
        payload, _ = read_page(ROOT / rec["source"], inventory)
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
        memberships[rec["date"]] = lookup
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
        RUSSELL / "membership-receipt.json",
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
