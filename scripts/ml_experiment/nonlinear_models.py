"""Small PyTorch ReLU regressor and fixed sklearn tree comparators.

Inputs: finite train-only matrices, matured labels and declared configuration.
Outputs: JSON-serializable fitted states, forecasts and training diagnostics.
Identity: h=ReLU(X W1+b1), yhat=h W2+b2; objective=MSE+l2*(||W1||²+||W2||²).
Backpropagation is autograd; an independent NumPy derivative is used in tests.
Tier: 2. No file I/O, evaluation labels, model provider, GPU or data download.
Run: imported by run_nonlinear.py; synthetic verification in test_ml_nonlinear.py.
"""

import math

import numpy as np
import torch
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor


def inputs(x, y=None):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or min(x.shape) == 0 or not np.isfinite(x).all():
        raise ValueError("Nonfinite, empty or wrong-dimensional inputs")
    if y is None:
        return x
    if any(isinstance(v, (bool, np.bool_)) for v in y):
        raise ValueError("Boolean targets are not return labels")
    y = np.asarray(y, dtype=np.float64)
    if y.ndim != 1 or len(x) != len(y) or not np.isfinite(y).all():
        raise ValueError("Nonfinite targets or input/target dimension mismatch")
    return x, y


def configure_cpu():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def initialize(p, mean, seed, width=4):
    if isinstance(p, bool) or not isinstance(p, int) or p < 1 or width < 1:
        raise ValueError("Invalid neural dimensions")
    if not math.isfinite(mean):
        raise ValueError("Nonfinite training mean")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return {
        "W1": torch.nn.Parameter(torch.randn(p, width, generator=generator,
                                              dtype=torch.float64) * math.sqrt(2 / p)),
        "b1": torch.nn.Parameter(torch.zeros(width, dtype=torch.float64)),
        "W2": torch.nn.Parameter(torch.randn(width, generator=generator,
                                              dtype=torch.float64) * 0.01),
        "b2": torch.nn.Parameter(torch.tensor(mean, dtype=torch.float64)),
    }


def forward(parameters, x):
    return torch.relu(x @ parameters["W1"] + parameters["b1"]) @ parameters["W2"] + parameters["b2"]


def objective(parameters, x, y, l2):
    if isinstance(l2, bool) or not math.isfinite(l2) or l2 < 0:
        raise ValueError("Invalid L2 penalty")
    mse = torch.mean((forward(parameters, x) - y) ** 2)
    penalty = l2 * (parameters["W1"].square().sum() + parameters["W2"].square().sum())
    return mse + penalty, mse, penalty


def numpy_gradients(parameters, x, y, l2):
    """Independent algebraic derivative for verifying autograd, not real fitting."""
    z = x @ parameters["W1"] + parameters["b1"]
    h = np.maximum(z, 0)
    residual = h @ parameters["W2"] + parameters["b2"] - y
    out = 2 * residual / len(y)
    hidden = (out[:, None] * parameters["W2"]) * (z > 0)
    return {"W1": x.T @ hidden + 2 * l2 * parameters["W1"],
            "b1": hidden.sum(axis=0),
            "W2": h.T @ out + 2 * l2 * parameters["W2"],
            "b2": np.asarray(out.sum())}


def snapshot(parameters):
    return {name: tensor.detach().cpu().numpy().tolist() for name, tensor in parameters.items()}


def predict_neural(state, x):
    x = inputs(x)
    params = {name: np.asarray(value, dtype=np.float64) for name, value in state.items()}
    p, width = params["W1"].shape
    if (x.shape[1] != p or params["b1"].shape != (width,)
            or params["W2"].shape != (width,) or params["b2"].shape != ()):
        raise ValueError("Neural state/input dimension mismatch")
    if not all(np.isfinite(value).all() for value in params.values()):
        raise ValueError("Nonfinite neural state")
    prediction = np.maximum(x @ params["W1"] + params["b1"], 0) @ params["W2"] + params["b2"]
    if not np.isfinite(prediction).all():
        raise ValueError("Nonfinite neural predictions")
    return prediction.tolist()


def fit_neural(x, y, config, seed):
    x, y = inputs(x, y)
    if (config["epochs"] < 1 or config["width"] != 4 or config["learning_rate"] <= 0
            or config["weight_decay"] != 0):
        raise ValueError("Unsupported neural training configuration")
    configure_cpu()
    tx, ty = torch.as_tensor(x), torch.as_tensor(y)
    parameters = initialize(x.shape[1], float(y.mean()), seed, config["width"])
    optimizer = torch.optim.Adam(list(parameters.values()), lr=config["learning_rate"],
                                 betas=tuple(config["betas"]), eps=config["epsilon"],
                                 weight_decay=0, foreach=False, fused=False, amsgrad=False)
    trace = []
    # Record gradients and loss at exactly the same parameter state. The final
    # gradient is diagnostic only: updates occur only at epochs 0..epochs-1.
    for epoch in range(config["epochs"] + 1):
        optimizer.zero_grad(set_to_none=True)
        loss, mse, penalty = objective(parameters, tx, ty, config["l2"])
        if not torch.isfinite(loss):
            raise ValueError(f"Nonfinite neural loss at seed {seed}, epoch {epoch}")
        loss.backward()
        if not all(torch.isfinite(value.grad).all() for value in parameters.values()):
            raise ValueError(f"Nonfinite neural gradients at seed {seed}, epoch {epoch}")
        norm = math.sqrt(sum(float(value.grad.square().sum()) for value in parameters.values()))
        trace.append({"epoch": epoch, "mse": float(mse.detach()),
                      "penalty": float(penalty.detach()), "objective": float(loss.detach()),
                      "gradient_norm": norm})
        if epoch < config["epochs"]:
            optimizer.step()
    state = snapshot(parameters)
    final = np.maximum(x @ np.asarray(state["W1"]) + np.asarray(state["b1"]), 0)
    return state, {"seed": seed, "parameter_count": 4 * x.shape[1] + 9,
                   "trace": trace, "training_activation_fraction": (final > 0).mean(axis=0).tolist(),
                   "inactive_training_neurons": int(np.sum(np.all(final == 0, axis=0)))}


def fit_trees(x, y, protocol):
    x, y = inputs(x, y)
    classes = {"tree": DecisionTreeRegressor, "forest": RandomForestRegressor,
               "boosting": GradientBoostingRegressor}
    fitted = {}
    for name, cls in classes.items():
        config = protocol[name]
        params = dict(config["params"])
        if name == "boosting":
            # sklearn 1.9 deprecates criterion as a no-op. Preserve the frozen
            # statistical choice, but do not pass the ignored deprecated kwarg.
            if params.pop("criterion") != "friedman_mse":
                raise ValueError("Unsupported frozen boosting criterion")
        fitted[name] = cls(**params, random_state=config["random_state"]).fit(x, y)
    return fitted


def tree_state(estimator):
    tree = estimator.tree_
    return {"children_left": tree.children_left.tolist(), "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(),
            "value": tree.value[:, 0, 0].tolist()}


def predict_tree(state, x):
    """Replay sklearn tree states as data; sklearn split comparisons use float32 X."""
    x = inputs(x).astype(np.float32)
    result = []
    for row in x:
        node = 0
        while state["children_left"][node] != -1:
            # sklearn compares float32 inputs against float64 thresholds. A
            # NumPy float32 scalar would instead round a Python threshold down
            # to float32 (NEP 50), changing branches at adjacent-input midpoints.
            value = float(row[state["feature"][node]])
            node = (state["children_left"][node] if value <= state["threshold"][node]
                    else state["children_right"][node])
        result.append(state["value"][node])
    return np.asarray(result)


def serialize_trees(fitted):
    return {"tree": {"trees": [tree_state(fitted["tree"])], "aggregation": "mean"},
            "forest": {"trees": [tree_state(t) for t in fitted["forest"].estimators_], "aggregation": "mean"},
            "boosting": {"trees": [tree_state(t) for t in fitted["boosting"].estimators_[:, 0]],
                         "aggregation": "sequential_sum", "initial_mean": float(fitted["boosting"].init_.constant_[0, 0]),
                         "learning_rate": fitted["boosting"].learning_rate}}


def predict_trees(state, x):
    if state["aggregation"] == "mean":
        result = np.mean([predict_tree(t, x) for t in state["trees"]], axis=0)
    else:
        result = np.full(len(x), state["initial_mean"], dtype=np.float64)
        for tree in state["trees"]:
            result += state["learning_rate"] * predict_tree(tree, x)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite tree predictions")
    return result.tolist()


def forecast(training_x, training_y, later_x, protocol):
    """Fit only from matured training data; the interface accepts no later labels."""
    x, y = inputs(training_x, training_y)
    later = inputs(later_x)
    if x.shape[1] != later.shape[1]:
        raise ValueError("Training/later input dimension mismatch")
    neural_states, diagnostics, seed_predictions = {}, {}, []
    values = {}
    for seed in protocol["seeds"]:
        state, trace = fit_neural(x, y, protocol["neural"], seed)
        name = f"neural_seed_{seed}"
        neural_states[name], diagnostics[name] = state, trace
        prediction = predict_neural(state, later)
        values[name] = prediction
        seed_predictions.append(prediction)
    values["neural_ensemble"] = np.mean(seed_predictions, axis=0).tolist()
    trees = fit_trees(x, y, protocol)
    tree_states = serialize_trees(trees)
    for name, estimator in trees.items():
        values[name] = predict_trees(tree_states[name], later)
        if not np.allclose(values[name], estimator.predict(later), rtol=1e-12, atol=1e-12):
            raise ValueError(f"Serialized tree prediction mismatch: {name}")
        diagnostics[name] = {"fit_params": estimator.get_params(),
                             "tree_count": len(tree_states[name]["trees"]),
                             "node_counts": [len(t["value"]) for t in tree_states[name]["trees"]]}
    if not all(np.isfinite(v).all() for v in values.values()):
        raise ValueError("Nonfinite nonlinear predictions")
    return values, {"neural": neural_states, "trees": tree_states}, diagnostics
