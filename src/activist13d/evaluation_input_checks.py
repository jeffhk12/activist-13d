"""Tier: 2. Outcome-blind source-key and pre-event liquidity checks.
Inputs: daily JSON rows or strictly prior rows. Outputs: key coverage and ADV.
Identity: required keys = present + absent; ADV uses exactly 20 prior sessions.
No future return/price values are read by key inspection.
Run: PYTHONPATH=src .venv/bin/python -m pytest tests/test_evaluation_input_checks.py
"""

from activist13d.phase1_baseline import number


def daily_keys(payload, day):
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) >= 50000 or payload.get("next"):
        raise ValueError("missing_or_truncated_page")
    keyed = {}
    for row in rows:
        key = row.get("permno")
        if type(key) is not int or row.get("dlycaldt") != day or key in keyed:
            raise ValueError("date_or_security_key_failure")
        keyed[key] = row
    return keyed


def presence(needed, keyed):
    return {
        "required": len(needed),
        "present": len(set(needed) & set(keyed)),
        "missing": sorted(set(needed) - set(keyed)),
    }


def lagged_adv(public, dates, rows):
    if len(dates) != 20 or len(set(dates)) != 20 or any(d >= public for d in dates):
        raise ValueError("exactly_twenty_strictly_prior_sessions_required")
    values = []
    for d in dates:
        row = rows.get(d, {})
        price = number(row.get("dlyclose"))
        volume = number(row.get("dlyvol"))
        if price is None or price <= 0 or volume is None or volume < 0:
            return None
        values.append(price * volume)
    result = sum(values) / 20
    return result if result > 0 else None
