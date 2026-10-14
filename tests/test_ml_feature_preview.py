"""Synthetic estimator and refusal checks for the ML feature preview; no data or APIs."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/ml_experiment/build_feature_preview.py"
SPEC = importlib.util.spec_from_file_location("ml_feature_preview", SCRIPT)
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


def field(value, status="present"):
    return {"status": status, "value": value}


def test_ownership_overlap_is_not_added_and_missing_is_not_zero():
    rows = [{"percent_of_class": field(v)} for v in (8, 8, 8, None)]
    # Three identical 8% reports and one missing: max=8, coverage=3/4.
    assert preview.ownership_summary(rows) == (8, 0.75)
    assert preview.ownership_summary([]) == (None, None)
    assert preview.ownership_summary([{"percent_of_class": field(0)}]) == (0, 1)
    assert preview.ownership_summary([{"percent_of_class": field(8, "ambiguous")}]) == (None, 0)


def test_out_of_range_and_nonfinite_ownership_are_unavailable():
    rows = [{"percent_of_class": field(v)} for v in (-1, 101, "nan", True)]
    assert preview.ownership_summary(rows) == (None, 0)


def test_market_cap_units_and_category_boundaries():
    assert preview.market_cap_usd("500000") == 500_000_000  # 500,000 thousands.
    assert preview.market_cap_usd(-1) is None
    assert preview.industry_code(3089) == "30"
    assert preview.industry_code("0100") == "01"
    assert preview.industry_code(9999) is None
    assert preview.industry_code(0) is None


def test_calendar_lag_and_future_event_refusal():
    assert preview.filing_lag("2020-01-06", "2020-01-03") == 3
    assert preview.filing_lag("2020-01-03", "2020-01-06") is None
    assert preview.filing_lag("2020-01-03", None) is None


def test_history_uses_maximum_not_sum_and_requires_matching_issuer():
    history = {"reporter_history": [
        {"prior_submission_count": 4, "prior_other_issuer_count": 2},
        {"prior_submission_count": 4, "prior_other_issuer_count": 2}],
        "issuer_history": [{"cik": "issuer", "prior_reporter_ciks_outside_current_group": 3}]}
    result = preview.history_features(history, "issuer")
    assert result == {"header_reporter_count": 2, "prior_header_submission_count_max": 4,
                      "prior_header_other_issuer_count_max": 2, "prior_issuer_other_reporter_count": 3}
    with pytest.raises(ValueError, match="unique matching issuer"):
        preview.history_features(history, "another")
