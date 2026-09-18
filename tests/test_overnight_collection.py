"""Regression pins for restartable discovery collection control flow.

Inputs: synthetic frozen-manifest rows and a fake cached SEC client.
Outputs: records and explicit parser-failure queue entries.
Identity: recoverable parser failures do not reduce subsequent manifest attempts.
Tier: 1
Run: .venv/bin/python -m pytest tests/test_overnight_collection.py
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "overnight_collection", ROOT / "scripts/collect_overnight.py"
)
collection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collection)


def test_parser_failure_is_queued_and_next_manifest_row_is_attempted(monkeypatch, tmp_path):
    """One malformed filing must not truncate the frozen sample."""
    monkeypatch.setattr(collection, "ROOT", tmp_path)
    monkeypatch.setattr(collection, "RAW", tmp_path / "raw")

    class Client:
        offline = False

        def __init__(self):
            self.urls = []

        def fetch(self, url, destination):
            self.urls.append(url)
            return b"ambiguous" if url.endswith("bad.txt") else b"valid"

    def parse(payload):
        if payload == b"ambiguous":
            raise ValueError("Expected one primary 13D document, found 2")
        return {
            "accession": "0000000000-00-000002", "documents": [], "parser_source": "synthetic",
            "event_date": None, "cusip": None, "item4_text": None, "evidence_bundle": {},
        }

    monkeypatch.setattr(collection, "parse_submission", parse)
    monkeypatch.setattr(collection, "evidence_bundle", lambda record: {"source": "synthetic"})
    client = Client()
    manifest = [
        {"accession": "0000000000-00-000001", "sample_origin": "expanded_deterministic",
         "path": "edgar/bad.txt", "filing_date": "2020-01-01", "sampling_period": "2018-2022",
         "selection_rank_sha256": "a"},
        {"accession": "0000000000-00-000002", "sample_origin": "expanded_deterministic",
         "path": "edgar/valid.txt", "filing_date": "2020-01-02", "sampling_period": "2018-2022",
         "selection_rank_sha256": "b"},
    ]
    records, failures = collection.parse_expansion(client, manifest, [])

    assert [record["accession"] for record in records] == ["0000000000-00-000002"], failures
    assert [failure["accession"] for failure in failures] == ["0000000000-00-000001"]
    assert client.urls == [
        "https://www.sec.gov/Archives/edgar/bad.txt",
        "https://www.sec.gov/Archives/edgar/valid.txt",
    ]
