"""Synthetic offline tests for the WRDS audit (no network or vendor endpoints)."""

import gzip
import hashlib
import json
from pathlib import Path

from wrds_audit import run


def _page(raw_root: Path, day: str, rows: list[dict], name: str) -> None:
    table = raw_root / "crsp.dsf_v2"
    table.mkdir(parents=True, exist_ok=True)
    payload = {"count": len(rows), "results": rows}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    path = table / f"{name}.json.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(raw)
    meta = {"sha256": hashlib.sha256(raw).hexdigest(), 'raw_bytes': len(raw),
            "request": {"params": {"dlycaldt": day}, "method": "GET", 'url': 'https://wrds-api.wharton.upenn.edu/data/crsp.dsf_v2/'}}
    path.with_name(f"{name}.json.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def test_audit_hash_duplicates_dates_years_and_open_fields(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    _page(raw, "2012-01-02", [
        {"permno": 1, "dlycaldt": "2012-01-02", "dlyopen": 10.0, "cusip": "a"},
        {"permno": 1, "dlycaldt": "2012-01-02", "dlyopen": 10.0, "cusip": "a"},
    ], "a")
    _page(raw, "2012-01-03", [
        {"permno": 2, "dlycaldt": "2012-01-03", "openprc": 4.0},
    ], "b")
    # Keep the synthetic task expectation small and deterministic.
    monkeypatch.setattr("wrds_audit._expected_tasks", lambda: [
        {"table": "crsp.dsf_v2", "filters": {"dlycaldt": "2012-01-02"}, "limit": 50000},
        {"table": "crsp.dsf_v2", "filters": {"dlycaldt": "2012-01-03"}, "limit": 50000},
    ])
    result = run(tmp_path / "out", raw, disk_reserve_bytes=0)
    assert result["files_verified"] == 2
    assert result["daily"]["duplicate_security_date_rows"] == 1
    assert result["daily"]["rows_by_year"] == {"2012": 3}
    assert result["daily"]["opening_price_fields_nonnull"] == {"dlyopen": 2, "openprc": 1}
    assert result["daily"]["missing_dates"] == []
    assert (tmp_path / "out/audit.json").exists()
    assert (tmp_path / "out/audit.md").exists()


def test_hash_mismatch_is_reported_and_resume_keeps_result(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    _page(raw, "2012-01-02", [{"permno": 1, "dlycaldt": "2012-01-02"}], "a")
    sidecar = raw / "crsp.dsf_v2/a.json.meta.json"
    sidecar.write_text(json.dumps({"sha256": "wrong", "request": {"params": {}}}), encoding="utf-8")
    monkeypatch.setattr("wrds_audit._expected_tasks", lambda: [])
    first = run(tmp_path / "out", raw, disk_reserve_bytes=0)
    second = run(tmp_path / "out", raw, disk_reserve_bytes=0)
    assert first["file_status_counts"] == {"hash_mismatch": 1}
    assert second["file_status_counts"] == first["file_status_counts"]


def test_missing_date_is_explicit(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    _page(raw, "2012-01-02", [{"permno": 1, "dlycaldt": "2012-01-02"}], "a")
    monkeypatch.setattr("wrds_audit._expected_tasks", lambda: [
        {"table": "crsp.dsf_v2", "filters": {"dlycaldt": "2012-01-02"}, "limit": 50000},
        {"table": "crsp.dsf_v2", "filters": {"dlycaldt": "2012-01-03"}, "limit": 50000},
    ])
    result = run(tmp_path / "out", raw, disk_reserve_bytes=0)
    assert result["daily"]["missing_dates"] == ["2012-01-03"]
    assert "does not certify complete" in " ".join(result["limitations"])
