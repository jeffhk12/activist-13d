"""Independently verify saved baseline predictions, target arithmetic and links.

Inputs: a baseline run, frozen feature/target/metadata, preprocessing and original
outcomes. Outputs: verification.json as a post-fit QA companion, never changes
the 13 frozen calculation artifacts. Identity: y=stock return-benchmark return;
prediction=b+sum(beta*x); SSE=sum((p-y)^2); ridge gradient=0 at fitted weights.
Tier: 1. Rechecks estimators pinned by tests/test_ml_baselines.py with scalar
arithmetic and exported CSV parity, without importing the model implementation.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
    scripts/ml_experiment/verify_baselines.py --run RUN
"""

import argparse
import csv
import hashlib
import json
import math
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "research/runs/ml-feature-preview/20261012-v1"
PREP = ROOT / "research/runs/ml-preprocessing/20261012-v1"
ANALYSIS = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-analysis-v1"
MODELS = ("training_mean", "zero_excess", "ridge")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def close(actual, expected):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError(f"Numerical parity failed: {actual} != {expected}")


class LocalLinks(HTMLParser):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.checked = 0

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href and not href.startswith(("https:", "http:", "#")):
            if not (self.parent / href).resolve().exists():
                raise ValueError(f"Broken local link: {href}")
            self.checked += 1


def verify(run):
    provenance = load(run / "provenance.json")
    for relative, sha in provenance["inputs_sha256"].items():
        if digest(ROOT / relative) != sha:
            raise ValueError(f"Changed calculation input: {relative}")
    for name, sha in provenance["outputs_sha256"].items():
        if digest(run / name) != sha:
            raise ValueError(f"Changed calculation artifact: {name}")
    targets = {row["row_id"]: row for row in lines(PREVIEW / "targets.jsonl")}
    meta = {row["row_id"]: row for row in lines(PREVIEW / "row-metadata.jsonl")}
    source_provenance = load(ANALYSIS / "provenance.json")
    if digest(ANALYSIS / "outcomes.json") != source_provenance["outputs"]["outcomes.json"]:
        raise ValueError("Original frozen outcomes hash mismatch")
    events = {row["input_key"]: row for row in load(ANALYSIS / "outcomes.json")["first_observed"]["504"]["russell"]}
    for row_id, target in targets.items():
        event = events[row_id]
        if event["status"] != "calculated_common_sample" or event["issuer"] != meta[row_id]["issuer"]:
            raise ValueError("Target-to-original-event join mismatch")
        close(target["target_russell_excess_504"], event["excess"])
        close(event["excess"], event["stock_return"] - event["benchmark_return"])
    predictions = lines(run / "predictions.jsonl")
    if not predictions or len(predictions) != len({row["row_id"] for row in predictions}):
        raise ValueError("Empty or duplicate scored event IDs")
    fold_inputs = load(PREP / "fold-inputs.json")
    states = load(run / "model-states.json")
    first_order_errors = {}
    for year, fold in fold_inputs.items():
        ids = fold["training_row_ids"]
        cutoff = f"{year}-01-01"
        if any(not meta[row_id]["label_end"] < cutoff for row_id in ids):
            raise ValueError("Unmatured label entered training")
        y = [targets[row_id]["target_russell_excess_504"] for row_id in ids]
        state = states[year]["ridge"]
        close(states[year]["training_mean"], math.fsum(y) / len(y))
        if states[year]["feature_names"] != fold["feature_names"]:
            raise ValueError("Saved weights/column names disagree")
        by_id = {row["row_id"]: row for row in predictions if str(row["prediction_year"]) == year}
        if list(by_id) != fold["later_row_ids"]:
            raise ValueError("Saved forecasts and later-row membership disagree")
        for row_id, x in zip(fold["later_row_ids"], fold["later_X"], strict=True):
            close(by_id[row_id]["predictions"]["ridge"], state["intercept"] + math.fsum(w * v for w, v in zip(state["coefficients"], x, strict=True)))
            close(by_id[row_id]["predictions"]["training_mean"], states[year]["training_mean"])
            close(by_id[row_id]["predictions"]["zero_excess"], 0)
        errors = [state["intercept"] + math.fsum(w * v for w, v in zip(state["coefficients"], x, strict=True)) - actual
                  for x, actual in zip(fold["training_X"], y, strict=True)]
        gradient = [2 * math.fsum(x[column] * error for x, error in zip(fold["training_X"], errors, strict=True)) / len(y) + 2 * state["lambda"] * weight
                    for column, weight in enumerate(state["coefficients"])]
        maximum = max(abs(2 * math.fsum(errors) / len(y)), *(abs(value) for value in gradient))
        if maximum > 1e-10:
            raise ValueError("Saved ridge state violates its declared mean-loss objective")
        first_order_errors[year] = maximum
    evaluation = load(run / "evaluation.json")
    with (run / "scored-events.csv").open(newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    csv_by_key = {(row["row_id"], row["model"]): row for row in csv_rows}
    if len(csv_rows) != len(csv_by_key) or len(csv_rows) != 3 * len(predictions):
        raise ValueError("CSV missing/duplicated event-model records")
    for model in MODELS:
        errors = []
        for prediction in predictions:
            row_id = prediction["row_id"]
            exported = csv_by_key[(row_id, model)]
            actual, predicted = targets[row_id]["target_russell_excess_504"], prediction["predictions"][model]
            close(float(exported["target"]), actual)
            close(float(exported["prediction"]), predicted)
            close(float(exported["error"]), predicted - actual)
            close(float(exported["squared_error"]), (predicted - actual) ** 2)
            errors.append(predicted - actual)
        result = evaluation["pooled"][model]
        close(result["sse"], math.fsum(error**2 for error in errors))
        close(result["rmse"], math.sqrt(math.fsum(error**2 for error in errors) / len(errors)))
        close(result["mae"], math.fsum(abs(error) for error in errors) / len(errors))
    links = LocalLinks(run)
    links.feed((run / "index.html").read_text())
    checkpoint_path = ROOT / "research/docs/ml-checkpoints.html"
    checkpoint_html = checkpoint_path.read_text()
    checkpoint_links = LocalLinks(checkpoint_path.parent)
    checkpoint_links.feed(checkpoint_html)
    labels = {"training_mean": "Earlier training mean", "zero_excess": "Zero benchmark-relative return", "ridge": "Fixed ridge regression"}
    for model, label in labels.items():
        result = evaluation["pooled"][model]
        expected = f"<td>{label}</td><td>{result['n']}</td><td>{result['rmse'] * 100:.2f}</td><td>{result['mae'] * 100:.2f}</td>"
        if expected not in checkpoint_html:
            raise ValueError("Checkpoint table disagrees with saved prediction metrics")
    home_links = LocalLinks(ROOT)
    home_links.feed((ROOT / "START-HERE.html").read_text().split("</section>", 1)[0])
    largest = max(targets.values(), key=lambda row: row["target_russell_excess_504"])
    return {"status": "passed", "calculation_artifacts_verified": len(provenance["outputs_sha256"]),
            "original_target_subtractions_checked": len(targets), "scored_events": len(predictions),
            "csv_event_model_rows_checked": len(csv_rows), "local_report_links_checked": links.checked,
            "checkpoint_links_checked": checkpoint_links.checked, "current_home_links_checked": home_links.checked,
            "checkpoint_table_matches_saved_metrics": True,
            "prediction_parity": "scalar weighted sums versus saved NumPy forecasts, rtol=atol=1e-10",
            "maximum_ridge_first_order_error_by_year": first_order_errors,
            "largest_frozen_target_checked": {"row_id": largest["row_id"], "target": largest["target_russell_excess_504"],
                                              "meaning": "Reconciles to frozen stock minus benchmark return; not a new raw-price audit"},
            "verification_script_sha256": digest(Path(__file__)),
            "source_outcomes_sha256": digest(ANALYSIS / "outcomes.json"),
            "frozen_calculations_changed": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.run)
    (args.run / "verification.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
