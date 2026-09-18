"""Disclosure-delay computation for Schedule 13D filings.

Turns the cover-page event date and the EDGAR filing date into the delay the
filer took, under whichever reporting regime was in force on the filing date.

This is Q2's treatment variable. It is disclosed on every 13D cover page as
"Date of Event Which Requires Filing of this Statement", and the filing date
comes from EDGAR metadata — no construction, no vendor.

Identity
    filed >= 2024-02-05   delay_bd = business days in (event, filing],
                                     US federal holidays excluded
                                     statutory cap: 5 business days
    filed <  2024-02-05   delay_cd = calendar days, filing - event
                                     statutory cap: 10 calendar days

The half-open interval is deliberate: the event day itself is day 0, so a
filing on the next business day is a delay of 1. That matches how the rule
reads ("within N days AFTER the event") and it is the convention the tests pin.

Tier: 1
Run:  set PYTHONNOUSERSITE=1, PYTHONIOENCODING=utf-8
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from pandas.tseries.holiday import USFederalHolidayCalendar

# The 13D initial-filing deadline changed from 10 calendar days to 5 business
# days. SEC adopted 2023-10-10; compliance required from this date.
RULE_CHANGE = date(2024, 2, 5)

CAP_CALENDAR_DAYS = 10
CAP_BUSINESS_DAYS = 5

# Conventions this module commits to. Asserted in tests/test_dates.py so a
# silent change to any of them fails loudly rather than moving every delay.
ESTIMATOR = {
    "interval": "half-open (event, filing] — event day is day 0",
    "business_day_holidays": "US federal, via pandas USFederalHolidayCalendar",
    "regime_boundary": "filing date >= 2024-02-05 uses business days",
    "weekend": "Saturday and Sunday are non-business days",
}

_CAL = USFederalHolidayCalendar()
_HOLIDAYS = np.array(
    _CAL.holidays(start="1990-01-01", end="2035-12-31").date,
    dtype="datetime64[D]",
)


@dataclass(frozen=True)
class Delay:
    """A filing delay, with the regime that produced it."""

    days: int
    unit: str  # "business" or "calendar"
    cap: int
    late: bool

    @property
    def used_full_window(self) -> bool:
        return self.days >= self.cap


def business_days_between(start: date, end: date) -> int:
    """Business days in the half-open interval (start, end].

    US federal holidays and weekends excluded. Negative if end precedes start.
    """
    # numpy counts [a, b). Shifting both bounds forward one day converts that
    # to (start, end] without special-casing whether either endpoint is itself
    # a business day.
    a = np.datetime64(start + timedelta(days=1), "D")
    b = np.datetime64(end + timedelta(days=1), "D")
    return int(np.busday_count(a, b, holidays=_HOLIDAYS))


def filing_delay(event_date: date, filing_date: date) -> Delay:
    """The delay a filer took, measured under the regime in force when filed.

    Raises ValueError if the filing precedes the event — that is a data error,
    not a negative delay, and it must not pass silently into the panel.
    """
    if filing_date < event_date:
        raise ValueError(
            f"filing_date {filing_date} precedes event_date {event_date}; "
            "check the cover-page parse before admitting this row"
        )

    if filing_date >= RULE_CHANGE:
        days = business_days_between(event_date, filing_date)
        return Delay(days, "business", CAP_BUSINESS_DAYS, days > CAP_BUSINESS_DAYS)

    days = (filing_date - event_date).days
    return Delay(days, "calendar", CAP_CALENDAR_DAYS, days > CAP_CALENDAR_DAYS)
