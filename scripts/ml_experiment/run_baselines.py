"""Fit and evaluate the frozen first 13D prediction comparisons.

Inputs: ml-baselines-v1, preserved feature/target/metadata JSONL and checkpoint-2
fold matrices/states. Outputs: prefit receipt, saved predictions before scoring,
coefficients, event errors, fold/group diagnostics, lesson HTML and provenance.
Identity: ridge minimizes mean((y-b-X beta)^2)+lambda*sum(beta^2), with an
unpenalized intercept; RMSE=sqrt(sum(error^2)/n), MAE=sum(abs(error))/n.
Tier: 2. Offline development evidence, not an independent investment test.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/run_baselines.py --output NEW_RUN [--verify]
"""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import sys
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_inputs import InputPreprocessor, split_rows  # noqa: E402

PREVIEW = ROOT / "research/runs/ml-feature-preview/20261012-v1"
PREP = ROOT / "research/runs/ml-preprocessing/20261012-v1"
PROTOCOL = ROOT / "research/protocol/ml-baselines-v1.json"
TARGET = "target_russell_excess_504"
MODELS = ("training_mean", "zero_excess", "ridge")
GROUPS = ("focused", "other_event_driven", "new_other_hfr", "other_unresolved")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False) + "\n").encode()


def vector(values, name):
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {name}") from error
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError(f"Empty, nonfinite or wrong-dimensional {name}")
    return array


def matrix(values, name):
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {name}") from error
    if array.ndim != 2 or min(array.shape) == 0 or not np.isfinite(array).all():
        raise ValueError(f"Empty, nonfinite or wrong-dimensional {name}")
    return array


def fit_ridge(x, y, penalty):
    """Solve the mean-loss ridge objective; the intercept is not penalized."""
    x, y = matrix(x, "training inputs"), vector(y, "training targets")
    if len(x) != len(y):
        raise ValueError("Training input/target length mismatch")
    if isinstance(penalty, bool) or not math.isfinite(penalty) or penalty <= 0:
        raise ValueError("Ridge penalty must be finite and strictly positive")
    x_mean, y_mean = x.mean(axis=0), float(y.mean())
    centered_x, centered_y = x - x_mean, y - y_mean
    lhs = centered_x.T @ centered_x + len(y) * penalty * np.eye(x.shape[1])
    rhs = centered_x.T @ centered_y
    beta = np.linalg.solve(lhs, rhs)
    intercept = y_mean - float(x_mean @ beta)
    if not np.isfinite(beta).all() or not math.isfinite(intercept):
        raise ValueError("Nonfinite fitted ridge state")
    return {"intercept": intercept, "coefficients": beta.tolist(), "lambda": penalty,
            "equivalent_sum_loss_alpha": len(y) * penalty}


def predict_ridge(state, x):
    x = matrix(x, "prediction inputs")
    coefficients = vector(state["coefficients"], "coefficients")
    if x.shape[1] != len(coefficients) or not math.isfinite(state["intercept"]):
        raise ValueError("Prediction dimensions or intercept disagree")
    values = state["intercept"] + x @ coefficients
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite predictions")
    return values.tolist()


def forecast(training_x, training_y, later_x, penalty):
    """The fitting interface deliberately accepts no later outcomes."""
    training_x, later_x = matrix(training_x, "training inputs"), matrix(later_x, "later inputs")
    training_y = vector(training_y, "training targets")
    if len(training_x) != len(training_y) or training_x.shape[1] != later_x.shape[1]:
        raise ValueError("Forecast input/target dimension mismatch")
    state = fit_ridge(training_x, training_y, penalty)
    mean = float(training_y.mean())
    return {"training_mean": [mean] * len(later_x), "zero_excess": [0.0] * len(later_x),
            "ridge": predict_ridge(state, later_x)}, {"training_mean": mean, "ridge": state}


def average_ranks(values):
    values = vector(values, "rank inputs")
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for position in ordered[start:end]:
            ranks[position] = rank
        start = end
    return ranks


def spearman(y, predictions):
    y, predictions = vector(y, "rank targets"), vector(predictions, "rank predictions")
    if len(y) != len(predictions):
        raise ValueError("Rank length mismatch")
    if len(y) < 2 or np.ptp(y) == 0 or np.ptp(predictions) == 0:
        return None
    a, b = np.asarray(average_ranks(y)), np.asarray(average_ranks(predictions))
    a, b = a - a.mean(), b - b.mean()
    return max(-1.0, min(1.0, float((a @ b) / math.sqrt(float((a @ a) * (b @ b))))))


def metrics(y, predictions, baseline, *, include_rank=True):
    y, predictions, baseline = (vector(values, name) for values, name in
                                ((y, "targets"), (predictions, "predictions"), (baseline, "baseline")))
    if not len(y) == len(predictions) == len(baseline):
        raise ValueError("Scoring rows do not align")
    errors = [float(p - actual) for p, actual in zip(predictions, y, strict=True)]
    sse = math.fsum(error * error for error in errors)
    base_sse = math.fsum(float(p - actual) ** 2 for p, actual in zip(baseline, y, strict=True))
    result = {"n": len(y), "sse": sse, "mae": math.fsum(abs(error) for error in errors) / len(y),
              "rmse": math.sqrt(sse / len(y)),
              "mse_skill_vs_training_mean": 1 - sse / base_sse if base_sse > 0 else None}
    if include_rank:
        result["spearman"] = spearman(y, predictions)
    return result


def distribution(values):
    values = vector(values, "distribution inputs")
    return {"n": len(values), "mean": float(values.mean()), "median": float(np.median(values)),
            "min": float(values.min()), "max": float(values.max())}


def validate_rows(features, targets, metadata):
    ids = [row["row_id"] for row in features]
    if len(set(ids)) != len(ids) or any([row["row_id"] for row in rows] != ids for rows in (targets, metadata)):
        raise ValueError("Duplicate, missing or misordered source row IDs")
    for target, meta in zip(targets, metadata, strict=True):
        value = target.get(TARGET)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Missing or nonfinite target; no zero substitution")
        if target.get("unit") != "decimal cumulative return difference" or target["label_end"] != meta["label_end"]:
            raise ValueError("Target unit or label-end mismatch")
        for key in ("entry", "label_end", "industry_as_of", "market_cap_as_of"):
            date.fromisoformat(meta[key])
        if not (meta["accepted_et"][:10] < meta["entry"] <= meta["label_end"]
                and meta["industry_as_of"] < meta["accepted_et"][:10]
                and meta["market_cap_as_of"] < meta["accepted_et"][:10]):
            raise ValueError("Invalid event or dated-feature chronology")
        if meta["cohort_for_diagnostics_only"] not in GROUPS:
            raise ValueError("Unknown diagnostic cohort")


def validate_fold(metadata, fold, year):
    expected_train, expected_later = split_rows(metadata, year)
    if fold["training_row_ids"] != expected_train or fold["later_row_ids"] != expected_later:
        raise ValueError("Fold membership or row order violates matured-label rule")
    if set(expected_train) & set(expected_later):
        raise ValueError("A row occurs in training and later evaluation")
    if len(fold["training_X"]) != len(expected_train) or len(fold["later_X"]) != len(expected_later):
        raise ValueError("Fold matrices do not align with row IDs")


def load_inputs():
    sources = {}

    def load(path, expected=None, lines=False):
        payload = path.read_bytes()
        sha = hashlib.sha256(payload).hexdigest()
        if expected is not None and sha != expected:
            raise ValueError(f"Frozen source hash mismatch: {path.relative_to(ROOT)}")
        sources[str(path.relative_to(ROOT))] = sha
        return [json.loads(line) for line in payload.splitlines()] if lines else json.loads(payload)

    protocol = load(PROTOCOL)
    if (protocol["version"] != "ml-baselines-v1" or protocol["prediction_years"] != [2021, 2022, 2023]
            or [model["name"] for model in protocol["models"]] != list(MODELS)
            or protocol["models"][2]["lambda"] != 1.0):
        raise ValueError("Unsupported first-baseline contract")
    preview_provenance = load(PREVIEW / "provenance.json")
    prep_provenance = load(PREP / "provenance.json")
    loaded = {}
    for name in ("features.jsonl", "targets.jsonl", "row-metadata.jsonl", "feature-dictionary.json"):
        loaded[name] = load(PREVIEW / name, preview_provenance["outputs_sha256"][name], lines=name.endswith("jsonl"))
    for name in ("fold-inputs.json", "preprocessing-state.json", "protocol.json", "summary.json"):
        loaded[name] = load(PREP / name, prep_provenance["outputs_sha256"][name])
    for name in ("scripts/ml_experiment/prepare_inputs.py", "research/protocol/ml-preprocessing-v1.json"):
        sha = digest(ROOT / name)
        if sha != prep_provenance["inputs_sha256"][name]:
            raise ValueError(f"Preprocessing implementation/contract changed: {name}")
        sources[name] = sha
    sources[str(Path(__file__).relative_to(ROOT))] = digest(Path(__file__))
    return protocol, loaded, sources


def fold_diagnostics(metadata, train_ids, later_ids, training_y, later_y, state):
    by_id = {row["row_id"]: row for row in metadata}
    training, later = ([by_id[row_id] for row_id in ids] for ids in (train_ids, later_ids))
    train_issuers = {row["issuer"] for row in training}
    later_issuers = {row["issuer"] for row in later}
    train_reporters = {cik for row in training for cik in row["header_reporter_ciks"]}
    later_reporters = {cik for row in later for cik in row["header_reporter_ciks"]}
    return {"training_events": len(training), "later_events": len(later),
            "training_target": distribution(training_y), "later_target": distribution(later_y),
            "latest_training_label_end": max(row["label_end"] for row in training),
            "shared_issuer_count": len(train_issuers & later_issuers),
            "later_events_with_training_issuer": sum(row["issuer"] in train_issuers for row in later),
            "shared_header_reporter_cik_count": len(train_reporters & later_reporters),
            "later_events_with_training_reporter": sum(bool(set(row["header_reporter_ciks"]) & train_reporters) for row in later),
            "input_columns": len(state["feature_names"]),
            "training_row_ids": train_ids, "later_row_ids": later_ids}


def score_predictions(predictions, targets):
    by_id = {row["row_id"]: row[TARGET] for row in targets}

    def score(rows, include_rank):
        y = [by_id[row["row_id"]] for row in rows]
        baseline = [row["predictions"]["training_mean"] for row in rows]
        return {model: metrics(y, [row["predictions"][model] for row in rows], baseline,
                               include_rank=include_rank) for model in MODELS}

    folds = {str(year): score([row for row in predictions if row["prediction_year"] == year], True)
             for year in sorted({row["prediction_year"] for row in predictions})}
    cohorts = {}
    for group in GROUPS:
        subset = [row for row in predictions if row["cohort"] == group]
        cohorts[group] = score(subset, False) if subset else {"n": 0, "status": "no_scored_events"}
    pooled = score(predictions, False)
    concentration = {}
    for model in MODELS:
        largest = sorted(({"row_id": row["row_id"], "prediction_year": row["prediction_year"],
                           "squared_error": (row["predictions"][model] - by_id[row["row_id"]]) ** 2}
                          for row in predictions), key=lambda row: (-row["squared_error"], row["row_id"]))
        total = pooled[model]["sse"]
        concentration[model] = {"largest_five_errors": largest[:5],
                                "largest_five_share_of_sse": math.fsum(row["squared_error"] for row in largest[:5]) / total if total else None}
    return {"pooled": pooled, "by_prediction_year": folds, "by_cohort": cohorts,
            "error_concentration": concentration, "rank_pooling": "none: ranks reported only within prediction years"}


def scored_csv(predictions, targets):
    by_id = {row["row_id"]: row[TARGET] for row in targets}
    stream = io.StringIO(newline="")
    fields = ["row_id", "prediction_year", "issuer", "entry", "label_end", "cohort", "model", "prediction", "target", "error", "squared_error"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in predictions:
        for model in MODELS:
            actual, prediction = by_id[row["row_id"]], row["predictions"][model]
            writer.writerow({**{key: row[key] for key in fields[:6]}, "model": model,
                             "prediction": prediction, "target": actual, "error": prediction - actual,
                             "squared_error": (prediction - actual) ** 2})
    return stream.getvalue().encode()


def build(emit_to_disk=None):
    """Emit a prefit snapshot, then predictions, then evaluation artifacts."""
    protocol, loaded, sources = load_inputs()
    artifacts = {}

    def emit(name, payload):
        artifacts[name] = payload
        if emit_to_disk is not None:
            emit_to_disk(name, payload)

    env = {"python": platform.python_version(), "numpy": np.__version__, "system": platform.system(),
           "machine": platform.machine(), "threads": {name: os.environ.get(name) for name in
           ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
    emit("prefit-manifest.json", encode({"status": "captured before model fitting", "protocol": protocol["version"],
                                         "inputs_sha256": sources, "environment": env,
                                         "prior_numerical_access": "All labels were inspected in prior development research; this is not prospective registration"}))
    emit("protocol.json", PROTOCOL.read_bytes())
    for name in ("run_baselines.py", "prepare_inputs.py"):
        emit(f"code/{name}", (Path(__file__).parent / name).read_bytes())
    features, targets, metadata = (loaded[name] for name in ("features.jsonl", "targets.jsonl", "row-metadata.jsonl"))
    validate_rows(features, targets, metadata)
    if len(features) != 667:
        raise ValueError("Current covered panel differs from the declared 667 events")
    x_by_id = {row["row_id"]: row["features"] for row in features}
    y_by_id = {row["row_id"]: row[TARGET] for row in targets}
    meta_by_id = {row["row_id"]: row for row in metadata}
    states, training_scores, prepared_folds = {}, {}, {}
    predictions = []
    expected_counts = {year: (train, later, columns) for year, train, later, columns in protocol["expected_fold_counts"]}
    for year in protocol["prediction_years"]:
        fold = loaded["fold-inputs.json"][str(year)]
        validate_fold(metadata, fold, year)
        train_ids, later_ids = fold["training_row_ids"], fold["later_row_ids"]
        train_rows, later_rows = ([x_by_id[row_id] for row_id in ids] for ids in (train_ids, later_ids))
        processor = InputPreprocessor(loaded["feature-dictionary.json"]["features"], loaded["protocol.json"]["log1p_columns"]).fit(train_rows)
        if processor.state != loaded["preprocessing-state.json"][str(year)]:
            raise ValueError("Reconstructed preprocessing state disagrees with checkpoint 2")
        if fold["feature_names"] != processor.state["feature_names"]:
            raise ValueError("Stored fold column names disagree with the reconstructed state")
        if processor.transform(train_rows) != fold["training_X"] or processor.transform(later_rows) != fold["later_X"]:
            raise ValueError("Reconstructed preprocessing matrices disagree with checkpoint 2")
        if (len(train_ids), len(later_ids), len(processor.state["feature_names"])) != expected_counts[year]:
            raise ValueError("Declared fold counts or input dimensions changed")
        training_y = [y_by_id[row_id] for row_id in train_ids]
        values, fitted = forecast(fold["training_X"], training_y, fold["later_X"], protocol["models"][2]["lambda"])
        fitted["feature_names"] = processor.state["feature_names"]
        states[str(year)] = fitted
        train_predictions = {"training_mean": [fitted["training_mean"]] * len(train_ids), "zero_excess": [0.0] * len(train_ids),
                             "ridge": predict_ridge(fitted["ridge"], fold["training_X"])}
        training_scores[str(year)] = {model: metrics(training_y, train_predictions[model], train_predictions["training_mean"])
                                      for model in MODELS}
        prepared_folds[str(year)] = {"fold": fold, "preprocessing": processor.state}
        for index, row_id in enumerate(later_ids):
            meta = meta_by_id[row_id]
            predictions.append({"row_id": row_id, "prediction_year": year, "issuer": meta["issuer"],
                                "entry": meta["entry"], "label_end": meta["label_end"], "cohort": meta["cohort_for_diagnostics_only"],
                                "predictions": {model: values[model][index] for model in MODELS}})
    if len(predictions) != len({row["row_id"] for row in predictions}) or len(predictions) != 302:
        raise ValueError("Later events duplicate across folds or differ from the declared count")
    emit("model-states.json", encode(states))
    emit("predictions.jsonl", b"".join(encode(row) for row in predictions))
    emit("prediction-manifest.json", encode({"status": "all forecasts saved before evaluation scoring", "events": len(predictions),
                                             "predictions_sha256": hashlib.sha256(artifacts["predictions.jsonl"]).hexdigest(),
                                             "model_states_sha256": hashlib.sha256(artifacts["model-states.json"]).hexdigest(),
                                             "evaluation_labels_passed_to_forecast": False}))
    evaluation = score_predictions(predictions, targets)
    evaluation["training_diagnostics"] = training_scores
    diagnostics = {}
    for year, prepared in prepared_folds.items():
        fold = prepared["fold"]
        diagnostics[year] = fold_diagnostics(metadata, fold["training_row_ids"], fold["later_row_ids"],
                                             [y_by_id[row_id] for row_id in fold["training_row_ids"]],
                                             [y_by_id[row_id] for row_id in fold["later_row_ids"]], prepared["preprocessing"])
        prep_summary = next(row for row in loaded["summary.json"]["folds"] if row["prediction_year"] == int(year))
        diagnostics[year]["unseen_later_industry_events"] = prep_summary["unseen_later_industry_events"]
    summary = {"status": "checkpoint_3_complete_first_fixed_prediction_comparisons", "protocol": protocol["version"],
               "candidate_panel_events": 667, "evaluated_events": len(predictions), "prediction_years": protocol["prediction_years"],
               "models": list(MODELS), "ridge_lambda": 1.0, "pooled": evaluation["pooled"],
               "by_prediction_year": evaluation["by_prediction_year"],
               "evaluated_cohort_counts": dict(Counter(row["cohort"] for row in predictions)),
               "preprocessing_reconstructed_exactly": True, "predictive_model_fitted": True,
               "neural_network_fitted": False, "llm_extraction_run": False, "hyperparameters_tuned": False,
               "independent_final_test": False, "investment_portfolio_evaluated": False,
               "interpretation": interpretation(evaluation), "limits": protocol["limits"]}
    emit("evaluation.json", encode(evaluation))
    emit("fold-diagnostics.json", encode(diagnostics))
    emit("scored-events.csv", scored_csv(predictions, targets))
    emit("summary.json", encode(summary))
    emit("index.html", report(summary, evaluation, diagnostics).encode())
    emit("provenance.json", encode({"inputs_sha256": sources, "environment": env,
                                    "outputs_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()},
                                    "execution_order": "prefit snapshot -> fit from matured training labels -> saved forecasts -> evaluation scores",
                                    "implementation": "NumPy float64 centered ridge linear solve, no model library or randomized training",
                                    "replay": "Exact within the recorded environment; cross-environment numerical tolerance 1e-10"}))
    return artifacts, summary


def interpretation(evaluation):
    pooled = evaluation["pooled"]
    wins = sum(values["ridge"]["rmse"] < values["training_mean"]["rmse"] for values in evaluation["by_prediction_year"].values())
    if pooled["ridge"]["rmse"] < pooled["training_mean"]["rmse"]:
        statement = "The fixed ridge model has lower pooled RMSE than the training-mean reference"
    else:
        statement = "The fixed ridge model does not improve pooled RMSE over the training-mean reference"
    return f"{statement}; it has lower RMSE in {wins} of 3 prediction years. This is development evidence, not established alpha or a tuned-model conclusion."


def report(summary, evaluation, diagnostics):
    labels = {"training_mean": "Earlier training mean", "zero_excess": "Zero excess reference", "ridge": "Fixed ridge regression"}

    def optional(value):
        return "Not defined" if value is None else f"{value:.3f}"

    def metric_rows(values):
        return "".join(f"<tr><td>{labels[model]}</td><td>{row['n']}</td><td>{row['rmse'] * 100:.2f}</td><td>{row['mae'] * 100:.2f}</td><td>{optional(row['mse_skill_vs_training_mean'])}</td></tr>"
                       for model in MODELS if (row := values[model]))

    fold_rows = "".join(f"<tr><td>{year}</td><td>{diagnostics[year]['training_events']}</td><td>{values['ridge']['n']}</td><td>{values['training_mean']['rmse'] * 100:.2f}</td><td>{values['ridge']['rmse'] * 100:.2f}</td><td>{optional(values['ridge']['spearman'])}</td></tr>"
                        for year, values in evaluation["by_prediction_year"].items())
    cohort_rows = "".join(f"<tr><td>{escape(group.replace('_', ' '))}</td><td>{values['ridge']['n']}</td><td>{values['training_mean']['rmse'] * 100:.2f}</td><td>{values['ridge']['rmse'] * 100:.2f}</td></tr>"
                          for group, values in evaluation["by_cohort"].items() if "ridge" in values)
    diagnostic_rows = "".join(f"<tr><td>{year}</td><td>{row['latest_training_label_end']}</td><td>{row['input_columns']}</td><td>{row['shared_issuer_count']}</td><td>{row['later_events_with_training_reporter']}</td><td>{row['unseen_later_industry_events']}</td></tr>"
                              for year, row in diagnostics.items())
    concentration = evaluation["error_concentration"]["ridge"]["largest_five_share_of_sse"]
    training_rows = "".join(f"<tr><td>{year}</td><td>{values['training_mean']['rmse'] * 100:.2f}</td><td>{values['ridge']['rmse'] * 100:.2f}</td><td>{evaluation['by_prediction_year'][year]['ridge']['rmse'] * 100:.2f}</td></tr>"
                            for year, values in evaluation["training_diagnostics"].items())
    limits = "".join(f"<li>{escape(text)}</li>" for text in summary["limits"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D checkpoint 3: first prediction comparisons</title><style>
body{{font:17px/1.65 system-ui,sans-serif;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1040px;margin:32px auto;padding:28px;background:white}}h1{{font-size:31px;line-height:1.25}}h2{{font-size:23px;margin-top:32px}}a{{color:#155c99}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:11px;text-align:left;border-bottom:1px solid #dce3e9;vertical-align:top}}th{{background:#edf3f7}}.scroll{{overflow:auto}}.takeaway{{background:#edf3f7;border-left:4px solid #185f91;padding:16px}}.example{{background:#faf5eb;padding:16px}}code{{overflow-wrap:anywhere}}details{{margin:15px 0}}li{{margin:8px 0}}</style></head><body><main>
<h1>Checkpoint 3: do filing inputs improve predictions?</h1><p>15 October 2026 | First fixed baseline models fitted | Chronological development evaluation</p>
<p class="takeaway"><strong>{escape(summary['interpretation'])}</strong> We now have saved forecasts for {summary['evaluated_events']} later events across 2021-2023. The neural network and LLM additions have not been run.</p>
<h2>What changed and why it matters</h2><p>Checkpoint 2 prepared numbers a model could accept. Here we first attach the known historical answers and learn a prediction rule. The target is the stock's cumulative total return minus its assigned Russell ETF-proxy return over 504 trading sessions. If the stock returns 30% and its benchmark 20%, the target is +10 percentage points (0.10 in the saved data). It is not a probability, annualized alpha or an invest/not-invest label.</p>
<p>The first reference gives every later event the average outcome from completed earlier examples. Zero excess is a second reference. Ridge regression lets the inputs change each prediction, while limiting the size of learned weights. The same events and target are used for every comparison.</p>
<h2>Lesson 1: what training and loss mean</h2><p><strong>Training</strong> chooses the model's weights using earlier examples with known answers. A <strong>loss</strong> measures the mistakes made by those predictions. We use mean squared error: subtract the true target from each prediction, square that difference, and average over training events. Squaring makes large misses count more strongly.</p>
<div class="example"><strong>Small example:</strong> two historical targets are -10 and +10 percentage points, with a prepared feature x equal to -1 and +1. Predicting zero for both gives errors +10 and -10 points, so RMSE and MAE both equal 10 points. Ordinary linear fitting could assign a weight of 10 points and fit these two examples perfectly. That does not show it will predict a new filing well.</div>
<h2>Lesson 2: what ridge regression adds</h2><p>A linear prediction is an intercept plus a weighted sum of inputs: <code>prediction = b + w1*x1 + ... + wp*xp</code>. A weight says how the model's prediction changes with an input, conditional on the others. It is an association learned from these data, not evidence that the feature causes returns.</p>
<p><strong>Regularization</strong> makes fitting large weights costly. Ridge chooses weights to minimize <code>mean squared training error + lambda * sum(weights squared)</code>. We fix lambda at 1 before this fit, without searching for a good-looking historical result. The intercept is unpenalized. This is a first reference, not an optimized model.</p>
<div class="example">For the same two examples, use decimal returns -0.10 and +0.10 and lambda=1. The fitted weight is 0.05, giving predictions -5 and +5 points. RMSE is 5 points; the error loss is 0.0025 and the weight penalty is 0.0025. A perfect-fit weight of 0.10 would have zero training error but a larger total objective of 0.01. Ridge chooses the smaller total, 0.005. This illustrates shrinkage; it does not establish the best penalty for our data.</div>
<h2>The actual experiment</h2><p>Retain all 667 covered candidate rows and the inherited initial-event schedule. HFR labels and identifiers are diagnostic metadata, not inputs. Every January model uses only entries whose entire return windows ended before January 1. Preprocessing states and matrices are reconstructed exactly from checkpoint 2; nothing is re-fitted on later events. There is no random split, penalty tuning, early stopping or outcome-driven feature removal.</p>
<p>The input columns include scaled numerical features, missingness flags and binary industry categories. Binary columns retain their checkpoint-2 scales. Our penalty uses <em>mean</em> squared error; the equivalent penalty in a sum-of-squares Ridge implementation is <code>alpha = training n * lambda</code>, not simply lambda.</p>
<h2>Prediction errors on later events</h2><p>All errors below are <strong>percentage points of the two-year benchmark-relative return</strong>. Lower RMSE or MAE is better. MSE skill is 1 minus model squared error divided by the training-mean reference's squared error; zero matches that reference, positive improves it, negative worsens it. It is not conventional R-squared.</p>
<div class="scroll"><table><thead><tr><th>Method</th><th>Later n</th><th>RMSE (pp)</th><th>MAE (pp)</th><th>MSE skill vs earlier mean</th></tr></thead><tbody>{metric_rows(evaluation['pooled'])}</tbody></table></div>
<p>Pooling weights events equally and computes RMSE from all squared errors; it does not average the three yearly RMSE values. These 302 entries are distinct across prediction years, but their two-year return windows overlap.</p>
<div class="scroll"><table><thead><tr><th>Prediction year</th><th>Matured training n</th><th>Later n</th><th>Mean RMSE (pp)</th><th>Ridge RMSE (pp)</th><th>Ridge Spearman</th></tr></thead><tbody>{fold_rows}</tbody></table></div>
<p><strong>Ranking</strong> asks whether larger predictions tend to accompany larger later returns. Spearman compares ranks, using average ranks for ties; +1 is perfect ordering, -1 reversed ordering. A constant prediction cannot rank events, so the two constant references have no defined within-year rank correlation. We do not pool ranks across years: different yearly reference levels could create a misleading pooled ordering.</p>
<h2>Training fit is different from later performance</h2><div class="scroll"><table><thead><tr><th>Year</th><th>Training mean RMSE (pp)</th><th>Training ridge RMSE (pp)</th><th>Later ridge RMSE (pp)</th></tr></thead><tbody>{training_rows}</tbody></table></div>
<p>Training error tells us how well the model fits examples it learned from. Later-year error tells us how the fixed rule behaves outside those training rows. Smaller training error alone is not a reason to prefer a method. All this history was already inspected in prior research; later-year evaluation here is development evidence, not a newly untouched holdout.</p>
<h2>Coverage and repeated identities</h2><div class="scroll"><table><thead><tr><th>Year</th><th>Last training label end</th><th>Input columns</th><th>Shared issuers</th><th>Later events sharing a training reporter CIK</th><th>Unseen later industries</th></tr></thead><tbody>{diagnostic_rows}</tbody></table></div>
<p>Reporter identifiers are not validated economic managers. Repeated issuers/reporters and overlapping market periods create dependence; 302 events do not supply 302 independent experiments. We do not attach IID significance tests or confidence intervals.</p>
<div class="scroll"><table><thead><tr><th>Existing diagnostic investor group</th><th>Later n</th><th>Mean RMSE (pp)</th><th>Ridge RMSE (pp)</th></tr></thead><tbody>{cohort_rows}</tbody></table></div>
<p>These are descriptive coverage checks, especially for small groups. They do not choose the investor universe. The five largest ridge prediction errors account for {concentration:.1%} of its pooled squared error; all observations remain included. Full error records are downloadable below.</p>
<h2>What was verified</h2><p>Frozen input hashes, unique aligned IDs and labels, dated feature checks, strictly matured training windows, exact checkpoint-2 reconstruction and identical comparison samples. Hand-calculated tests pin the ridge solution, unpenalized intercept, error metrics and tied ranks; an augmented least-squares path independently checks the ridge solver. Refusal and temporal-boundary tests guard invalid inputs and future-label use. Saved predictions precede evaluation scoring. The run supports exact offline replay in its recorded environment.</p>
<h2>Limits and next checkpoint</h2><ul>{limits}</ul><p><strong>Checkpoint 4:</strong> explain hidden layers, activations, learning and regularization, then define a small neural-network experiment. Use these saved baselines, target and evaluation rows as comparisons. Do not change this run's penalty or sample after viewing its results. A tuned extension needs a new protocol and valid matured inner folds.</p>
<h2>Catch up before the neural network</h2><details><summary>Why not train on all 667 rows?</summary><p>For a prediction at January 2023, a two-year outcome ending in 2025 was unavailable. Only 365 events had both entered and completed their outcomes before that cutoff. The 86 later 2023 entries are evaluated after their outcomes eventually become known.</p></details><details><summary>Why do we need a constant prediction?</summary><p>It tests whether the inputs add anything beyond a simple estimate of the overall return level. If the feature-based model cannot improve that reference, a more complicated fitted model is not yet justified by this comparison.</p></details><details><summary>Does an accurate return prediction tell us how much to invest?</summary><p>No. Sizing also needs risk, costs, capital and portfolio constraints. This checkpoint measures prediction. It does not implement a funded investment strategy.</p></details>
<h2>Evidence and replay</h2><p><a href="protocol.json">Frozen experiment</a> · <a href="prefit-manifest.json">Prefit source/environment snapshot</a> · <a href="prediction-manifest.json">Prediction receipt</a> · <a href="predictions.jsonl">Saved forecasts</a> · <a href="model-states.json">Weights and intercepts</a> · <a href="scored-events.csv">Every scored event/model</a> · <a href="evaluation.json">All metrics</a> · <a href="fold-diagnostics.json">Fold membership and diagnostics</a> · <a href="provenance.json">Hashes</a></p>
<p><a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p><p>Method references: <a href="https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification">ridge formulation</a>; <a href="https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics">regression errors</a>; <a href="https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html">NumPy linear solver</a>. Local calculations implement the stated mean-loss convention explicitly. AI-assisted code and explanation; no LLM extraction or neural network in this run.</p></main></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        artifacts, summary = build()
        for name, payload in artifacts.items():
            if (args.output / name).read_bytes() != payload:
                raise ValueError(f"Baseline replay mismatch: {name}")
        print(f"Exact offline replay verified for all {len(artifacts)} baseline artifacts.")
    else:
        args.output.mkdir(parents=True, exist_ok=False)

        def write(name, payload):
            path = args.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)

        _, summary = build(write)
        print(json.dumps({key: summary[key] for key in ("status", "evaluated_events", "pooled", "interpretation")}, indent=2))


if __name__ == "__main__":
    main()
