"""Tier: 2. Hand pins, lag conventions, refusals and deterministic replay.
Inputs: artificial pre-event records. Outputs: pytest assertions.
Identity: six issuers = one focal plus five distinct controls; no returns.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_phase1_eligibility_closeout_audit.py
"""

import pytest

from activist13d.phase1_eligibility_closeout_audit import CONVENTIONS, coverage


def fixture():
    events = [
        dict(
            accession=str(i),
            entry="2020-03-03",
            issuer=str(i),
            permno=i,
            focused=i == 0,
            broad=i < 2,
        )
        for i in range(6)
    ]
    assignments = {
        e["accession"] + "|" + e["entry"]: dict(
            permno=e["permno"],
            pre="2020-02-28",
            public="2020-03-01",
            snapshot="2020-01-31",
            status="matched",
            etf="IWM",
            industry="35",
        )
        for e in events
    }
    return events, assignments


def test_hand_pin_and_replay():
    e, a = fixture()
    rows, groups = coverage(e, a)
    assert rows[0]["potential_control_issuers"] == 5
    assert rows[0]["potential_five_control_match"]
    assert groups[0]["n"] == 6 and groups[0]["benchmark_matched"] == 6
    assert coverage(e, a) == coverage(e, a)
    assert CONVENTIONS["outcomes_used"] is False
    assert CONVENTIONS["minimum_control_issuers"] == 5


def test_distinct_issuers_and_unknown():
    e, a = fixture()
    e[5]["issuer"] = "4"
    rows, _ = coverage(e, a)
    assert rows[0]["potential_control_issuers"] == 4
    assert not rows[0]["potential_five_control_match"]
    a["0|2020-03-03"].update(status="no_constituent_match", etf=None)
    rows, groups = coverage(e, a)
    assert rows[0]["potential_control_issuers"] is None
    assert groups[0]["benchmark_matched"] == 5


@pytest.mark.parametrize("problem", ["missing", "duplicate", "wrong_security", "future"])
def test_refuse(problem):
    e, a = fixture()
    if problem == "missing":
        a.pop("0|2020-03-03")
    if problem == "duplicate":
        e.append(e[0])
    if problem == "wrong_security":
        a["0|2020-03-03"]["permno"] = 99
    if problem == "future":
        a["0|2020-03-03"]["snapshot"] = "2020-03-01"
    with pytest.raises(ValueError):
        coverage(e, a)
