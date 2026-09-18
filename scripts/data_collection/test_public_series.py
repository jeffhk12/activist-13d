"""Offline contracts for public-series provenance and source parsing.

Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest -q scripts/data_collection/test_public_series.py
"""

from __future__ import annotations

import io
import zipfile

from scripts.data_collection.public_series import date_coverage_csv, date_coverage_zip, sha256_bytes


def test_fred_coverage_preserves_dot_missing_values() -> None:
    data = b"observation_date,DTB3\n2020-01-02,1.50\n2020-01-03,.\n"
    result = date_coverage_csv(data)
    assert result["coverage_start"] == "2020-01-02"
    assert result["coverage_end"] == "2020-01-03"
    assert result["missing_sentinel_count"] == 1
    assert result["units"].startswith("percent")


def test_french_archive_coverage_reads_monthly_and_daily_date_shapes() -> None:
    payload = b"Header\n192607,1,2,3\n202607,4,-99.99,6\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("factors.csv", payload)
    coverage = date_coverage_zip(buf.getvalue())["text_member_coverage"]["factors.csv"]
    assert coverage["coverage_start"] == "192607"
    assert coverage["coverage_end"] == "202607"
    assert coverage["rows"] == 2
    assert coverage["missing_sentinel_count"] == 1


def test_hash_is_stable_for_source_bytes() -> None:
    assert sha256_bytes(b"public source") == sha256_bytes(b"public source")
    assert sha256_bytes(b"public source") != sha256_bytes(b"changed source")
