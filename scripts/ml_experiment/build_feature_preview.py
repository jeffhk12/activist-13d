"""Join deterministic filing features to existing 13D development labels.

Inputs: frozen outcomes, dated assignments, facts/bundles, prior CIK history,
human protection list, and ml-feature-preview-v1.json.
Outputs: separate feature/target/metadata JSONL, evidence, coverage and lesson HTML.
Identity: ownership=max(valid per-row percentages), never their sum;
cap USD=CRSP snapshot dlycap*1000; lag=filing date-event date; prior counts
are strict-earlier restricted-cache observations. No preprocessing or model fit.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/build_feature_preview.py --output NEW_RUN [--verify]
"""

import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from activist13d.edgar.deterministic import verify_citations  # noqa: E402
from activist13d.local_paths import resolve_project_path  # noqa: E402

ANALYSIS = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-analysis-v1"
MARKET = ROOT / "research/runs/phase1-baseline/20260924-long-horizon-inputs-v1"
FACTS = ROOT / "research/runs/phase2-overnight/20260924-full-v1"
AUDIT = ROOT / "research/runs/phase2-readiness/20260924-full-v1"
CONTRACT = ROOT / "research/protocol/ml-feature-preview-v1.json"
PROTECTION = ROOT / "research/runs/phase1-baseline/20260924-development-v4/human-review-protection.json"


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def field_value(field):
    return field.get("value") if field.get("status") == "present" else None


def finite_number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def market_cap_usd(value):
    number = finite_number(value)
    return number * 1000 if number is not None and number > 0 else None


def industry_code(value):
    number = finite_number(value)
    if number is None or not number.is_integer() or not 100 <= number < 9999:
        return None
    return f"{int(number):04d}"[:2]


def filing_lag(filing_day, event_day):
    try:
        lag = (date.fromisoformat(filing_day) - date.fromisoformat(event_day)).days
    except (TypeError, ValueError):
        return None
    return lag if lag >= 0 else None


def ownership_summary(rows):
    values = []
    for row in rows:
        number = finite_number(field_value(row.get("percent_of_class", {})))
        if number is not None and 0 <= number <= 100:
            values.append(number)
    return (max(values) if values else None, len(values) / len(rows) if rows else None)


def history_features(history, issuer):
    reporters = history["reporter_history"]
    matches = [r for r in history["issuer_history"] if r["cik"] == issuer]
    if len(matches) != 1:
        raise ValueError("Prior history has no unique matching issuer")
    for row in reporters:
        for key in ("prior_submission_count", "prior_other_issuer_count"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError("Invalid prior count")
    other = matches[0]["prior_reporter_ciks_outside_current_group"]
    if type(other) is not int or other < 0:
        raise ValueError("Invalid issuer history count")
    return {
        "header_reporter_count": len(reporters),
        "prior_header_submission_count_max": max(
            (r["prior_submission_count"] for r in reporters), default=None
        ),
        "prior_header_other_issuer_count_max": max(
            (r["prior_other_issuer_count"] for r in reporters), default=None
        ),
        "prior_issuer_other_reporter_count": other,
    }


def build():
    inputs = {}

    def remember(path, expected=None):
        sha = digest(path)
        if expected is not None and sha != expected:
            raise ValueError(f"Frozen hash mismatch: {path.relative_to(ROOT)}")
        inputs[str(path.relative_to(ROOT))] = sha
        return sha

    def load(path, expected=None):
        remember(path, expected)
        return json.loads(path.read_text())

    analysis_prov = load(ANALYSIS / "provenance.json")
    market_prov = load(MARKET / "provenance.json")
    audit_prov = load(AUDIT / "provenance.json")
    outcomes = load(ANALYSIS / "outcomes.json", analysis_prov["outputs"]["outcomes.json"])
    assignments = load(MARKET / "assignments.json", market_prov["outputs"]["assignments.json"])
    selection = load(FACTS / "selection.json", audit_prov["source_hashes"][str((FACTS / "selection.json").relative_to(ROOT))])
    selected = {r["accession"]: r for r in selection}
    history_path = FACTS / "prior-header-cik-history.jsonl"
    remember(history_path, audit_prov["source_hashes"][str(history_path.relative_to(ROOT))])
    history = {r["accession"]: r for line in history_path.read_text().splitlines() if (r := json.loads(line))}
    protection = load(PROTECTION, market_prov["inputs"][str(PROTECTION.relative_to(ROOT))])
    contract = load(CONTRACT)
    remember(Path(__file__))
    features, targets, metadata, evidence, exclusions = [], [], [], [], []
    join_issues = Counter()
    rows = [r for r in outcomes["first_observed"]["504"]["russell"]
            if r["status"] == "calculated_common_sample" and len(r["accessions"]) == 1
            and r["accession"] in selected]
    if len(rows) != 667:
        raise ValueError("Candidate count differs from the completed feasibility assessment")
    for event in sorted(rows, key=lambda r: (r["entry"], r["accession"])):
        accession = event["accession"]
        if accession in protection["accessions"] or event["issuer"] in protection["issuers"]:
            raise ValueError("Protected human-review observation reached feature preparation")
        receipt = load(FACTS / "receipts" / f"{accession}.json")
        if receipt["status"] != "processed" or receipt["source_sha256"] != selected[accession]["source_sha256"]:
            raise ValueError("Factual receipt/source disagreement")
        loaded = {}
        for folder, sha_key in (("facts", "facts_sha256"), ("bundles", "bundle_sha256")):
            path = FACTS / folder / f"{accession}.json.gz"
            remember(path, receipt[sha_key])
            loaded[folder] = json.loads(gzip.decompress(path.read_bytes()))
        fact, bundle = loaded["facts"], loaded["bundles"]
        if fact["accession"] != accession or bundle["accession"] != accession:
            raise ValueError("Accession join mismatch")
        source = resolve_project_path(bundle["source_path"], ROOT)
        if not source.is_relative_to((ROOT / "data/raw/edgar").resolve()):
            raise ValueError("Source path outside the preserved SEC cache")
        remember(source, receipt["source_sha256"])
        verify_citations(fact, bundle)
        issuer_set = {field_value(r["cik"]) for r in fact["issuers"]}
        if issuer_set != {event["issuer"]} or len(fact["filings"]) != 1:
            exclusions.append({"accession": accession, "reason": "nonunique_or_disagreeing_header_issuer"})
            continue
        filing = fact["filings"][0]
        accepted = field_value(filing["acceptance_datetime_et"])
        hist = history[accession]
        if accepted != selected[accession]["accepted"] or hist["available_at_acceptance_et"] != accepted:
            raise ValueError("Acceptance/history chronology mismatch")
        reporter_ciks = {field_value(r["cik"]) for r in fact["filing_entities"]}
        if reporter_ciks != {r["cik"] for r in hist["reporter_history"]}:
            raise ValueError("Header reporter/history identifier mismatch")
        assignment = assignments[event["input_key"]]
        if assignment["permno"] != event["permno"] or assignment["etf"] != event["assigned_etf"] or assignment["status"] != "matched":
            raise ValueError("Historical security/benchmark assignment mismatch")
        if not assignment["snapshot"] <= assignment["pre"] < accepted[:10] < event["entry"] or assignment["public"] != accepted[:10]:
            raise ValueError("Market feature chronology mismatch")
        security = assignment["historical_security"]
        matches = [s for s in fact["securities"] if
                   isinstance((c := field_value(s["cusip"])), str)
                   and len(c) == 9 and c[:8] == security["cusip"]]
        if len(matches) == 1:
            ownership = [r for r in fact["ownership"] if r["security_id"] == matches[0]["security_id"]]
            ownership_status = "unique_cusip_prefix_agreement"
        else:
            ownership = []
            ownership_status = "unresolved_security_attribution"
            join_issues[ownership_status] += 1
        max_pct, valid_fraction = ownership_summary(ownership)
        event_day = field_value(filing["event_date"])
        filed_day = field_value(filing["filing_date"])
        x = {
            "snapshot_security_market_cap_usd": market_cap_usd(security["dlycap"]),
            "pre_disclosure_industry_sic2": industry_code(assignment["siccd"]),
            "parsed_reporting_person_count": len(fact["reporting_persons"]),
            "reported_ownership_pct_max": max_pct,
            "ownership_pct_valid_fraction": valid_fraction,
            "filing_event_lag_calendar_days": filing_lag(filed_day, event_day),
            **history_features(hist, event["issuer"]),
        }
        if set(x) != set(contract["features"]):
            raise ValueError("Feature dictionary disagreement")
        row_id = event["input_key"]
        features.append({"row_id": row_id, "features": x})
        targets.append({"row_id": row_id, "target_russell_excess_504": event["excess"],
                        "unit": "decimal cumulative return difference", "label_end": event["exit"]})
        metadata.append({"row_id": row_id, "accession": accession, "issuer": event["issuer"],
                         "header_reporter_ciks": sorted(reporter_ciks), "permno": event["permno"],
                         "accepted_et": accepted, "entry": event["entry"], "label_end": event["exit"],
                         "cohort_for_diagnostics_only": event["disjoint_cohort"],
                         "ownership_security_status": ownership_status,
                         "market_cap_as_of": assignment["snapshot"],
                         "industry_as_of": assignment["pre"],
                         "quality_issue_count": len(fact["quality_issues"])})
        evidence.append({"row_id": row_id, "facts_path": str((FACTS / "facts" / f"{accession}.json.gz").relative_to(ROOT)),
                         "source_path": str(source.relative_to(ROOT)), "source_sha256": receipt["source_sha256"],
                         "market_assignment_key": event["input_key"], "market_assignment": assignment,
                         "history": hist, "filing_event_date": filing["event_date"],
                         "filing_date": filing["filing_date"],
                         "ownership_rows": ownership})
    assert len(features) + len(exclusions) == 667
    assert len(features) == len(targets) == len(metadata) == len(evidence)
    assert len({r["row_id"] for r in features}) == len(features)
    coverage = {}
    for key in contract["features"]:
        by_year = {}
        for year in sorted({r["entry"][:4] for r in metadata}):
            pairs = [(x, m) for x, m in zip(features, metadata, strict=True) if m["entry"][:4] == year]
            by_year[year] = {"rows": len(pairs), "present": sum(x["features"][key] is not None for x, _ in pairs)}
        present = sum(r["features"][key] is not None for r in features)
        coverage[key] = {"rows": len(features), "present": present,
                         "missing": len(features) - present, "by_entry_year": by_year}
    summary = {"status": "candidate_feature_preview_no_model_fitting",
               "candidate_events": 667, "joined_events": len(features),
               "excluded_events": len(exclusions), "exclusion_reasons": dict(Counter(r["reason"] for r in exclusions)),
               "join_issues": dict(join_issues), "feature_coverage": coverage,
               "cohort_counts": dict(Counter(r["cohort_for_diagnostics_only"] for r in metadata)),
               "checks": ["frozen outcome/assignment/history/selection hashes", "facts/bundle/raw-source hashes",
                          "exact canonical citations", "issuer/reporter identifiers", "pre-disclosure dates",
                          "features separated from targets and diagnostic cohorts"],
               "limits": ["Semantic extraction remains unvalidated.", "No confirmed point-in-time HFR identity feature is included.",
                          "Market observations are dated vendor history, not certification of vendor publication timing.",
                          "No liquidity, volatility, momentum or fundamentals features have been assembled here.",
                          "Previously examined labels remain development evidence."]}
    artifacts = {"features.jsonl": b"".join(map(encode, features)),
                 "targets.jsonl": b"".join(map(encode, targets)),
                 "row-metadata.jsonl": b"".join(map(encode, metadata)),
                 "field-evidence.jsonl": b"".join(map(encode, evidence)),
                 "exclusions.json": encode(exclusions), "summary.json": encode(summary),
                 "feature-dictionary.json": encode(contract),
                 "index.html": report(summary, contract).encode()}
    artifacts["provenance.json"] = encode({"inputs_sha256": inputs,
        "outputs_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()}})
    return artifacts, summary


def report(summary, contract):
    rows = "".join(f'<tr><td>{escape(definition["description"])}</td><td>{stats["present"]} / {stats["rows"]}</td><td>{stats["missing"]}</td></tr>'
                   for key, definition in contract["features"].items()
                   if (stats := summary["feature_coverage"][key]))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>13D features and targets lesson</title><style>body{{font:17px/1.6 system-ui;color:#203448;background:#f4f6f8;margin:0}}main{{max-width:980px;margin:30px auto;padding:24px;background:white}}table{{width:100%;border-collapse:collapse;font-size:15px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ddd;vertical-align:top}}th{{background:#edf3f7}}a{{color:#155c99}}code{{overflow-wrap:anywhere}}</style></head><body><main>
<h1>13D features and targets lesson</h1><p>October 12, 2026 | Data preparation and teaching preview</p>
<p><strong>Can we turn the broader 13D evidence into inputs for a neural-network selection model?</strong> We joined {summary['joined_events']} of 667 candidate two-year events to deterministic filing facts, prior disclosure histories and dated company characteristics. This establishes a candidate feature table, not a trained model or an investment edge.</p>
<h2>One row is one investment opportunity</h2><p>Each row describes one issuer-entry event associated with one eligible initial filing. Columns describe what was observable before entry. The answer we want the model to learn is kept separately: the later two-year stock return minus its assigned Russell ETF-proxy return. Related positions and repeated issuers make rows dependent; they are not independent trials.</p>
<h2>Features are inputs and targets are answers</h2><p><strong>Illustrative example:</strong> a filing reports an 8% stake, the issuer has a $500 million market capitalization, and the reporter has 12 earlier submissions. These are inputs. If the stock later returns 30% while the benchmark returns 10%, the target is +20 percentage points, stored as 0.20. The future return cannot appear among the inputs.</p>
<p>Mathematically, we call the input table <strong>X</strong> and the answer column <strong>y</strong>. A model learns a mapping from X to an estimate of y. Whether to buy then depends on a trading rule that considers its prediction, costs and portfolio constraints. Predicting return and executing a position are separate steps.</p>
<h2>The candidate feature columns</h2><table><thead><tr><th>Input and meaning</th><th>Present / joined events</th><th>Missing</th></tr></thead><tbody>{rows}</tbody></table>
<p>Company size comes from the prior benchmark snapshot, which can be older than the day before disclosure. Its actual date is retained. Industry comes from the pre-disclosure observation. Historical vendor data can be revised, so these dates do not certify historical vendor publication timing.</p>
<h2>Missing does not mean zero</h2><p>A recorded 0% is a number. An unreadable or unextracted percentage is unknown. The feature table keeps unknown values empty. A later training pipeline may replace missing inputs using statistics learned on training rows and retain missing-value flags. Compute these replacements separately inside each training fold; future rows cannot influence them.</p>
<h2>Ownership overlap and identity uncertainty</h2><p>If three related parties report the same 8%, our summary is the largest reported percentage, 8%, not a sum of 24%. It is a description of the source rows, not confirmed economic ownership. Original rows and citations remain in the evidence file. If security attribution is unresolved, ownership summaries remain missing.</p>
<p>Current HFR labels and retrospectively chosen activist cohorts are retained only as diagnostic metadata. They are not input columns. Prior CIK counts describe the restricted archive, not validated manager skill or continuing positions.</p>
<h2>What comes before neural-network training</h2><p>We still need to review source/format gaps, settle the first target and comparison rules, and define chronological training and validation. Inputs such as market capitalization, ownership percentage and filing counts use different units. Scaling makes numerical columns comparable for optimization; its parameters must be learned from training data only. Industry is a category and needs an encoding that does not imply that industry 60 is twice industry 30.</p>
<p>The central planned method is a small feedforward neural network, with regularized regression and boosted trees as comparisons. The preview fits no scaling, imputers, hyperparameters or models. It performs no LLM calls. Existing accounting limitations still constrain portfolio claims.</p>
<h2>Evidence and continuation</h2><p><a href="summary.json">Coverage by year and checks</a> · <a href="feature-dictionary.json">Exact feature definitions</a> · <a href="features.jsonl">Inputs X</a> · <a href="targets.jsonl">Targets y</a> · <a href="row-metadata.jsonl">Dates and diagnostic groups</a> · <a href="field-evidence.jsonl">Source evidence</a> · <a href="provenance.json">Hashes</a></p>
<p><a href="../../../docs/ml-experiment-20261012.html">Experiment and learning plan</a> · <a href="../../../../START-HERE.html">Project home</a></p>
<p>Method references: <a href="https://scikit-learn.org/stable/modules/preprocessing.html">preprocessing and encoding</a>; <a href="https://scikit-learn.org/stable/modules/impute.html">missing-value treatment</a>. AI-assisted local tooling and explanations.</p></main></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    artifacts, summary = build()
    if args.verify:
        for name, payload in artifacts.items():
            if (args.output / name).read_bytes() != payload:
                raise ValueError(f"Offline replay mismatch: {name}")
        print("Exact offline replay verified for all nine preview artifacts.")
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, payload in artifacts.items():
            (args.output / name).write_bytes(payload)
        print(json.dumps({k: v for k, v in summary.items() if k != "feature_coverage"}, indent=2))
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_entry_year"}
                          for k, v in summary["feature_coverage"].items()}, indent=2))


if __name__ == "__main__":
    main()
