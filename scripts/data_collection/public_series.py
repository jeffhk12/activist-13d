"""Freeze public cash, factor, and supplied HFR research series.

Reads the official FRED DTB3 CSV and Ken French U.S. Fama/French 3-factor
daily/monthly ZIP archives over HTTPS, plus the user's supplied HFR workbook
directory. Writes immutable raw responses, extracted archive members, and a
JSON provenance/coverage record under data/raw/public-series/<run-id> and a
human-readable report under output/data-collection/public-series-<run-id>.

Identity: this collector copies source bytes and reports source coverage;
it does not transform rates, accrue cash, choose a benchmark, or compute
strategy returns. Missing observations remain source sentinels.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/public_series.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "public-series"
OUT_ROOT = ROOT / "output" / "data-collection"
SOURCES = {
    "fred_dtb3": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3",
    "ken_french_3factor_daily": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_Factors_daily_CSV.zip"
    ),
    "ken_french_3factor_monthly": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_Factors_CSV.zip"
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "activist-13d public-series collector"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (fixed HTTPS URLs)
        return response.read(), {k.lower(): v for k, v in response.headers.items()}


def date_coverage_csv(data: bytes) -> dict[str, object]:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    date_key = next((key for key in rows[0] if key.lower() in {"observation_date", "date"}), None)
    if not date_key:
        raise ValueError("FRED response has no date column")
    dates = [row[date_key] for row in rows if row[date_key]]
    value_key = next((key for key in rows[0] if key != date_key), None)
    missing = sum(1 for row in rows if value_key and row[value_key] in {".", "", "NA", "NaN"})
    return {
        "rows": len(rows),
        "date_column": date_key,
        "value_column": value_key,
        "coverage_start": min(dates) if dates else None,
        "coverage_end": max(dates) if dates else None,
        "missing_sentinel_count": missing,
        "source_sentinel": ".",
        "units": "percent, not seasonally adjusted; daily; discount basis",
    }


def date_coverage_zip(data: bytes) -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.namelist()
        text_members = [name for name in members if name.lower().endswith((".csv", ".txt"))]
        coverage: dict[str, dict[str, object]] = {}
        for name in text_members:
            text = archive.read(name).decode("latin-1")
            dates: list[str] = []
            data_rows = 0
            for line in text.splitlines():
                fields = [field.strip() for field in line.split(",")]
                if fields and len(fields[0]) in (6, 8) and fields[0].isdigit():
                    dates.append(fields[0])
                    data_rows += 1
            if dates:
                coverage[name] = {
                    "rows": data_rows,
                    "coverage_start": min(dates),
                    "coverage_end": max(dates),
                    "units": "percent per source archive; factor values are not rescaled",
                    "missing_sentinel_count": sum(
                        field.strip() == "-99.99"
                        for line in text.splitlines()
                        for field in line.split(",")[1:]
                    ),
                    "source_sentinel": "-99.99 (where present; preserved)",
                }
        return {"members": members, "text_member_coverage": coverage}


def refresh_frozen(run_id: str) -> None:
    """Rebuild metadata from an existing raw freeze without network access."""
    raw_dir = RAW_ROOT / run_id
    original = OUT_ROOT / f"public-series-{run_id}" / "manifest.json"
    if not raw_dir.is_dir() or not original.is_file():
        raise SystemExit(f"frozen run not found: {run_id}")
    manifest = json.loads(original.read_text(encoding="utf-8"))
    # The original run recorded redundant HFR copies; corrected public-series
    # metadata is scoped to the three public HTTP series only.
    manifest["hfr_files"] = []
    for source in manifest["sources"]:
        path = ROOT / source["stored_path"]
        data = path.read_bytes()
        source["bytes"] = len(data)
        source["sha256"] = sha256_bytes(data)
        source["coverage"] = date_coverage_csv(data) if path.suffix == ".csv" else date_coverage_zip(data)
    manifest["refreshed_at_utc"] = datetime.now(UTC).isoformat()
    manifest["refresh_mode"] = "offline; read-only recomputation from frozen raw bytes"
    out_dir = OUT_ROOT / f"public-series-{run_id}-corrected-v2"
    out_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        f"# Corrected public series metadata ({run_id})",
        "",
        "This report was rebuilt offline from the existing frozen raw bytes. No network request or HFR copy was performed.",
        "",
        f"Manifest: `{manifest_path.relative_to(ROOT)}`",
        "",
    ]
    for source in manifest["sources"]:
        report.append(f"- **{source['key']}**: {source['bytes']} bytes, SHA-256 `{source['sha256']}`; corrected coverage metadata is in the manifest.")
    (out_dir / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "refresh_mode": manifest["refresh_mode"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-refresh", metavar="RUN_ID", help="refresh metadata from a frozen run without refetching")
    args = parser.parse_args()
    if args.offline_refresh:
        refresh_frozen(args.offline_refresh)
        return
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = RAW_ROOT / run_id
    out_dir = OUT_ROOT / f"public-series-{run_id}"
    raw_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "run_id": run_id,
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "paid_model_apis": "off; no model/API credentials used",
        "transformations": "none; raw bytes and source sentinels preserved",
        "sources": [],
        "hfr_files": [],
    }
    for key, url in SOURCES.items():
        data, headers = fetch(url)
        suffix = ".csv" if key == "fred_dtb3" else ".zip"
        target = raw_dir / f"{key}{suffix}"
        target.write_bytes(data)
        record: dict[str, object] = {
            "key": key,
            "url": url,
            "stored_path": str(target.relative_to(ROOT)),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "http_headers": {k: headers[k] for k in ("content-type", "last-modified", "etag") if k in headers},
        }
        record["coverage"] = date_coverage_csv(data) if suffix == ".csv" else date_coverage_zip(data)
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(raw_dir / key)
        manifest["sources"].append(record)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        f"# Public series freeze ({run_id})",
        "",
        "Raw source bytes are preserved under `data/raw/public-series/" + run_id + "`. No rates were transformed, no benchmark was selected, and no strategy returns were computed.",
        "",
        f"Manifest: `{manifest_path.relative_to(ROOT)}`",
        "",
        "## Sources",
        "",
    ]
    for source in manifest["sources"]:
        report.extend([f"- **{source['key']}**: {source['bytes']} bytes, SHA-256 `{source['sha256']}`; coverage metadata recorded in manifest."])
    report.extend(["", "## HFR supplied files", "", "HFR ingestion is owned by the HFR workstream; this collector does not copy HFR files on rerun.", ""])
    (out_dir / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "manifest": str(manifest_path), "hfr_files": len(manifest["hfr_files"])}, indent=2))


if __name__ == "__main__":
    main()
