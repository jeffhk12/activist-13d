"""Hand-pinned neural derivatives, tree rules, refusals and offline preparation.

Inputs: invented examples and optionally preserved preprocessing archives.
Outputs: assertions; no real-data predictive fit or newly scored real outcomes.
Identity: ReLU forward/derivative, explicit mean-MSE weight penalty, Adam update,
leaf means and additive residual corrections; pooled metrics inherit baseline.
Tier: 2 support. Run: .venv/bin/python -m pytest tests/test_ml_nonlinear.py
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("sklearn")
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts/ml_experiment"))
import nonlinear_models as models  # noqa: E402
import run_nonlinear as runner  # noqa: E402

PROTOCOL = json.loads(runner.PROTOCOL.read_bytes())


def toy_parameters():
    return {name: torch.nn.Parameter(torch.tensor(value, dtype=torch.float64)) for name, value in
            {"W1": [[0.5, -1], [0.25, 0.5]], "b1": [0.1, -0.2], "W2": [0.2, -0.3], "b2": 0.1}.items()}


def test_hand_computed_forward_loss_penalty_and_all_derivatives():
    params = toy_parameters()
    x, y = torch.tensor([[1., 2.]], dtype=torch.float64), torch.tensor([0.5], dtype=torch.float64)
    # z=[1.1,-.2], h=[1.1,0], yhat=.32; error=-.18.
    # Weight squares = 1.6925, bias squares excluded.
    assert models.forward(params, x).item() == pytest.approx(0.32)
    loss, mse, penalty = models.objective(params, x, y, 0.01)
    assert mse.item() == pytest.approx(0.0324)
    assert penalty.item() == pytest.approx(0.016925)
    assert loss.item() == pytest.approx(0.049325)
    loss.backward()
    expected = {"W1": [[-0.062, -0.02], [-0.139, 0.01]], "b1": [-0.072, 0],
                "W2": [-0.392, -0.006], "b2": -0.36}
    for name, value in expected.items():
        np.testing.assert_allclose(params[name].grad.numpy(), value, rtol=1e-12, atol=1e-12)


def test_autograd_matches_independent_algebra_and_finite_differences():
    params = toy_parameters()
    # Avoid ReLU's nondifferentiable zero; second row also exercises a different activation.
    x = torch.tensor([[1., 2.], [-2., 1.]], dtype=torch.float64)
    y = torch.tensor([0.5, -0.2], dtype=torch.float64)
    loss, *_ = models.objective(params, x, y, 0.01)
    loss.backward()
    arrays = {key: np.array(value) for key, value in models.snapshot(params).items()}
    algebra = models.numpy_gradients(arrays, x.numpy(), y.numpy(), 0.01)
    for name, param in params.items():
        expected = param.grad.numpy().copy()
        np.testing.assert_allclose(algebra[name], expected, atol=1e-12, rtol=1e-12)
        for index in np.ndindex(tuple(param.shape)):
            original = param.detach()[index].item()
            with torch.no_grad():
                param[index] = original + 1e-6
            hi = models.objective(params, x, y, 0.01)[0].item()
            with torch.no_grad():
                param[index] = original - 1e-6
            lo = models.objective(params, x, y, 0.01)[0].item()
            with torch.no_grad():
                param[index] = original
            assert (hi - lo) / 2e-6 == pytest.approx(expected[index], abs=1e-8, rel=1e-7)


def test_relu_zero_derivative_and_negative_linear_output():
    params = {name: torch.nn.Parameter(torch.tensor(value, dtype=torch.float64)) for name, value in
              {"W1": [[1.]], "b1": [0.], "W2": [-2.], "b2": -0.1}.items()}
    x = torch.tensor([[0.], [1.]], dtype=torch.float64)
    assert models.forward(params, x).tolist() == pytest.approx([-0.1, -2.1])
    models.forward(params, x[:1]).sum().backward()
    assert params["W1"].grad.item() == 0 and params["b1"].grad.item() == 0


def test_first_adam_step_is_hand_pinned():
    param = torch.nn.Parameter(torch.tensor(2., dtype=torch.float64))
    optimizer = torch.optim.Adam([param], lr=0.1, betas=(0.9, 0.999), eps=1e-8,
                                 weight_decay=0, foreach=False, fused=False)
    param.grad = torch.tensor(3., dtype=torch.float64)
    optimizer.step()
    # m=.3, v=.009; bias correction yields 3 and 9.
    assert param.item() == pytest.approx(2 - 0.1 * 3 / (3 + 1e-8), abs=1e-14)


def test_initialization_dimensions_biases_local_rng_and_same_seed():
    before = torch.random.get_rng_state().clone()
    a = models.initialize(3, 0.25, 11)
    b = models.initialize(3, 0.25, 11)
    assert sum(p.numel() for p in a.values()) == 4 * 3 + 9
    assert a["b1"].tolist() == [0] * 4 and a["b2"].item() == 0.25
    assert models.snapshot(a) == models.snapshot(b)
    assert models.snapshot(a) != models.snapshot(models.initialize(3, 0.25, 23))
    assert torch.equal(before, torch.random.get_rng_state())
    assert all(p.dtype == torch.float64 and p.device.type == "cpu" for p in a.values())


def test_synthetic_training_replays_and_final_diagnostics_match_final_state():
    x = np.linspace(-1, 1, 30).reshape(-1, 1)
    y = np.maximum(x[:, 0], 0) * 0.4 - 0.1
    config = {**PROTOCOL["neural"], "epochs": 80}
    a, trace = models.fit_neural(x, y, config, 11)
    b, again = models.fit_neural(x, y, config, 11)
    assert a == b and trace == again
    assert len(trace["trace"]) == 81 and trace["trace"][-1]["epoch"] == 80
    assert trace["trace"][-1]["objective"] < trace["trace"][0]["objective"]
    predictions = np.array(models.predict_neural(a, x))
    mse = float(np.mean((predictions - y) ** 2))
    assert trace["trace"][-1]["mse"] == pytest.approx(mse, abs=1e-13)


def small_protocol():
    protocol = copy.deepcopy(PROTOCOL)
    protocol["neural"]["epochs"] = 2
    for name in ("tree", "forest", "boosting"):
        protocol[name]["params"]["min_samples_leaf"] = 1
        protocol[name]["params"]["max_depth"] = 1
    protocol["forest"]["params"].update(n_estimators=3, bootstrap=False, max_features=None)
    protocol["boosting"]["params"].update(n_estimators=1, learning_rate=0.5)
    return protocol


def test_tree_leaf_means_forest_average_and_first_boost_correction_hand_pinned():
    # Split between 1 and 2. Leaf means 0 and 2; overall mean 1.
    # One boost tree fits residuals -1,+1 and applies half: .5,1.5.
    x, y = [[0], [1], [2], [3]], [0, 0, 2, 2]
    fitted = models.fit_trees(x, y, small_protocol())
    assert fitted["tree"].predict(x).tolist() == [0, 0, 2, 2]
    assert fitted["forest"].predict(x).tolist() == [0, 0, 2, 2]
    assert fitted["boosting"].predict(x).tolist() == [0.5, 0.5, 1.5, 1.5]
    serialized = models.serialize_trees(fitted)
    assert serialized["boosting"]["initial_mean"] == 1
    for name in fitted:
        assert models.predict_trees(serialized[name], x) == pytest.approx(fitted[name].predict(x), abs=1e-14)


def test_serialized_ensembles_reproduce_library_predictions_on_new_inputs():
    rng = np.random.default_rng(73)
    x, later = rng.normal(size=(90, 3)), rng.normal(size=(13, 3))
    y = np.maximum(x[:, 0], 0) + x[:, 1] * x[:, 2]
    fitted = models.fit_trees(x, y, PROTOCOL)
    state = models.serialize_trees(fitted)
    roundtrip = json.loads(json.dumps(state, allow_nan=False))
    for name, estimator in fitted.items():
        assert models.predict_trees(roundtrip[name], later) == pytest.approx(estimator.predict(later), abs=1e-12)
        for tree in state[name]["trees"]:
            assert len(tree["value"]) <= (7 if name != "forest" else 15)


def test_forest_export_preserves_a_split_between_adjacent_float32_inputs():
    # Two exactly representable inputs with a double-precision midpoint split.
    # Exercise the same forest export/check seam as the Windows failure.
    lower = np.nextafter(np.float32(2), np.float32(np.inf))
    upper = np.nextafter(lower, np.float32(np.inf))
    x = [[float(lower)], [float(upper)]]
    protocol = small_protocol()
    protocol["tree"]["params"]["min_samples_leaf"] = 2  # constant tree isolates forest
    values, _, _ = models.forecast(x, [0, 2], x, protocol)
    assert values["forest"] == pytest.approx([0, 2], abs=1e-14)


def test_ensemble_contains_every_seed_and_forecast_excludes_later_labels():
    x, y, later = [[-1], [0], [1], [2]], [0, 0, 1, 2], [[-0.5], [1.5]]
    original = copy.deepcopy((x, y, later))
    values, state, diagnostics = models.forecast(x, y, later, small_protocol())
    expected = np.mean([values[f"neural_seed_{s}"] for s in PROTOCOL["seeds"]], axis=0)
    assert values["neural_ensemble"] == pytest.approx(expected)
    assert len(state["neural"]) == len(diagnostics) - 3 == 5
    assert (x, y, later) == original
    assert "later_y" not in __import__('inspect').signature(models.forecast).parameters


@pytest.mark.parametrize("x,y", [([], []), ([[1]], [float("nan")]), ([[float("inf")]], [0]),
                                  ([[1], [2]], [0]), ([[1]], [True])])
def test_bad_training_inputs_are_refused(x, y):
    with pytest.raises(ValueError):
        models.fit_neural(x, y, PROTOCOL["neural"], 11)


def test_bad_dimensions_penalty_and_failed_seed_are_not_silently_ignored(monkeypatch):
    with pytest.raises(ValueError, match="dimension"):
        models.forecast([[1]], [0], [[1, 2]], PROTOCOL)
    with pytest.raises(ValueError, match="penalty"):
        models.objective(toy_parameters(), torch.tensor([[1., 2.]], dtype=torch.float64),
                         torch.tensor([0.5]), -1)
    def fail(*args, **kwargs):
        raise ValueError("seed failed")
    monkeypatch.setattr(models, "fit_neural", fail)
    with pytest.raises(ValueError, match="seed failed"):
        models.forecast([[1]], [0], [[2]], PROTOCOL)


def test_generic_metrics_are_hand_pinned_and_ranks_not_pooled():
    rows = [{"row_id": str(i), "prediction_year": 2021 if i < 2 else 2022, "cohort": "focused",
             "predictions": {"training_mean": 0., "test": p}} for i, p in enumerate([0., 0., 3.])]
    targets = [{"row_id": str(i), runner.baseline.TARGET: 0} for i in range(3)]
    result = runner.score(rows, targets, ["training_mean", "test"])
    assert result["pooled"]["test"]["rmse"] == math.sqrt(3)
    assert result["pooled"]["test"]["mae"] == 1
    assert "spearman" not in result["pooled"]["test"]
    assert result["largest_five_share_of_sse"]["test"] == 1
    assert result["by_prediction_year"]["2021"]["test"]["spearman"] is None


def test_frozen_model_and_temporal_conventions():
    assert runner.baseline.digest(runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert PROTOCOL["neural"]["width"] == 4 and PROTOCOL["neural"]["epochs"] == 500
    assert PROTOCOL["neural"]["l2"] == 0.01 and PROTOCOL["seeds"] == [11, 23, 37, 51, 71]
    assert PROTOCOL["tree"]["params"]["max_depth"] == 2
    assert PROTOCOL["forest"]["params"]["bootstrap"] is True
    assert PROTOCOL["boosting"]["params"]["n_iter_no_change"] is None
    assert "no Bloomberg" in PROTOCOL["features"]


def test_prepare_replays_without_real_data_fitting(monkeypatch):
    if not (runner.baseline.PREVIEW / "targets.jsonl").exists():
        pytest.skip("Preserved local input archive absent in CI")
    def refuse_fit(*args, **kwargs):
        raise AssertionError("Preparation called a real-data predictor fit")
    monkeypatch.setattr(runner, "forecast", refuse_fit)
    first, summary = runner.build(fit=False)
    second, again = runner.build(fit=False)
    assert first == second and summary == again
    assert summary["real_data_model_fits"] == 0 and summary["reference_events"] == 302
    assert "evaluation.json" not in first and "predictions.jsonl" not in first
    assert list(first)[0] == "prefit-manifest.json"


def test_prediction_persistence_precedes_scoring_with_synthetic_runner_fixture(monkeypatch):
    # Exercise the real orchestration with only invented rows and targets.
    protocol = small_protocol()
    protocol["expected_fold_counts"] = [[2021, 4, 2, 1]]
    folds = {"2021": {"training_X": [[-1], [0], [1], [2]], "training_y": [0, 0, 1, 2],
                      "later_X": [[0.5], [3]], "later_row_ids": ["a", "b"], "feature_names": ["toy"]}}
    targets = [{"row_id": name, runner.baseline.TARGET: y} for name, y in [("a", 1), ("b", 2)]]
    refs = [{"row_id": name, "prediction_year": 2021, "cohort": "focused",
             "predictions": {"training_mean": 0.75, "zero_excess": 0, "ridge": 0.5}}
            for name in ["a", "b"]]
    monkeypatch.setattr(runner, "load_prepared", lambda: (protocol, folds, targets, refs, {}))
    order = []
    first, _ = runner.build(fit=True, emit_to_disk=lambda name, data: order.append(name))
    second, _ = runner.build(fit=True)
    assert first == second
    assert order.index("predictions.jsonl") < order.index("evaluation.json")
    assert order.index("prefit-manifest.json") < order.index("model-states.json")
    assert b"neural_seed_71" in first["predictions.jsonl"]


def test_changed_frozen_protocol_is_refused(tmp_path, monkeypatch):
    changed = tmp_path / "changed.json"
    changed.write_text('{}')
    monkeypatch.setattr(runner, "PROTOCOL", changed)
    with pytest.raises(ValueError, match="hash mismatch"):
        runner.load_prepared()
