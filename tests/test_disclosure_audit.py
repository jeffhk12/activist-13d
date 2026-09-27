"""Tier: 2. Pin amendment/footnote separation and exposure arithmetic."""

import pytest

from activist13d.disclosure_audit import cover_amendments, exposure


def test_numbered_cover_and_exact_span():
    text = "SCHEDULE 13D (Amendment No. 2)* Issuer"
    r = cover_amendments(text)[0]
    assert r["number"] == 2
    assert text[r["start"] : r["end"]] == r["quote"] == "(Amendment No. 2)"
    assert cover_amendments(text) == [r]


def test_blank_field_footnote_and_body_not_cover():
    assert cover_amendments("(Amendment No. ) 1 Issuer") == []
    assert cover_amendments("(Amendment No. 0)") == []
    assert cover_amendments("x" * 2000 + "(Amendment No. 2)") == []
    with pytest.raises(ValueError):
        cover_amendments(None)


def test_exposure_contribution_and_missing_category():
    rows = [
        dict(excess=0.3, industry="57"),
        dict(excess=0.1, industry="57"),
        dict(excess=-0.1, industry="missing"),
    ]
    d = exposure(rows, "industry")
    assert d["57"]["mean"] == pytest.approx(0.2)
    assert d["57"]["contribution"] == pytest.approx(0.4 / 3)
    assert d["57"]["leave_out"]["mean"] == -0.1
    assert sum(s["contribution"] for s in d.values()) == pytest.approx(0.1)
    assert sum(s["n"] for s in d.values()) == 3
