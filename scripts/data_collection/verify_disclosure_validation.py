"""Tier: 1. Verify disclosure citations, source identities and sensitivity arithmetic.
Inputs: immutable audit, raw SEC sources and original development events.
Outputs: separate QA receipt. Identity: exact source hashes/spans and group sums.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_disclosure_validation.py
"""

import hashlib
import json
import math
import re

from run_disclosure_validation import BBB, CONC, OUT, REG, ROOT
from run_phase1_development import digest, encode, freeze

from activist13d.edgar.submission import parse_submission


def main():
    prov = json.loads((OUT / "provenance.json").read_text())
    for root, key in [(OUT, "outputs"), (ROOT, "inputs"), (ROOT, "raw_sources")]:
        for name, expected in prov[key].items():
            assert digest(root / name) == expected, name
    registry = {
        r["accession"]: r for line in REG.read_text().splitlines() if (r := json.loads(line))
    }
    audits = json.loads((OUT / "filing-audit.json").read_text())
    reviews = json.loads((OUT / "relationship-reviews.json").read_text())
    for audit in audits:
        a = audit["accession"]
        r = registry[a]
        parsed = parse_submission((ROOT / audit["source_path"]).read_bytes())
        assert parsed["acceptance_datetime_et"] == r["acceptance_datetime_et"]
        assert {s["cik"] for s in parsed["subjects"]} == {s["cik"] for s in r["subjects"]}
        docs = json.loads((OUT / "documents" / f"{a}.json").read_text())["documents"]
        by_index = {d["source_document_index"]: d for d in docs}
        citations = audit["cover_flags"] + audit["numbered_body_mentions"]
        citations += [
            c for review in reviews if review["accession"] == a for c in review["citations"]
        ]
        for c in citations:
            d = by_index[c["document_id"]]
            t = d["text"]
            assert hashlib.sha256(t.encode()).hexdigest() == c["text_sha256"]
            assert t[c["start"] : c["end"]] == c["quote"]
            assert d["filename"] == c["filename"]
    bad = {r["accession"] for r in audits if r["excluded_amendment"]}
    assert bad == {"0000928464-20-000019", "0000928464-20-000021"}
    events = json.loads((CONC / "events.json").read_text())
    sensitivity = json.loads((OUT / "sensitivity.json").read_text())
    protected = set(
        json.loads(
            (OUT.parent / "20260924-development-v4/human-review-protection.json").read_text()
        )["issuers"]
    )
    for h, rows in events.items():
        assert all(r["issuer"] not in protected and r["exit"] <= "2023-12-29" for r in rows)
        clean = [r for r in rows if not set(r["accessions"]) & bad]
        variants = {
            "original": rows,
            "exclude_numbered_amendments": clean,
            "also_exclude_prior_BBBY_campaign": [r for r in clean if BBB not in r["accessions"]],
            "clean_exclude_2020": [r for r in clean if r["year"] != "2020"],
            "clean_exclude_2020Q2": [
                r for r in clean if not "2020-04-01" <= r["entry"] <= "2020-06-30"
            ],
        }
        for k, v in variants.items():
            s = sensitivity[h][k]
            assert len(v) == s["calculated"]
            assert math.isclose(
                sum(r["excess"] for r in v) / len(v), s["mean_excess"], abs_tol=1e-12
            )
    expos = json.loads((OUT / "exposures.json").read_text())
    for name, dimensions in expos.items():
        for groups in dimensions.values():
            assert sum(s["n"] for s in groups.values()) == sensitivity["252"][name]["calculated"]
            assert math.isclose(
                sum(s["contribution"] for s in groups.values()),
                sensitivity["252"][name]["mean_excess"],
                abs_tol=1e-12,
            )
    for p in [OUT / "index.html", *sorted((OUT / "documents").glob("*.html"))]:
        for link in re.findall(r'href="([^"]+)"', p.read_text()):
            if not link.startswith("https:"):
                assert (p.parent / link).exists(), link
    qa = OUT.parent / "20260924-disclosure-verification-v1"
    freeze(
        qa / "verification.json",
        encode(
            dict(
                source_hashes=True,
                acceptance_dates_issuer_ids=True,
                exact_citation_spans=True,
                sensitivity_means_counts=True,
                exposure_contributions=True,
                protected_boundaries=True,
                local_links=True,
            )
        ),
    )
    print("Independent verification passed")


if __name__ == "__main__":
    main()
