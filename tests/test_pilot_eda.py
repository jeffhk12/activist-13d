"""Hand-computed descriptive pins and offline reproducibility for pilot EDA.

Inputs: explicit values and optional cached pilot. Outputs: assertions.
Identity: calendar subtraction and midpoint of sorted observations.
Tier: 1
Run: .venv/bin/python -m pytest tests/test_pilot_eda.py
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot_eda", ROOT / "scripts/probe_pilot_eda.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_calendar_days_and_missing():
    # Dec 21 -> Dec 31 = 10 days, plus Jan 1 and 2 = 12.
    assert probe.calendar_gap("2023-12-21", "2024-01-02") == 12
    assert probe.calendar_gap(None, "2024-01-02") is None


def test_summary_pinned():
    # Sorted 0, 2, 6, 12; midpoint (2 + 6) / 2 = 4; None is excluded.
    assert probe.summarize([12, None, 2, 0, 6]) == {"n": 4, "min": 0, "median": 4, "max": 12}
    assert probe.summarize([]) == {"n": 0, "min": None, "median": None, "max": None}


def test_refuses_wrong_universe():
    with pytest.raises(ValueError, match="exactly the ten"):
        probe.build([])


def test_cached_reproducibility_and_evidence():
    path = ROOT / "data/interim/pilot/filings.jsonl"
    if not path.exists():
        pytest.skip("Local pilot is not part of the repository")
    records = [json.loads(line) for line in path.read_text().splitlines()]
    first = probe.build(records)
    assert probe.render(first) == probe.render(probe.build(list(reversed(records))))
    # Ten explicit accession mappings matched to ten unique source records.
    assert len(first["rows"]) == len(probe.TRIAGE) == 10
    records[0]["item4_text"] = "Missing supporting evidence"
    with pytest.raises(ValueError, match="Supporting span missing"):
        probe.build(records)
