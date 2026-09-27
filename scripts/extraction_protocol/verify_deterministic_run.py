"""Verify completed deterministic facts against frozen evidence and output links.

Inputs: 52 records, manifests, source bundles, generated HTML and source snapshot.
Output: verification.json, optionally FINALIZED.json to prevent accidental reruns.
Identity: hashes/citations match; table rows equal joined per-filing records.
Tier: 1. Run with project .venv/bin/python and PYTHONNOUSERSITE/PYTHONIOENCODING.
"""

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from run_deterministic import OUT, PACK, TABLES, encode, validate  # noqa: E402

from activist13d.edgar.deterministic import sha, verify_citations  # noqa: E402


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


def main(finalize=False):
    manifest = json.loads((OUT / "input-manifest.json").read_text())
    records = []
    citation_count = 0
    for row in manifest:
        bundle_path = ROOT / row["bundle_path"]
        raw_path = ROOT / row["source_path"]
        assert sha(bundle_path.read_bytes()) == row["bundle_sha256"]
        assert sha(raw_path.read_bytes()) == row["expected_source_sha256"]
        bundle = json.loads(bundle_path.read_text())
        record = json.loads((OUT / "records" / f"{row['accession']}.json").read_text())
        assert record["filings"][0]["parsing_status"] == "processed"
        validate(record, bundle)
        citation_count += verify_citations(record, bundle)
        records.append(record)
    assert len(records) == 52
    for table in TABLES:
        stored = [
            json.loads(line)
            for line in (OUT / "tables" / f"{table}.jsonl").read_text().splitlines()
        ]
        assert stored == [row for record in records for row in record[table]], table
    first = next(r for r in records if r["accession"] == "0000899140-19-000386")
    assert len(first["reporting_persons"]) == len(first["ownership"]) == 11
    assert first["ownership"][0]["aggregate_shares"]["value"] == 1641562
    assert first["ownership"][0]["percent_of_class"]["value"] == "9.82"
    assert first["securities"][0]["cusip"]["value"] == "598039105"
    assert first["filings"][0]["event_date"]["value"] == "2019-04-30"
    htmls = list(PACK.glob("*.html"))
    checked_links = 0
    for path in htmls:
        parser = Links()
        parser.feed(path.read_text())
        for link in parser.links:
            parts = urlsplit(link)
            if not parts.scheme and parts.path:
                assert (path.parent / unquote(parts.path)).resolve().exists(), (path, link)
                checked_links += 1
    provenance = json.loads((OUT / "provenance.json").read_text())
    for relative, digest in provenance["source_hashes"].items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
        assert sha((OUT / "code" / relative).read_bytes()) == digest, relative
    results = {
        "status": "passed",
        "accessions": 52,
        "raw_and_bundle_hashes_verified": 52,
        "exact_text_citations_including_issue_copies": citation_count,
        "related_table_parity": "passed",
        "first_filing_source_pins": "passed",
        "html_files_checked": len(htmls),
        "local_links_checked": checked_links,
        "source_snapshot_matches_working_code": True,
        "limitations": [
            "No browser surface available for visual inspection; HTML source and links checked.",
            "Availability is not semantic accuracy.",
            "No empirical XML in the 52; synthetic tests cover supported XML paths.",
        ],
    }
    test_report = ElementTree.parse(OUT / "offline-tests.xml")
    suites = list(test_report.getroot().iter("testsuite"))
    results["offline_tests"] = {
        key: sum(int(s.get(key, 0)) for s in suites)
        for key in ["tests", "failures", "errors", "skipped"]
    }
    assert results["offline_tests"]["failures"] == results["offline_tests"]["errors"] == 0
    results["test_scope_note"] = (
        "Final test run explicitly excluded network-marked tests. An earlier broad invocation attempted one existing SEC index test; HTTP403, no dataset download."
    )
    (OUT / "verification.json").write_text(encode(results))
    if finalize:
        hashes = {
            str(p.relative_to(OUT)): sha(p.read_bytes())
            for p in sorted(OUT.rglob("*"))
            if p.is_file() and p.name != "FINALIZED.json"
        }
        (OUT / "FINALIZED.json").write_text(encode({"status": "handed_off", "file_sha256": hashes}))
    print(encode(results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    main(parser.parse_args().finalize)
