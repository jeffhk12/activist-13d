"""Tier: 1. Independently verify Russell common-sample arithmetic and source joins.
Inputs: frozen Russell and SPY event runs. Outputs: separate QA receipt.
Identity: mean=sum(valid returns)/n; original stock and SPY remain identical.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_russell_returns.py
"""

import json
import math
import re
from datetime import date

from collect_russell_membership import snapshot_date
from run_phase1_development import digest, encode, freeze
from run_russell_returns import BASE, EXPANDED, INPUT, OUT, ROOT

QA = OUT.parent / "20260924-russell-verification-v1"


def main():
    assert snapshot_date("2020-03-01", ["2020-01-31", "2020-02-28", "2020-03-02"]) == "2020-02-28"
    assert snapshot_date("2020-03-31", ["2020-02-28", "2020-03-02", "2020-03-31"]) == "2020-02-28"
    for run in [INPUT, OUT]:
        provenance = json.loads((run / "provenance.json").read_text())
        for root, key in [(run, "outputs"), (ROOT, "inputs")]:
            for name, expected in provenance[key].items():
                assert digest(root / name) == expected, name
    originals = json.loads((EXPANDED / "outcomes.json").read_text())
    outcomes = json.loads((OUT / "outcomes.json").read_text())
    summaries = json.loads((OUT / "summary.json").read_text())
    assignments = json.loads((INPUT / "assignments.json").read_text())
    protected = set(json.loads((BASE / "human-review-protection.json").read_text())["issuers"])
    for a in assignments.values():
        lag = (date.fromisoformat(a["public_date"]) - date.fromisoformat(a["snapshot_date"])).days
        assert 0 < lag <= 35
        assert a["snapshot_date"][:7] < a["public_date"][:7]
        if a["status"] == "matched":
            assert len(a["matched_rows"]) == 1
            r = a["matched_rows"][0]
            assert r["cusip"][:8] == a["snapshot_security"]["cusip"]
            assert r["date"] == a["snapshot_date"]
            assert a["snapshot_security"]["permco"] == a["pre_disclosure_security"]["permco"]
    for h, rows in outcomes.items():
        for old, new in zip(originals[h], rows, strict=True):
            assert old["stock_return"] == new["stock_return"]
            assert old["benchmark_return"] == new["spy_return"]
            assert old["excess"] == new["spy_excess"]
            assert (
                old["accessions"] == new["accessions"]
                and old["entry"] == new["entry"]
                and old["exit"] == new["exit"]
            )
            assert new["issuer"] not in protected and new["exit"] <= "2023-12-29"
        for group, s in summaries[h].items():
            subset = [
                r
                for r in rows
                if group == "all"
                or (group == "expanded" and r["expanded_manager"])
                or (group == "hfr_only" and r["hfr_only"])
                or r["disjoint_cohort"] == group
            ]
            valid = [r for r in subset if r["excess"] is not None]
            excluded = [r for r in subset if r["excess"] is None and r["spy_excess"] is not None]
            assert len(subset) == s["russell"]["scheduled"]
            assert (
                len(valid)
                == s["russell"]["calculated"]
                == s["spy_common"]["calculated"]
                == s["iwv_common"]["calculated"]
            )
            assert len(excluded) == s["excluded_spy"]["calculated"]
            for field, target in [
                ("excess", s["russell"]["mean_excess"]),
                ("spy_excess", s["spy_common"]["mean_excess"]),
                ("stock_return", s["russell"]["mean_stock"]),
            ]:
                assert math.isclose(
                    sum(r[field] for r in valid) / len(valid), target, abs_tol=1e-12
                )
    for link in re.findall(r'href="([^"]+)"', (OUT / "index.html").read_text()):
        if not link.startswith("https:"):
            assert (OUT / link).exists(), link
    QA.mkdir(parents=True, exist_ok=True)
    freeze(
        QA / "verification.json",
        encode(
            dict(
                hashes=True,
                pre_disclosure_monthly_assignments=True,
                exact_identifier_joins=True,
                original_stock_spy_parity=True,
                independent_common_sample_counts_means=True,
                protected_outcomes_excluded=True,
                report_links=True,
            )
        ),
    )
    for horizon, s in summaries.items():
        print("Horizon", horizon)
        for group, v in s.items():
            r = v["russell"]
            print(
                group,
                r["calculated"],
                "stock",
                round(r.get("mean_stock", 0) * 100, 2),
                "russell",
                round(r.get("mean_benchmark", 0) * 100, 2),
                "excess",
                round(r.get("mean_excess", 0) * 100, 2),
                "spy_excess",
                round(v["spy_common"].get("mean_excess", 0) * 100, 2),
                "CI",
                [round(x * 100, 2) for x in r.get("issuer_bootstrap_95", [])],
            )


if __name__ == "__main__":
    main()
