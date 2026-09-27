"""Tier: 2. Diagnose missing marks without estimating unobserved investment returns.

Inputs: frozen daily rows, event schedules and stopped portfolio positions.
Outputs: first unresolved mark per schedule and isolated mark sensitivities.
Identity: hypothetical NAV = last observed NAV + position value * (multiple - 1).
Conventions: no future execution or reinvestment; no finite upside bound for equity.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_phase1_valuation_audit.py
"""

import math

from activist13d.phase1_baseline import number

CONVENTIONS = {
    "sensitivity": "isolated instantaneous mark; all other assets unchanged",
    "performance": "not a daily or terminal strategy return",
    "missing": "refuse; never zero fill, carry forward or bridge",
    "upper_bound": None,
}


def invalid_mark(row, previous):
    if row is None:
        return "missing_row"
    ret = number(row.get("dlyret"))
    if ret is None or ret < -1 or not math.isfinite(ret):
        return "missing_or_invalid_return"
    if row.get("dlyretmissflg") != "NA":
        return "return_missing_flag"
    if row.get("dlyprevdt") != previous:
        return "noncontiguous_return"
    if row.get("dlydelflg") not in {"N", "Y"}:
        return "unknown_delisting_status"
    return None


def first_gap(event, rows):
    """Potential holding-window gap, independent of whether portfolio buys it."""
    days = event["days"]
    for previous, day in zip(days, days[1:], strict=False):
        row = rows.get(day)
        reason = invalid_mark(row, previous)
        if reason:
            return {"day": day, "reason": reason, "raw_row": row}
        if row["dlydelflg"] == "Y":
            break
    return None


def isolated_sensitivity(nav, value, capital, multiple):
    if not all(math.isfinite(x) for x in (nav, value, capital, multiple)):
        raise ValueError("finite inputs required")
    if capital <= 0 or nav <= 0 or value < 0 or value > nav or multiple < 0:
        raise ValueError("invalid long-only mark inputs")
    delta = value * (multiple - 1)
    return {"assumed_value_multiple": multiple, "hypothetical_nav": nav + delta,
            "nav_change_dollars": delta, "nav_change_fraction": delta / nav,
            "initial_capital_change_fraction": delta / capital,
            "observed_return": None}
