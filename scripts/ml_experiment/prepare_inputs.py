"""Prepare train-only numerical inputs and a learning checkpoint for 13D ML.

Inputs: immutable feature preview, metadata, evidence and preprocessing contract.
Outputs: fold matrices, fitted preprocessing states, gap diagnostics, lesson HTML.
Identity: z=(log1p(x) where specified, then training-median filled x - training
mean)/training population SD; one-hot categories and varying-column mask use
training rows only. Training requires entry and label_end before forecast cutoff.
Tier: 1. No numerical targets, predictive fitting, LLM calls or network access.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/prepare_inputs.py --output NEW_RUN [--verify]
"""

import argparse
import hashlib
import json
import math
import platform
from collections import Counter
from html import escape
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "research/runs/ml-feature-preview/20261012-v1"
PROTOCOL = ROOT / "research/protocol/ml-preprocessing-v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False) + "\n").encode()


def split_rows(metadata, year):
    cutoff, end = f"{year}-01-01", f"{year + 1}-01-01"
    training = [r["row_id"] for r in metadata if r["entry"] < cutoff and r["label_end"] < cutoff]
    later = [r["row_id"] for r in metadata if cutoff <= r["entry"] < end]
    return training, later


class InputPreprocessor:
    """JSON-serializable, auditable implementation of the declared transformations."""

    def __init__(self, definitions, log_columns):
        self.definitions = definitions
        self.numeric = sorted(k for k, v in definitions.items() if v["kind"] == "numeric")
        categorical = [k for k, v in definitions.items() if v["kind"] == "categorical"]
        if len(categorical) != 1 or not set(log_columns) <= set(self.numeric):
            raise ValueError("Unsupported or inconsistent feature definition")
        self.category = categorical[0]
        self.log_columns = set(log_columns)
        self.state = None

    def numeric_values(self, row):
        if set(row) != set(self.definitions):
            raise ValueError("Inputs must contain only the declared feature columns")
        values = []
        for key in self.numeric:
            value = row[key]
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"Nonfinite or nonnumeric input: {key}")
                if key in self.log_columns:
                    if value < 0:
                        raise ValueError(f"Negative log1p input: {key}")
                    value = math.log1p(value)
            values.append(value)
        if row[self.category] is not None and not isinstance(row[self.category], str):
            raise ValueError("Industry must be a category string, not a numerical magnitude")
        return values

    def fit(self, rows):
        if not rows:
            raise ValueError("No matured training rows")
        values = [self.numeric_values(row) for row in rows]
        medians, means, scales, all_missing = {}, {}, {}, []
        for index, key in enumerate(self.numeric):
            observed = [row[index] for row in values if row[index] is not None]
            fill = median(observed) if observed else 0.0
            if not observed:
                all_missing.append(key)
            imputed = [fill if row[index] is None else row[index] for row in values]
            mean = math.fsum(imputed) / len(imputed)
            variance = math.fsum((v - mean) ** 2 for v in imputed) / len(imputed)
            medians[key], means[key], scales[key] = fill, mean, math.sqrt(variance) or 1.0
        categories = sorted({row[self.category] for row in rows if row[self.category] is not None})
        names = self.numeric + [f"{key}__missing" for key in self.numeric]
        names += [f"{self.category}=={value}" for value in categories]
        self.state = {"numeric_columns": self.numeric, "category_column": self.category,
                      "log1p_columns": sorted(self.log_columns), "medians": medians,
                      "means": means, "scales": scales, "categories": categories,
                      "all_missing_training_columns": all_missing, "raw_encoded_names": names}
        raw = [self.raw_transform(row) for row in rows]
        keep = [i for i in range(len(names)) if any(row[i] != raw[0][i] for row in raw[1:])]
        if not keep:
            raise ValueError("No varying training inputs")
        self.state.update(keep_indices=keep, feature_names=[names[i] for i in keep],
                          dropped_constant_columns=[name for i, name in enumerate(names) if i not in keep])
        return self

    def raw_transform(self, row):
        if self.state is None:
            raise ValueError("Preprocessing has not been fitted")
        values = self.numeric_values(row)
        numbers = []
        for key, value in zip(self.numeric, values, strict=True):
            if key in self.state["all_missing_training_columns"]:
                numbers.append(0.0)
            else:
                filled = self.state["medians"][key] if value is None else value
                numbers.append((filled - self.state["means"][key]) / self.state["scales"][key])
        return numbers + [int(v is None) for v in values] + [
            int(row[self.category] == category) for category in self.state["categories"]]

    def transform(self, rows):
        if self.state is None:
            raise ValueError("Preprocessing has not been fitted")
        result = []
        for row in rows:
            raw = self.raw_transform(row)
            result.append([raw[i] for i in self.state["keep_indices"]])
        if not all(math.isfinite(v) for row in result for v in row):
            raise ValueError("Nonfinite transformed inputs")
        return result


def gap_diagnostics(features, metadata, evidence):
    reasons = Counter()
    row_reasons = []
    for x, m, e in zip(features, metadata, evidence, strict=True):
        if x["features"]["reported_ownership_pct_max"] is not None:
            continue
        if m["ownership_security_status"] != "unique_cusip_prefix_agreement":
            reason = "unresolved_security_attribution"
        elif not e["ownership_rows"]:
            reason = "no_extracted_ownership_rows_for_matched_security"
        elif any(r["percent_of_class"]["status"] == "present" for r in e["ownership_rows"]):
            reason = "present_percentage_is_not_a_usable_number"
        else:
            reason = "parser_has_no_present_percentage_in_extracted_rows"
        reasons[reason] += 1
        row_reasons.append({"row_id": x["row_id"], "reason": reason,
                            "field_status_counts": dict(Counter(r["percent_of_class"]["status"] for r in e["ownership_rows"]))})
    return {"missing_ownership_events": sum(reasons.values()), "reason_counts": dict(reasons),
            "interpretation": "Mechanical gap categories, not semantic source review or proof that a disclosure lacks ownership.",
            "rows": row_reasons}


def build():
    inputs = {}

    def load(path):
        inputs[str(path.relative_to(ROOT))] = digest(path)
        return json.loads(path.read_text())

    provenance = load(PREVIEW / "provenance.json")
    loaded = {}
    for name in ("features.jsonl", "row-metadata.jsonl", "field-evidence.jsonl", "feature-dictionary.json"):
        path = PREVIEW / name
        sha = digest(path)
        if sha != provenance["outputs_sha256"][name]:
            raise ValueError(f"Feature-preview artifact hash mismatch: {name}")
        inputs[str(path.relative_to(ROOT))] = sha
        loaded[name] = ([json.loads(line) for line in path.read_text().splitlines()]
                        if name.endswith(".jsonl") else json.loads(path.read_text()))
    features, metadata, evidence = (loaded[name] for name in ("features.jsonl", "row-metadata.jsonl", "field-evidence.jsonl"))
    ids = [row["row_id"] for row in features]
    if len(ids) != 667 or len(set(ids)) != 667 or any([row["row_id"] for row in data] != ids for data in (metadata, evidence)):
        raise ValueError("Feature, metadata and evidence rows do not align")
    protocol = load(PROTOCOL)
    definitions = loaded["feature-dictionary.json"]["features"]
    inputs[str(Path(__file__).relative_to(ROOT))] = digest(Path(__file__))
    by_id = {row["row_id"]: row["features"] for row in features}
    meta_by_id = {row["row_id"]: row for row in metadata}
    matrices, states, summaries = {}, {}, []
    for year in protocol["prediction_years"]:
        train_ids, later_ids = split_rows(metadata, year)
        training, later = ([by_id[i] for i in selected] for selected in (train_ids, later_ids))
        processor = InputPreprocessor(definitions, protocol["log1p_columns"]).fit(training)
        train_x, later_x = processor.transform(training), processor.transform(later)
        unknown = [i for i in later_ids if by_id[i][processor.category] not in processor.state["categories"]]
        means = [math.fsum(row[j] for row in train_x) / len(train_x) for j in range(len(train_x[0]))]
        state = processor.state
        states[str(year)] = state
        matrices[str(year)] = {"feature_names": state["feature_names"],
                               "training_row_ids": train_ids, "training_X": train_x,
                               "later_row_ids": later_ids, "later_X": later_x}
        summaries.append({"prediction_year": year, "training_events": len(train_ids),
                          "later_events": len(later_ids), "encoded_input_columns": len(state["feature_names"]),
                          "industry_categories_learned": len(state["categories"]),
                          "unseen_later_industry_events": len(unknown), "unseen_later_industry_row_ids": unknown,
                          "dropped_constant_columns": state["dropped_constant_columns"],
                          "training_ownership_missing_events": sum(row["reported_ownership_pct_max"] is None for row in training),
                          "later_ownership_missing_events": sum(row["reported_ownership_pct_max"] is None for row in later),
                          "training_ownership_fill_percent": state["medians"]["reported_ownership_pct_max"],
                          "latest_training_label_end": max(meta_by_id[i]["label_end"] for i in train_ids),
                          "all_matrix_values_finite": True,
                          "numeric_training_means_near_zero": all(abs(means[j]) < 1e-10 for j, name in enumerate(state["feature_names"]) if name in processor.numeric)})
    gaps = gap_diagnostics(features, metadata, evidence)
    assert gaps["missing_ownership_events"] == 110
    assert [(r["training_events"], r["later_events"]) for r in summaries] == [(118, 106), (254, 110), (365, 86)]
    summary = {"status": "checkpoint_2_complete_preprocessing_only", "events": 667,
               "folds": summaries, "gap_reason_counts": gaps["reason_counts"],
               "numerical_target_values_read": False, "predictive_model_fitted": False,
               "interpretation": "Chronological development input preparation; no prediction accuracy or investment performance result."}
    artifacts = {"summary.json": encode(summary), "preprocessing-state.json": encode(states),
                 "fold-inputs.json": encode(matrices), "ownership-gap-diagnostics.json": encode(gaps),
                 "protocol.json": encode(protocol), "index.html": report(summary).encode()}
    artifacts["provenance.json"] = encode({"inputs_sha256": inputs, "python": platform.python_version(),
        "implementation": "Python standard library; explicit median, log1p, ddof=0 scaling and categorical encoding",
        "outputs_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}})
    return artifacts, summary


def report(summary):
    rows = "".join(f'<tr><td>{r["prediction_year"]}</td><td>{r["training_events"]}</td><td>{r["later_events"]}</td><td>{r["encoded_input_columns"]}</td><td>{r["training_ownership_fill_percent"]:g}%</td><td>{r["unseen_later_industry_events"]}</td></tr>' for r in summary["folds"])
    gap_rows = "".join(f'<tr><td>{escape(reason.replace("_", " "))}</td><td>{count}</td></tr>' for reason, count in summary["gap_reason_counts"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D checkpoint 2 preparing model inputs</title><style>body{{font:17px/1.6 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:1000px;margin:32px auto;padding:24px;background:white}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #ddd}}th{{background:#edf3f7}}.scroll{{overflow:auto}}a{{color:#155c99}}details{{margin:15px 0}}</style></head><body><main>
<h1>Checkpoint 2 preparing model inputs</h1><p>October 12, 2026 | Input preparation complete; predictive modeling has not started</p>
<p><strong>Can we prepare the 13D inputs without giving a future prediction access to future data?</strong> Three chronological development folds now have finite numerical input tables and saved training-only preprocessing settings. The 667 candidate events are preserved. No numerical return targets were read for these calculations, and no predictive model has been fitted.</p>
<h2>What we did and why</h2><ol><li>Separated earlier events with completed outcomes from the next prediction year's entries. A two-year result cannot enter training before its return window ends.</li><li>Compressed the scale of size and count features with log(1+x), preserving zero. This reduces the numerical spread of very large values without choosing cutoffs from outcomes.</li><li>Filled missing numerical inputs with the training median and added missing-value flags.</li><li>Scaled numerical inputs using training means and population standard deviations.</li><li>Encoded each training industry category as a separate binary column. Later unseen industries use an all-zero category vector and are flagged in diagnostics.</li><li>Removed columns that never varied in training, then applied that same column selection later. Original missingness remains in the feature preview and diagnostics.</li></ol>
<h2>Worked example imputation and scaling</h2><p>Suppose the observed training ownership percentages are 4% and 8%, with a third missing. The median is 6%, so the filled values are [4, 8, 6]. Their mean is 6 and population standard deviation is about 1.633. The scaled values are about [-1.225, +1.225, 0]. A separate missing flag is [0, 0, 1]. The filled 6% is a computational placeholder, not a claim about actual ownership.</p>
<p>Now suppose a later filing reports 20%. Apply the earlier mean and scale: (20-6)/1.633 is about 8.573. Do not recompute the mean using 20%. A large standardized value signals that this input is far from the training distribution; standardization does not guarantee a safe prediction.</p>
<h2>Encoding an industry category</h2><p>If training contains industries 30 and 60, use two columns: industry 30 becomes [1,0] and industry 60 becomes [0,1]. Industry 75 encountered later becomes [0,0] and is recorded as unseen. These codes identify groups; they are not sizes or scores. Encoding can turn ten original fields into many numerical columns.</p>
<h2>Actual chronological input tables</h2><div class="scroll"><table><thead><tr><th>Prediction year</th><th>Earlier training events</th><th>Later events</th><th>Input columns after encoding</th><th>Training ownership fill</th><th>Unseen later industries</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>These are candidate development folds, not untouched final tests. No hyperparameters have been selected. A later model experiment still needs inner validation that respects when outcomes become known; a random split or an ordinary row-order split does not establish that timing.</p>
<h2>Why ownership inputs are missing</h2><table><thead><tr><th>Mechanical gap</th><th>Events among the 110 missing summaries</th></tr></thead><tbody>{gap_rows}</tbody></table>
<p>These categories explain the stored parser/join state, not the full meaning of the source filing. No semantic source correction has been made. Imputation allows model computation; it cannot repair extraction errors. LLM assistance remains a separately validated experiment.</p>
<h2>Catch up checks</h2><details><summary>Why not calculate the median using all 667 events?</summary><p>Because later events would change how we represent earlier training data. Learn the fill value only from rows whose outcomes were available at that prediction cutoff, then reuse it.</p></details><details><summary>Why did the number of columns grow?</summary><p>Industry became several binary columns, and numerical inputs received missing flags. Columns with no variation in training were removed. The saved state names every retained and dropped column.</p></details><details><summary>Does a completed input table show that the neural network will work?</summary><p>No. It shows the data can be passed to a model under explicit transformations. Predictive usefulness still needs comparisons and chronological evaluation; semantic source accuracy and sample coverage still matter.</p></details>
<h2>Checkpoint status and next stage</h2><p>Completed: row alignment, preview hashes, matured-training rules, gap categorization and train-only transforms. Next: freeze a small first predictive experiment and establish its naive/regularized comparisons before evaluating the neural network. Explain loss, weights, training and validation through that work. Liquidity, volatility and fundamentals are not yet inputs.</p>
<p><a href="summary.json">Exact counts</a> · <a href="preprocessing-state.json">Saved training settings</a> · <a href="fold-inputs.json">Numerical input tables</a> · <a href="ownership-gap-diagnostics.json">Gap diagnostics</a> · <a href="protocol.json">Transformation contract</a> · <a href="provenance.json">Reproducibility</a></p>
<p><a href="../../../docs/ml-checkpoints.html">Learning checkpoints</a> · <a href="../../../../START-HERE.html">Project home</a></p><p>Method references: <a href="https://scikit-learn.org/stable/modules/preprocessing.html">scaling and categorical encoding</a>; <a href="https://scikit-learn.org/stable/modules/impute.html">imputation and missing indicators</a>. Formulas are implemented here with Python's standard library and checked on synthetic examples. AI-assisted local tooling and explanation.</p></main></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    artifacts, summary = build()
    if args.verify:
        for name, payload in artifacts.items():
            if (args.output / name).read_bytes() != payload:
                raise ValueError(f"Preprocessing replay mismatch: {name}")
        print("Exact offline replay verified for all seven preprocessing artifacts.")
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, payload in artifacts.items():
            (args.output / name).write_bytes(payload)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
