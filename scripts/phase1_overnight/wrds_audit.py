"""Offline integrity and coverage audit for the frozen WRDS bulk-v1 cache.

Inputs: ``data/raw/wrds/bulk-v1`` gzip pages and their ``.meta.json`` sidecars;
the existing WRDS task generator and metadata report define intended inputs.
Outputs: resumable machine JSON and Markdown reports in an isolated output
directory.  Daily CRSP rows are checked by ``(security, date)`` and grouped by
calendar year; observed columns, including opening-price columns, are counted.
Identity: total rows = sum(rows yielded by each response's ``results`` array);
duplicate keys are counted whenever a ``(permno, dlycaldt)`` key repeats.
Tier: 1
Run: ``PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
scripts/phase1_overnight/wrds_audit.py --output output/data-collection/wrds-audit``
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = ROOT / "data/raw/wrds/bulk-v1"
RESERVE = 20 * 1024**3


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expected_tasks() -> list[dict]:
    """Use the collector's task definition, without making a network call."""
    sys.path.insert(0, str(ROOT / "scripts/data_collection"))
    try:
        from wrds_collect import tasks
        return [{"table": t, "filters": f, "limit": n} for t, f, n in tasks()]
    except (ImportError, OSError):
        # This fallback preserves the documented range if a minimal test
        # environment cannot import the collector's requests dependency.
        rows = [{"table": t, "filters": {}, "limit": 1000}
                for t in ("crsp.dsenames", "crsp.stocknames", "crsp.dsedelist",
                          "crsp.ccmxpf_lnkhist", "crsp.dsi",
                          "audit.feed31_shareholder_activism", "crsp.stocknames_v2")]
        rows += [{"table": "comp.funda", "filters": {"fyear": str(y)}, "limit": 1000}
                 for y in range(2011, 2027)]
        current, end = date(2012, 1, 1), date(2026, 9, 13)
        while current <= end:
            if current.weekday() < 5:
                rows.append({"table": "crsp.dsf_v2", "filters": {"dlycaldt": current.isoformat()}, "limit": 50000})
            current += timedelta(days=1)
        return rows


def _iter_results(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[dict]:
    """Yield response rows incrementally, retaining at most a chunk and one row."""
    decoder = json.JSONDecoder()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        buf = ""
        found = False
        while True:
            chunk = stream.read(chunk_size)
            if chunk:
                buf += chunk
            if not found:
                marker = buf.find('"results"')
                if marker < 0:
                    if not chunk:
                        raise ValueError("response has no results array")
                    buf = buf[-32:]
                    continue
                start = buf.find("[", marker)
                if start < 0:
                    if not chunk:
                        raise ValueError('response results is not an array')
                    continue
                buf, found = buf[start + 1:], True
            while True:
                buf = buf.lstrip()
                if buf.startswith(","):
                    buf = buf[1:]
                    continue
                if buf.startswith("]"):
                    return
                if not buf:
                    break
                try:
                    value, end = decoder.raw_decode(buf)
                except json.JSONDecodeError:
                    break
                if not isinstance(value, dict):
                    raise ValueError("results contains a non-object row")
                yield value
                buf = buf[end:]
            if not chunk:
                raise ValueError("truncated results array")


def _raw_sha(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with gzip.open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _file_record(path: Path, raw_root: Path, production: bool = False) -> dict:
    rel = str(path.relative_to(raw_root))
    sidecar = path.with_suffix(".meta.json")
    record = {"path": rel, "table": path.parent.name, "status": "verified", "rows": 0}
    if not sidecar.exists():
        record.update(status="missing_sidecar", error="gzip has no .meta.json sidecar")
        return record
    try:
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        record['sidecar_sha256'] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
        expected = meta.get("sha256")
        actual, raw_bytes = _raw_sha(path)
        record["sha256"] = actual
        record["raw_bytes"] = raw_bytes
        if expected != actual:
            record.update(status="hash_mismatch", expected_sha256=expected)
            return record
        params = meta.get("request", {}).get("params", {})
        request_url = meta.get("request", {}).get("url", "")
        expected_url = f"https://wrds-api.wharton.upenn.edu/data/{record['table']}/"
        if request_url != expected_url:
            raise ValueError("sidecar request table does not match cache directory")
        if meta.get('raw_bytes') != raw_bytes:
            raise ValueError('sidecar raw_bytes does not match decompressed response')
        if meta.get('request', {}).get('method') == 'OPTIONS':
            record.update(status='verified_metadata', filters=params)
            return record
        if meta.get("request", {}).get("method") != "GET":
            raise ValueError("daily cache sidecar is not a GET response")
        if isinstance(meta.get("raw_bytes"), int) and meta["raw_bytes"] != raw_bytes:
            raise ValueError("sidecar raw_bytes does not match decompressed response")
        record["filters"] = params
        seen: set[tuple[str, str]] = set()
        duplicates = 0
        fields: Counter[str] = Counter()
        field_nonnull: Counter[str] = Counter()
        years: Counter[str] = Counter()
        dates: Counter[str] = Counter()
        for row in _iter_results(path):
            record["rows"] += 1
            fields.update(row.keys())
            field_nonnull.update(k for k, v in row.items() if v is not None)
            row_date = row.get("dlycaldt", row.get("date"))
            security = row.get("permno", row.get("security_id", row.get("security")))
            requested_day = params.get("dlycaldt") or params.get("date")
            if production and path.parent.name == "crsp.dsf_v2":
                if requested_day is None or row_date != str(requested_day)[:10]:
                    raise ValueError("production daily row date differs from requested date")
                if security is None:
                    raise ValueError("production daily row has no security identifier")
            if row_date is not None:
                row_date = str(row_date)[:10]
                dates[row_date] += 1
                years[row_date[:4]] += 1
            if path.parent.name == "crsp.dsf_v2" and row_date is not None and security is not None:
                key = (str(security), row_date)
                duplicate = key in seen
                if duplicate:
                    duplicates += 1
                seen.add(key)
        record.update(field_counts=dict(fields), nonnull_field_counts=dict(field_nonnull),
                      years=dict(years), dates=dict(dates), duplicate_security_dates=duplicates,
                      observed_dates=sorted(dates))
    except (OSError, ValueError, json.JSONDecodeError, EOFError) as exc:
        record.update(status="invalid", error=str(exc))
    return record


def _production_cache_paths(raw_root: Path) -> set[str]:
    """Return cache paths recorded by completed collector task envelopes."""
    task_dir = ROOT / "output/data-collection/wrds/tasks"
    paths: set[str] = set()
    for task in task_dir.glob("*.json"):
        try:
            value = json.loads(task.read_text(encoding="utf-8"))
            for page in value.get("pages", []):
                source = page.get("source", {})
                cache_path = source.get("cache_path")
                if cache_path:
                    candidate = (ROOT / cache_path).resolve()
                    paths.add(str(candidate.relative_to(raw_root.resolve())))
        except (OSError, ValueError, KeyError):
            continue
    return paths


def run(output: Path, raw_root: Path = DEFAULT_RAW, disk_reserve_bytes: int = RESERVE,
        stop: callable | None = None) -> dict:
    """Audit the frozen cache offline and return the machine-readable summary."""
    output = Path(output)
    raw_root = Path(raw_root)
    if shutil.disk_usage(output.parent if output.parent.exists() else Path.cwd()).free < disk_reserve_bytes:
        raise RuntimeError("free disk below 20 GiB reserve")
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_db = sqlite3.connect(output / 'checkpoint.sqlite')
    checkpoint_db.execute('CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
    files = sorted(raw_root.rglob("*.json.gz")) if raw_root.exists() else []
    production_paths = _production_cache_paths(raw_root)
    current_paths = {str(path.relative_to(raw_root)) for path in files}
    records = {key: json.loads(value) for key, value in checkpoint_db.execute('SELECT path,record_json FROM files') if key in current_paths}
    for path in files:
        if stop is not None and stop():
            break
        if shutil.disk_usage(output).free < disk_reserve_bytes:
            raise RuntimeError("free disk below 20 GiB reserve")
        key = str(path.relative_to(raw_root))
        # Reuse only a record tied to the current file size and mtime; this
        # makes resume safe if a frozen evidence file is replaced unexpectedly.
        stat = path.stat()
        stamp = f"{stat.st_size}:{stat.st_mtime_ns}"
        if records.get(key, {}).get("file_stamp") == stamp:
            prior = records[key]
            sidecar = path.with_suffix(".meta.json")
            try:
                expected = json.loads(sidecar.read_text(encoding="utf-8")).get("sha256")
                if prior.get("sha256") == expected and _raw_sha(path)[0] == expected and prior.get('sidecar_sha256') == hashlib.sha256(sidecar.read_bytes()).hexdigest():
                    continue
            except (OSError, ValueError, EOFError):
                pass
        production = (not production_paths and raw_root.resolve() != DEFAULT_RAW.resolve()) or key in production_paths
        rec = _file_record(path, raw_root, production=production)
        rec["file_stamp"] = stamp
        records[key] = rec
        checkpoint_db.execute('INSERT OR REPLACE INTO files VALUES (?,?)', (key, json.dumps(rec)))
        checkpoint_db.commit()
        _write(output / 'progress.json', {'status': 'running', 'files_audited': len(records), 'files_total': len(files), 'updated_at': _utc()})
    checkpoint_db.close()
    valid = [r for r in records.values() if r.get("status") == "verified"]
    daily = [r for r in valid if r.get("table") == "crsp.dsf_v2" and
             ((not production_paths and raw_root.resolve() != DEFAULT_RAW.resolve()) or r.get("path") in production_paths)]
    expected = {t["filters"]["dlycaldt"] for t in _expected_tasks()
                if t["table"] == "crsp.dsf_v2" and "dlycaldt" in t["filters"]}
    observed = {d for r in daily for d in r.get("observed_dates", [])}
    tables = {}
    for r in valid:
        if r['path'] not in production_paths and raw_root.resolve() == DEFAULT_RAW.resolve():
            continue
        table = tables.setdefault(r['table'], {'rows': 0, 'files': 0, 'nonnull_fields': Counter()})
        table['rows'] += r['rows']
        table['files'] += 1
        table['nonnull_fields'].update(r.get('nonnull_field_counts', {}))
    year_rows: Counter[str] = Counter()
    date_counts: Counter[str] = Counter()
    observed_fields: Counter[str] = Counter()
    opening_fields: Counter[str] = Counter()
    duplicate_total = 0
    date_files: defaultdict[str, set[str]] = defaultdict(set)
    for r in daily:
        year_rows.update(r.get("years", {}))
        date_counts.update(r.get("dates", {}))
        observed_fields.update(r.get("field_counts", {}))
        duplicate_total += r.get("duplicate_security_dates", 0)
        for day in r.get("observed_dates", []):
            date_files[day].add(r["path"])
        opening_fields.update({k: v for k, v in r.get("nonnull_field_counts", {}).items() if "open" in k.lower()})
    overlap_dates = sorted(day for day, paths in date_files.items() if len(paths) > 1)
    summary = {"schema_version": "wrds-audit-v1", "generated_at": _utc(),
               "raw_root": str(raw_root), "output_dir": str(output),
               "files_discovered": len(files), "files_audited": len(records),
               'tables': tables,
               'missing_production_cache_paths': sorted(production_paths - current_paths),
               "production_daily_files": len(daily), "diagnostic_daily_files_excluded": max(0, sum(1 for r in valid if r.get("table") == "crsp.dsf_v2") - len(daily)),
               "files_verified": sum(r.get('status') in ('verified', 'verified_metadata') for r in records.values()), "file_status_counts": dict(Counter(r.get("status") for r in records.values())),
               "daily": {"expected_dates": len(expected), "observed_dates": len(observed),
                         "missing_dates": sorted(expected - observed), "unexpected_dates": sorted(observed - expected),
                         "rows": sum(r.get("rows", 0) for r in daily), "duplicate_security_date_rows": duplicate_total,
                         "overlap_dates": overlap_dates,
                         "duplicate_certification": "certified within each file; cross-file certification unavailable for overlapping dates" if overlap_dates else "certified for disjoint production dates",
                         "rows_by_year": dict(sorted(year_rows.items())), "rows_by_date": dict(sorted(date_counts.items())),
                         "observed_fields": dict(sorted(observed_fields.items())),
                         "opening_price_fields_nonnull": dict(sorted(opening_fields.items()))},
               "provenance": {"task_source": "scripts/data_collection/wrds_collect.py:tasks", "metadata_source": str(ROOT / "output/data-collection/wrds/metadata.json"),
                              "hash": "sha256 of decompressed JSON bytes, compared with sidecar sha256", "network_calls": 0},
               "limitations": ["Vendor count and next metadata remain unresolved; this audit does not certify complete coverage.",
                               "Observed dates and fields describe rows present in frozen responses only.",
                               "No model APIs, network requests, or raw evidence edits are performed."]}
    _write(output / "audit.json", summary)
    _write(output / 'progress.json', {'status': 'stopped' if stop and stop() else 'completed_with_coverage_unverified', 'files_audited': len(records), 'files_total': len(files), 'updated_at': _utc()})
    md = ["# WRDS bulk-v1 audit", "", f"Generated: {summary['generated_at']}", "", "## Coverage", "",
          f"- Daily expected dates: {len(expected)}; observed: {len(observed)}; missing: {len(expected-observed)}",
          f"- Daily rows: {summary['daily']['rows']}; duplicate security-date rows: {duplicate_total}",
          "- Vendor counts remain unresolved; coverage is not certified complete.", "", "## Provenance", "",
          f"- Raw root: `{raw_root}`", "- Hashes: SHA-256 of decompressed JSON bytes versus sidecars", "- Network/model API calls: 0"]
    (output / "audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.raw_root), indent=2))
