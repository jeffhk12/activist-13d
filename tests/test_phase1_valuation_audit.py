"""Tier: 2. Hand pins and refusal/convention tests for isolated valuation audit.
Inputs: synthetic daily rows. Output: pytest assertions. Identity: NAV=C+V.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_phase1_valuation_audit.py
"""
import pytest

from activist13d.phase1_valuation_audit import (
    CONVENTIONS,
    first_gap,
    invalid_mark,
    isolated_sensitivity,
)


def row(**kw):
    return dict(dlyret=0.1, dlyretmissflg="NA", dlyprevdt="a", dlydelflg="N", **kw)


def test_hand_pins():
    # $100 NAV includes $10 position. Half mark removes $5; capital was $80.
    x = isolated_sensitivity(100, 10, 80, .5)
    assert x["hypothetical_nav"] == 95
    assert x["nav_change_fraction"] == -.05
    assert x["initial_capital_change_fraction"] == -.0625
    assert isolated_sensitivity(100, 10, 80, 0)["hypothetical_nav"] == 90
    assert isolated_sensitivity(100, 10, 80, 2)["hypothetical_nav"] == 110


@pytest.mark.parametrize("args", [(100, 101, 80, 1), (100, 10, 0, 1), (100, 10, 80, -1), (100, 10, 80, float('nan'))])
def test_refuse(args):
    with pytest.raises(ValueError):
        isolated_sensitivity(*args)


def test_missing_mark_and_noncontiguous_refused():
    assert invalid_mark(None, "a") == "missing_row"
    assert invalid_mark(dict(row(), dlyret=None, dlyretmissflg="NT"), "a") == "missing_or_invalid_return"
    assert invalid_mark(row(), "z") == "noncontiguous_return"
    assert invalid_mark(row(), "a") is None


def test_delisting_stops_window():
    e = {"days": ["a", "b", "c"]}
    assert first_gap(e, {"b": dict(row(), dlydelflg="Y")}) is None
    assert first_gap(e, {"b": row()})["day"] == "c"


def test_contract():
    assert CONVENTIONS["upper_bound"] is None
    assert isolated_sensitivity(100, 10, 80, 1)["observed_return"] is None
