"""Build the ML professor update including baseline results and the NN draft.

Inputs: preserved feature/preprocessing/baseline evidence and the proposed network
plan. Output: four-page professor PDF, companion notes, snapshots and QA receipt.
Identity: errors are decimal return differences * 100 in percentage points;
proposed p->4->1 network has 4*p+9 parameters. No research/model run.
Tier: 2 presentation of preserved evidence; visual QA follows rendering.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 bundled PDF-runtime Python
    research/docs/professor-update-20261015/build_update.py
"""

import hashlib
import json
import sys
from html import escape
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from reportlab.platypus import Flowable, SimpleDocTemplate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "professor-discussion-20261013"))
import build_briefs as b  # noqa: E402

PDF = HERE / "13D_Machine_Learning_Project_Update_20261015.pdf"
SOURCES = {
    "feature-preview-summary.json": ROOT / "research/runs/ml-feature-preview/20261012-v1/summary.json",
    "preprocessing-summary.json": ROOT / "research/runs/ml-preprocessing/20261012-v1/summary.json",
    "baseline-summary.json": ROOT / "research/runs/ml-baselines/20261015-v1/summary.json",
    "baseline-evaluation.json": ROOT / "research/runs/ml-baselines/20261015-v1/evaluation.json",
    "baseline-verification.json": ROOT / "research/runs/ml-baselines/20261015-v1/verification.json",
    "baseline-contract.json": ROOT / "research/protocol/ml-baselines-v1.json",
    "network-plan.html": ROOT / "research/docs/neural-network-lessons/20261015/network-plan.html",
    "factual-staging.json": ROOT / "research/runs/phase2-overnight/20260924-full-v1/progress.json",
}
FEATURE = json.loads(SOURCES["feature-preview-summary.json"].read_text())
PREP = json.loads(SOURCES["preprocessing-summary.json"].read_text())
BASE = json.loads(SOURCES["baseline-summary.json"].read_text())
EVALUATION = json.loads(SOURCES["baseline-evaluation.json"].read_text())
STAGING = json.loads(SOURCES["factual-staging.json"].read_text())
assert FEATURE["joined_events"] == 667 and sum(FEATURE["cohort_counts"].values()) == 667
assert STAGING["processed"] == 15813
assert STAGING["selected_initial_filings"] + sum(STAGING["selection_exclusions"].values()) == 75631
assert BASE["evaluated_events"] == 302 and not BASE["neural_network_fitted"]
assert BASE["evaluated_cohort_counts"] == {"focused": 18, "new_other_hfr": 25, "other_event_driven": 4, "other_unresolved": 255}
assert [(row["prediction_year"], row["encoded_input_columns"] * 4 + 9) for row in PREP["folds"]] == [(2021, 213), (2022, 261), (2023, 285)]
assert all(EVALUATION["by_prediction_year"][str(year)]["ridge"]["rmse"] > EVALUATION["by_prediction_year"][str(year)]["training_mean"]["rmse"] for year in (2021, 2022, 2023))
NETWORK_TEXT = SOURCES["network-plan.html"].read_text()
for phrase in ("four ReLU", "500 updates", "0.001", "0.01", "11, 23, 37, 51 and 71", "not a frozen experiment"):
    assert phrase.casefold() in NETWORK_TEXT.casefold(), phrase


class Network(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 532, 176

    def draw(self):
        c = self.canv
        c.setStrokeColor(b.RULE)
        c.setLineWidth(1)
        for y in (139, 105, 71, 37):
            c.line(146, 88, 257, y)
            c.line(283, y, 420, 88)
        c.setFillColor(b.PALE)
        c.roundRect(0, 59, 146, 58, 5, fill=1, stroke=1)
        c.setFillColor(b.NAVY)
        c.setFont("BriefBold", 11)
        c.drawCentredString(73, 91, "Prepared inputs")
        c.setFont("Brief", 9.5)
        c.drawCentredString(73, 75, "p = 51, 63 or 69")
        c.setFillColor(b.TEAL)
        c.setFont("BriefBold", 10.4)
        c.drawCentredString(270, 162, "4 hidden ReLU neurons")
        for i, y in enumerate((139, 105, 71, 37), 1):
            c.setFillColor(b.PALE)
            c.circle(270, y, 13, stroke=1, fill=1)
            c.setFillColor(b.NAVY)
            c.setFont("Brief", 9.5)
            c.drawCentredString(270, y - 3, f"h{i}")
        c.setFillColor(b.PALE)
        c.roundRect(420, 59, 112, 58, 5, fill=1, stroke=1)
        c.setFillColor(b.NAVY)
        c.setFont("BriefBold", 10.5)
        c.drawCentredString(476, 91, "Linear output")
        c.setFont("Brief", 9)
        c.drawCentredString(476, 75, "Return estimate")
        c.setFont("Brief", 8.5)
        c.setFillColor(b.GRAY)
        c.drawCentredString(266, 9, "All prepared inputs connect to every hidden neuron. Weights and biases are learned.")


def story():
    s = []
    b.paragraph(s, "Machine learning for 13D investment selection", "title")
    b.paragraph(s, "Advanced Machine Learning | Project update 15 October 2026", "meta")
    b.paragraph(s, "<b>Research question:</b> can a small neural network improve predictions of post-disclosure benchmark-relative stock returns, and does validated LLM-extracted ownership and intent information add value?")
    b.paragraph(s, "<b>Progress:</b> structured data preparation, chronological preprocessing and the first fixed linear comparisons are complete. Ridge regression did not improve the training-mean reference's RMSE in any of the three evaluation years. A four-neuron network is now specified as a <b>draft plan; it has not been frozen, implemented or trained</b>.")
    s.append(b.ProcessStrip([("Prepared inputs", "667 covered event rows", False), ("First comparisons", "302 later events scored", False), ("Small neural network", "proposed; untrained", True)], height=64))
    b.paragraph(s, "<b>Target and timing:</b> 504-exchange-session cumulative stock total return minus its assigned historical Russell size-segment ETF-proxy return. Entry is the opening of the second exchange session after public acceptance. This is continuous-return prediction; investment selection and allocation policies are later decisions. [E4]")
    b.heading(s, "Completed checkpoint 3: first predictive comparison")
    rows = [["Method", "Later n", "RMSE (pp)", "MAE (pp)"]]
    for key, label in (("training_mean", "Earlier training mean"), ("zero_excess", "Zero excess reference"), ("ridge", "Fixed ridge regression")):
        value = BASE["pooled"][key]
        rows.append([label, str(value["n"]), f"{100 * value['rmse']:.2f}", f"{100 * value['mae']:.2f}"])
    b.table(s, rows, [218, 70, 122, 122])
    b.paragraph(s, "Errors are percentage points of the cumulative two-year stock-minus-benchmark return; lower is better. These are <b>prediction errors, not investment returns</b>. The same 302 entry events from 2021-2023 are evaluated for every method, with eventual outcomes through 2025. [E3]")
    b.table(s, [["Prediction year", "Mean RMSE (pp)", "Ridge RMSE (pp)", "Ridge rank correlation"],
               *[[year, f"{100 * values['training_mean']['rmse']:.2f}", f"{100 * values['ridge']['rmse']:.2f}", f"{values['ridge']['spearman']:.3f}"]
                 for year, values in EVALUATION["by_prediction_year"].items()]], [120, 130, 130, 152], padding=4)
    b.heading(s, "Interpretation and limits")
    b.paragraph(s, "This fixed ridge specification has not demonstrated predictive improvement. Its penalty was declared in advance, without tuning on the later years. The result motivates a testable nonlinear comparison; it does not establish that a neural network will work. Simple disclosure-following research also has not established a reliable investable edge.")
    b.paragraph(s, "All historical outcomes were previously examined in development research. Return windows overlap, and issuers/reporters may recur. These are chronological development results, not a new untouched holdout, independent significance test, after-cost portfolio result or risk-adjusted alpha.", "small")

    b.page(s, "Proposed small network: inputs to learned signals")
    b.paragraph(s, "Use one hidden layer of <b>four ReLU neurons</b> and one linear output. Each hidden neuron learns a weighted combination of all prepared inputs and its own bias. ReLU replaces a negative weighted sum with zero and passes a positive one onward. The output combines the four hidden signals into a continuous return estimate. [M1]")
    s.append(Network())
    b.heading(s, "Architecture and parameter budget")
    b.table(s, [["Forecast year", "Network p -> 4 -> 1", "Parameters", "Training n", "Later n"],
               *[[str(row["prediction_year"]), f"{row['encoded_input_columns']} -> 4 -> 1", str(4 * row["encoded_input_columns"] + 9), str(row["training_events"]), str(row["later_events"])] for row in PREP["folds"]]],
            [100, 151, 92, 93, 96])
    b.paragraph(s, "Parameter count: 4p input weights + 4 hidden biases + 4 output weights + 1 output bias = <b>4p + 9</b>. Width is four hidden neurons; depth is one hidden layer, followed by the output layer. Even this small structure has 213 parameters for only 118 training events in 2021. Regularization and later-year evaluation are essential; small architecture does not establish robustness.")
    b.heading(s, "Why this design")
    b.table(s, [
        ["Choice", "Reason"],
        ["Existing encoded inputs", "Isolate the first method comparison using the same information and rows as ridge."],
        ["Four hidden neurons", "A bounded first test of several learned nonlinear combinations; not an optimized width."],
        ["One hidden layer", "Keep capacity and the forward/backward calculations tractable."],
        ["Linear output", "Permit positive and negative benchmark-relative return forecasts. Hidden activations are intermediate signals, not returns."],
    ], [156, 376], padding=4)
    b.paragraph(s, "The network could learn activation boundaries involving combinations of ownership, company context and prior activity. Individual neurons need not be stable financial concepts, and an activation boundary is not automatically an investment decision rule. [E5]", "small")

    b.page(s, "Proposed training and evaluation settings")
    b.paragraph(s, "These are <b>untuned starting choices</b>, not validated optimal settings. The exact experiment, software environment and implementation checks must be frozen before fitting the network. The target, rows and historical cutoff rules remain those of the completed baseline.")
    b.table(s, [
        ["Component", "Proposed specification"],
        ["Hidden initialization", "Independent He-normal weights with variance 2/p; hidden biases zero. Independent draws give hidden neurons different starting weights. [M2]"],
        ["Output initialization", "Independent normal weights, SD 0.01; output bias equals the matured training-target mean. Random initial outputs are centered on the naive reference."],
        ["Objective", "Mean squared error + 0.01 times the sum of squared weights in both layers; biases unpenalized. No target clipping, winsorization or new target transform."],
        ["Optimizer", "Adam; learning rate 0.001; beta values 0.9/0.999; epsilon 1e-8. Apply the L2 penalty explicitly in the loss; no additional optimizer weight decay. [M3]"],
        ["Batch and duration", "Full training sample per update; 500 updates, equivalent to 500 epochs. Fixed budget, not a guarantee of convergence. Save loss and gradient diagnostics."],
        ["Five fixed starts", "Seeds 11, 23, 37, 51 and 71. Report every run and their variation. Proposed primary neural prediction: equal-weight mean across all five runs, a declared ensemble."],
        ["No later-year tuning", "No best-seed selection, architecture search or stopping based on later evaluation errors. A tuned extension needs valid matured inner folds and a new protocol."],
    ], [135, 397], padding=4)
    b.heading(s, "Chronological comparison")
    b.paragraph(s, "Fit one model per start at each January cutoff using only entries whose entire two-year outcomes ended before that cutoff. Reconstruct and reuse the saved training-only imputations, scales, industry vocabulary and constant-column masks. Save predictions before scoring the same 302 later entries used by ridge.")
    b.paragraph(s, "Report pooled RMSE/MAE, within-year Spearman correlation, every year and every seed, plus the declared ensemble. Show training diagnostics and inactive neurons without discarding unfavorable starts. Fixed ridge and neural specifications differ in parameterization and penalties; any gain would not isolate architecture as its sole cause.")
    b.heading(s, "Checks before a real neural fit")
    b.paragraph(s, "Work through a tiny forward prediction, its loss and a backward update. Pin hand-computed examples, check gradients numerically and validate dimensions, dated joins and label maturity. The current proposal uses PyTorch automatic differentiation; dependency setup and version pinning remain pending. No neural implementation or gradient test is claimed complete.")
    b.paragraph(s, "Squared-error loss is sensitive to very large outcomes. Existing targets remain unchanged; heavy-tail behavior is an explicit limitation. Alternative robust losses or target transformations require a separately specified, outcome-aware experiment. [E3-E5]", "small")

    b.page(s, "Data scope, LLM additions and next checkpoints")
    b.table(s, [
        ["Prepared data", "Scope and remaining limits"],
        ["Archive and factual staging", "75,631 filing records, 2013-September 2026; separately, 15,813 initial candidates from 2013-2025 processed for facts and prior histories."],
        ["Current model panel", "667 single-filing candidates: 55 focused activist, 12 other Event-Driven, 44 other HFR and 556 other/unresolved. Entries 2018-2023; outcomes through 2025."],
        ["Information available", "Ten fields: company size/industry (2), ownership/extraction summaries (3), filing/event lag (1), header-party/prior-disclosure activity (4)."],
        ["Gaps and coverage", "Ownership summaries present for 557/667; 110 missing, including 14 unresolved security attributions. HFR identities are diagnostics, not inputs. No liquidity, volatility, momentum or fundamentals added."],
    ], [149, 383], padding=4)
    b.paragraph(s, "The 667 rows are the covered subset of 694 calculable two-year labels from 2,107 scheduled events; 27 merged events await aggregation rules. The archive/staging counts are not successive steps in that return-sample funnel. The 302 evaluated entries include 255 other/unresolved, 18 focused activist, four other Event-Driven and 25 other HFR candidate events. Missing identity does not establish non-activist status. [E1-E3]", "small")
    b.heading(s, "LLM extraction is a later information-set experiment")
    b.table(s, [
        ["Information set", "Test within comparable model families"],
        ["A | deterministic", "Current prepared facts and dated context: the first neural experiment."],
        ["B | assisted attribution", "Add separately validated LLM ownership/identity interpretation."],
        ["C | stated intent", "Add validated Item 4 objectives to test information beyond attribution."],
    ], [146, 386], padding=4)
    b.paragraph(s, "Human source-based development references precede model answers on eligible cases. Retain citations, actors, uncertainty and abstentions. Repeated LLM extraction measures stability separately from accuracy; it is distinct from random neural initialization. No LLM extraction or incremental LLM result has been produced here.")
    b.heading(s, "Next deliverables")
    b.paragraph(s, "<b>1.</b> Complete the forward/backward learning example and implementation checks. <b>2.</b> Freeze and fit the small neural experiment. <b>3.</b> Compare with saved references, then introduce the bounded validated LLM additions. Boosted trees remain a planned nonlinear comparison. Selection, entry timing, horizon and sizing policies follow prediction validation.")
    b.heading(s, "Evidence and methods")
    b.paragraph(s, "E1: factual staging and feature preview (24 September / 12 October). E2: chronological preprocessing (12 October). E3: fixed baseline predictions, event errors and scalar audit (15 October). E4: frozen baseline contract. E5: proposed network plan (15 October). Companion notes provide links and preserved source snapshots.", "small")
    b.paragraph(s, 'M1: <link href="https://docs.pytorch.org/docs/2.14/generated/torch.nn.ReLU.html" color="#146d76">ReLU</link>; M2: <link href="https://docs.pytorch.org/docs/2.14/nn.init.html#torch.nn.init.kaiming_normal_" color="#146d76">He initialization</link>; M3: <link href="https://docs.pytorch.org/docs/2.14/generated/torch.optim.Adam.html" color="#146d76">Adam</link>. These document methods; they do not validate the proposed project settings.', "small")
    b.paragraph(s, "AI-assisted tooling and writing. Earlier briefs, research outputs and human-review records are preserved. This update runs no new model, LLM extraction, return calculation or investment account.", "small")
    return s


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(b.RULE)
    canvas.line(40, 29, 572, 29)
    canvas.setFont("Brief", 8)
    canvas.setFillColor(b.GRAY)
    canvas.drawRightString(572, 17, f"{doc.page} / 4")
    canvas.restoreState()


def main():
    old_pdf = HERE.parent / "professor-discussion-20261013/13D_Machine_Learning_Brief_20261013.pdf"
    old_sha = hashlib.sha256(old_pdf.read_bytes()).hexdigest()
    doc = SimpleDocTemplate(str(PDF), pagesize=b.letter, leftMargin=34, rightMargin=34,
                           topMargin=36, bottomMargin=41, title="13D Machine Learning Project Update - 15 October 2026", author="Jeff Lu")
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(PDF)
    assert len(reader.pages) == 4, len(reader.pages)
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    for expected in ("89.90", "87.08", "93.68", "64.78", "60.87", "67.84", "213", "261", "285", "500", "0.001", "0.01", "302", "667", "15,813"):
        assert expected in text, expected
    assert "has not been frozen, implemented or trained" in text
    assert "not a new untouched holdout" in text
    bounds = []
    with pdfplumber.open(PDF) as parsed:
        for i, page in enumerate(parsed.pages, 1):
            chars = [char for char in page.chars if char["text"].strip() and char["top"] < 750]
            assert min(char["x0"] for char in chars) >= 38, i
            assert max(char["x1"] for char in chars) <= 575, i
            assert max(char["bottom"] for char in chars) < 750, i
            bounds.append({"page": i, "lowest_body_from_top": round(max(char["bottom"] for char in chars), 2)})
    snapshots = HERE / "source-snapshots"
    snapshots.mkdir(exist_ok=True)
    sha = {}
    for name, path in SOURCES.items():
        payload = path.read_bytes()
        (snapshots / name).write_bytes(payload)
        sha[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest()
    note_links = "".join(f'<li><a href="source-snapshots/{name}">{escape(name)}</a> &middot; <a href="../../../{path.relative_to(ROOT)}">live project source</a></li>' for name, path in SOURCES.items())
    (HERE / "index.html").write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D ML professor update - 15 October 2026</title><style>body{{font:17px/1.65 system-ui;color:#19374a;background:#f4f6f8}}main{{max-width:920px;margin:30px auto;padding:26px;background:white}}h2{{color:#146d76}}a{{color:#146d76}}blockquote{{border-left:4px solid #146d76;margin:16px 0;padding:8px 18px}}</style></head><body><main>
<h1>13D Machine Learning professor update</h1><p>15 October 2026 | <a href="{PDF.name}">Open the four-page project update</a></p>
<h2>Short progress explanation</h2><blockquote>I have completed the structured-input preparation and first chronological prediction comparisons. Fixed ridge regression did not beat the training-mean reference in any of three years. My proposed neural network has one hidden layer with four ReLU neurons and a linear return output, with 213-285 parameters depending on the year's input encoding. I will keep the same two-year target and evaluation rows, use regularization and five declared random starts, and report all runs and their average prediction. The network is a draft design and has not been implemented or trained. LLM ownership and intent extraction remain later feature experiments.</blockquote>
<h2>Input to seek from the professor</h2><ol><li>Is one hidden layer with four ReLU neurons an appropriate first neural method given 118-365 matured training events and sparse industry columns?</li><li>Is a fixed mean-squared-error first comparison appropriate with the very large observed target tails, followed by a separately declared robust-loss extension?</li><li>Does the proposed chronological development evaluation, fixed training budget and all-seed reporting meet the course expectations? Which additional method or validation evidence is required?</li></ol>
<p>The diagram and training settings are proposed, not fitted results. Existing history was already inspected; no untouched final test is claimed. No material has been sent to the professor.</p>
<h2>Evidence retained with this update</h2><ul>{note_links}</ul><p><a href="evidence.json">Hashes and build record</a> &middot; <a href="verification.json">Final PDF verification</a></p><p><a href="../../../START-HERE.html">Project home</a> &middot; <a href="../ml-checkpoints.html">Learning checkpoints</a> &middot; <a href="../professor-discussion-20261013/13D_Machine_Learning_Brief_20261013.pdf">Preserved October 13 ML handout</a></p></main></body></html>''', encoding="utf-8")
    assert hashlib.sha256(old_pdf.read_bytes()).hexdigest() == old_sha
    evidence = {"as_of": "2026-10-15", "pdf": PDF.name, "pages": 4,
                "source_sha256": sha, "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
                "code_sha256": {str(Path(__file__).relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                str(Path(b.__file__).relative_to(ROOT)): hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest()},
                "environment": {"python": b.platform.python_version(), "reportlab": b.version("reportlab"), "pypdf": b.version("pypdf")},
                "preserved_prior_pdf_sha256": old_sha,
                "new_research_or_training_run": False,
                "neural_network_status": "draft plan, not frozen, implemented or trained",
                "visual_review": "pending final PNG inspection"}
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (HERE / "verification.json").write_text(json.dumps({"pages": 4, "text_and_numeric_checks": "passed", "body_bounds": bounds, "visual_review": "pending"}, indent=2) + "\n")
    print(json.dumps({"pages": 4, "text_and_numeric_checks": "passed", "prior_ml_pdf": "preserved", "body_bounds": bounds}))


if __name__ == "__main__":
    main()
