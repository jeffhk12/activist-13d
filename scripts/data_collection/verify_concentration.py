"""Tier: 1. Independent arithmetic and evidence checks for concentration report.
Inputs: frozen diagnostic/event/source files. Outputs: separate verification JSON.
Identity: all group contributions sum to original mean; deletions recomputed.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_concentration.py
"""

import json
import math
import re

from run_concentration import BASE, OUT, ROOT
from run_phase1_development import digest, encode, freeze


def main():
    provenance = json.loads((OUT / "provenance.json").read_text())
    for root, key in [(OUT, "outputs"), (ROOT, "inputs")]:
        for name, expected in provenance[key].items():
            assert digest(root / name) == expected, name
    events = json.loads((OUT / "events.json").read_text())
    d = json.loads((OUT / "diagnostics.json").read_text())
    old = json.loads((BASE / "outcomes.json").read_text())
    for h, rows in events.items():
        source = [r for r in old[h] if r["focused"] and r["excess"] is not None]
        assert [{k: r[k] for k in s} for r, s in zip(rows, source, strict=True)] == source
        mean = sum(r["excess"] for r in rows) / len(rows)
        assert math.isclose(mean, d[h]["overall"]["mean"], abs_tol=1e-12)
        for dimension, groups in d[h]["groups"].items():
            assert math.isclose(
                sum(v["contribution"] for v in groups.values()), mean, abs_tol=1e-12
            )
            for k, s in groups.items():
                remain = [
                    r
                    for r in rows
                    if (k not in r["managers"] if dimension == "manager" else r[dimension] != k)
                ]
                assert len(remain) == s["leave_out"]["n"]
                if remain:
                    assert math.isclose(
                        sum(r["excess"] for r in remain) / len(remain),
                        s["leave_out"]["mean"],
                        abs_tol=1e-12,
                    )
        ordered = sorted(rows, key=lambda r: (-r["excess"], r["accession"], r["entry"]))
        for removal in d[h]["removals"]:
            k = removal["removed_events"]
            remain = ordered[k:]
            assert len(remain) == removal["without_top_events"]["n"]
            assert math.isclose(
                sum(r["excess"] for r in remain) / len(remain),
                removal["without_top_events"]["mean"],
                abs_tol=1e-12,
            )
    for link in re.findall(r'href="([^"]+)"', (OUT / "index.html").read_text()):
        assert (OUT / link).exists(), link
    qa = OUT.parent / "20260924-concentration-verification-v1"
    freeze(
        qa / "verification.json",
        encode(
            dict(
                source_output_hashes=True,
                original_event_parity=True,
                independent_mean_contributions_removals=True,
                report_links=True,
            )
        ),
    )
    print("Independent verification passed")


if __name__ == "__main__":
    main()
