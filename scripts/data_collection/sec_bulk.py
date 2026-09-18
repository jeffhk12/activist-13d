"""Freeze and collect the complete 2013-current Schedule 13D filing family.

Inputs: 55 verified cached quarterly index inventories, an optional append-only
current-quarter index snapshot, and official SEC complete-submission URLs.
Outputs: immutable submission bytes plus provenance sidecars, a frozen manifest,
and restart/progress/failure records under the bulk-v1 namespace.
Identity: sha256(submission bytes) = sidecar sha256; one manifest row per accession.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/sec_bulk.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from activist13d.file_lock import acquire_exclusive  # noqa: E402

RAW = ROOT / "data/raw/edgar/bulk-v1"
INTERIM = ROOT / "data/interim/bulk-v1"
OUTPUT = ROOT / "output/data-collection/sec"
MANIFEST = INTERIM / "sec-manifest.json"
PROGRESS = OUTPUT / "progress.json"
FAILURES = OUTPUT / "failures.jsonl"
BASE = "https://www.sec.gov/Archives/"
MIN_INTERVAL_SECONDS = 0.5
MIN_FREE_BYTES = 20 * 1024**3
MAX_RESPONSE_BYTES = 250 * 1024**2


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_submission(payload: bytes, accession: str, filing_date: str) -> None:
    """Refuse generic pages and submissions that do not match the index row."""
    header = payload[:256 * 1024].decode("latin-1", errors="replace")
    accession_match = re.search(r"(?mi)^ACCESSION NUMBER:\s*([0-9-]+)\s*$", header)
    filed_match = re.search(r"(?mi)^FILED AS OF DATE:\s*(\d{8})\s*$", header)
    if not accession_match or not filed_match:
        raise ValueError("response is not a complete SEC submission with required header fields")
    if accession_match.group(1) != accession:
        raise ValueError(f"submission accession mismatch: expected {accession}")
    if filed_match.group(1) != filing_date.replace("-", ""):
        raise ValueError(f"submission filing-date mismatch: expected {filing_date}")


def load_contact() -> str:
    value = os.environ.get("EDGAR_USER_AGENT", "").strip()
    contact_path = ROOT / "data/local/sec-contact.json"
    if not value and contact_path.exists():
        try:
            value = str(json.loads(contact_path.read_text(encoding="utf-8")).get("user_agent", "")).strip()
        except (OSError, json.JSONDecodeError):
            value = ""
    if not re.search(r"\S+@\S+\.\S+", value) or "example." in value:
        raise ValueError("EDGAR_USER_AGENT must contain a real contact email")
    return value


def verified_existing() -> dict[str, dict]:
    """Return the old 100 caches only after byte, URL and sidecar checks."""
    found: dict[str, dict] = {}
    for collection in ("pilot", "overnight"):
        for path in sorted((ROOT / f"data/raw/edgar/{collection}/filings").glob("*/submission.txt")):
            accession = path.parent.name
            meta_path = path.with_suffix(path.suffix + ".meta.json")
            if not meta_path.exists():
                raise ValueError(f"Existing SEC cache lacks sidecar: {path}")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            expected_suffix = f"/{accession}.txt"
            if (meta.get("sha256") != sha256(path)
                    or int(meta.get("bytes", -1)) != path.stat().st_size
                    or not str(meta.get("url", "")).endswith(expected_suffix)):
                raise ValueError(f"Existing SEC cache provenance mismatch: {path}")
            if accession in found and found[accession]["sha256"] != meta["sha256"]:
                raise ValueError(f"Conflicting frozen sources for {accession}")
            found[accession] = {
                "storage_path": str(path.relative_to(ROOT)),
                "sha256": meta["sha256"],
                "bytes": path.stat().st_size,
                "reused_frozen_source": True,
            }
    if len(found) != 100:
        raise ValueError(f"Expected exactly 100 verified existing submissions; found {len(found)}")
    return found


def load_cached_inventory() -> list[dict]:
    inventory_dir = ROOT / "data/interim/overnight/index-metadata"
    rows: dict[str, dict] = {}
    files = sorted(inventory_dir.glob("*.json"))
    if len(files) != 55:
        raise ValueError(f"Expected 55 cached quarterly inventories; found {len(files)}")
    for metadata_path in files:
        records = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not records:
            continue
        index_path = ROOT / records[0]["index_source_path"]
        digest = sha256(index_path)
        for record in records:
            if record.get("index_source_sha256") != digest:
                raise ValueError(f"Index inventory provenance mismatch: {metadata_path}")
            previous = rows.get(record["accession"])
            if previous and previous["path"] != record["path"]:
                raise ValueError(f"Conflicting index paths for {record['accession']}")
            rows[record["accession"]] = record
    return list(rows.values())


def parse_index_snapshot(payload: bytes, source_path: str, source_sha: str) -> list[dict]:
    """Parse only 13D-family rows without loading the multi-million-row index."""
    row_re = re.compile(
        r"^(?P<form>(?:SC|SCHEDULE) 13D(?:/A)?)\s{2,}.*?\s+(?P<cik>\d+)\s+"
        r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<path>edgar/\S+)\s*$"
    )
    out: dict[str, dict] = {}
    for line in payload.decode("latin-1").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        path = match.group("path")
        accession = Path(path).name.removesuffix(".txt")
        form = "13D/A" if match.group("form").endswith("/A") else "13D"
        entry = out.setdefault(accession, {
            "accession": accession, "form": form, "filing_date": match.group("date"),
            "path": path, "ciks": [], "index_source_path": source_path,
            "index_source_sha256": source_sha,
        })
        entry["ciks"] = sorted(set(entry["ciks"] + [int(match.group("cik"))]))
    if not out:
        raise ValueError("Current SEC index snapshot contained no 13D-family rows")
    return list(out.values())


class Collector:
    def __init__(self, user_agent: str, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.last_call = 0.0

    def fetch(
        self,
        url: str,
        destination: Path,
        *,
        retries: int = 3,
        expected_accession: str | None = None,
        expected_filing_date: str | None = None,
        evidence_kind: str = "sec_index",
    ) -> dict:
        if urlparse(url).hostname not in {"www.sec.gov", "data.sec.gov"}:
            raise ValueError("Only official SEC hosts are allowed")
        if destination.exists():
            meta_path = destination.with_suffix(destination.suffix + ".meta.json")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if (meta.get("url") != url or meta.get("sha256") != sha256(destination)
                    or int(meta.get("bytes", -1)) != destination.stat().st_size):
                raise ValueError(f"Cache provenance mismatch: {destination}")
            if expected_accession and expected_filing_date:
                validate_submission(destination.read_bytes(), expected_accession, expected_filing_date)
            return {**meta, "cache_hit": True}
        if shutil.disk_usage(destination.parent if destination.parent.exists() else RAW).free < MIN_FREE_BYTES:
            raise RuntimeError("disk_guard: less than 20 GiB free")
        for attempt in range(retries + 1):
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - self.last_call)
            if wait > 0:
                time.sleep(wait)
            self.last_call = time.monotonic()
            try:
                response = self.session.get(
                    url, headers=self.headers, timeout=(20, 120), stream=True, allow_redirects=False
                )
            except requests.RequestException:
                if attempt >= retries:
                    raise
                time.sleep(min(30, 2**attempt))
                continue
            if response.status_code in {403, 429}:
                retry_after = response.headers.get("Retry-After")
                if hasattr(response, "close"):
                    response.close()
                raise RuntimeError(f"SEC_ACCESS_STOP status={response.status_code} retry_after={retry_after or 'unspecified'}")
            if 300 <= response.status_code < 400:
                if hasattr(response, "close"):
                    response.close()
                raise RuntimeError(f"SEC redirect refused: status={response.status_code}")
            if response.status_code >= 500 and attempt < retries:
                if hasattr(response, "close"):
                    response.close()
                time.sleep(min(30, 2**attempt))
                continue
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            part = destination.with_suffix(destination.suffix + ".part")
            digest = hashlib.sha256()
            size = 0
            try:
                with part.open("xb") as handle:
                    for chunk in response.iter_content(64 * 1024):
                        if not chunk:
                            continue
                        if b"Your Request Originates from an Undeclared Automated Tool" in chunk:
                            raise RuntimeError("SEC_ACCESS_STOP status=200 denial_page=true")
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise ValueError("SEC response exceeds 250 MiB bound")
                        digest.update(chunk)
                        handle.write(chunk)
                if size == 0:
                    raise ValueError("SEC returned an empty response")
                if expected_accession and expected_filing_date:
                    validate_submission(part.read_bytes(), expected_accession, expected_filing_date)
                part.replace(destination)
            except Exception:
                part.unlink(missing_ok=True)
                raise
            finally:
                if hasattr(response, "close"):
                    response.close()
            meta = {
                "url": url, "retrieved_at_utc": utcnow(), "sha256": digest.hexdigest(),
                "bytes": size, "content_type": response.headers.get("Content-Type"),
                "evidence_kind": evidence_kind,
            }
            if evidence_kind == "complete_submission_text":
                meta.update(embedded_documents_included=True,
                            externally_referenced_exhibits="not_independently_fetched_or_verified")
            atomic_json(destination.with_suffix(destination.suffix + ".meta.json"), meta)
            return {**meta, "cache_hit": False}
        raise AssertionError("unreachable")


def refresh_current_index(client: Collector) -> list[dict]:
    snapshot_dir = RAW / "index-snapshots/2026-QTR3"
    existing = sorted(snapshot_dir.glob("form-2026-QTR3-*.idx"))
    if existing:
        path = existing[-1]
        meta = json.loads(path.with_suffix(path.suffix + ".meta.json").read_text(encoding="utf-8"))
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = snapshot_dir / f"form-2026-QTR3-{stamp}.idx"
        meta = client.fetch(
            "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/form.idx", path,
            evidence_kind="sec_quarterly_form_index",
        )
    return parse_index_snapshot(path.read_bytes(), str(path.relative_to(ROOT)), meta["sha256"])


def freeze_manifest(client: Collector, refresh: bool) -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {row["accession"]: row for row in load_cached_inventory()}
    if refresh:
        for row in refresh_current_index(client):
            records[row["accession"]] = row
    reused = verified_existing()
    manifest_rows = []
    for accession, row in sorted(records.items(), key=lambda item: (item[1]["filing_date"], item[0])):
        manifest_rows.append({
            **row,
            "source_url": BASE + row["path"],
            "storage_path": reused.get(accession, {}).get(
                "storage_path", f"data/raw/edgar/bulk-v1/filings/{accession}/submission.txt"
            ),
            "reused_frozen_source": accession in reused,
            "externally_referenced_exhibits": "not_independently_fetched_or_verified",
        })
    result = {
        "schema_version": "sec-bulk-v1", "frozen_at_utc": utcnow(),
        "scope": "Schedule 13D initial filings and amendments, 2013 through current 2026-Q3 snapshot",
        "n": len(manifest_rows), "reused_verified_n": len(reused), "records": manifest_rows,
    }
    atomic_json(MANIFEST, result)
    return result


def append_failure(row: dict, exc: Exception) -> None:
    FAILURES.parent.mkdir(parents=True, exist_ok=True)
    with FAILURES.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at_utc": utcnow(), "accession": row["accession"],
                                 "error": f"{type(exc).__name__}: {exc}"}) + "\n")


def run(refresh: bool = True) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "collector.lock").open("a") as lock:
        try:
            acquire_exclusive(lock)
        except BlockingIOError:
            raise SystemExit("SEC bulk collector already running") from None
        client = Collector(load_contact())
        manifest = freeze_manifest(client, refresh)
        prior = json.loads(PROGRESS.read_text(encoding="utf-8")) if PROGRESS.exists() else {}
        state = {
            "status": "running", "started_at_utc": utcnow(), "updated_at_utc": utcnow(),
            "pid": os.getpid(), "restart_count": int(prior.get("restart_count", -1)) + 1,
            "total": manifest["n"], "completed": 0, "reused": 0, "cached_bulk": 0, "downloaded": 0,
            "failed": 0, "new_bytes": 0, "requests_per_second_cap": 2,
        }
        sizes = []
        for number, row in enumerate(manifest["records"], 1):
            destination = ROOT / row["storage_path"]
            try:
                meta = client.fetch(
                    row["source_url"], destination,
                    expected_accession=row["accession"], expected_filing_date=row["filing_date"],
                    evidence_kind="complete_submission_text",
                )
                sizes.append(int(meta["bytes"]))
                if row["reused_frozen_source"]:
                    state["reused"] += 1
                elif meta["cache_hit"]:
                    state["cached_bulk"] += 1
                else:
                    state["downloaded"] += 1
                    state["new_bytes"] += int(meta["bytes"])
            except Exception as exc:
                state["failed"] += 1
                append_failure(row, exc)
                if "SEC_ACCESS_STOP" in str(exc) or "disk_guard" in str(exc):
                    state.update(status="stopped", stop_reason=str(exc), updated_at_utc=utcnow())
                    atomic_json(PROGRESS, state)
                    return
            state["completed"] = number
            if number % 10 == 0 or number == manifest["n"]:
                state["updated_at_utc"] = utcnow()
                state["observed_mean_bytes"] = round(sum(sizes) / len(sizes)) if sizes else None
                state["estimated_remaining_bytes"] = (
                    round((manifest["n"] - number) * sum(sizes) / len(sizes)) if sizes else None
                )
                state["free_bytes"] = shutil.disk_usage(RAW).free
                atomic_json(PROGRESS, state)
                print(f"SEC {number}/{manifest['n']} downloaded={state['downloaded']} cached_bulk={state['cached_bulk']} reused={state['reused']} failed={state['failed']}", flush=True)
        final_status = "completed" if state["failed"] == 0 else "completed_with_failures"
        state.update(status=final_status, finished_at_utc=utcnow(), updated_at_utc=utcnow())
        atomic_json(PROGRESS, state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-refresh-current", action="store_true")
    args = parser.parse_args()
    run(refresh=not args.no_refresh_current)


if __name__ == "__main__":
    main()
