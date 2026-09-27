"""Tier: 2. Cash-conserving development portfolio with lagged liquidity and costs.
Inputs: signal schedules (no future-return filter), daily rows, lagged cash factors.
Outputs: daily NAV, trades, contemporaneous skips and explicit incomplete status.
Identity: NAV=cash+marked positions; one issuer position; never bridge missing returns.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_portfolio_accounting.py
"""

import math
import statistics
from collections import defaultdict
from datetime import date

from activist13d.phase1_baseline import number


def bill_daily(discount_percent):
    d = number(discount_percent)
    if d is None or not -5 < d < 50:
        raise ValueError("Invalid cash rate")
    price = 1 - (d / 100) * 91 / 360
    return (1 / price) ** (1 / 91) - 1


def cost(notional, adv, zero=False):
    if zero or notional <= 0:
        return 0.0
    if adv <= 0:
        raise ValueError("Positive lagged ADV required")
    return notional * (0.001 + 0.005 * math.sqrt(notional / adv)) + 1.0


def prior_adv(permno, day, sessions, panel, positions):
    i = positions[day]
    if i < 20:
        return None
    values = []
    for d in sessions[i - 20 : i]:
        row = panel.get(permno, {}).get(d, {})
        close = number(row.get("dlyclose"))
        volume = number(row.get("dlyvol"))
        if close is None or close <= 0 or volume is None or volume < 0:
            return None
        values.append(close * volume)
    result = statistics.mean(values)
    return result if result > 0 else None


def portfolio(
    events, sessions, panel, cash_factors, capital, start, end, zero_cost=False, zero_cash=False
):
    positions = {day: i for i, day in enumerate(sessions)}
    days = [d for d in sessions if start <= d <= end]
    signals = defaultdict(list)
    for e in events:
        signals[e["entry"]].append(e)
    cash = float(capital)
    holds = {}
    ledger = []
    trades = []
    skips = []
    previous_nav = float(capital)
    previous = sessions[positions[days[0]] - 1]
    failure = None
    for day in days:
        staged = {k: dict(v) for k, v in holds.items()}
        pending = []
        pending_skips = []
        try:
            factor = 0.0 if zero_cash else cash_factors[day]
            cash_now = cash * (1 + factor)
            interest = cash_now - cash
            proceeds_at_close = 0.0
            daily_cost = 0.0
            # Mark existing positions; delisting settlement is available only at close.
            for issuer, h in list(staged.items()):
                row = panel.get(h["permno"], {}).get(day)
                ret = number(row.get("dlyret")) if row else None
                if (
                    row is None
                    or ret is None
                    or ret < -1
                    or row.get("dlyretmissflg") != "NA"
                    or row.get("dlyprevdt") != previous
                    or row.get("dlydelflg") not in {"N", "Y"}
                ):
                    raise ValueError("unresolved_held_return:" + issuer + ":" + str(h["permno"]))
                h["value"] *= 1 + ret
                if row["dlydelflg"] == "Y":
                    proceeds_at_close += h["value"]
                    pending.append(
                        dict(
                            day=day,
                            side="delisting",
                            issuer=issuer,
                            permno=h["permno"],
                            notional=h["value"],
                            cost=0,
                            accession=h["accession"],
                        )
                    )
                    del staged[issuer]
            for e in sorted(signals.get(day, []), key=lambda x: x["accession"]):
                reason = None
                row = panel.get(e["permno"], {}).get(day, {})
                opening = number(row.get("dlyopen"))
                adv = prior_adv(e["permno"], day, sessions, panel, positions)
                if e["issuer"] in holds or e["issuer"] in staged:
                    reason = "issuer_already_held"
                elif len(staged) >= 20:
                    reason = "position_limit"
                elif (
                    opening is None
                    or opening <= 0
                    or row.get("conditionaltype") != "RW"
                    or row.get("tradingstatusflg") != "A"
                ):
                    reason = "unusable_entry_open"
                elif adv is None:
                    reason = "missing_prior_20_session_liquidity"
                if reason:
                    pending_skips.append(dict(day=day, accession=e["accession"], reason=reason))
                    continue
                order = min(0.05 * previous_nav, 0.01 * adv, cash_now)
                lo = 0.0
                hi = order
                for _ in range(50):
                    mid = (lo + hi) / 2
                    if mid + cost(mid, adv, zero_cost) <= cash_now:
                        lo = mid
                    else:
                        hi = mid
                order = lo
                if order < 0.001 * capital:
                    pending_skips.append(
                        dict(
                            day=day,
                            accession=e["accession"],
                            reason="below_minimum_after_cash_or_capacity",
                        )
                    )
                    continue
                close = number(row.get("dlyclose"))
                if close is None or close <= 0 or row.get("dlydelflg") != "N":
                    raise ValueError("unresolved_new_position_mark:" + e["accession"])
                fee = cost(order, adv, zero_cost)
                cash_now -= order + fee
                daily_cost += fee
                staged[e["issuer"]] = dict(
                    permno=e["permno"],
                    value=order * close / opening,
                    exit=e["exit"],
                    accession=e["accession"],
                )
                pending.append(
                    dict(
                        day=day,
                        side="buy",
                        issuer=e["issuer"],
                        permno=e["permno"],
                        accession=e["accession"],
                        notional=order,
                        cost=fee,
                        adv=adv,
                        target=0.05 * previous_nav,
                    )
                )
            for issuer, h in list(staged.items()):
                if day < h["exit"]:
                    continue
                row = panel.get(h["permno"], {}).get(day, {})
                adv = prior_adv(h["permno"], day, sessions, panel, positions)
                close = number(row.get("dlyclose"))
                vol = number(row.get("dlyvol"))
                if (
                    adv is None
                    or close is None
                    or close <= 0
                    or vol is None
                    or vol <= 0
                    or row.get("conditionaltype") != "RW"
                    or row.get("tradingstatusflg") != "A"
                ):
                    pending_skips.append(
                        dict(
                            day=day,
                            accession=h["accession"],
                            reason="exit_waits_for_usable_trade_liquidity",
                        )
                    )
                    continue
                amount = min(h["value"], 0.01 * adv)
                fee = min(amount, cost(amount, adv, zero_cost))
                daily_cost += fee
                proceeds_at_close += amount - fee
                h["value"] -= amount
                pending.append(
                    dict(
                        day=day,
                        side="sell",
                        issuer=issuer,
                        permno=h["permno"],
                        accession=h["accession"],
                        notional=amount,
                        cost=fee,
                        adv=adv,
                    )
                )
                if h["value"] < 1e-8:
                    del staged[issuer]
            cash_now += proceeds_at_close
            invested = sum(h["value"] for h in staged.values())
            nav = cash_now + invested
            if cash_now < -1e-7 or not math.isfinite(nav) or nav <= 0:
                raise ValueError("accounting_refusal")
            daily = dict(
                day=day,
                nav=nav,
                cash=cash_now,
                invested=invested,
                positions=len(staged),
                return_=nav / previous_nav - 1,
                cost=daily_cost,
                cash_interest=interest,
            )
        except (ValueError, KeyError) as error:
            failure = dict(day=day, reason=str(error))
            break
        ledger.append(daily)
        trades.extend(pending)
        skips.extend(pending_skips)
        cash = cash_now
        holds = staged
        previous_nav = nav
        previous = day
    complete = failure is None
    summary = dict(
        status="complete" if complete else "incomplete_unresolved_mark",
        failure=failure,
        capital=capital,
        days=len(ledger),
        last_valued_day=ledger[-1]["day"] if ledger else None,
        terminal_nav=previous_nav if complete else None,
        total_return=previous_nav / capital - 1 if complete else None,
        total_cost=sum(r["cost"] for r in trades),
        buys=sum(r["side"] == "buy" for r in trades),
        open_positions=len(holds),
        average_cash_weight=statistics.mean(r["cash"] / r["nav"] for r in ledger)
        if ledger
        else None,
        turnover=sum(r["notional"] for r in trades if r["side"] in {"buy", "sell"})
        / statistics.mean(r["nav"] for r in ledger)
        if ledger
        else None,
    )
    if complete and ledger:
        elapsed = (
            date.fromisoformat(days[-1]) - date.fromisoformat(sessions[positions[days[0]] - 1])
        ).days
        peak = capital
        drawdown = 0.0
        for r in ledger:
            peak = max(peak, r["nav"])
            drawdown = min(drawdown, r["nav"] / peak - 1)
        summary.update(
            cagr=(previous_nav / capital) ** (365.25 / elapsed) - 1, max_drawdown=drawdown
        )
    return dict(summary=summary, daily=ledger, trades=trades, skips=skips, terminal_positions=holds)
