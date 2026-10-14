"""Hand-pinned preprocessing, temporal-boundary and leakage refusal tests."""

import copy
import importlib.util
import math
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/ml_experiment/prepare_inputs.py"
SPEC = importlib.util.spec_from_file_location("ml_prepare_inputs", SCRIPT)
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)

DEFINITIONS = {"ownership": {"kind": "numeric"}, "industry": {"kind": "categorical"}}


def test_training_median_scaling_and_missing_flag_are_hand_pinned():
    rows = [{"ownership": value, "industry": "30"} for value in (4, 8, None)]
    processor = prepare.InputPreprocessor(DEFINITIONS, []).fit(rows)
    assert processor.state["medians"]["ownership"] == 6
    assert processor.state["means"]["ownership"] == 6
    assert processor.state["scales"]["ownership"] == pytest.approx(math.sqrt(8 / 3))
    matrix = processor.transform(rows)
    assert matrix[0] == pytest.approx([-math.sqrt(1.5), 0])
    assert matrix[1] == pytest.approx([math.sqrt(1.5), 0])
    assert matrix[2] == pytest.approx([0, 1])


def test_future_extreme_does_not_refit_and_unknown_category_is_all_zero():
    rows = [{"ownership": 4, "industry": "30"}, {"ownership": 8, "industry": "60"}]
    processor = prepare.InputPreprocessor(DEFINITIONS, []).fit(rows)
    before = copy.deepcopy(processor.state)
    # Training mean=6, SD=2. New value 20 maps to 7, not a new fitted mean.
    assert processor.transform([{"ownership": 20, "industry": "75"}]) == [[7, 0, 0]]
    assert processor.state == before
    assert processor.state["categories"] == ["30", "60"]


def test_log_transform_and_constant_removal_depend_only_on_training():
    rows = [{"ownership": 0, "industry": "30"}, {"ownership": 3, "industry": "30"}]
    processor = prepare.InputPreprocessor(DEFINITIONS, ["ownership"]).fit(rows)
    # log1p(0)=0 and log1p(3)=log(4); mean=log(4)/2, SD=log(4)/2.
    matrix = processor.transform(rows)
    assert matrix[0] == pytest.approx([-1])
    assert matrix[1] == pytest.approx([1])
    assert processor.state["feature_names"] == ["ownership"]
    assert "industry==30" in processor.state["dropped_constant_columns"]


def test_empty_matured_training_and_invalid_features_are_refused():
    processor = prepare.InputPreprocessor(DEFINITIONS, [])
    with pytest.raises(ValueError, match="No matured"):
        processor.fit([])
    with pytest.raises(ValueError, match="only the declared"):
        processor.fit([{"ownership": 4, "industry": "30", "future_return": 0.5}])
    with pytest.raises(ValueError, match="Nonfinite"):
        processor.fit([{"ownership": float("nan"), "industry": "30"}])
    with pytest.raises(ValueError, match="Negative"):
        prepare.InputPreprocessor(DEFINITIONS, ["ownership"]).fit([{"ownership": -1, "industry": "30"}])


def test_labels_must_finish_strictly_before_the_prediction_cutoff():
    rows = [{"row_id": "mature", "entry": "2018-01-01", "label_end": "2020-12-31"},
            {"row_id": "at_cutoff", "entry": "2019-01-01", "label_end": "2021-01-01"},
            {"row_id": "later", "entry": "2021-01-04", "label_end": "2023-01-04"}]
    assert prepare.split_rows(rows, 2021) == (["mature"], ["later"])
