"""Offline contract tests for the complete SEC 13D-family collector.

Inputs: synthetic indexes and HTTP responses. Outputs: cache/provenance assertions.
Identity: one accession per index and sha256(cache) = sidecar sha256.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/pytest tests/test_sec_bulk.py
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/data_collection/sec_bulk.py"
SPEC = importlib.util.spec_from_file_location("sec_bulk", SCRIPT)
sec_bulk = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(sec_bulk)


class Response:
    status_code = 200
    headers = {"Content-Type": "text/plain"}

    def __init__(self, body: bytes = b"submission") -> None:
        self.body = body

    def iter_content(self, _size: int):
        yield self.body

    def raise_for_status(self) -> None:
        return None

    def close(self) -> None:
        return None


class Session:
    def __init__(self, response: Response | None = None) -> None:
        self.response = response or Response()
        self.calls = 0

    def get(self, *_args, **_kwargs):
        self.calls += 1
        return self.response


def test_index_deduplicates_two_party_rows() -> None:
    body = ("SC 13D       FILER                 1 2026-09-01 edgar/data/1/0001-26-000001.txt\n"
            "SC 13D       SUBJECT               2 2026-09-01 edgar/data/1/0001-26-000001.txt\n"
            "SCHEDULE 13D/A  SUBJECT             2 2026-09-02 edgar/data/2/0002-26-000002.txt\n").encode()
    rows = sec_bulk.parse_index_snapshot(body, "snapshot.idx", hashlib.sha256(body).hexdigest())
    assert len(rows) == 2
    assert rows[0]["ciks"] == [1, 2]
    assert {row["form"] for row in rows} == {"13D", "13D/A"}


def test_fetch_writes_bytes_and_provenance_then_reuses_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sec_bulk, "MIN_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(sec_bulk, "MIN_FREE_BYTES", 0)
    session = Session(Response(b"exact bytes"))
    client = sec_bulk.Collector("Researcher researcher@university.edu", session=session)
    destination = tmp_path / "submission.txt"
    first = client.fetch("https://www.sec.gov/Archives/edgar/data/1/a.txt", destination)
    second = client.fetch("https://www.sec.gov/Archives/edgar/data/1/a.txt", destination)
    assert destination.read_bytes() == b"exact bytes"
    assert first["sha256"] == hashlib.sha256(b"exact bytes").hexdigest()
    assert second["cache_hit"] is True
    assert session.calls == 1


def test_submission_validation_refuses_wrong_accession() -> None:
    body = (b"ACCESSION NUMBER:\t\t0000000001-26-000001\n"
            b"FILED AS OF DATE:\t\t20260901\n")
    with pytest.raises(ValueError, match="accession mismatch"):
        sec_bulk.validate_submission(body, "0000000002-26-000002", "2026-09-01")


def test_submission_validation_refuses_generic_html() -> None:
    with pytest.raises(ValueError, match="not a complete SEC submission"):
        sec_bulk.validate_submission(b"<html><title>SEC.gov</title></html>",
                                     "0000000001-26-000001", "2026-09-01")


@pytest.mark.parametrize("status", [403, 429])
def test_access_denial_stops_without_retry(tmp_path: Path, monkeypatch, status: int) -> None:
    monkeypatch.setattr(sec_bulk, "MIN_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(sec_bulk, "MIN_FREE_BYTES", 0)
    response = Response()
    response.status_code = status
    response.headers = {"Retry-After": "120"}
    session = Session(response)
    client = sec_bulk.Collector("Researcher researcher@university.edu", session=session)
    with pytest.raises(RuntimeError, match="SEC_ACCESS_STOP"):
        client.fetch("https://www.sec.gov/Archives/x", tmp_path / "x")
    assert session.calls == 1


def test_refuses_non_sec_host(tmp_path: Path) -> None:
    client = sec_bulk.Collector("Researcher researcher@university.edu", session=Session())
    with pytest.raises(ValueError, match="official SEC"):
        client.fetch("https://example.com/x", tmp_path / "x")
