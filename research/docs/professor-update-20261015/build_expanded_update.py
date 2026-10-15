"""Expand the ML professor update without a fixed page limit.

Inputs: preserved preparation/baseline runs, feature definitions, sample bridge,
HFR matching notes and the untrained network draft. Outputs: expanded PDF,
companion outline, source snapshots and verification records. No new model fit.
Identities: parameters=4*p+9; y=stock-return minus ETF-proxy return;
toy gradients follow the chain rule for e^2 + lambda*(w^2+v^2).
Tier: 2 presentation of source-backed research and labelled teaching examples.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 bundled PDF-runtime Python
    research/docs/professor-update-20261015/build_expanded_update.py
"""

import hashlib
import json
import math
from html import escape
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from reportlab.platypus import SimpleDocTemplate

import build_update as prior

b, ROOT, HERE = prior.b, prior.ROOT, prior.HERE
PDF = HERE / "13D_Machine_Learning_Project_Update_20261015_v2.pdf"
SOURCES = dict(prior.SOURCES)
SOURCES.update({
    "feature-dictionary.json": ROOT / "research/runs/ml-feature-preview/20261012-v1/feature-dictionary.json",
    "sample-bridge.json": ROOT / "research/docs/professor-discussion-20261005/visual-assets/chart-evidence.json",
    "hfr-summary.json": ROOT / "research/runs/hfr-all-managers/20260924-v1/summary.json",
    "hfr-qualifications.md": ROOT / "research/docs/HFR-ALL-MANAGERS-HANDOFF-20260924.md",
    "baseline-validation.json": ROOT / "research/runs/ml-baselines/20261015-v1/validation-notes.json",
})
BRIDGE = json.loads(SOURCES["sample-bridge.json"].read_text())["phase1_sample_bridge"]
HFR = json.loads(SOURCES["hfr-summary.json"].read_text())
BASE, PREP, FEATURE, EVAL = prior.BASE, prior.PREP, prior.FEATURE, prior.EVALUATION
assert BRIDGE["metadata_initial_registry"] - sum(BRIDGE["base_exclusions"].values()) == 4673
assert 4673 - sum(BRIDGE["history_exclusions"].values()) == 4440
assert 4440 - sum(BRIDGE["schedule_exclusions"].values()) - BRIDGE["merged_record_reduction"] == 2107
assert HFR["snapshot_count"] == 35 and HFR["matched_firm_ids"] == 180

# Hand-calculated, invented one-hidden-neuron example, not the proposed fit.
TOY = {"x": 2.0, "w": 0.5, "b": 0.0, "v": 0.1, "c": 0.0, "y": 0.2, "lambda": 0.01}
TOY["z"] = TOY["w"] * TOY["x"] + TOY["b"]
TOY["h"] = max(0.0, TOY["z"])
TOY["prediction"] = TOY["v"] * TOY["h"] + TOY["c"]
TOY["error"] = TOY["prediction"] - TOY["y"]
TOY["loss"] = TOY["error"] ** 2 + TOY["lambda"] * (TOY["w"] ** 2 + TOY["v"] ** 2)
TOY["gradients"] = {
    "v": 2 * TOY["error"] * TOY["h"] + 2 * TOY["lambda"] * TOY["v"],
    "c": 2 * TOY["error"],
    "w": 2 * TOY["error"] * TOY["v"] * TOY["x"] + 2 * TOY["lambda"] * TOY["w"],
    "b": 2 * TOY["error"] * TOY["v"],
}
assert TOY["z"] == 1 and TOY["prediction"] == 0.1
assert math.isclose(TOY["loss"], 0.0126, abs_tol=1e-14)
assert all(math.isclose(TOY["gradients"][key], value, abs_tol=1e-14)
           for key, value in {"v": -0.198, "c": -0.2, "w": -0.03, "b": -0.02}.items())
TOY["illustrative_gradient_descent_rate"] = 0.1
TOY["after_step"] = {key: TOY[key] - 0.1 * value for key, value in TOY["gradients"].items()}
assert math.isclose(TOY["after_step"]["w"], 0.503) and math.isclose(TOY["after_step"]["v"], 0.1198)
TOY["after_prediction"] = TOY["after_step"]["v"] * max(0, TOY["after_step"]["w"] * TOY["x"] + TOY["after_step"]["b"]) + TOY["after_step"]["c"]
assert math.isclose(TOY["after_prediction"], 0.1407584, abs_tol=1e-12)

SECTIONS = []


def section(s, title):
    SECTIONS.append(title)
    b.page(s, title)


def p(s, text, kind="body"):
    b.paragraph(s, text, kind)


def table(s, rows, widths, padding=4):
    b.table(s, rows, widths, padding=padding)


def full_story():
    SECTIONS.clear()
    s = []
    SECTIONS.append("Project summary and current status")
    p(s, "Machine learning for 13D investment selection", "title")
    p(s, "Advanced Machine Learning | Expanded project update | 15 October 2026", "meta")
    p(s, "<b>Research question:</b> can supervised learning improve predictions of post-13D benchmark-relative stock returns, and does separately validated LLM extraction of ownership relationships and stated intentions improve the same models?")
    p(s, "The central class deliverable is a small feedforward neural network compared with simple prediction references. The project tests an investment-data hypothesis; positive alpha is not assumed. LLM extraction is a later source of candidate ML inputs.")
    s.append(b.ProcessStrip([("Data and baselines", "completed and checked", False), ("Small neural network", "draft; not trained", True), ("LLM feature additions", "planned validation", True)], height=62))
    b.heading(s, "Completed work and the first result")
    table(s, [
        ["Stage", "Evidence and meaning"],
        ["Factual preparation", "75,631-record archive; 15,813 initial candidates processed for source-backed facts and prior histories. These are filing counts, not independent investments."],
        ["Current feature table", "667 covered initial-event candidates with ten structured fields and separate targets, metadata and source evidence."],
        ["Chronological inputs", "Training-only transformation states for forecast years 2021-2023; 118, 254 and 365 matured training events respectively."],
        ["First predictions", "Training-mean, zero-excess and fixed-ridge comparisons evaluated on the same 302 later entries. Ridge does not improve reference RMSE in any of the three years."],
    ], [135, 397])
    rows = [["Method", "Later n", "RMSE (pp)", "MAE (pp)"]]
    for model, name in (("training_mean", "Training mean"), ("zero_excess", "Zero excess"), ("ridge", "Fixed ridge")):
        result = BASE["pooled"][model]
        rows.append([name, str(result["n"]), f"{100 * result['rmse']:.2f}", f"{100 * result['mae']:.2f}"])
    table(s, rows, [218, 70, 122, 122])
    p(s, "These numbers are <b>prediction errors in percentage points</b>, not investment returns. They describe the existing covered development sample. The proposed network has one hidden layer of four ReLU neurons and a linear output, with 213-285 parameters depending on input encoding.")
    p(s, "<b>Current boundary:</b> the neural plan is not frozen, implemented or trained. No LLM extraction or incremental LLM result has been produced. Previously examined outcomes remain development history; no untouched final test or after-cost alpha is claimed.", "small")

    section(s, "Data and the unit of observation")
    p(s, "A model observation is an eligible initial-disclosure event linked to the correct historical stock, a delayed entry date and a subsequent return window. It is not necessarily a validated independent activist campaign. Amendments can supply prior context or separately timed update observations; future amendments cannot enter an initial-event row.")
    b.heading(s, "Two preparation paths, with different purposes")
    p(s, "The source-audited archive has 75,631 filing records accepted in 2013-September 2026. A separate factual-staging selection processed 15,813 initial candidates from 2013-2025. The historical return path below starts from an older metadata initial registry; it does not pass sequentially through the 15,813 staging count. [D1-D2]")
    table(s, [
        ["Return-sample path", "Rule or coverage change"],
        ["17,795 metadata initial records", "Older registry classification, distinct from the source-audited initial count."],
        ["4,673 screened records", "2018-2025 entry window, human-review exclusions, standalone/source/security and basic trading checks."],
        ["4,440 first-pair records", "Remove 233 prior investor-issuer history records; first observed in this archive is not necessarily first ever."],
        ["2,107 two-year scheduled events", "Remove 1,995 for issuer overlap, multiple securities or insufficient calendar; same-entry/issuer merges reduce records by 338."],
        ["694 calculable common labels", "712 assigned benchmarks less 18 return refusals. Another 1,395 scheduled events lack the required benchmark assignment."],
        ["667 single-filing feature rows", "Defer 27 merged events until a feature-aggregation rule is defined. All 667 join to prepared facts."],
    ], [169, 363])
    table(s, [
        ["Diagnostic investor group", "Panel n", "Later evaluation n"],
        ["Focused activist candidates", "55", "18"],
        ["Other Event-Driven candidates", "12", "4"],
        ["Other HFR candidates", "44", "25"],
        ["Other / unresolved", "556", "255"],
        ["Total, disjoint groups", "667", "302"],
    ], [274, 112, 146])
    p(s, "HFR matching uses 35 historical supplied snapshots and exact normalized firm/fund-name rules, plus seven fixed activist supplements. The 180 matched HFR firm IDs are candidate links, not validated economic managers. Strategy offerings do not establish intent in each filing. Snapshot delivery dates are unverified availability proxies; unmatched does not mean passive or non-hedge-fund. HFR labels remain diagnostic, not model inputs. [D3]", "small")
    p(s, "The inherited issuer non-overlap rule came from portfolio following. A broader ML panel that retains overlaps is a possible later design revision, not a change implemented in this experiment. Missing labels stay missing; broader archive coverage cannot be turned automatically into supervised examples.", "small")

    section(s, "Inputs, source limitations and preprocessing")
    p(s, "Use ten deterministic candidate fields. Each has an explicit construction rule and source trail. They describe observable context, reported ownership or disclosure activity; none is a verified measure of manager skill or a guarantee of source completeness. [D4]")
    fields = [
        ("Snapshot security size", "snapshot_security_market_cap_usd", "Dated CRSP security-level market capitalization; dlycap times 1,000."),
        ("Industry", "pre_disclosure_industry_sic2", "Two-digit SIC from a pre-disclosure observation; categorical, not a numerical score."),
        ("Reporting-person count", "parsed_reporting_person_count", "Parsed cover-page reporting persons; not independent investors."),
        ("Reported percentage", "reported_ownership_pct_max", "Largest valid percentage for the uniquely matched security; never sum overlapping holdings."),
        ("Percentage coverage", "ownership_pct_valid_fraction", "Valid percentages divided by extracted rows for that security; no rows means missing."),
        ("Event-to-filing lag", "filing_event_lag_calendar_days", "Filing date minus cover-page event date; not a legal deadline assessment."),
        ("Header reporter count", "header_reporter_count", "Distinct header CIKs; not validated economic managers."),
        ("Prior submission count", "prior_header_submission_count_max", "Maximum strictly prior submission count among header CIKs, not their sum."),
        ("Prior other issuers", "prior_header_other_issuer_count_max", "Maximum strictly prior other-issuer count among header CIKs."),
        ("Issuer's prior reporters", "prior_issuer_other_reporter_count", "Strictly prior reporter CIKs outside the current group; no continuing-position claim."),
    ]
    table(s, [["Candidate field", "Construction / interpretation", "Present / 667"],
              *[[label, description, str(FEATURE["feature_coverage"][key]["present"])] for label, key, description in fields]], [144, 288, 100])
    p(s, "Ownership summaries are missing in 110 rows: 89 have no present parsed percentage, seven have no extracted ownership rows for the matched security, and 14 have unresolved security attribution. These are mechanical gap categories, not semantic review. Filling missing values does not make ownership correct.", "small")
    b.heading(s, "Transformations learned from training inputs only")
    p(s, "Apply log(1+x) to declared size/count/lag fields; fill missing numerical inputs with observed training medians and preserve missing flags; scale by training means and population standard deviations; one-hot encode training industry categories; remove training-constant columns. Reuse the saved settings later. Unknown later industries use an all-zero category vector and are flagged. [D5]")
    p(s, "Ten original fields become 51, 63 or 69 retained columns across the three folds. In 2023, 58 industry columns account for most of the expansion. Raw IDs, future returns, exit dates, later amendments and retrospective investor classifications are excluded from X. Liquidity, volatility, momentum and fundamentals are not assembled here.", "small")
    p(s, "Hashes, citations, joins and dates have been checked; semantic extraction, original vendor publication timing and economic manager identities remain uncertified. Disclosure history is restricted to the supplied archive beginning in 2013.", "small")

    section(s, "Prediction target and completed baseline experiment")
    p(s, "The target y is the 504-exchange-session cumulative stock total return minus the assigned historical Russell size-segment ETF-proxy return. Entry is the opening of the second exchange session after public acceptance; entry counts as session one. A 30% stock return versus a 20% benchmark gives y = 0.10, or +10 percentage points. It is neither a probability nor annualized alpha. [D6]")
    table(s, [
        ["Rule", "Frozen baseline specification"],
        ["Training mean", "Predict the mean of completed earlier targets for every later event."],
        ["Zero excess", "Predict zero stock-minus-benchmark return for every event."],
        ["Ridge regression", "Minimize mean((y - b - X beta)^2) + lambda * sum(beta^2), with lambda = 1 and an unpenalized intercept. No tuning."],
        ["Timing", "Fit at January 1 using only entries and label-end dates strictly before that cutoff. Score that year's later entries using eventual outcomes."],
    ], [133, 399])
    table(s, [["Forecast year", "Training n", "Later n", "Mean RMSE (pp)", "Ridge RMSE (pp)", "Ridge rank"],
              *[[str(row["prediction_year"]), str(row["training_events"]), str(row["later_events"]),
                 f"{100 * EVAL['by_prediction_year'][str(row['prediction_year'])]['training_mean']['rmse']:.2f}",
                 f"{100 * EVAL['by_prediction_year'][str(row['prediction_year'])]['ridge']['rmse']:.2f}",
                 f"{EVAL['by_prediction_year'][str(row['prediction_year'])]['ridge']['spearman']:.3f}"] for row in PREP["folds"]]], [90, 76, 67, 109, 109, 81])
    b.heading(s, "How the comparisons are scored")
    p(s, "RMSE is the square root of mean squared error and gives large misses greater influence. MAE is mean absolute error. Errors are reported in percentage points. Spearman compares prediction and target ranks within each year; constant predictions have no defined within-year rank correlation. Pooled RMSE is calculated from all 302 squared errors, not by averaging yearly RMSE values.")
    p(s, "Fixed ridge's pooled RMSE is 93.68 pp versus 89.90 for the training mean and 87.08 for zero excess. Its later-year rank correlations are negative in all three years. This particular fixed specification has not demonstrated predictive improvement; it does not settle the value of other penalties, nonlinear methods or additional information. [D7]")
    p(s, "The largest frozen training target is about +2,960 pp and reconciles to its stored stock-minus-benchmark return arithmetic. Large target tails can dominate squared-error fitting, but this is not a demonstrated causal explanation of the model's failure. No target trimming or outcome-driven exclusions were introduced.")
    b.heading(s, "Verification and investment interpretation")
    p(s, "The baseline's 13 calculation artifacts replay exactly. Scalar checks reconcile 667 original target subtractions, 302 forecasts, 906 exported event/model errors and ridge first-order conditions. The offline suite passed 250 tests, with one network test deselected; new code passes lint while existing repository-wide findings remain. These checks validate the stated calculations, not an investable edge. [D8]")
    p(s, "A return forecast is distinct from a policy deciding whether to invest, when to enter, how long to hold and how much to allocate. Those decisions require explicit costs, risk and capital constraints. No funded account is evaluated in this ML checkpoint.", "small")

    section(s, "Proposed network and learned activation boundaries")
    p(s, "Use one hidden layer of four fully connected ReLU neurons, followed by one linear output. Each hidden neuron receives all prepared inputs and learns its own weights and bias. Width is four; depth is one hidden layer, followed by an output layer. The output remains linear to allow negative as well as positive benchmark-relative forecasts.")
    s.append(prior.Network())
    table(s, [["Forecast year", "Network", "Parameters", "Training n", "Later n"],
              *[[str(row["prediction_year"]), f"{row['encoded_input_columns']} -> 4 -> 1", str(4 * row["encoded_input_columns"] + 9), str(row["training_events"]), str(row["later_events"])] for row in PREP["folds"]]], [103, 148, 91, 94, 96])
    p(s, "There are 4p input weights, four hidden biases, four output weights and one output bias: 4p + 9 parameters. Four neurons is a bounded first design, not an optimized width. Even the 2021 model has 213 parameters for 118 training examples. Regularization and evaluation are essential; capacity is not evidence of robustness.")
    b.heading(s, "What the nonlinear layer changes")
    p(s, "For hidden neuron j: z_j = sum_k(W_kj * x_k) + b_j; h_j = max(0, z_j). The return forecast is yhat = c + sum_j(v_j * h_j). W and b define the hidden features; v and c combine them into the forecast. Training learns both levels jointly. [M1]")
    p(s, "Without nonlinear activation, successive affine layers collapse to another affine prediction rule. ReLU introduces bends. Each unit has one activation boundary in the inputs it receives; weights and bias can move it during training. Multiple units can contribute different boundaries and responses.")
    p(s, "Ridge or lasso can also use nonlinear terms if ratios, products or thresholds are supplied as engineered inputs. The network's distinguishing feature here is learning hidden combinations and their output weights jointly. It does not automatically create more reliable predictors or require a higher-dimensional hidden representation.", "small")
    p(s, "<b>Invented illustration:</b> h1 = max(0, ownership - 8), h2 = max(0, ownership - 12), and forecast = -2 + 2h1 - 2h2 (pp). The response is flat below 8%, rising between 8% and 12%, and flat above 12%. These thresholds are teaching assumptions, not discovered predictors or investment rules.", "small")
    p(s, "Individual neurons need not correspond to stable or causal financial concepts. They are learned candidate features whose joint predictive value must be evaluated. A more flexible function can capture signal or fit noise; current sample sizes do not justify assuming the former.", "small")

    section(s, "Forward pass, loss and backpropagation")
    p(s, "A forward pass transforms X into hidden signals and a prediction. Loss compares that prediction with y. Backpropagation applies the chain rule to calculate how each parameter changes the loss; an optimizer then uses those derivatives to update parameters. These are distinct operations. Automatic differentiation is the proposed implementation approach, not an already completed fit. [M4]")
    b.heading(s, "Proposed objective and derivative structure")
    p(s, "L = (1/n) * sum_i((yhat_i - y_i)^2) + 0.01 * (sum(W^2) + sum(v^2)). Biases are unpenalized. The target remains in decimal return-difference units; numerical input scaling is inherited from checkpoint 2. The penalty is added once to mean error, not divided by n again. [M5]")
    table(s, [
        ["Parameter", "Single-example derivative; e = yhat - y, lambda = 0.01"],
        ["Output weight v_j", "2 * e * h_j + 2 * lambda * v_j"],
        ["Output bias c", "2 * e"],
        ["Hidden error delta_j", "2 * e * v_j * I(z_j > 0)"],
        ["Hidden weight W_kj", "delta_j * x_k + 2 * lambda * W_kj"],
        ["Hidden bias b_j", "delta_j"],
    ], [150, 382])
    p(s, "For a batch, average the data-loss derivatives over its n events, then add each weight's L2 derivative once. ReLU passes a data-loss derivative when z is positive; it blocks that path when z is negative. At zero, the implementation must specify its convention. Gradient checks should use points away from the kink. L2 still acts on weights even for inactive units.", "small")
    b.heading(s, "Invented one-hidden-neuron calculation")
    p(s, "This reduced example illustrates the calculus, not the four-neuron experiment or a historical filing. Let x = 2, w = 0.5, hidden bias b = 0, output weight v = 0.1, output bias c = 0 and target y = 0.2. Then z = 1, h = 1, yhat = 0.1 and e = -0.1. Squared error is 0.01; the penalty is 0.0026; total loss is 0.0126.")
    table(s, [
        ["Parameter", "Derivative", "After an illustrative gradient step"],
        ["Hidden weight w", "-0.030", "0.503"],
        ["Hidden bias b", "-0.020", "0.002"],
        ["Output weight v", "-0.198", "0.1198"],
        ["Output bias c", "-0.200", "0.020"],
    ], [150, 120, 262])
    p(s, "The table uses theta_new = theta - 0.1 * derivative to make a plain gradient-descent step visible. The next prediction is 0.1407584, closer to the invented 0.2 target. This illustration uses neither the proposed Adam update nor its 0.001 learning rate. It is a hand-checked teaching calculation, not evidence that real-data training converges.", "small")

    section(s, "Initialization, optimization and random starts")
    p(s, "The following settings are a draft first reference. They have not been tuned or validated as optimal. The experiment, software versions and tests will be frozen before a neural fit. The fixed ridge result remains unchanged.")
    table(s, [
        ["Component", "Proposed setting and rationale"],
        ["Hidden weights and biases", "Independent He-normal draws with variance 2/p; biases zero. Independent draws break identical starts among hidden neurons; the scale accounts for input count. [M2]"],
        ["Output weights and bias", "Independent normal weights with SD 0.01; bias equal to the matured training-target mean. Random initial predictions are centered on the naive reference."],
        ["Regularization", "Explicit L2 coefficient 0.01 on weights in both layers; biases unpenalized. No additional optimizer weight decay."],
        ["Adam", "Learning rate 0.001; beta values 0.9 and 0.999; epsilon 1e-8. Adam uses running gradient information to calculate updates. [M3]"],
        ["Training batch", "All matured training events in each update. No random data split or mini-batch reshuffling is proposed for this first run."],
        ["Update budget", "500 full-batch updates = 500 epochs. Save training loss, parameter/gradient diagnostics and inactive-neuron counts. Fixed duration is not a convergence guarantee."],
        ["Random seeds", "11, 23, 37, 51 and 71, declared in advance. Report every run, not only the best-performing start."],
        ["Primary neural prediction", "Equal-weight mean of the five saved predictions: a predeclared ensemble. Also show individual-run metrics and variation."],
        ["Additional flexibility", "No dropout, batch normalization, width/depth search or selection of stopping time from later-year performance in the first run."],
    ], [137, 395])
    b.heading(s, "Checks before fitting and handling failures")
    p(s, "Pin synthetic forward predictions, losses and gradient steps; compare analytic/automatic derivatives with finite differences away from ReLU kinks; check dimensions, parameter counts, source hashes and dated joins. Confirm preprocessing matches saved states exactly and that only matured training labels reach the optimizer.")
    p(s, "The proposed framework is PyTorch automatic differentiation. It is not yet installed in this project environment; dependency setup and version pinning are implementation work. The real-data network and its gradient-test suite have not been implemented. The labelled toy arithmetic and diagrams do not count as a fitted research model.")
    p(s, "If a run is nonfinite or fails implementation checks, preserve the failure and create a separately identified correction. Record unfavorable starts and inactive units rather than selecting a successful-looking seed. Architecture, penalty and learning-rate changes require a new specified experiment; later-year errors must not choose them.", "small")
    p(s, "A tuned extension would require valid chronological inner folds with completed earlier labels and training-only preprocessing. Ordinary row-order splitting, shuffled validation or automatic random early stopping would not establish historical availability. The first run therefore uses a fixed untuned budget.", "small")

    section(s, "Evaluation, LLM additions and next deliverables")
    b.heading(s, "Keep the comparison aligned")
    p(s, "Reuse the same target, entry convention, prepared inputs, inherited event schedule and 302 later entries as checkpoint 3. For each forecast year, require both entry and label-end dates strictly before January 1 for training. Later events never reset imputation, scales, industry categories or column selection. Save all neural predictions before scoring their eventual outcomes.")
    p(s, "Report pooled event-weighted RMSE/MAE, within-year Spearman correlations, every forecast year, all five seeds and their declared ensemble. Report training diagnostics, identity overlap, missingness and subgroup coverage. Do not pool ranks across years or attach IID confidence intervals to dependent outcomes. A fixed neural-versus-ridge comparison does not isolate architecture alone because parameterization and penalties differ.")
    b.heading(s, "Three information sets, after separate validation")
    table(s, [
        ["Experiment", "Inputs", "Question"],
        ["A | deterministic", "Current prepared facts and dated context", "Do the supervised methods improve prediction over the simple references?"],
        ["B | assisted attribution", "A plus validated LLM ownership/identity interpretation", "Does improved attribution or ownership structure add information?"],
        ["C | stated intentions", "B plus validated Item 4 objectives", "Do disclosed plans improve the same models beyond attribution?"],
    ], [110, 223, 199])
    p(s, "Human source-based development references precede model answers on eligible cases. Preserve supporting passages, accession/actor/company attribution, model and prompt versions, uncertainty and abstentions. Run a bounded pilot before broad extraction. Compare common observations and report coverage changes separately.")
    p(s, "Repeated LLM interpretation measures extraction stability, not correctness or calibrated truth probabilities. Retain empirical uncertainty; it is separate from variability across neural starting seeds and from uncertainty in future returns. Restrict extraction to information available at the event. Modern LLM pretraining may contain later knowledge, so source grounding alone cannot certify an exposure-clean historical test.")
    b.heading(s, "Remaining work and class-project outcome")
    table(s, [
        ["Next stage", "Deliverable and status"],
        ["Checkpoint 4", "Complete the forward/backward lesson and implementation checks; freeze and fit the small network; report results even if negative."],
        ["Further comparisons", "Gradient-boosted trees remain planned. Any tuned or robust-loss extension needs its own declared design and exposure limits."],
        ["Checkpoint 5", "Validate a bounded ownership/intent extraction pilot, then compare A/B/C under comparable models, rows and evaluation."],
        ["Checkpoint 6", "Translate forecasts into declared selection/timing/horizon/sizing policies with costs, cash and capacity constraints. Existing Aratana accounting affects relevant portfolio work."],
    ], [140, 392])
    p(s, "Success for the ML class is a credible, reproducible comparison of methods and information sets, with clearly stated limitations. A new independent two-year prospective outcome cannot be completed within the course timeline; the present work should be reported honestly as development research.", "small")

    section(s, "Evidence, reproducibility and method references")
    p(s, "This update separates completed computations, proposed design choices and invented teaching examples. Frozen research inputs and earlier reports remain preserved. The companion index links exact source snapshots and their live project locations.")
    table(s, [
        ["ID", "Dated evidence", "What it supports"],
        ["D1", "Factual staging, 24 September", "15,813 processed initial candidates and the 75,631-record archive reconciliation."],
        ["D2", "Source-audited sample bridge, October 5 brief", "Separate metadata-to-return scheduling cuts and event-merging reductions."],
        ["D3", "HFR all-manager run and handoff, 24 September", "35 supplied snapshots, 180 firm-ID candidates and historical matching qualifications."],
        ["D4", "Feature preview and dictionary, 12 October", "667 aligned feature/target/metadata rows, field construction, coverage and source limitations."],
        ["D5", "Preprocessing run, 12 October", "118/254/365 training events, 106/110/86 later entries and 51/63/69 encoded columns."],
        ["D6", "ml-baselines-v1, frozen 15 October", "Target, matured-label cutoffs, ridge objective and identical scoring conventions."],
        ["D7", "Baseline summary and evaluation, 15 October", "Saved predictions, all-year comparisons, group coverage and target/error diagnostics."],
        ["D8", "Baseline verification and validation notes", "Exact offline replay, scalar arithmetic checks and local test/lint results; no remote CI claim."],
        ["D9", "Proposed network plan, 15 October", "Untrained p -> 4 -> 1 architecture, draft training settings and learning sequence."],
    ], [37, 216, 279])
    b.heading(s, "Primary method documentation")
    refs = [
        ("M1", "ReLU", "https://docs.pytorch.org/docs/2.14/generated/torch.nn.ReLU.html"),
        ("M2", "He initialization", "https://docs.pytorch.org/docs/2.14/nn.init.html#torch.nn.init.kaiming_normal_"),
        ("M3", "Adam", "https://docs.pytorch.org/docs/2.14/generated/torch.optim.Adam.html"),
        ("M4", "Autograd and the chain rule", "https://docs.pytorch.org/docs/2.14/notes/autograd.html"),
        ("M5", "Mean squared error", "https://docs.pytorch.org/docs/2.14/generated/torch.nn.MSELoss.html"),
    ]
    for key, label, url in refs:
        p(s, f'{key}: <link href="{url}" color="#146d76">PyTorch documentation: {label}</link>.', "small")
    p(s, "Method documentation explains the operations; it does not validate the proposed hyperparameters, prove predictive value or establish historical information availability. The teaching calculation uses plain gradient descent for visibility; the proposed real optimizer is Adam.", "small")
    b.heading(s, "Reproducibility and release status")
    p(s, "The baseline calculations remain frozen and support exact replay in their recorded environment. This expanded report adds no neural fit, LLM extraction, return recomputation, policy optimization or real trading. Its source fingerprints, toy arithmetic and final page rendering are checked separately from research validation. Existing professor PDFs and human-review records are unchanged.")
    p(s, "AI-assisted code, document preparation and explanation. The report has no fixed page cap; section breaks follow the subject matter and allow readable tables and equations.", "small")
    return s


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(b.RULE)
    canvas.line(40, 29, 572, 29)
    canvas.setFont("Brief", 8)
    canvas.setFillColor(b.GRAY)
    canvas.drawRightString(572, 17, str(doc.page))
    canvas.restoreState()


def main():
    preserved = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
                 (prior.PDF, HERE.parent / "professor-discussion-20261013/13D_Machine_Learning_Brief_20261013.pdf")}
    doc = SimpleDocTemplate(str(PDF), pagesize=b.letter, leftMargin=34, rightMargin=34, topMargin=36, bottomMargin=41,
                           title="13D Machine Learning Project Update - Expanded", author="Jeff Lu")
    doc.build(full_story(), onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(PDF)
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    for value in ("93.68", "89.90", "87.08", "17,795", "4,673", "4,440", "2,107", "694", "667", "302", "213", "261", "285", "0.0126", "0.1407584"):
        assert value in text, value
    assert "not frozen, implemented or trained" in text
    assert len(reader.pages) > 4
    bounds = []
    with pdfplumber.open(PDF) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            chars = [char for char in page.chars if char["text"].strip() and char["top"] < 750]
            assert min(char["x0"] for char in chars) >= 38, number
            assert max(char["x1"] for char in chars) <= 575, number
            assert max(char["bottom"] for char in chars) < 750, number
            bounds.append({"page": number, "lowest_body_from_top": round(max(char["bottom"] for char in chars), 2)})
    snapshots = HERE / "source-snapshots-v2"
    snapshots.mkdir(exist_ok=True)
    sources = {}
    links = []
    for name, path in SOURCES.items():
        payload = path.read_bytes()
        (snapshots / name).write_bytes(payload)
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest()
        links.append(f'<li><a href="source-snapshots-v2/{name}">{escape(name)} snapshot</a> &middot; <a href="../../../{path.relative_to(ROOT)}">live source</a></li>')
    for name, sha in preserved.items():
        path = prior.PDF if name == prior.PDF.name else HERE.parent / "professor-discussion-20261013" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
    contents = "".join(f"<li>{escape(title)}</li>" for title in SECTIONS)
    (HERE / "index-v2.html").write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expanded 13D ML professor update</title><style>body{{font:17px/1.65 system-ui;color:#19374a;background:#f4f6f8}}main{{max-width:940px;margin:30px auto;padding:26px;background:white}}a{{color:#146d76}}h2{{color:#146d76}}</style></head><body><main><h1>Expanded 13D Machine Learning project update</h1><p>15 October 2026 | {len(reader.pages)} pages | No fixed page cap</p><p><a href="{PDF.name}">Open the expanded professor update</a> &middot; <a href="{prior.PDF.name}">Preserved four-page version</a></p><p>The summary leads; detailed data construction, features, baseline results, network equations, a labelled forward/backward illustration, initialization and optimization, evaluation and LLM additions follow. The network remains a draft, not a trained model.</p><h2>Contents</h2><ol>{contents}</ol><h2>Professor discussion prompts</h2><ol><li>Does the observation construction and broader covered universe support the proposed prediction task?</li><li>Is the proposed four-neuron model an appropriate first neural comparison given the sample size and sparse industries?</li><li>Should a separately declared robust-loss comparison accompany the fixed squared-error experiment?</li><li>What validation and reporting are expected given prior exposure to these historical outcomes and limited matured inner-fold history?</li></ol><h2>Source snapshots and live evidence</h2><ul>{''.join(links)}</ul><p><a href="evidence-v2.json">Build evidence</a> &middot; <a href="verification-v2.json">Final verification</a> &middot; <a href="toy-calculation-v2.json">Invented teaching arithmetic</a></p><p><a href="../../../START-HERE.html">Project home</a> &middot; <a href="../ml-checkpoints.html">Learning checkpoints</a> &middot; <a href="index.html">Earlier speaking notes</a></p><p>No document has been sent to the professor. This expansion changes no frozen research result, protocol or human reference.</p></main></body></html>''', encoding="utf-8")
    (HERE / "toy-calculation-v2.json").write_text(json.dumps({"status": "invented teaching example; no model fit", **TOY}, indent=2) + "\n")
    evidence = {"date": "2026-10-15", "pdf": PDF.name, "pages": len(reader.pages), "fixed_page_cap": None,
                "sections": SECTIONS, "source_sha256": sources, "preserved_pdf_sha256": preserved,
                "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
                "code_sha256": {str(Path(__file__).relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                str(Path(prior.__file__).relative_to(ROOT)): hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest(),
                                str(Path(b.__file__).relative_to(ROOT)): hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest()},
                "neural_network_fitted": False, "new_llm_or_return_run": False,
                "teaching_arithmetic_checked": True, "visual_review": "pending final page inspection"}
    (HERE / "evidence-v2.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (HERE / "verification-v2.json").write_text(json.dumps({"pages": len(reader.pages), "body_bounds": bounds, "text_and_arithmetic_checks": "passed", "visual_review": "pending"}, indent=2) + "\n")
    print(json.dumps({"pages": len(reader.pages), "sections": len(SECTIONS), "fixed_page_cap": None, "bounds": bounds, "preserved_pdfs": "unchanged"}))


if __name__ == "__main__":
    main()
