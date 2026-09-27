"""Tier: 2. Hand-computable accounting, liquidity, cash and failure fixtures."""

from datetime import date, timedelta

import pytest

from activist13d.portfolio_accounting import bill_daily, cost, portfolio, prior_adv


def fixture():
    days = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(25)]
    panel = {
        1: {
            d: dict(
                dlyopen=10,
                dlyclose=10,
                dlyvol=100000,
                dlyret=0,
                dlyretmissflg="NA",
                dlyprevdt=days[i - 1],
                dlydelflg="N",
                conditionaltype="RW",
                tradingstatusflg="A",
            )
            for i, d in enumerate(days)
        }
    }
    event = dict(accession="a", issuer="i", permno=1, entry=days[20], exit=days[22])
    return days, panel, event


def test_round_trip_and_cash_conservation():
    days, p, e = fixture()
    result = portfolio([e], days, p, {d: 0 for d in days}, 100000, days[20], days[24])
    assert result["summary"]["status"] == "complete"
    fee = cost(5000, 1000000)
    assert result["summary"]["terminal_nav"] == pytest.approx(100000 - 2 * fee)
    assert len(result["trades"]) == 2
    for r in result["daily"]:
        assert r["nav"] == pytest.approx(r["cash"] + r["invested"])
        assert r["cash"] >= 0


def test_missing_future_mark_refuses_without_dropping_entry():
    days, p, e = fixture()
    del p[1][days[21]]
    r = portfolio([e], days, p, {d: 0 for d in days}, 100000, days[20], days[24])
    assert r["summary"]["status"] == "incomplete_unresolved_mark"
    assert r["summary"]["total_return"] is None
    assert r["trades"][0]["side"] == "buy"
    assert r["summary"]["last_valued_day"] == days[20]


def test_delisting_once_and_prior_liquidity():
    days, p, e = fixture()
    p[1][days[20]]["dlyvol"] = 1e12
    assert prior_adv(1, days[20], days, p, {d: i for i, d in enumerate(days)}) == 1000000
    p[1][days[21]].update(dlydelflg="Y", dlyret=0.2)
    del p[1][days[22]]
    r = portfolio([e], days, p, {d: 0 for d in days}, 100000, days[20], days[24], zero_cost=True)
    assert r["summary"]["terminal_nav"] == pytest.approx(101000)
    assert [t["side"] for t in r["trades"]] == ["buy", "delisting"]


def test_capacity_minimum_duplicate_and_cash_conversion():
    days, p, e = fixture()
    r = portfolio([e], days, p, {d: 0 for d in days}, 100000000, days[20], days[24])
    assert not r["trades"]
    assert r["skips"][0]["reason"] == "below_minimum_after_cash_or_capacity"
    r = portfolio(
        [e, dict(e, accession="b")], days, p, {d: 0 for d in days}, 100000, days[20], days[24]
    )
    assert r["summary"]["buys"] == 1
    assert r["skips"][0]["reason"] == "issuer_already_held"
    assert (1 + bill_daily(5)) ** 91 == pytest.approx(1 / (1 - 0.05 * 91 / 360))


def test_exit_wind_down_is_marked_until_fully_sold():
    days, p, e = fixture()
    for d in days[21:]:
        p[1][d]["dlyret"] = 1
    r = portfolio([e], days, p, {d: 0 for d in days}, 100000, days[20], days[24], zero_cost=True)
    sells = [t for t in r["trades"] if t["side"] == "sell"]
    assert len(sells) == 3
    assert all(t["notional"] <= 0.01 * t["adv"] for t in sells)
    assert r["summary"]["open_positions"] == 1
