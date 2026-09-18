"""Bounded, restartable SEC Schedule 13D discovery collection.

Inputs: cached and official SEC quarterly form.idx files plus complete filings.
Outputs: frozen raw evidence, a fixed 100-filing manifest, evidence bundles,
         metrics and a morning handoff.
Identity: sample = 10 retained pilot accessions + 90 lowest SHA-256 ranks per
          fixed period allocation; gap_cd = filing date - event date.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/collect_overnight.py
     PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/collect_overnight.py --offline
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from activist13d.edgar.client import SecClient  # noqa: E402
from activist13d.edgar.index import distinct_filings, schedule_13  # noqa: E402
from activist13d.edgar.submission import evidence_bundle, parse_submission  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/edgar/overnight"
INTERIM = ROOT / "data/interim/overnight"
OUTPUT = ROOT / "output/overnight"
PROGRESS = OUTPUT / "progress.json"
SEED = "activist-13d-overnight-2026-09-09-v1"
ALLOCATIONS = {"2013-2017": 23, "2018-2022": 23, "2023-2024": 22, "2025-2026": 22}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def progress(phase: str, status: str, **details: object) -> None:
    state = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {"phases": {}}
    state["updated_at_utc"] = utcnow()
    state["phases"][phase] = {"status": status, **details}
    write_json(PROGRESS, state)


def task_hash() -> str:
    return hashlib.sha256((ROOT / "docs/OVERNIGHT-TASK-2026-09-09.txt").read_bytes()).hexdigest()


def period(year: int) -> str:
    if year <= 2017:
        return "2013-2017"
    if year <= 2022:
        return "2018-2022"
    if year <= 2024:
        return "2023-2024"
    return "2025-2026"


def quarters() -> list[tuple[int, int, str]]:
    out = [(year, quarter, "completed") for year in range(2013, 2027)
           for quarter in range(1, 5) if (year < 2026 or quarter <= 2)]
    return out + [(2026, 3, "partial_through_retrieval_time")]


def index_url(year: int, quarter: int) -> str:
    return f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx"


def source_url(path: str) -> str:
    return "https://www.sec.gov/Archives/" + path


def contact_available() -> bool:
    """Load the local SEC contact without emitting its sensitive value."""
    contact = ROOT / "data/local/sec-contact.json"
    if not contact.exists():
        return False
    try:
        value = json.loads(contact.read_text(encoding="utf-8")).get("user_agent", "").strip()
    except (json.JSONDecodeError, OSError):
        return False
    if value:
        os.environ["EDGAR_USER_AGENT"] = value
        return True
    return False


def cache_index(client: SecClient, year: int, quarter: int) -> list[dict]:
    destination = RAW / "index" / f"form-{year}-QTR{quarter}.idx"
    metadata_path = INTERIM / "index-metadata" / f"{year}-QTR{quarter}.json"
    if metadata_path.exists():
        # Never trust an interrupted-run checkpoint merely because its derived
        # metadata exists. Re-reading through SecClient verifies the raw cache,
        # provenance sidecar, and SHA-256 without making a network call.
        payload = client.fetch(index_url(year, quarter), destination)
        rows = json.loads(metadata_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(payload).hexdigest()
        if any(row.get("index_source_sha256") != digest for row in rows):
            raise ValueError(f"Index metadata hash mismatch: {year} Q{quarter}")
        return rows
    payload = client.fetch(index_url(year, quarter), destination)
    filings = distinct_filings(schedule_13(payload.decode("latin-1")))
    rows = []
    for filing in filings.itertuples():
        rows.append({"accession": filing.accession, "form": filing.form,
                     "filing_date": filing.date_filed.date().isoformat(), "path": filing.path,
                     "ciks": [int(cik) for cik in filing.ciks], "parties": filing.parties,
                     "index_source_path": str(destination.relative_to(ROOT)),
                     "index_source_sha256": hashlib.sha256(payload).hexdigest()})
    write_json(metadata_path, rows)
    return rows


def collect_indexes(client: SecClient) -> tuple[list[dict], bool]:
    inventory, complete = [], True
    for year, quarter, status in quarters():
        try:
            rows = cache_index(client, year, quarter)
            inventory.append({"year": year, "quarter": quarter, "status": status,
                              "distinct_13d_family": len(rows)})
            print(f"{year} Q{quarter}: {len(rows)} distinct 13D-family filings", flush=True)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            complete = False
            inventory.append({"year": year, "quarter": quarter, "status": "failed",
                              "error": f"{type(exc).__name__}: {exc}"})
            # A stopped live collector may still use already cached independent quarters offline.
            if not client.offline:
                break
    write_json(INTERIM / "index-inventory.json", inventory)
    return inventory, complete


def pilot_records() -> list[dict]:
    path = ROOT / "data/interim/pilot/filings.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(records) != 10 or len({record["accession"] for record in records}) != 10:
        raise ValueError("The retained pilot must contain ten distinct accessions")
    for record in records:
        raw = ROOT / record["source_path"]
        if hashlib.sha256(raw.read_bytes()).hexdigest() != record["source_sha256"]:
            raise ValueError(f"Pilot source hash mismatch: {record['accession']}")
        record["sample_origin"] = "retained_pilot"
        record["evidence_bundle"] = evidence_bundle(record)
    return records


def rank(accession: str) -> str:
    return hashlib.sha256(f"{SEED}:{accession}".encode()).hexdigest()


def select_expansion(pilot: list[dict]) -> list[dict]:
    """Keep bounded heaps: no full-index rows are retained across years."""
    pilot_ids = {record["accession"] for record in pilot}
    heaps: dict[str, list[tuple[str, str, dict]]] = {key: [] for key in ALLOCATIONS}
    for metadata_path in sorted((INTERIM / "index-metadata").glob("*.json")):
        for row in json.loads(metadata_path.read_text(encoding="utf-8")):
            if row["form"] != "13D" or row["accession"] in pilot_ids:
                continue
            bucket = period(int(row["filing_date"][:4]))
            value = rank(row["accession"])
            entry = ("".join(chr(255 - ord(char)) for char in value), row["accession"], row)
            heap = heaps[bucket]
            heapq.heappush(heap, entry)
            if len(heap) > ALLOCATIONS[bucket]:
                heapq.heappop(heap)
    selected = []
    for bucket, allocation in ALLOCATIONS.items():
        if len(heaps[bucket]) < allocation:
            raise ValueError(f"Insufficient initial filings for {bucket}")
        chosen = [entry[2] for entry in heaps[bucket]]
        for row in sorted(chosen, key=lambda item: (rank(item["accession"]), item["accession"])):
            row["sample_origin"] = "expanded_deterministic"
            row["sampling_period"] = bucket
            row["selection_rank_sha256"] = rank(row["accession"])
            selected.append(row)
    return selected


def freeze_manifest(pilot: list[dict], expansion: list[dict]) -> list[dict]:
    manifest = []
    for record in pilot:
        manifest.append({"accession": record["accession"], "sample_origin": "retained_pilot",
                         "filing_date": record["index_filing_date"], "source_path": record["source_path"]})
    manifest.extend(expansion)
    if len(manifest) != 100 or len({row["accession"] for row in manifest}) != 100:
        raise ValueError("Manifest must freeze exactly 100 distinct accessions")
    write_json(INTERIM / "sample-manifest.json", {"seed": SEED, "allocations": ALLOCATIONS,
               "not_representative": True, "frozen_at_utc": utcnow(), "records": manifest})
    return manifest


def parse_expansion(client: SecClient, manifest: list[dict], pilot: list[dict]) -> tuple[list[dict], list[dict]]:
    records, failures = list(pilot), []
    for row in manifest:
        if row["sample_origin"] == "retained_pilot":
            continue
        destination = RAW / "filings" / row["accession"] / "submission.txt"
        try:
            payload = client.fetch(source_url(row["path"]), destination)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            failures.append({"accession": row["accession"], "phase": "submission_fetch",
                             "error": f"{type(exc).__name__}: {exc}"})
            # These are collection-wide boundaries: missing offline evidence,
            # exhausted budget, or broken cache provenance. Continuing would
            # misrepresent the frozen manifest as fully attempted.
            if not client.offline:
                break
            continue
        try:
            record = parse_submission(payload)
            if record["accession"] != row["accession"]:
                raise ValueError("submission accession does not match frozen manifest")
            record.update({"source_url": source_url(row["path"]),
                           "source_path": str(destination.relative_to(ROOT)),
                           "source_sha256": hashlib.sha256(payload).hexdigest(),
                           "index_filing_date": row["filing_date"], "universe_status": "unscreened_initial_13d",
                           "sample_origin": row["sample_origin"], "sampling_period": row["sampling_period"],
                           "selection_rank_sha256": row["selection_rank_sha256"]})
            record["evidence_bundle"] = evidence_bundle(record)
            records.append(record)
        except Exception as exc:  # preserves a parsable queue instead of fabricating a record
            failures.append({"accession": row["accession"], "phase": "submission_parse",
                             "error": f"{type(exc).__name__}: {exc}"})
            # Parser failures are filing-local. The original batch erroneously
            # stopped here after the first ambiguous submission.
            continue
    return records, failures


def write_records(records: list[dict], failures: list[dict]) -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    (INTERIM / "records.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8"
    )
    for record in records:
        write_json(INTERIM / "evidence" / f"{record['accession']}.json", {
            "accession": record["accession"], "source_sha256": record["source_sha256"],
            "bundle": record["evidence_bundle"],
        })
    write_json(INTERIM / "parser-failure-queue.json", failures)


def render_eda(records: list[dict], failures: list[dict]) -> dict:
    gaps = []
    for record in records:
        try:
            event = record.get("event_date")
            gaps.append((date.fromisoformat(record["index_filing_date"]) - date.fromisoformat(event)).days if event else None)
        except ValueError:
            gaps.append(None)
    documents = [document for record in records for document in record["documents"]]
    unresolved = sum(1 for record in records for group in ("referenced_sections", "referenced_exhibits")
                     for reference in record["evidence_bundle"][group]
                     if reference["status"] == "unresolved_or_external")
    metrics = {"n": len(records), "not_representative": True, "periods": dict(Counter(
        record.get("sampling_period", "retained_pilot") for record in records)),
        "formats": dict(Counter(record["parser_source"] for record in records)),
        "missingness": {key: sum(not bool(record.get(key)) for record in records)
                        for key in ("item4_text", "event_date", "cusip")},
        "document_counts": {"total": len(documents), "per_filing": len(documents) / len(records) if records else 0},
        "candidate_date_gaps_calendar_days": {"n": sum(value is not None for value in gaps),
                                                "values": gaps},
        "unresolved_references": unresolved, "parser_failure_queue": failures,
        "source_hashes": {record["accession"]: record["source_sha256"] for record in records},
        "instruction_sha256": task_hash(), "generated_at_utc": utcnow()}
    lines = ["# Overnight discovery EDA", "", "This is an unscreened deterministic filing sample, not a representative prevalence estimate.", "",
             f"- n: {metrics['n']}", f"- Formats: {metrics['formats']}", f"- Periods: {metrics['periods']}",
             f"- Missingness: {metrics['missingness']}", f"- Documents: {metrics['document_counts']}",
             f"- Candidate event-date gaps (calendar days): {metrics['candidate_date_gaps_calendar_days']}",
             f"- Unresolved/external references: {unresolved}", f"- Parser failure queue: {len(failures)}", "",
             "Every record's source SHA-256 is in `metrics.json`. Candidate date gaps are descriptive only and make no legal judgment."]
    write_json(OUTPUT / "metrics.json", metrics)
    (OUTPUT / "EDA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def handoff(status: str, inventory: list[dict], records: list[dict], failures: list[dict], reason: str | None) -> None:
    budget = json.loads((OUTPUT / "budget.json").read_text()) if (OUTPUT / "budget.json").exists() else {"successful_requests": 0, "new_raw_bytes": 0}
    lines = ["# Morning handoff", "", f"Status: **{status}**.", "",
             "## Completed", "", "- Offline baseline and bounded restartable collector implementation.",
             "- Retained-pilot source-hash verification and evidence-bundle generation.", "",
             "## Collection", "", f"- Reason: {reason or 'completed'}.",
             f"- SEC successful new requests: {budget['successful_requests']}/200; new raw bytes: {budget['new_raw_bytes']}/3221225472.",
             f"- Index inventory entries: {len(inventory)}; parsed records: {len(records)}; parser failures: {len(failures)}.",
             "- Amendments: skipped unless the full initial-filing manifest and submission phase complete; issuer CIK alone is never treated as a verified campaign join.", "",
             "## Rerun", "", "```sh", "PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest -m 'not network'",
             "PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m ruff check .",
             "PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/collect_overnight.py",
             "```", "", "No model API calls or semantic evidence-bundle review were performed in this run."]
    (OUTPUT / "MORNING-HANDOFF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    progress("setup", "completed", instruction_sha256=task_hash(), seed=SEED)
    pilot = pilot_records()
    progress("pilot_validation", "completed", retained_pilot_n=len(pilot))
    # The second and final contact check is intentionally after code/tests preparation.
    has_contact = contact_available()
    if not has_contact and not args.offline:
        progress("live_collection", "blocked", reason="SEC contact missing after second check")
        write_records(pilot, [])
        render_eda(pilot, [])
        handoff("blocked", [], pilot, [], "EDGAR_USER_AGENT absent from data/local/sec-contact.json")
        return
    client = SecClient(offline=args.offline, budget_path=OUTPUT / "budget.json")
    inventory, complete = collect_indexes(client)
    progress("index_collection", "completed" if complete else "partial", inventory=inventory)
    if not complete:
        write_records(pilot, [])
        render_eda(pilot, [])
        handoff("partial", inventory, pilot, [], "index collection incomplete; manifest not frozen")
        return
    expansion = select_expansion(pilot)
    manifest = freeze_manifest(pilot, expansion)
    progress("manifest", "completed", n=len(manifest), allocations=ALLOCATIONS)
    records, failures = parse_expansion(client, manifest, pilot)
    write_records(records, failures)
    progress("submission_collection", "completed" if len(records) == 100 else "partial", n=len(records), failures=failures)
    render_eda(records, failures)
    handoff("completed" if len(records) == 100 else "partial", inventory, records, failures, None)


if __name__ == "__main__":
    main()
