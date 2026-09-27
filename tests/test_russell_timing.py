"""Tier: 2. Pin prior-month membership timing without live vendor requests."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/data_collection'))
from collect_russell_membership import snapshot_date  # noqa: E402


def test_weekend_month_end_and_month_start():
    sessions=['2020-01-31','2020-02-28','2020-03-02','2020-03-31']
    assert snapshot_date('2020-03-01',sessions)=='2020-02-28'
    assert snapshot_date('2020-03-31',sessions)=='2020-02-28'
    assert snapshot_date('2020-04-01',sessions)=='2020-03-31'


def test_no_prior_calendar_refused():
    with pytest.raises(ValueError,match='No historical month-end'):
        snapshot_date('2020-01-15',['2020-01-02','2020-01-31'])
