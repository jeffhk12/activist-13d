"""Offline integrity follow-up for the completed Phase 1 preparation.

Reads a completed preparation run, its frozen records and manifest, cached SEC
submissions/indexes, and co-located provenance metadata. Writes an isolated
audit run containing date, index-row, hash, lockfile/package, and packet
replay checks. Identity: every recorded filing date must equal both the raw
``FILED AS OF DATE`` header and its independent raw index row. A sidecar hash
is consistency evidence, not an external authenticity anchor.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_prep/integrity_followup.py
"""

import hashlib
import importlib.metadata
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from run import packet

ROOT = Path(__file__).resolve().parents[2]
COMPLETED = ROOT / "output/phase1-prep/20260914T003050627334Z"
RAW = (ROOT / "data/raw/edgar").resolve()
INDEX_ROW = re.compile(
    r"^(?P<form>\S+(?: \S+)*?)\s{2,}(?P<company>.*?)\s+"
    r"(?P<cik>\d+)\s+"
    r"(?P<filing_date>\d{4}-\d{2}-\d{2})\s+(?P<path>edgar/\S+)\s*$"
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("path outside approved root")
    return path


def verify_packet(path: Path, expected: str | None = None) -> dict:
    if not path.is_file():
        return {"status": "missing"}
    actual = digest(path)
    return {"status": "verified" if expected is None or actual == expected else "integrity_failure",
            "sha256": actual, "bytes": path.stat().st_size}


def filed_as_of(raw: bytes) -> str | None:
    match = re.search(rb"FILED AS OF DATE:\s*(\d{8})", raw[:4096])
    if not match:
        return None
    value = match.group(1).decode()
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None
    return parsed.isoformat()


def index_rows(index_paths: list[Path], accessions: set[str]) -> dict[str, dict]:
    found = {}
    for path in index_paths:
        with path.open("r", encoding="latin-1") as stream:
            for line in stream:
                if not line or line.startswith(("Description:", "Last Data", "Comments:", "Form ")):
                    continue
                match = INDEX_ROW.match(line.rstrip("\n"))
                if not match:
                    continue
                fields = match.groupdict()
                form, company, cik = fields["form"], fields["company"], fields["cik"]
                date_filed, source = fields["filing_date"], fields["path"]
                accession = Path(source).stem
                if accession in accessions:
                    row = {"form": form, "company": company, "cik": cik,
                           "filing_date": date_filed, "path": source, "index_path": str(path)}
                    # SEC indexes repeat one accession under filer/issuer CIK
                    # directories; path and company can legitimately differ.
                    if accession in found and any(found[accession][key] != row[key] for key in ("filing_date", "form")):
                        raise ValueError(f"conflicting raw index rows for {accession}")
                    found[accession] = row
    return found


def verify_submission(source: Path, record: dict) -> bytes:
    """Validate containment, URL, byte count, and both recorded digests."""
    source = source.resolve()
    if not source.is_relative_to(RAW.resolve()):
        raise ValueError("source path outside raw SEC cache")
    sidecar = Path(str(source) + ".meta.json")
    meta = json.loads(sidecar.read_text())
    raw = source.read_bytes()
    if record.get("source_url") != meta.get("url"):
        raise ValueError("source URL disagrees with sidecar")
    if len(raw) != meta.get("bytes") or digest(source) != meta.get("sha256"):
        raise ValueError("submission sidecar mismatch")
    if digest(source) != record.get("source_sha256"):
        raise ValueError("submission hash mismatch")
    return raw


def verify_dates(header_date, *recorded_dates):
    if header_date is None or any(value != header_date for value in recorded_dates):
        raise ValueError("filing date missing or disagrees across sources")


def package_provenance() -> dict:
    files = ["pyproject.toml", "requirements.txt", "requirements-ci.txt", "requirements-pilot-lock.txt"]
    files += ["output/overnight/collector.lock", "output/overnight/worker.lock"]
    result = {name: {"sha256": digest(ROOT / name), "bytes": (ROOT / name).stat().st_size}
              for name in files if (ROOT / name).is_file()}
    packages = {}
    for name in ("beautifulsoup4", "lxml", "numpy", "pandas", "pydantic", "pytest", "requests", "ruff"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"files": result, "packages": packages}


def audit(completed: Path = COMPLETED, output: Path | None = None) -> tuple[Path, dict]:
    records_path = ROOT / "data/interim/overnight/records.jsonl"
    manifest_path = ROOT / "data/interim/overnight/sample-manifest.json"
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    manifest_rows = json.loads(manifest_path.read_text())["records"]
    manifest = {row["accession"]: row for row in manifest_rows}
    if not manifest or len(manifest) != len(manifest_rows) or len({r["accession"] for r in records}) != len(records) or {r["accession"] for r in records} != set(manifest):
        raise ValueError("manifest and records must have identical nonempty unique accession sets")
    recorded_index = {}
    recorded_index_hashes = {}
    metadata_hashes = {}
    for metadata_path in sorted((ROOT / "data/interim/overnight/index-metadata").glob("*.json")):
        metadata_hashes[str(metadata_path.relative_to(ROOT))] = digest(metadata_path)
        for row in json.loads(metadata_path.read_text()):
            recorded_index_hashes.setdefault(row["index_source_path"], set()).add(row["index_source_sha256"])
            if row["accession"] in manifest:
                if row["accession"] in recorded_index and recorded_index[row["accession"]] != row:
                    raise ValueError("conflicting recorded index metadata")
                recorded_index[row["accession"]] = row
    index_paths = sorted((ROOT / "data/raw/edgar/overnight/index").glob("form-*.idx"))
    rows = index_rows(index_paths, {r["accession"] for r in records})
    index_audit = []
    for path in index_paths:
        sidecar = Path(str(path) + ".meta.json")
        meta = json.loads(sidecar.read_text())
        actual = digest(path)
        recorded_hashes = recorded_index_hashes.get(str(path.relative_to(ROOT)), set())
        index_audit.append({"path": str(path.relative_to(ROOT)), "sha256": actual,
                            "bytes": path.stat().st_size, "sidecar_sha256": digest(sidecar),
                            "recorded_sha256": meta.get("sha256"), "recorded_bytes": meta.get("bytes"),
                            "independently_recorded_hashes": sorted(recorded_hashes),
                            "status": "verified" if actual == meta.get("sha256") and path.stat().st_size == meta.get("bytes") and recorded_hashes == {actual} else "refused"})
    index_digests = {str(ROOT / item["path"]): item["sha256"] for item in index_audit}
    findings = []
    for record in records:
        accession = record["accession"]
        try:
            if accession not in manifest:
                raise ValueError("missing from manifest")
            source = _safe(ROOT, record["source_path"])
            raw = verify_submission(source, record)
            header_date = filed_as_of(raw)
            row = rows.get(accession)
            if not row:
                raise ValueError("accession absent from raw index")
            metadata_row = recorded_index.get(accession)
            if not metadata_row or metadata_row.get("filing_date") != row["filing_date"]:
                raise ValueError("recorded index metadata disagrees with raw index row")
            if metadata_row.get("index_source_sha256") != index_digests.get(row["index_path"]):
                raise ValueError("recorded index metadata hash disagrees with raw index")
            verify_dates(header_date, record.get("index_filing_date"), row["filing_date"], manifest[accession].get("filing_date"))
            if Path(record["source_url"].rsplit("/", 1)[-1]).stem != accession:
                raise ValueError("source URL accession mismatch")
            findings.append({"accession": accession, "status": "verified", "header_date": header_date,
                             "index_date": row["filing_date"], "index_path": row["index_path"]})
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            findings.append({"accession": accession, "status": "refused", "error": str(error)})
    inventory_path = completed / "candidate-inventory.json"
    inventory = json.loads(inventory_path.read_text()) if inventory_path.is_file() else []
    inventory_by_accession = {r["accession"]: r for r in inventory}
    reparsed_path = completed / "reparsed-records.jsonl"
    reparsed = [json.loads(line) for line in reparsed_path.read_text().splitlines() if line.strip()] if reparsed_path.is_file() else []
    reparsed_by_accession = {r["accession"]: r for r in reparsed}
    packet_before = {p.name: digest(p) for p in sorted((completed / "packets").glob("*.html"))}
    inventory_dates = {r["accession"]: r.get("filing_date") for r in inventory}
    inventory_dates_match = all(inventory_dates.get(r["accession"]) == r.get("header_date") for r in findings if r["status"] == "verified")
    packet_sets_match = (set(manifest) == set(inventory_by_accession) == set(reparsed_by_accession)
                         == {Path(name).stem for name in packet_before})
    packet_render_match = packet_sets_match and all(
        (completed / "packets" / f"{accession}.html").read_text() == packet(record, inventory_by_accession[accession])
        for accession, record in reparsed_by_accession.items()
    )
    packet_after = {p.name: digest(p) for p in sorted((completed / "packets").glob("*.html"))}
    packet_replay = packet_before == packet_after
    index_sets_match = {str(p.relative_to(ROOT)) for p in index_paths} == set(recorded_index_hashes)
    result = {"status": "verified" if all(x["status"] == "verified" for x in findings) and all(x["status"] == "verified" for x in index_audit) and packet_replay and packet_render_match and inventory_dates_match and index_sets_match else "refused",
              "n_records": len(records), "verified_records": sum(x["status"] == "verified" for x in findings),
              "n_index_files": len(index_paths), "n_index_rows": len(rows), "filings": findings,
              "index_audit": index_audit, "packet_hashes_before": packet_before,
              "packet_hashes_after": packet_after, "packet_hash_count": len(packet_before),
              "old_packets_unchanged": packet_replay,
              "packet_render_match": packet_render_match,
              "inventory_dates_match": inventory_dates_match, "index_sets_match": index_sets_match,
              "packet_replay_note": "Only unchanged during this audit; no external prior hash anchor exists.",
              "package_provenance": package_provenance(),
              "source_records_sha256": digest(records_path), "manifest_sha256": digest(manifest_path),
              "worker_sha256": digest(ROOT / "scripts/phase1_prep/run.py"),
              "audit_script_sha256": digest(Path(__file__)), "index_metadata_hashes": metadata_hashes,
              "inventory_sha256": digest(inventory_path), "reparsed_sha256": digest(reparsed_path),
              "network_calls": 0, "model_api_calls": 0,
              "completed_run": str(completed.relative_to(ROOT))}
    output = output or ROOT / "output/phase1-prep" / ("integrity-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "REPORT.md").write_text("# Phase 1 integrity follow-up\n\n```json\n" + json.dumps({k: result[k] for k in ("status", "n_records", "verified_records", "n_index_files", "n_index_rows", "packet_hash_count", "old_packets_unchanged", "packet_render_match", "inventory_dates_match", "index_sets_match")}, indent=2) + "\n```\n\nSupersedes earlier integrity follow-up outputs. All index bytes are compared with both sidecars and separately recorded index metadata hashes. Filing dates agree across raw headers, raw index rows, manifest, prior records, and packet inventory. Original blank packets match deterministic rendering from the completed run. These are local consistency checks, not external authentication or semantic validation. Full hashes and package provenance are in audit.json. No network or model API calls.\n")
    return output, result


if __name__ == "__main__":
    path, result = audit()
    print(json.dumps({"output": str(path), "status": result["status"], "verified_records": result["verified_records"]}, indent=2))
