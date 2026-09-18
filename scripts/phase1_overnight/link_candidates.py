"""Offline issuer candidates and historical CRSP identifier matching.

Inputs: a SQLite ``records(accession, record_json)`` table and frozen gzip JSON
WRDS pages for ``crsp.stocknames``/``crsp.dsenames``. Outputs: streaming
candidate JSONL, summary JSON, and an auditable REPORT.md in ``output``.
Identity: a CRSP match is valid iff the filing CUSIP equals a row's ``cusip``
or ``ncusip`` and ``namedt <= filing_date <= nameenddt`` (open end dates are
allowed); a match is refused when more than one PERMNO remains. Candidate
groups are mechanical issuer CIK + exact nonempty reporting-party CIK set.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_overnight/link_candidates.py DB OUTPUT
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
WRDS_ROOT = ROOT / "data/raw/wrds/bulk-v1"
TABLES = ("crsp.stocknames", "crsp.dsenames")


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except (TypeError, ValueError):
        return None


def _cusip(value: Any) -> str | None:
    value = "" if value is None else str(value)
    value = "".join(value.split()).upper()
    if len(value) not in (8, 9) or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in value):
        return None
    return value[:8]


def _ciks(record: dict, key: str) -> tuple[str, ...]:
    values = set()
    for item in record.get(key, []):
        raw = str(item.get("cik", "")).strip() if isinstance(item, dict) else ""
        if raw.isdigit():
            values.add(str(int(raw)))
    return tuple(sorted(values))


def candidate_group(record: dict) -> str | None:
    """Return the exact issuer/reporting-party key, or refuse incomplete identity."""
    issuer = _ciks(record, "subjects")
    parties = _ciks(record, "filers")
    if len(issuer) != 1 or not parties:
        return None
    return f"issuer_cik={issuer[0]}|reporting_party_ciks={','.join(parties)}"


def _cache_rows(root: Path | None = None) -> Iterable[tuple[str, dict]]:
    """Yield rows and their frozen page path without making network requests."""
    root = WRDS_ROOT if root is None else root
    for table in TABLES:
        for path in sorted((root / table).glob("*.json.gz")):
            sidecar = path.with_suffix(".meta.json")
            if not sidecar.is_file():
                raise ValueError(f"missing frozen cache sidecar: {sidecar}")
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            request = metadata.get("request", {})
            if (request.get("method") not in {"GET", "OPTIONS"} or not str(request.get("url", "")).endswith(f"/{table}/")
                    or not isinstance(request.get("params"), dict)):
                raise ValueError(f"cache provenance does not identify {table}: {path}")
            raw = gzip.open(path, "rb").read()
            if hashlib.sha256(raw).hexdigest() != metadata.get("sha256") or len(raw) != metadata.get("raw_bytes"):
                raise ValueError(f"frozen cache integrity failure: {path}")
            payload = json.loads(raw)
            if request.get("method") != "GET":
                continue
            for row in payload.get("results", []):
                if isinstance(row, dict):
                    yield str(path), row


def _index_rows(root: Path | None = None) -> tuple[dict[str, list[tuple[str, dict]]], list[str]]:
    index: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    pages: list[str] = []
    for path, row in _cache_rows(root):
        if path not in pages:
            pages.append(path)
        # CRSP ncusip is the historical security identifier. Current cusip is
        # deliberately a fallback only where ncusip is absent.
        key = _cusip(row.get("ncusip") or row.get("cusip"))
        if key:
            index[key].append((path, row))
    return index, pages


def _match(cusip: str | None, filing_date: date | None,
           index: dict[str, list[tuple[str, dict]]]) -> dict:
    if not cusip:
        return {"status": "unmatched", "reason": "missing_cusip", "permno": None, "source": []}
    if filing_date is None:
        return {"status": "unmatched", "reason": "missing_or_invalid_filing_date", "permno": None, "source": []}
    valid = []
    invalid_dates = []
    for path, row in index.get(cusip, []):
        start = _date(row.get("namedt"))
        end = _date(row.get("nameenddt", row.get("nameendt", row.get("end_date"))))
        raw_end = row.get("nameenddt", row.get("nameendt"))
        if start is None or (raw_end not in (None, "") and end is None) or (end is not None and end < start):
            invalid_dates.append(path)
            continue
        if start <= filing_date and (end is None or filing_date <= end):
            valid.append((str(row.get("permno")), path, row))
    permnos = sorted({item[0] for item in valid if item[0] not in {"None", ""}})
    if len(permnos) != 1:
        return {"status": "conflict" if len(permnos) > 1 else "unmatched",
                "reason": "multiple_valid_permnos" if len(permnos) > 1 else ("invalid_historical_dates" if invalid_dates else "no_valid_historical_row"),
                "permno": None, "permnos": permnos,
                "source": sorted({path for _, path, _ in valid})}
    chosen = next(item for item in valid if item[0] == permnos[0])
    return {"status": "matched", "reason": "unique_valid_historical_row", "permno": int(permnos[0]),
            "permnos": permnos, "source": [chosen[1]],
            "crsp_row": {k: chosen[2].get(k) for k in ("cusip", "ncusip", "permno", "namedt", "nameenddt", "nameendt")}}


def _amendment(record: dict) -> bool:
    if isinstance(record.get("is_amendment"), bool):
        return record["is_amendment"]
    return str(record.get("form") or "").upper().endswith("/A")


def run(db_path: Path, output: Path) -> dict:
    """Link every record offline and write deterministic artifacts under output."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(ROOT).free < 20 * 1024 ** 3:
        raise RuntimeError("free disk below 20 GiB reserve")
    index, pages = _index_rows()
    rows: list[dict] = []
    with sqlite3.connect(str(db_path)) as db:
        cursor = db.execute("SELECT accession, record_json FROM records ORDER BY accession")
        for accession, raw in cursor:
            record = json.loads(raw)
            filing = _date(record.get("filing_date") or record.get("index_filing_date"))
            linked = _match(_cusip(record.get("cusip")), filing, index)
            row = {"accession": accession, "filing_date": filing.isoformat() if filing else None,
                   "form": record.get("form"), "is_amendment": _amendment(record),
                   "cusip": _cusip(record.get("cusip")), "issuer_ciks": list(_ciks(record, "subjects")),
                   "reporting_party_ciks": list(_ciks(record, "filers")),
                   "candidate_group_key": candidate_group(record), "candidate_campaign_status": "not_validated",
                   "crsp": linked, "source_path": record.get("source_path"),
                   "source_sha256": record.get("source_sha256"), "flags": list(record.get("flags") or [])}
            if linked["status"] != "matched":
                row["flags"].append("crsp_" + linked["status"])
            rows.append(row)
    with (output / "candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["candidate_group_key"]:
            groups[row["candidate_group_key"]].append(row)
    group_rows = [{"candidate_group_key": key, "accessions": [r["accession"] for r in value],
                   "n_records": len(value), "n_initials": sum(not r["is_amendment"] for r in value),
                   "n_amendments": sum(r["is_amendment"] for r in value),
                   "distinct_initials": len({r["accession"] for r in value if not r["is_amendment"]}),
                   "distinct_amendments": len({r["accession"] for r in value if r["is_amendment"]})}
                  for key, value in sorted(groups.items())]
    with (output / "groups.jsonl").open("w", encoding="utf-8") as handle:
        for group in group_rows:
            handle.write(json.dumps(group, ensure_ascii=False, sort_keys=True) + "\n")
    statuses = Counter(row["crsp"]["status"] for row in rows)
    eligible = sum(row["cusip"] is not None and row["filing_date"] is not None for row in rows)
    matched = statuses["matched"]
    by_year = {}
    years = sorted({r["filing_date"][:4] for r in rows if r["filing_date"]})
    for year in years:
        subset = [r for r in rows if r["filing_date"] and r["filing_date"][:4] == year]
        e = sum(r["cusip"] is not None and r["filing_date"] is not None for r in subset)
        m = sum(r["crsp"]["status"] == "matched" for r in subset)
        by_year[year] = {"n": len(subset), "eligible_cusip": e, "matched": m,
                         "match_rate": m / e if e else None}
    summary = {"n_records": len(rows), "n_groups": len(group_rows),
               "crsp_status": dict(statuses), "eligible_cusip_and_date": eligible,
               "matched": matched, "match_rate": matched / eligible if eligible else None,
               "match_rates_by_year": by_year, "unmatched": statuses["unmatched"],
               "conflicts": statuses["conflict"], "frozen_crsp_pages": len(pages),
               "frozen_crsp_page_paths": [str(Path(p).relative_to(WRDS_ROOT)) if Path(p).is_relative_to(WRDS_ROOT)
                                           else str(Path(p)) for p in pages],
               "source_manifest_sha256": hashlib.sha256(json.dumps(
                   [{"accession": r["accession"], "source_path": r["source_path"],
                     "source_sha256": r["source_sha256"]} for r in rows], sort_keys=True).encode()).hexdigest(),
               "candidates_sha256": hashlib.sha256((output / "candidates.jsonl").read_bytes()).hexdigest(),
               "groups_sha256": hashlib.sha256((output / "groups.jsonl").read_bytes()).hexdigest()}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = ["# Offline candidate linking", "", "Mechanical issuer/reporting-party grouping and historical CRSP CUSIP matching; candidate groups are not validated campaigns.", "", "```json", json.dumps(summary, indent=2, sort_keys=True), "```", "", f"Candidate groups: {len(group_rows)}. CRSP match rate among records with CUSIP and filing date: {matched}/{eligible}.", "All rows retain SEC source path and SHA-256 metadata."]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.db_path, args.output), indent=2, sort_keys=True))
