"""Tier: 2. Hand pins, refusals and invariance to future outcome values.
Run: PYTHONPATH=src .venv/bin/python -m pytest tests/test_evaluation_input_checks.py
"""

import pytest

from activist13d.evaluation_input_checks import daily_keys, lagged_adv, presence


def test_key_coverage_and_outcome_invariance():
    payload = {
        "results": [{"permno": 1, "dlycaldt": "2024-01-02", "dlyret": 999, "dlyclose": -999}],
        "next": None,
    }
    a = presence({1, 2}, daily_keys(payload, "2024-01-02"))
    payload["results"][0].update(dlyret=None, dlyclose=None)
    assert (
        presence({1, 2}, daily_keys(payload, "2024-01-02"))
        == a
        == {"required": 2, "present": 1, "missing": [2]}
    )


@pytest.mark.parametrize(
    "rows", [[{"permno": 1, "dlycaldt": "wrong"}], [{"permno": 1, "dlycaldt": "d"}] * 2]
)
def test_refuse_keys(rows):
    with pytest.raises(ValueError):
        daily_keys({"results": rows}, "d")


def test_adv_arithmetic_and_time_refusal():
    dates = [f"2024-01-{i:02}" for i in range(1, 21)]
    rows = {d: {"dlyclose": 10, "dlyvol": 100} for d in dates}
    assert lagged_adv("2024-02-01", dates, rows) == 1000
    rows[dates[0]]["dlyclose"] = None
    assert lagged_adv("2024-02-01", dates, rows) is None
    with pytest.raises(ValueError):
        lagged_adv("2024-01-20", dates, rows)
    with pytest.raises(ValueError):
        lagged_adv("2024-02-01", dates[:19], rows)
