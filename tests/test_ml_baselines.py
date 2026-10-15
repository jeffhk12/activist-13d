"""Hand-pinned ridge/metric contracts, temporal refusals, parity and replay.

Inputs: synthetic examples plus optional preserved local 13D data.
Outputs: assertions; no vendor/model endpoint or source-data mutation.
Identity: centered ridge normal equations, mean-loss penalty and event errors.
Tier: 2 support. Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
    .venv/bin/python -m pytest tests/test_ml_baselines.py
"""

import copy
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/ml_experiment/run_baselines.py"
SPEC = importlib.util.spec_from_file_location("ml_baselines", SCRIPT)
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


def test_ridge_mean_loss_penalty_is_hand_pinned():
    # X=[-1,+1], y=[0,2]. xbar=0, ybar=1; sum(x*yc)=2.
    # beta=2/(2+n*lambda)=2/4=.5, intercept=1.
    state = baseline.fit_ridge([[-1], [1]], [0, 2], 1)
    assert state["coefficients"] == pytest.approx([0.5])
    assert state["intercept"] == pytest.approx(1)
    assert state["equivalent_sum_loss_alpha"] == 2
    assert baseline.predict_ridge(state, [[-1], [1]]) == pytest.approx([0.5, 1.5])


def test_intercept_is_not_penalized_and_feature_translation_preserves_predictions():
    # Translate X by 10 and y by 100: beta stays .5, b=101-10*.5=96.
    state = baseline.fit_ridge([[9], [11]], [100, 102], 1)
    assert state["coefficients"] == pytest.approx([0.5])
    assert state["intercept"] == pytest.approx(96)
    assert baseline.predict_ridge(state, [[9], [11]]) == pytest.approx([100.5, 101.5])


def test_ridge_matches_independent_augmented_least_squares_path():
    # A redundant column makes unregularized normal equations singular.
    x = np.array([[-2, -4, 1], [-1, -2, 0], [1, 2, 1], [2, 4, 0]], dtype=float)
    y, penalty = np.array([0, 1, 2, 4], dtype=float), 0.3
    state = baseline.fit_ridge(x, y, penalty)
    xc, yc = x - x.mean(axis=0), y - y.mean()
    # Solve least squares on [Xc; sqrt(n*lambda)*I], [yc; 0].
    augmented = np.vstack([xc, math.sqrt(len(y) * penalty) * np.eye(x.shape[1])])
    rhs = np.concatenate([yc, np.zeros(x.shape[1])])
    expected, *_ = np.linalg.lstsq(augmented, rhs, rcond=None)
    assert state["coefficients"] == pytest.approx(expected, rel=1e-10, abs=1e-10)
    assert state["intercept"] == pytest.approx(y.mean() - x.mean(axis=0) @ expected)


def test_error_estimators_and_skill_have_hand_computed_values():
    # y=[0,2], p=[1,0] -> errors=[1,-2], SSE=5, MAE=1.5, RMSE=sqrt(2.5).
    # Reference [1,1] has SSE=2, so MSE skill=1-5/2=-1.5.
    result = baseline.metrics([0, 2], [1, 0], [1, 1])
    assert result["n"] == 2
    assert result["sse"] == 5
    assert result["mae"] == 1.5
    assert result["rmse"] == math.sqrt(2.5)
    assert result["mse_skill_vs_training_mean"] == -1.5
    assert result["spearman"] == pytest.approx(-1)


def test_tied_ranks_and_undefined_rank_or_skill_are_explicit():
    assert baseline.average_ranks([1, 1, 3]) == [1.5, 1.5, 3]
    assert baseline.spearman([1, 2, 3], [1, 1, 3]) == pytest.approx(math.sqrt(3) / 2)
    assert baseline.spearman([1, 2], [0, 0]) is None
    assert baseline.spearman([1], [2]) is None
    assert baseline.metrics([1, 1], [1, 1], [1, 1])["mse_skill_vs_training_mean"] is None


@pytest.mark.parametrize("penalty", [0, -1, float("inf"), float("nan"), True])
def test_invalid_penalties_are_refused(penalty):
    with pytest.raises(ValueError, match="penalty"):
        baseline.fit_ridge([[-1], [1]], [0, 2], penalty)


def test_invalid_targets_dimensions_and_predictions_are_refused():
    with pytest.raises(ValueError, match="nonfinite"):
        baseline.fit_ridge([[-1], [1]], [0, float("nan")], 1)
    with pytest.raises(ValueError, match="Empty"):
        baseline.fit_ridge([], [], 1)
    with pytest.raises(ValueError, match="length mismatch"):
        baseline.fit_ridge([[-1], [1]], [0], 1)
    with pytest.raises(ValueError, match="dimension"):
        baseline.forecast([[-1], [1]], [0, 2], [[1, 2]], 1)
    with pytest.raises(ValueError, match="dimensions"):
        baseline.predict_ridge({"coefficients": [1], "intercept": 0}, [[1, 2]])
    with pytest.raises(ValueError, match="do not align"):
        baseline.metrics([1, 2], [1], [0, 0])


def test_forecast_does_not_use_or_mutate_later_outcomes_or_inputs():
    training_x, training_y, later_x = [[-1], [1]], [0, 2], [[0], [2]]
    before = copy.deepcopy((training_x, training_y, later_x))
    values, state = baseline.forecast(training_x, training_y, later_x, 1)
    assert values == {"training_mean": [1, 1], "zero_excess": [0, 0], "ridge": [1, 2]}
    assert state["ridge"]["coefficients"] == pytest.approx([0.5])
    # Evaluation values can be changed without entering the forecast interface.
    baseline.metrics([0, 1], values["ridge"], values["training_mean"])
    baseline.metrics([1_000, -1_000], values["ridge"], values["training_mean"])
    after_values, _ = baseline.forecast(training_x, training_y, later_x, 1)
    assert values == after_values
    assert (training_x, training_y, later_x) == before


def test_future_label_and_wrong_order_cannot_enter_a_fold():
    metadata = [{"row_id": "known", "entry": "2018-01-01", "label_end": "2020-12-31"},
                {"row_id": "cutoff", "entry": "2019-01-01", "label_end": "2021-01-01"},
                {"row_id": "new", "entry": "2021-01-04", "label_end": "2023-01-04"}]
    fold = {"training_row_ids": ["known"], "later_row_ids": ["new"], "training_X": [[0]], "later_X": [[1]]}
    baseline.validate_fold(metadata, fold, 2021)
    fold["training_row_ids"].append("cutoff")
    fold["training_X"].append([2])
    with pytest.raises(ValueError, match="matured-label"):
        baseline.validate_fold(metadata, fold, 2021)


def test_row_alignment_label_unit_and_missing_outcome_refusals():
    features = [{"row_id": "a"}]
    targets = [{"row_id": "a", baseline.TARGET: 0, "label_end": "2020-01-01", "unit": "decimal cumulative return difference"}]
    meta = [{"row_id": "a", "entry": "2018-01-01", "accepted_et": "2017-12-29T12:00:00", "label_end": "2020-01-01",
             "industry_as_of": "2017-12-28", "market_cap_as_of": "2017-11-30", "cohort_for_diagnostics_only": "focused"}]
    baseline.validate_rows(features, targets, meta)
    for value in (None, float("nan"), True):
        wrong = copy.deepcopy(targets)
        wrong[0][baseline.TARGET] = value
        with pytest.raises(ValueError, match="no zero substitution"):
            baseline.validate_rows(features, wrong, meta)
    wrong = copy.deepcopy(targets)
    wrong[0]["unit"] = "percent"
    with pytest.raises(ValueError, match="unit"):
        baseline.validate_rows(features, wrong, meta)
    with pytest.raises(ValueError, match="row IDs"):
        baseline.validate_rows(features * 2, targets * 2, meta * 2)
    wrong = copy.deepcopy(meta)
    wrong[0]["industry_as_of"] = "2018-01-02"
    with pytest.raises(ValueError, match="chronology"):
        baseline.validate_rows(features, targets, wrong)


def test_pooled_rmse_uses_pooled_errors_not_mean_fold_rmse():
    # Three errors [0,0,3] give pooled RMSE sqrt(9/3)=sqrt(3), not (0+3)/2.
    predictions = [{"row_id": name, "prediction_year": year, "cohort": "focused",
                    "predictions": dict(training_mean=0, zero_excess=0, ridge=value)}
                   for name, year, value in (("a", 2021, 0), ("b", 2021, 0), ("c", 2022, 3))]
    targets = [{"row_id": name, baseline.TARGET: 0} for name in ("a", "b", "c")]
    result = baseline.score_predictions(predictions, targets)
    assert result["pooled"]["ridge"]["rmse"] == pytest.approx(math.sqrt(3))
    assert "spearman" not in result["pooled"]["ridge"]
    assert result["by_prediction_year"]["2021"]["ridge"]["spearman"] is None
    assert result["error_concentration"]["ridge"]["largest_five_share_of_sse"] == 1


def test_frozen_contract_declares_conventions_before_fitting():
    protocol = json.loads(baseline.PROTOCOL.read_text())
    assert protocol["target"]["horizon_sessions"] == 504
    assert protocol["prediction_years"] == [2021, 2022, 2023]
    assert [row["name"] for row in protocol["models"]] == list(baseline.MODELS)
    assert protocol["models"][2]["lambda"] == 1
    assert protocol["models"][2]["intercept_penalized"] is False
    assert protocol["expected_fold_counts"] == [[2021, 118, 106, 51], [2022, 254, 110, 63], [2023, 365, 86, 69]]
    assert protocol["primary_metric"].startswith("RMSE")
    assert "None in checkpoint 3" in protocol["tuning"]


def test_offline_artifact_replay_and_prediction_before_evaluation():
    if not (baseline.PREVIEW / "targets.jsonl").exists():
        pytest.skip("Preserved local feature/target archive is absent in CI")
    order = []
    first, summary = baseline.build(lambda name, payload: order.append(name))
    second, replay = baseline.build()
    assert first == second and summary == replay
    assert order[0] == "prefit-manifest.json"
    assert order.index("predictions.jsonl") < order.index("evaluation.json")
    assert summary["evaluated_events"] == 302
    assert sum(summary["evaluated_cohort_counts"].values()) == 302
    assert summary["preprocessing_reconstructed_exactly"]
    assert not summary["hyperparameters_tuned"]
    assert not summary["independent_final_test"]
