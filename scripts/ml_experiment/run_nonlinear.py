"""Prepare or explicitly fit the fixed nonlinear 13D comparison on Windows.

Inputs: frozen ml-nonlinear-v1, checkpoint-2 matrices and checkpoint-3 references.
Outputs: preparation receipt OR prefit snapshot, JSON states/forecasts, diagnostics,
event errors, metrics, HTML and hashes. Preparation never calls a model fit.
Identity: inherit matured-label folds, unchanged decimal two-year target and
event-weighted RMSE/MAE; NN ensemble is the mean of all five fixed seeds.
Tier: 2. Offline development evaluation, never an untouched investment test.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/run_nonlinear.py --prepare --output NEW_RUN
     (Use --fit instead only on the chosen training computer.)
"""

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import platform
import sys
from html import escape
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_baselines as baseline  # noqa: E402
from nonlinear_models import (  # noqa: E402
    configure_cpu,
    forecast,
    predict_neural,
    predict_trees,
)
from prepare_inputs import InputPreprocessor  # noqa: E402

PROTOCOL = ROOT / "research/protocol/ml-nonlinear-v1.json"
PROTOCOL_SHA256 = "6cd7dbb5587034e4b942d82013d79fa3a0b92ddec4c67d69420f7f4eba2398d9"
REFERENCE = ROOT / "research/runs/ml-baselines/20261015-v1"
REQUIRED = {"numpy": "2.5.3", "scipy": "1.18.1", "scikit-learn": "1.9.1", "torch": "2.14.0",
            "joblib": "1.6.0", "threadpoolctl": "3.7.0"}


def environment():
    versions = {name: importlib.metadata.version(name) for name in REQUIRED}
    if any(versions[name].split("+")[0] != wanted for name, wanted in REQUIRED.items()):
        raise ValueError(f"Model dependencies differ from requirements-ml.txt: {versions}")
    if sys.version_info[:2] not in ((3, 13), (3, 14)):
        raise ValueError("This comparison requires Python 3.13 or 3.14")
    return {"python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "versions": versions,
            "all_installed_packages": dict(sorted((d.metadata['Name'], d.version)
                                                  for d in importlib.metadata.distributions())),
            "device": "CPU", "torch_threads": 1, "torch_deterministic_algorithms": True}


def load_prepared():
    """Reconstruct preprocessing and validate membership without fitting a predictor."""
    if baseline.digest(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("Frozen nonlinear protocol hash mismatch; create a new protocol version")
    protocol = json.loads(PROTOCOL.read_bytes())
    _, loaded, sources = baseline.load_inputs()
    features, targets, metadata = (loaded[name] for name in
                                   ("features.jsonl", "targets.jsonl", "row-metadata.jsonl"))
    baseline.validate_rows(features, targets, metadata)
    if len(features) != 667:
        raise ValueError("The declared 667-event source panel changed")
    x_by_id = {row["row_id"]: row["features"] for row in features}
    y_by_id = {row["row_id"]: row[baseline.TARGET] for row in targets}
    folds = loaded["fold-inputs.json"]
    for year, train_count, later_count, columns in protocol["expected_fold_counts"]:
        fold = folds[str(year)]
        baseline.validate_fold(metadata, fold, year)
        train, later = ([x_by_id[row_id] for row_id in fold[key]]
                        for key in ("training_row_ids", "later_row_ids"))
        processor = InputPreprocessor(loaded["feature-dictionary.json"]["features"],
                                     loaded["protocol.json"]["log1p_columns"]).fit(train)
        if (processor.state != loaded["preprocessing-state.json"][str(year)]
                or processor.state["feature_names"] != fold["feature_names"]
                or processor.transform(train) != fold["training_X"]
                or processor.transform(later) != fold["later_X"]):
            raise ValueError("Reconstructed preprocessing differs from checkpoint 2")
        if (len(train), len(later), len(fold["feature_names"])) != (train_count, later_count, columns):
            raise ValueError("Frozen fold counts or dimensions changed")
        fold["training_y"] = [y_by_id[row_id] for row_id in fold["training_row_ids"]]
    reference_provenance = json.loads((REFERENCE / "provenance.json").read_bytes())
    refs_path = REFERENCE / "predictions.jsonl"
    expected = reference_provenance["outputs_sha256"][refs_path.name]
    if baseline.digest(refs_path) != expected:
        raise ValueError("Preserved baseline prediction hash mismatch")
    refs = [json.loads(line) for line in refs_path.read_bytes().splitlines()]
    expected_ids = [row_id for year, *_ in protocol["expected_fold_counts"]
                    for row_id in folds[str(year)]["later_row_ids"]]
    if [row["row_id"] for row in refs] != expected_ids or len(set(expected_ids)) != 302:
        raise ValueError("Reference forecasts differ from declared later rows or ordering")
    for relative in ["research/protocol/ml-nonlinear-v1.json", "requirements-ml.txt",
                     "scripts/ml_experiment/nonlinear_models.py", "scripts/ml_experiment/run_nonlinear.py",
                     "scripts/ml_experiment/run_baselines.py", "scripts/ml_experiment/prepare_inputs.py",
                     "research/runs/ml-baselines/20261015-v1/predictions.jsonl",
                     "research/runs/ml-baselines/20261015-v1/provenance.json"]:
        sources[relative] = baseline.digest(ROOT / relative)
    return protocol, folds, targets, refs, sources


def score(predictions, targets, models):
    by_id = {row["row_id"]: row[baseline.TARGET] for row in targets}

    def subset(rows, rank):
        y = [by_id[row["row_id"]] for row in rows]
        ref = [row["predictions"]["training_mean"] for row in rows]
        return {name: baseline.metrics(y, [row["predictions"][name] for row in rows], ref,
                                        include_rank=rank) for name in models}

    yearly = {str(year): subset([r for r in predictions if r["prediction_year"] == year], True)
              for year in sorted({r["prediction_year"] for r in predictions})}
    groups = {group: subset(rows, False) for group in baseline.GROUPS
              if (rows := [r for r in predictions if r["cohort"] == group])}
    pooled = subset(predictions, False)
    concentration = {}
    for name in models:
        errors = sorted(((r["predictions"][name] - by_id[r["row_id"]]) ** 2 for r in predictions), reverse=True)
        total = pooled[name]["sse"]
        concentration[name] = sum(errors[:5]) / total if total else None
    return {"pooled": pooled, "by_prediction_year": yearly, "by_cohort": groups,
            "largest_five_share_of_sse": concentration,
            "rank_pooling": "none; report Spearman only within each prediction year"}


def event_errors(predictions, targets, models):
    by_id = {row["row_id"]: row[baseline.TARGET] for row in targets}
    stream = io.StringIO(newline="")
    fields = ["row_id", "prediction_year", "cohort", "model", "prediction", "target", "error", "squared_error"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in predictions:
        actual = by_id[row["row_id"]]
        for name in models:
            prediction = row["predictions"][name]
            writer.writerow({"row_id": row["row_id"], "prediction_year": row["prediction_year"],
                             "cohort": row["cohort"], "model": name, "prediction": prediction,
                             "target": actual, "error": prediction - actual,
                             "squared_error": (prediction - actual) ** 2})
    return stream.getvalue().encode()


def build(*, fit=False, emit_to_disk=None):
    configure_cpu()
    env = environment()
    protocol, folds, targets, references, sources = load_prepared()
    artifacts = {}

    def emit(name, payload):
        artifacts[name] = payload
        if emit_to_disk is not None:
            emit_to_disk(name, payload)

    emit("prefit-manifest.json", baseline.encode({"status": "captured before any real-data predictor fit",
                                                  "inputs_sha256": sources, "environment": env,
                                                  "evaluation_status": "previously inspected development history",
                                                  "requested_mode": "fit" if fit else "prepare_only"}))
    emit("protocol.json", PROTOCOL.read_bytes())
    for name in ("nonlinear_models.py", "run_nonlinear.py", "run_baselines.py", "prepare_inputs.py"):
        emit(f"code/{name}", (Path(__file__).parent / name).read_bytes())
    if not fit:
        summary = {"status": "ready_for_windows_fit_not_run", "real_data_model_fits": 0,
                   "protocol": protocol["version"], "fold_counts": protocol["expected_fold_counts"],
                   "preprocessing_reconstructed_exactly": True, "reference_events": len(references),
                   "bloomberg_features_used": False, "new_scores_computed": False}
        emit("preparation.json", baseline.encode(summary))
    else:
        predictions, states, diagnostics = [], {}, {}
        ref_by_id = {r["row_id"]: r for r in references}
        for year, *_ in protocol["expected_fold_counts"]:
            print(f"Fitting fixed models for prediction year {year}...", flush=True)
            fold = folds[str(year)]
            values, state, trace = forecast(fold["training_X"], fold["training_y"], fold["later_X"], protocol)
            states[str(year)], diagnostics[str(year)] = state, trace
            diagnostics[str(year)]["feature_names"] = fold["feature_names"]
            train_forecasts = {name: predict_neural(s, fold["training_X"]) for name, s in state["neural"].items()}
            train_forecasts["neural_ensemble"] = np.mean(list(train_forecasts.values()), axis=0).tolist()
            train_forecasts.update({name: predict_trees(s, fold["training_X"]) for name, s in state["trees"].items()})
            mean = [float(np.mean(fold["training_y"]))] * len(fold["training_y"])
            diagnostics[str(year)]["training_metrics"] = {
                name: baseline.metrics(fold["training_y"], v, mean) for name, v in train_forecasts.items()}
            for index, row_id in enumerate(fold["later_row_ids"]):
                old = ref_by_id[row_id]
                if old["prediction_year"] != year:
                    raise ValueError("Reference forecast year does not align")
                predictions.append({**old, "predictions": {**old["predictions"],
                                                           **{name: v[index] for name, v in values.items()}}})
        emit("model-states.json", baseline.encode(states))
        emit("training-diagnostics.json", baseline.encode(diagnostics))
        emit("predictions.jsonl", b"".join(baseline.encode(r) for r in predictions))
        emit("prediction-manifest.json", baseline.encode({"status": "all predictions saved before evaluation",
            "events": len(predictions), "predictions_sha256": hashlib.sha256(artifacts["predictions.jsonl"]).hexdigest(),
            "later_targets_passed_to_forecast": False, "all_declared_seeds_reported": True}))
        evaluation = score(predictions, targets, protocol["model_reporting"])
        emit("evaluation.json", baseline.encode(evaluation))
        emit("scored-events.csv", event_errors(predictions, targets, protocol["model_reporting"]))
        summary = {"status": "fixed_nonlinear_development_comparison_complete", "events": len(predictions),
                   "pooled": evaluation["pooled"], "protocol": protocol["version"],
                   "tuned": False, "independent_final_test": False, "bloomberg_features_used": False,
                   "investment_portfolio_evaluated": False, "limits": protocol["limits"]}
        emit("summary.json", baseline.encode(summary))
        emit("index.html", report(evaluation, protocol).encode())
    emit("provenance.json", baseline.encode({"inputs_sha256": sources, "environment": env,
        "outputs_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()},
        "execution_order": list(artifacts), "real_data_fit_requested": fit}))
    return artifacts, summary


def report(evaluation, protocol):
    def rows(values, rank=False):
        output = []
        for name in protocol["model_reporting"]:
            value = values[name]
            rho = value.get("spearman")
            tail = f"<td>{rho:.3f}</td>" if rho is not None else "<td>Undefined</td>"
            output.append(f"<tr><td>{escape(name)}</td><td>{value['n']}</td>"
                          f"<td>{100*value['rmse']:.2f}</td><td>{100*value['mae']:.2f}</td>"
                          + (tail if rank else "") + "</tr>")
        return "".join(output)

    yearly = "".join(f"<h2>Prediction year {year}</h2><table><tr><th>Model</th><th>Events</th><th>RMSE pp</th><th>MAE pp</th><th>Spearman</th></tr>{rows(values, True)}</table>"
                     for year, values in evaluation["by_prediction_year"].items())
    limits = "".join(f"<li>{escape(value)}</li>" for value in protocol["limits"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D fixed nonlinear development comparison</title><style>body{{font:17px/1.6 system-ui,sans-serif;color:#203448;background:#f4f6f8}}main{{max-width:1000px;margin:auto;padding:24px;background:white}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;text-align:left;border-bottom:1px solid #ddd}}a{{color:#155c99}}</style></head><body><main>
<h1>Do nonlinear inputs improve post-13D return predictions?</h1><p>Fixed development comparison · protocol ml-nonlinear-v1</p>
<p>This run compares a four-ReLU-neuron network, a shallow tree, a random forest and gradient boosting with preserved references on the same 302 later events. The target is cumulative stock-minus-Russell ETF-proxy return over 504 sessions. Entries, labels and inputs are inherited unchanged. Lower prediction error is better; these numbers are not investment returns or established alpha.</p>
<h2>Every model, pooled event errors</h2><table><tr><th>Model</th><th>Events</th><th>RMSE pp</th><th>MAE pp</th></tr>{rows(evaluation['pooled'])}</table>{yearly}
<h2>How the methods learn</h2><p>The network learns weighted combinations and ReLU boundaries through loss derivatives and Adam updates. A tree learns successive threshold rules. A forest averages 200 varied shallow trees. Boosting adds 100 small corrections at learning rate 0.05. The neural ensemble averages all five declared seeds; individual runs are displayed, never selected on their later performance.</p>
<p>RMSE is the square root of the average squared forecast error, reported in percentage points; MAE is average absolute error. Spearman compares within-year orderings. Pooled error uses all event errors, not an average of yearly RMSE. Training errors, losses, gradients and neuron activity are saved in diagnostics; larger later than training errors are consistent with poor transfer, not a reason to select a different checkpoint after the fact.</p>
<h2>Limits and next checkpoint</h2><ul>{limits}</ul><p>Review loss curves and every year/seed, then discuss what transfers. A tuned extension, new features or a new loss needs a separately identified experiment. No immediate investment threshold or model-selection rule follows.</p>
<p><a href="protocol.json">Protocol</a> · <a href="prefit-manifest.json">Prefit sources/environment</a> · <a href="prediction-manifest.json">Prediction receipt</a> · <a href="predictions.jsonl">All forecasts</a> · <a href="evaluation.json">Full metrics and subgroups</a> · <a href="training-diagnostics.json">Training diagnostics</a> · <a href="model-states.json">JSON model states</a> · <a href="scored-events.csv">Every scored error</a> · <a href="provenance.json">Hashes</a></p></main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true", help="Validate without fitting any real-data model")
    modes.add_argument("--fit", action="store_true", help="Explicitly run actual comparison on the chosen training computer")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true", help="Replay an existing run in its recorded environment")
    args = parser.parse_args()
    if args.verify:
        receipt = json.loads((args.output / "prefit-manifest.json").read_bytes())
        if receipt["environment"] != environment():
            raise ValueError("Replay environment differs from the recorded original")
        artifacts, _ = build(fit=args.fit)
        for name, payload in artifacts.items():
            if (args.output / name).read_bytes() != payload:
                raise ValueError(f"Replay differs: {name}")
        print(f"Exact replay verified: {len(artifacts)} artifacts")
        return
    args.output.mkdir(parents=True, exist_ok=False)

    def write(name, payload):
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    try:
        _, summary = build(fit=args.fit, emit_to_disk=write)
    except Exception as error:
        write("failure.json", baseline.encode({"status": "refused; do not use incomplete run",
                                               "type": type(error).__name__, "message": str(error)}))
        raise
    print(json.dumps(summary, indent=2))
    print(f"Saved run: {args.output.resolve()}")


if __name__ == "__main__":
    main()
