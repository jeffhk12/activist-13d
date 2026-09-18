"""Collect a deterministic ten-filing SEC parser pilot, not an activist universe.

Inputs: full quarterly indexes for 2024 Q1 and 2025 Q1; full submission text.
Outputs: frozen raw submissions, parsed JSONL, and an audit summary.
Identity: five evenly spaced initial accessions per quarter after deduplication.
Tier: 1
Run: EDGAR_USER_AGENT='Name email' .venv/bin/python scripts/collect_pilot.py
     .venv/bin/python scripts/collect_pilot.py --offline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from activist13d.edgar.client import SecClient  # noqa: E402
from activist13d.edgar.index import distinct_filings, schedule_13  # noqa: E402
from activist13d.edgar.submission import parse_submission  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pilot_compatible(record: dict) -> dict:
    """Keep the frozen pilot JSONL schema stable; new fields live overnight."""
    copy = {key: value for key, value in record.items()
            if key not in {"item4_source_location", "evidence_bundle"}}
    copy["documents"] = [
        {key: value for key, value in document.items() if key != "source_document_index"}
        for document in record["documents"]
    ]
    return copy


def write_review(records: list[dict], audit: dict) -> None:
    """Render a readable inventory and full Item 4 review sheets from the JSONL."""
    output = ROOT / "output"
    sheets = output / "pilot-filings"
    sheets.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SEC pilot extraction", "",
        f"Downloaded and parsed {audit['n']} initial 13D filings: five from 2024 Q1 and five from 2025 Q1.",
        "This is an unscreened parser pilot, not a validated activist campaign dataset.", "",
        f"- Item 4 candidate passages found: {audit['item4_found']}/{audit['n']}.",
        f"- Filer and subject roles found: {audit['roles_found']}/{audit['n']}.",
        f"- CUSIP candidates found: {audit['cusip_found']}/{audit['n']}.",
        f"- Event dates found: {audit['event_date_found']}/{audit['n']}.",
        "- No LLM extraction, judge, or other paid API calls were made.", "",
        "| Filing date | Filer (header) | Subject (header) | Format | Review sheet |",
        "|---|---|---|---|---|",
    ]
    for record in records:
        accession = record["accession"]
        filer = "; ".join(p["name"] or "Unknown" for p in record["filers"])
        subject = "; ".join(p["name"] or "Unknown" for p in record["subjects"])
        lines.append(f"| {record['index_filing_date']} | {filer.replace('|', '/')} | "
                     f"{subject.replace('|', '/')} | {record['parser_source']} | "
                     f"[{accession}](pilot-filings/{accession}.md) |")
        sheet = [
            f"# {accession}", "", f"Filer (header): {filer}", "", f"Subject (header): {subject}", "",
            "Header names can differ from cover-page names after a rename or business combination.", "",
            f"- Filed: {record['index_filing_date']}",
            f"- Accepted (Eastern): {record['acceptance_datetime_et']}",
            f"- CUSIP candidate: {record['cusip']}",
            f"- Event date candidate: {record['event_date']}",
            f"- Item 4 extraction status: {record['item4_status']}",
            f"- Ownership status: {record['ownership_status']}",
            f"- [SEC complete submission]({record['source_url']})",
            f"- [Local raw submission]({ROOT / record['source_path']})",
            f"- Source SHA-256: `{record['source_sha256']}`", "",
            "## Item 4 candidate text — review required", "",
            record["item4_text"] or "Not located; review the raw submission.", "",
            "## Submitted documents", "",
        ]
        for doc in record["documents"]:
            sheet.append(f"- {doc['filename']} ({doc['type']}): {doc['text_status']}")
        for doc in record["documents"]:
            if doc["type"] and doc["type"].startswith("EX-"):
                sheet.extend(["", f"## Exhibit: {doc['filename']}", "",
                              doc["text"] or "Binary content retained in raw submission."])
        sheet.extend(["", "Full document/exhibit text and per-person XML fields are preserved in filings.jsonl.", ""])
        (sheets / f"{accession}.md").write_text("\n".join(sheet), encoding="utf-8")
    lines.extend(["", "## Next validation steps", "",
                  "Review Item 4 boundaries and referenced exhibits, screen actual activist intent, "
                  "resolve manager entities, and collect amendment chains. Legacy ownership percentages "
                  "are not yet parsed; XML ownership is retained per reporting person without aggregation.", ""])
    (output / "SEC-PILOT-REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    client = SecClient(offline=args.offline)
    records = []
    summary = []
    for year, quarter in [(2024, 1), (2025, 1)]:
        url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx"
        raw_path = ROOT / f"data/raw/edgar/pilot/index/form-{year}-QTR{quarter}.idx"
        payload = client.fetch(url, raw_path)
        rows = schedule_13(payload.decode("latin-1"))
        filings = distinct_filings(rows)
        initial = filings[filings["form"] == "13D"].sort_values(
            ["date_filed", "accession"]
        ).reset_index(drop=True)
        if len(initial) < 5:
            raise ValueError(f"Expected at least five initial filings in {year} Q{quarter}")
        sample = initial.iloc[[i * (len(initial) - 1) // 4 for i in range(5)]]
        summary.append({"year": year, "quarter": quarter, "initial_filings": len(initial)})
        for filing in sample.itertuples():
            url = "https://www.sec.gov/Archives/" + filing.path
            folder = ROOT / "data/raw/edgar/pilot/filings" / filing.accession
            payload = client.fetch(url, folder / "submission.txt")
            record = parse_submission(payload)
            if record["accession"] != filing.accession:
                raise ValueError("Submission accession does not match index")
            record.update({
                "source_url": url,
                "source_path": str((folder / "submission.txt").relative_to(ROOT)),
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "index_filing_date": filing.date_filed.date().isoformat(),
                "universe_status": "unscreened_initial_13d",
            })
            records.append(pilot_compatible(record))
            print(f"{filing.accession}: {record['parser_source']}, "
                  f"Item 4 {record['item4_status']}, {len(record['documents'])} documents", flush=True)
    out = ROOT / "data/interim/pilot"
    out.mkdir(parents=True, exist_ok=True)
    (out / "filings.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8"
    )
    audit = {
        "sampling": "five evenly spaced initial filings per quarter, by date then accession",
        "not_representative": True,
        "quarters": summary,
        "n": len(records),
        "item4_found": sum(bool(r["item4_text"]) for r in records),
        "roles_found": sum(bool(r["filers"] and r["subjects"]) for r in records),
        "cusip_found": sum(bool(r["cusip"]) for r in records),
        "event_date_found": sum(bool(r["event_date"]) for r in records),
        "no_llm_calls": True,
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    write_review(records, audit)
    print(json.dumps(audit, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
