"""Tier: 2. Hand-pinned decomposition, weighting, removals and refusal tests."""

import pytest

from activist13d.concentration import diagnostic, simple


def sample():
    return [
        dict(
            accession=str(i),
            entry="2020-01-01",
            year="2020" if i < 2 else "2021",
            issuer="a" if i < 2 else "b",
            managers=m,
            excess=x,
        )
        for i, (m, x) in enumerate([(["m"], 0.6), (["m", "n"], 0.2), (["n"], -0.2)])
    ]


def test_contributions_and_weighting():
    d = diagnostic(sample())
    assert d["overall"]["mean"] == pytest.approx(0.2)  # (.6+.2-.2)/3
    assert d["equal_company_mean"] == pytest.approx(0.1)  # ((.6+.2)/2-.2)/2
    assert d["groups"]["manager"]["m"]["contribution"] == pytest.approx(0.7 / 3)
    assert d["groups"]["manager"]["n"]["contribution"] == pytest.approx(-0.1 / 3)
    assert d["groups"]["manager"]["m"]["leave_out"]["mean"] == -0.2
    assert d["groups"]["manager"]["n"]["leave_out"]["mean"] == 0.6
    for dimension in d["groups"].values():
        assert sum(v["contribution"] for v in dimension.values()) == pytest.approx(0.2)


def test_removals_and_replay():
    d = diagnostic(sample())
    assert d["removals"][0]["without_top_events"]["mean"] == 0
    assert d["removals"][0]["share_positive_excess"] == pytest.approx(0.75)
    assert d["removals"][0]["without_top_companies"]["mean"] == -0.2
    assert diagnostic(sample()) == d
    assert sample()[0]["excess"] == 0.6


def test_refuse_invalid_or_ambiguous_inputs():
    with pytest.raises(ValueError):
        diagnostic([])
    with pytest.raises(ValueError):
        diagnostic([dict(sample()[0], managers=[])])
    with pytest.raises(ValueError):
        diagnostic([dict(sample()[0], managers=["m", "m"])])
    with pytest.raises(ValueError):
        simple([dict(excess=None)])
    assert simple([])["mean"] is None
