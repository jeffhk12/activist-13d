"""Tier: 2. Diagnose concentration of frozen benchmark-relative event returns.
Inputs: calculable event rows, each with deduplicated candidate manager IDs.
Outputs: partitions, leave-one-out and realized-winner removal diagnostics.
Identity: group contribution=sum(excess/group_memberships)/total_event_count.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_concentration.py
"""

import math
import statistics
from collections import defaultdict


def simple(rows):
    if not rows:
        return dict(n=0, mean=None, median=None, win_fraction=None)
    values = [r["excess"] for r in rows]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("Calculable finite excess required")
    return dict(
        n=len(rows),
        mean=statistics.mean(values),
        median=statistics.median(values),
        win_fraction=sum(v > 0 for v in values) / len(values),
    )


def diagnostic(rows):
    simple(rows)
    if not rows or any(
        not r.get("managers") or len(set(r["managers"])) != len(r["managers"]) for r in rows
    ):
        raise ValueError("Nonempty sample with unique manager evidence required")
    groups = {}
    for dimension in ["year", "issuer", "manager"]:
        buckets = defaultdict(list)
        contributions = defaultdict(float)
        for r in rows:
            keys = r["managers"] if dimension == "manager" else [r[dimension]]
            for k in keys:
                buckets[k].append(r)
                contributions[k] += r["excess"] / len(keys) / len(rows)
        groups[dimension] = {
            k: dict(
                simple(values),
                contribution=contributions[k],
                leave_out=simple(
                    [
                        r
                        for r in rows
                        if k not in (r["managers"] if dimension == "manager" else [r[dimension]])
                    ]
                ),
            )
            for k, values in sorted(buckets.items())
        }
    ordered = sorted(rows, key=lambda r: (-r["excess"], r["accession"], r["entry"]))
    positive = sum(max(0, r["excess"]) for r in rows)
    removals = []
    firms = sorted(groups["issuer"], key=lambda k: (-groups["issuer"][k]["contribution"], k))
    for k in [1, 3, 5]:
        top = [r for r in ordered if r["excess"] > 0][:k]
        keys = {(r["accession"], r["entry"]) for r in top}
        companies = [f for f in firms if groups["issuer"][f]["contribution"] > 0][:k]
        removals.append(
            dict(
                requested=k,
                removed_events=len(top),
                top_event_contribution=sum(r["excess"] for r in top) / len(rows),
                share_positive_excess=sum(r["excess"] for r in top) / positive
                if positive
                else None,
                without_top_events=simple(
                    [r for r in rows if (r["accession"], r["entry"]) not in keys]
                ),
                removed_companies=companies,
                without_top_companies=simple([r for r in rows if r["issuer"] not in companies]),
            )
        )
    return dict(
        overall=simple(rows),
        groups=groups,
        removals=removals,
        equal_company_mean=statistics.mean(v["mean"] for v in groups["issuer"].values()),
        multiple_manager_events=sum(len(r["managers"]) > 1 for r in rows),
    )
