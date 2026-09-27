"""Tier: 2. Pin issuer weighting, no self-control, strata and coverage refusal."""

import pytest

from activist13d.matched_controls import match_events


def r(a, issuer, x, focused=False, industry="57", year="2020"):
    return dict(
        accession=a,
        issuer=issuer,
        excess=x,
        focused=focused,
        industry=industry,
        entry=year + "-01-02",
        assigned_etf="IWM",
    )


def test_equal_issuer_weight_not_event_weight():
    rows = [r("f", "f", 0.4, True), r("a1", "a", 0.1), r("a2", "a", 0.3), r("b", "b", -0.1)]
    s = match_events(rows, min_issuers=2)[0]
    assert s["control_mean"] == pytest.approx(0.05)  # ((.1+.3)/2-.1)/2
    assert s["difference"] == pytest.approx(0.35)
    assert s["control_issuers"] == 2 and s["control_events"] == 3
    assert match_events(rows, min_issuers=2) == [s]


def test_self_other_year_industry_excluded_and_minimum():
    rows = [
        r("f", "f", 0.4, True),
        r("self", "f", 0.8),
        r("other", "a", 0.1, year="2019"),
        r("sector", "b", 0.1, industry="28"),
    ]
    s = match_events(rows)[0]
    assert s["status"] == "fewer_than_five_control_issuers" and s["control_issuers"] == 0
    assert match_events([r("f", "f", None, True)])[0]["status"] == "unresolved_focal"
