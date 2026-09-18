"""Verify live-source pilot coverage and byte-identical offline reproduction.

Inputs: cached SEC pilot, source-backed JSONL, provenance sidecars.
Outputs: explicit assertions and a verification summary.
Identity: sha256(parsed outputs before replay) = sha256(outputs after replay).
Tier: 1
Run: .venv/bin/python scripts/verify_pilot.py (no network).
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    outputs = [ROOT / "data/interim/pilot" / name for name in ["filings.jsonl", "audit.json"]]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs]
    subprocess.run([sys.executable, str(ROOT / "scripts/collect_pilot.py"), "--offline"], check=True)
    assert before == [hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs]
    records = [json.loads(line) for line in outputs[0].read_text().splitlines()]
    assert len(records) == len({r["accession"] for r in records}) == 10
    for record in records:
        assert record["filers"] and record["subjects"] and record["item4_text"]
        assert hashlib.sha256((ROOT / record["source_path"]).read_bytes()).hexdigest() == record["source_sha256"]
    old = next(r for r in records if r["accession"] == "0001104659-24-000323")
    # Read directly from this submission's cover page and SGML header.
    assert old["cusip"] == "60743G100"
    assert old["event_date"] == "2023-12-21"
    assert old["filers"][0]["cik"] == "0001855211"
    new = next(r for r in records if r["accession"] == "0000807249-25-000003")
    # Read directly from XML coverPageHeader and item4/transactionPurpose.
    assert new["cusip"] == "G9001E102"
    assert new["event_date"] == "2024-12-27"
    assert new["item4_text"].startswith("Each of the Reporting Persons has purchased")
    print("VERIFIED: 10 unique filings; source hashes; two source-pinned examples; identical offline replay.")
    for record in records:
        print(record["accession"], record["cusip"], record["event_date"],
              len(record["item4_text"]), "Item 4 characters")


if __name__ == "__main__":
    main()
