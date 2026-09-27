"""Pre-event coverage accounting without reading returns.

Inputs: frozen scheduled events and historical benchmark assignments.
Outputs: per-event source/match coverage and stratified counts.
Identity: covered fraction = matched assignments / scheduled events; potential
controls count distinct other issuers in the same entry year, SIC2 and ETF.
Tier: 2. Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
.venv/bin/python -m pytest tests/test_phase1_eligibility_closeout_audit.py
"""

from collections import Counter, defaultdict

CONVENTIONS = {
    "minimum_control_issuers": 5,
    "controls": "nonfocused",
    "outcomes_used": False,
    "matching": "entry_year_sic2_etf",
    "cohorts": "focused; broad_not_focused; other",
    "size": "historical_Russell_segment_proxy_or_unassigned",
}


def coverage(events, assignments):
    rows = []
    seen = set()
    for e in events:
        key = e["accession"] + "|" + e["entry"]
        if key in seen:
            raise ValueError("duplicate event key")
        seen.add(key)
        if key not in assignments:
            raise ValueError("missing assignment join")
        a = assignments[key]
        if a["permno"] != e["permno"]:
            raise ValueError("security join mismatch")
        if not a["pre"] < a["public"] or not a["snapshot"] < a["public"]:
            raise ValueError("nonlagged assignment")
        matched = a["status"] == "matched"
        if matched and not a["etf"]:
            raise ValueError("matched without ETF")
        rows.append(
            dict(
                accession=e["accession"],
                issuer=e["issuer"],
                entry=e["entry"],
                focused=e["focused"],
                broad=e["broad"],
                cohort="focused"
                if e["focused"]
                else "broad_not_focused"
                if e["broad"]
                else "other",
                year=e["entry"][:4],
                industry=a["industry"] or "unobserved",
                size=a["etf"] or "unassigned",
                assignment_status=a["status"],
                benchmark_matched=matched,
                pre=a["pre"],
                snapshot=a["snapshot"],
                historical_cap_observed=(a.get("historical_security") or {}).get("dlycap")
                is not None,
            )
        )
    peers = defaultdict(set)
    for r in rows:
        if not r["focused"] and r["benchmark_matched"] and r["industry"] != "unobserved":
            peers[(r["year"], r["industry"], r["size"])].add(r["issuer"])
    for r in rows:
        possible = r["benchmark_matched"] and r["industry"] != "unobserved"
        r["potential_control_issuers"] = (
            len(peers[(r["year"], r["industry"], r["size"])] - {r["issuer"]}) if possible else None
        )
        r["potential_five_control_match"] = bool(possible and r["potential_control_issuers"] >= 5)
    groups = []
    for dimension in ["all", "cohort", "year", "industry", "size"]:
        for value in sorted({r.get(dimension, "all") for r in rows}):
            subset = [r for r in rows if r.get(dimension, "all") == value]
            groups.append(
                dict(
                    dimension=dimension,
                    value=value,
                    n=len(subset),
                    benchmark_matched=sum(r["benchmark_matched"] for r in subset),
                    focused_n=sum(r["focused"] for r in subset),
                    focused_potential_control_match=sum(
                        r["focused"] and r["potential_five_control_match"] for r in subset
                    ),
                    assignment_statuses=dict(
                        sorted(Counter(r["assignment_status"] for r in subset).items())
                    ),
                )
            )
    return rows, groups
