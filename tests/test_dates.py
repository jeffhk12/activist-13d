"""Pins for the disclosure-delay computation.

Every expected value below is computed by hand from a calendar and written out
in the comment above it. None is taken from the implementation's own output —
that would pin the bug in place along with the behaviour.

Business-day arithmetic across weekends and federal holidays is a classic
silent bug, and this quantity is Q2's treatment variable, so it gets the
first tests in the repo.

Tier: 1
"""

from __future__ import annotations

from datetime import date

import pytest

from activist13d import dates

# --- the convention contract ------------------------------------------------

def test_estimator_conventions_are_declared():
    """If any of these change, every delay in the panel changes with it."""
    assert dates.ESTIMATOR["interval"] == "half-open (event, filing] — event day is day 0"
    assert dates.ESTIMATOR["regime_boundary"] == "filing date >= 2024-02-05 uses business days"
    assert dates.RULE_CHANGE == date(2024, 2, 5)
    assert dates.CAP_BUSINESS_DAYS == 5
    assert dates.CAP_CALENDAR_DAYS == 10


# --- business-day arithmetic ------------------------------------------------

def test_delay_spanning_a_weekend():
    """Event Fri 2024-03-01, filed Wed 2024-03-06.

    Business days after the event, by hand:
        Mar 2 Sat  -
        Mar 3 Sun  -
        Mar 4 Mon  1
        Mar 5 Tue  2
        Mar 6 Wed  3   <- filed
    Expected: 3 business days.
    """
    d = dates.filing_delay(date(2024, 3, 1), date(2024, 3, 6))
    assert d.days == 3
    assert d.unit == "business"
    assert not d.late


def test_delay_spanning_thanksgiving():
    """Event Mon 2024-11-25, filed Mon 2024-12-02.

    Thanksgiving 2024 is Thursday 28 November (fourth Thursday).
        Nov 26 Tue  1
        Nov 27 Wed  2
        Nov 28 Thu  -   federal holiday
        Nov 29 Fri  3
        Nov 30 Sat  -
        Dec  1 Sun  -
        Dec  2 Mon  4   <- filed
    Expected: 4 business days. A calendar-day count would say 7, and a
    business-day count that ignored the holiday would say 5 — which would
    wrongly place this filing exactly at the cap.
    """
    d = dates.filing_delay(date(2024, 11, 25), date(2024, 12, 2))
    assert d.days == 4
    assert d.unit == "business"
    assert not d.used_full_window


def test_same_day_filing_is_zero():
    """Filed on the event date itself. The event day is day 0."""
    d = dates.filing_delay(date(2024, 6, 3), date(2024, 6, 3))
    assert d.days == 0


def test_next_business_day_is_one():
    """Event Fri 2024-06-07, filed Mon 2024-06-10 — the next business day."""
    assert dates.filing_delay(date(2024, 6, 7), date(2024, 6, 10)).days == 1


# --- regime selection -------------------------------------------------------

def test_pre_rule_change_uses_calendar_days():
    """Event 2023-06-01, filed 2023-06-09 — eight calendar days, old regime."""
    d = dates.filing_delay(date(2023, 6, 1), date(2023, 6, 9))
    assert d.days == 8
    assert d.unit == "calendar"
    assert d.cap == 10
    assert not d.late


def test_regime_switches_on_the_compliance_date_not_the_adoption_date():
    """Adopted 2023-10-10, compliance from 2024-02-05. The boundary is the
    compliance date, and it is inclusive."""
    before = dates.filing_delay(date(2024, 1, 20), date(2024, 2, 2))
    on = dates.filing_delay(date(2024, 1, 29), date(2024, 2, 5))
    assert before.unit == "calendar"
    assert on.unit == "business"


# --- lateness and the cap ---------------------------------------------------

def test_late_filing_under_the_new_regime():
    """Event Mon 2024-04-01, filed Tue 2024-04-09 — six business days.

        Apr 2 Tue 1, Apr 3 Wed 2, Apr 4 Thu 3, Apr 5 Fri 4,
        Apr 8 Mon 5, Apr 9 Tue 6   <- filed
    Six exceeds the five-business-day cap.
    """
    d = dates.filing_delay(date(2024, 4, 1), date(2024, 4, 9))
    assert d.days == 6
    assert d.late
    assert d.used_full_window


def test_exactly_at_the_cap_is_not_late():
    """Event Mon 2024-04-01, filed Mon 2024-04-08 — five business days."""
    d = dates.filing_delay(date(2024, 4, 1), date(2024, 4, 8))
    assert d.days == 5
    assert not d.late
    assert d.used_full_window


# --- refuse, don't fabricate ------------------------------------------------

def test_filing_before_event_raises_rather_than_returning_a_negative():
    """A negative delay is a parse error, not a measurement. It must not pass
    silently into the panel."""
    with pytest.raises(ValueError, match="precedes"):
        dates.filing_delay(date(2024, 5, 10), date(2024, 5, 3))
