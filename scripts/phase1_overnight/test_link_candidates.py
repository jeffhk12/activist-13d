"""Offline tests for candidate grouping and date-valid CRSP matching."""

import gzip
import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

import link_candidates


@pytest.fixture(autouse=True)
def synthetic_disk_capacity(monkeypatch):
    """Tiny fixtures test linking independently of the host's current free disk."""
    monkeypatch.setattr(link_candidates.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=21 * 1024**3))


def test_low_disk_reserve_refuses_work(tmp_path, monkeypatch):
    monkeypatch.setattr(link_candidates.shutil, "disk_usage",
                        lambda _: SimpleNamespace(free=19 * 1024**3))
    with pytest.raises(RuntimeError, match="20 GiB reserve"):
        link_candidates.run(tmp_path / "unused.sqlite", tmp_path / "out")


def _db(path: Path, records: list[dict]) -> Path:
    db = path / "records.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE records(accession TEXT PRIMARY KEY, record_json TEXT)")
        for record in records:
            conn.execute("INSERT INTO records VALUES (?, ?)", (record["accession"], json.dumps(record)))
    return db


def _cache(path: Path, rows: list[dict]) -> None:
    folder = path / "crsp.stocknames"
    folder.mkdir(parents=True)
    raw = json.dumps({"results": rows}).encode()
    page = folder / "page.json.gz"
    with gzip.open(page, "wb") as handle:
        handle.write(raw)
    (folder / "page.json.meta.json").write_text(json.dumps({
        "request": {"url": "https://wrds-api.wharton.upenn.edu/data/crsp.stocknames/", "method": "GET", "params": {}},
        "sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
    }))


def _record(accession, cusip, day, filer="2", amendment=False):
    return {"accession": accession, "cusip": cusip, "filing_date": day, "form": "SC 13D/A" if amendment else "SC 13D",
            "filers": [{"cik": filer}], "subjects": [{"cik": "1"}], "source_path": "raw/x", "source_sha256": "abc"}


def test_unique_match_rate_and_exact_group(tmp_path, monkeypatch):
    _cache(tmp_path, [{"cusip": "12345678", "permno": 10, "namedt": "2000-01-01", "nameenddt": "2020-12-31"}])
    monkeypatch.setattr(link_candidates, "WRDS_ROOT", tmp_path)
    db = _db(tmp_path, [_record("a", "1234 5678", "2010-01-01"), _record("b", "", "2011-01-01")])
    summary = link_candidates.run(db, tmp_path / "out")
    assert summary["matched"] == 1
    assert summary["eligible_cusip_and_date"] == 1
    assert summary["match_rate"] == 1 / 1
    rows = [json.loads(x) for x in (tmp_path / "out/candidates.jsonl").read_text().splitlines()]
    assert rows[0]["candidate_group_key"] == "issuer_cik=1|reporting_party_ciks=2"


def test_ambiguous_and_date_refuse(tmp_path, monkeypatch):
    _cache(tmp_path, [{"cusip": "12345678", "permno": 10, "namedt": "2000-01-01", "nameenddt": "2020-12-31"},
                      {"cusip": "12345678", "permno": 11, "namedt": "2010-01-01", "nameenddt": "2020-12-31"}])
    monkeypatch.setattr(link_candidates, "WRDS_ROOT", tmp_path)
    db = _db(tmp_path, [_record("a", "12345678", "2015-01-01"), _record("b", "12345678", "2021-01-01")])
    summary = link_candidates.run(db, tmp_path / "out")
    assert summary["conflicts"] == 1
    assert summary["unmatched"] == 1


def test_deterministic_bytes(tmp_path, monkeypatch):
    _cache(tmp_path, [{"cusip": "12345678", "permno": 10, "namedt": "2000-01-01", "nameenddt": None}])
    monkeypatch.setattr(link_candidates, "WRDS_ROOT", tmp_path)
    db = _db(tmp_path, [_record("b", "12345678", "2022-01-01"), _record("a", "12345678", "2021-01-01", amendment=True)])
    first = link_candidates.run(db, tmp_path / "one")["candidates_sha256"]
    second = link_candidates.run(db, tmp_path / "two")["candidates_sha256"]
    assert first == second
