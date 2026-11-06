"""Verify and publish the requested Bloomberg terminal Markdown guide locally.

Purpose: Check the guide against preserved pilot inputs and copy it to Downloads.
Inputs: The October 27 pilot CSVs/handoff and the new November 4 Markdown.
Outputs: Identical Downloads guide, companion input copies, verification.json.
Identity: 10 unique events x 9 unique fields = 90 unique logical requests;
          embedded CSV bytes equal source text; copied artifacts retain SHA-256.
Tier: 1 (document/data-integrity assertions; no estimator or model is run).
Run: env PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     research/docs/bloomberg-terminal-guide-20261104/verify_guide.py
"""

import csv
import hashlib
import io
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "research/runs/bloomberg-remediation-handoff/20261027-v1"
GUIDE = OUT / "13D_Bloomberg_Terminal_Guide_20261104.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    text = GUIDE.read_text(encoding="utf-8")
    sources = {
        name: (SOURCE / name).read_text(encoding="utf-8")
        for name in ("pilot_events.csv", "field_dictionary.csv", "result_template.csv")
    }
    events = list(csv.DictReader(io.StringIO(sources["pilot_events.csv"])))
    fields = list(csv.DictReader(io.StringIO(sources["field_dictionary.csv"])))
    requests = list(csv.DictReader(io.StringIO(sources["result_template.csv"])))
    assert len(events) == len({row["row_id"] for row in events}) == 10
    assert len(fields) == len({row["field_id"] for row in fields}) == 9
    assert len(requests) == len({row["request_id"] for row in requests}) == 90
    expected = {(event["row_id"], field["field_id"]) for event in events for field in fields}
    assert {(row["row_id"], row["field_id"]) for row in requests} == expected
    assert all(row["status"] == "not_requested" and not row["raw_value"] and not row["value"] for row in requests)
    embedded = re.findall(r"~~~csv\n(.*?)\n~~~", text, re.DOTALL)
    assert len(embedded) == 3
    assert embedded[0] == sources["pilot_events.csv"].rstrip("\n")
    assert embedded[1] == sources["field_dictionary.csv"].rstrip("\n")
    assert embedded[2] == sources["result_template.csv"].splitlines()[0]
    controls = {
        "F01": ("0000863436", "2019-01-03", "08160H101"),
        "F06": ("0001124105", "2019-07-22", "14888D208"),
        "F10": ("0001646228", "2021-05-14", "04650Y100"),
    }
    for row in events:
        assert len(row["issuer_cik"]) == 10 and row["cutoff_timezone"] == "America/New_York"
        if row["case_id"] in controls:
            assert (row["issuer_cik"], row["as_of_date"], row["filing_cusip9_candidate"]) == controls[row["case_id"]]
    assert text.count("~~~") % 2 == 0
    assert all(token not in text for token in ("${events}", "${fields}", "${schema}", "turn87", "turn88"))
    downloads = Path.home() / "Downloads" / GUIDE.name
    if downloads.exists():
        assert digest(downloads) == digest(GUIDE), "Refuse to overwrite a different existing Downloads guide"
    else:
        shutil.copy2(GUIDE, downloads)
    assert digest(downloads) == digest(GUIDE)
    inputs = OUT / "inputs"
    inputs.mkdir(exist_ok=True)
    hashes = {}
    for name in sources:
        target = inputs / name
        if target.exists():
            assert digest(target) == digest(SOURCE / name)
        else:
            shutil.copy2(SOURCE / name, target)
        assert digest(target) == digest(SOURCE / name)
        hashes[name] = digest(target)
    receipt = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "guide": str(GUIDE),
        "downloads_copy": str(downloads),
        "guide_sha256": digest(GUIDE),
        "guide_words_whitespace": len(text.split()),
        "source_directory": str(SOURCE),
        "source_handoff_sha256": digest(SOURCE / "13D_Bloomberg_Extraction_20261027.handoff.txt"),
        "source_csv_sha256": hashes,
        "events": len(events),
        "fields": len(fields),
        "logical_requests": len(requests),
        "checks": "Exact embedded CSV parity; unique 10x9 coverage; blank prepared results; identifier/cutoff controls; byte-identical copies",
        "new_bloomberg_queries": 0,
    }
    (OUT / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
