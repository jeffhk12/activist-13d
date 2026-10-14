"""Build two four-page professor briefs from preserved 13D project evidence.

Inputs: frozen following results and October 12 feature/preprocessing summaries.
Outputs: ML and Private Markets Modeling PDFs, speaking notes, evidence/QA records.
Identity: cohort counts sum to 667; sample bridge is 2107 -> 694 -> 667;
illustrative scenario EV=sum(p*terminal wealth), PV=EV/(1+r)^years.
Tier: 2 presentation of preserved evidence; no new return or predictive estimator.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 PDF-runtime Python build_briefs.py.
Preserves all older briefs and research outputs. Requires subsequent rendered QA.
"""

import hashlib
import json
import platform
from html import escape
from importlib.metadata import version
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
FILES = {
    "E1 historical baseline": PROJECT / "research/runs/phase1-baseline/20260924-long-horizon-analysis-v1/summary.json",
    "E2 factual staging": PROJECT / "research/runs/phase2-overnight/20260924-full-v1/progress.json",
    "E3 ML sample feasibility": PROJECT / "research/runs/ml-feasibility/20261012-v1/summary.json",
    "E4 feature preview": PROJECT / "research/runs/ml-feature-preview/20261012-v1/summary.json",
    "E5 preprocessing": PROJECT / "research/runs/ml-preprocessing/20261012-v1/summary.json",
    "feature definitions": PROJECT / "research/protocol/ml-feature-preview-v1.json",
    "preprocessing protocol": PROJECT / "research/protocol/ml-preprocessing-v1.json",
    "baseline conventions": PROJECT / "research/protocol/phase1-long-horizon-v1.md",
    "historical qualifications": PROJECT / "research/docs/PHASE1-FINAL-CONCLUSION-20260924.md",
    "learning checkpoints": PROJECT / "research/docs/ml-checkpoints.html",
}
SOURCE_HASHES = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in FILES.items()}
baseline = json.loads(FILES["E1 historical baseline"].read_text())["first_observed"]["504"]["russell"]["focused"]
staging = json.loads(FILES["E2 factual staging"].read_text())
feasibility = json.loads(FILES["E3 ML sample feasibility"].read_text())
preview = json.loads(FILES["E4 feature preview"].read_text())
prep = json.loads(FILES["E5 preprocessing"].read_text())
two_year = next(row for row in feasibility["horizons"] if row["horizon_sessions"] == 504)
assert staging["processed"] == 15813 and staging["failed"] == 0
assert staging["selected_initial_filings"] + sum(staging["selection_exclusions"].values()) == 75631
assert (two_year["scheduled_events"], two_year["valid_russell_labels"], two_year["single_filing_prepared_candidates"]) == (2107, 694, 667)
assert preview["joined_events"] == 667 and sum(preview["cohort_counts"].values()) == 667
assert preview["cohort_counts"] == {"focused": 55, "other_event_driven": 12, "new_other_hfr": 44, "other_unresolved": 556}
assert preview["feature_coverage"]["reported_ownership_pct_max"]["present"] == 557
assert [(f["training_events"], f["later_events"], f["encoded_input_columns"]) for f in prep["folds"]] == [(118, 106, 51), (254, 110, 63), (365, 86, 69)]
assert prep["gap_reason_counts"] == {"parser_has_no_present_percentage_in_extracted_rows": 89, "no_extracted_ownership_rows_for_matched_security": 7, "unresolved_security_attribution": 14}
assert not prep["predictive_model_fitted"] and not prep["numerical_target_values_read"]
assert baseline["calculated"] == 56
assert abs(baseline["mean_excess"] * 100 - 8.66) < 0.005
assert abs(baseline["median_excess"] * 100 + 14.91) < 0.005

SCENARIOS = [("Base", .50, 120), ("Upside", .25, 160), ("Downside", .25, 70)]
assert sum(p for _, p, _ in SCENARIOS) == 1
EV = sum(p * wealth for _, p, wealth in SCENARIOS)
PV = EV / 1.1**2
assert EV == 117.5 and abs(PV - 97.1074380165289) < 1e-10

NAVY = colors.HexColor("#19374a")
TEAL = colors.HexColor("#146d76")
GRAY = colors.HexColor("#576b78")
PALE = colors.HexColor("#edf4f6")
RULE = colors.HexColor("#d6e2e7")
AMBER = colors.HexColor("#a56838")
WIDTH = 532
for name, filename in (("Brief", "Arial.ttf"), ("BriefBold", "Arial Bold.ttf"), ("BriefItalic", "Arial Italic.ttf")):
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + filename))
pdfmetrics.registerFontFamily("Brief", normal="Brief", bold="BriefBold", italic="BriefItalic", boldItalic="BriefBold")
STYLES = {
    "title": ParagraphStyle("title", fontName="BriefBold", fontSize=22, leading=25, textColor=NAVY, spaceAfter=8),
    "page": ParagraphStyle("page", fontName="BriefBold", fontSize=19, leading=22, textColor=NAVY, spaceAfter=8),
    "head": ParagraphStyle("head", fontName="BriefBold", fontSize=11.3, leading=14, textColor=TEAL, spaceBefore=9, spaceAfter=5, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="Brief", fontSize=10.3, leading=13.5, textColor=NAVY, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Brief", fontSize=8.5, leading=11.2, textColor=GRAY, spaceAfter=5),
    "meta": ParagraphStyle("meta", fontName="Brief", fontSize=9, leading=12, textColor=GRAY, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName="Brief", fontSize=9.6, leading=12.1, textColor=NAVY),
    "th": ParagraphStyle("th", fontName="BriefBold", fontSize=9.4, leading=12, textColor=colors.white),
}


class ProcessStrip(Flowable):
    def __init__(self, boxes, height=64):
        super().__init__()
        self.boxes, self.width, self.height = boxes, WIDTH, height

    def draw(self):
        gap = 18
        width = (self.width - gap * (len(self.boxes) - 1)) / len(self.boxes)
        for index, (main, sub, planned) in enumerate(self.boxes):
            x = index * (width + gap)
            self.canv.setFillColor(PALE if not planned else colors.HexColor("#f5f2ec"))
            self.canv.setStrokeColor(RULE)
            self.canv.roundRect(x, 7, width, self.height - 14, 5, fill=1, stroke=1)
            self.canv.setFillColor(TEAL if not planned else AMBER)
            self.canv.setFont("BriefBold", 10.3)
            self.canv.drawCentredString(x + width / 2, self.height - 26, main)
            self.canv.setFillColor(GRAY)
            self.canv.setFont("Brief", 8.3)
            self.canv.drawCentredString(x + width / 2, self.height - 41, sub)
            if index < len(self.boxes) - 1:
                self.canv.setStrokeColor(GRAY)
                self.canv.line(x + width + 3, self.height / 2, x + width + gap - 3, self.height / 2)
                self.canv.line(x + width + gap - 7, self.height / 2 + 3, x + width + gap - 3, self.height / 2)
                self.canv.line(x + width + gap - 7, self.height / 2 - 3, x + width + gap - 3, self.height / 2)


class ScenarioChart(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 114

    def draw(self):
        left, right, bottom, top = 155, 505, 24, 100
        self.canv.setFont("Brief", 8.2)
        self.canv.setStrokeColor(RULE)
        self.canv.setFillColor(GRAY)
        for value in (0, 50, 100, 150):
            x = left + (right - left) * value / 180
            self.canv.line(x, bottom, x, top)
            self.canv.drawCentredString(x, 11, str(value))
        for index, (label, probability, wealth) in enumerate(SCENARIOS):
            y = top - 20 - index * 24
            self.canv.setFillColor(NAVY)
            self.canv.setFont("Brief", 9)
            self.canv.drawString(0, y + 3, f"{label} | assumed {probability:.0%}")
            self.canv.setFillColor(AMBER if label == "Downside" else TEAL)
            self.canv.rect(left, y, (right - left) * wealth / 180, 14, stroke=0, fill=1)
            self.canv.setFillColor(NAVY)
            self.canv.drawString(left + (right - left) * wealth / 180 + 5, y + 3, str(wealth))
        self.canv.setStrokeColor(AMBER)
        self.canv.setDash(3, 3)
        x = left + (right - left) * 100 / 180
        self.canv.line(x, bottom, x, top)
        self.canv.setDash()
        self.canv.setFillColor(GRAY)
        self.canv.setFont("Brief", 8)
        self.canv.drawRightString(WIDTH, 0, "Illustrative terminal wealth; initial investment = 100")


def paragraph(story, text, kind="body"):
    story.append(Paragraph(text, STYLES[kind]))


def heading(story, text):
    paragraph(story, text, "head")


def table(story, rows, widths, padding=5):
    cells = [[Paragraph(str(value), STYLES["th" if i == 0 else "cell"]) for value in row] for i, row in enumerate(rows)]
    item = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1)
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALE, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LINEBELOW", (0, 1), (-1, -1), .4, RULE),
    ]))
    story.extend((item, Spacer(1, 5)))


def page(story, title):
    if story:
        story.append(PageBreak())
    paragraph(story, title, "page")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.line(40, 29, 572, 29)
    canvas.setFont("Brief", 8)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(572, 17, f"{doc.page} / 4")
    canvas.restoreState()


def evidence(story, methods=True):
    heading(story, "Evidence and research status")
    table(story, [
        ["Record", "Supporting evidence"],
        ["E1 | 24 September", "Frozen historical following results and long-horizon trading conventions."],
        ["E2 | 24-25 September", "Completed factual staging and audit: 15,813 initial-filing candidates."],
        ["E3-E5 | 12 October", "Sample feasibility, feature/source joins and train-only preprocessing; exact local replay."],
    ], [122, 410], padding=4)
    if methods:
        paragraph(story, 'M1: <link href="https://scikit-learn.org/stable/modules/neural_networks_supervised.html" color="#146d76">scikit-learn neural-network documentation</link>; M2: <link href="https://scikit-learn.org/stable/modules/cross_validation.html" color="#146d76">chronological validation documentation</link>. Local evidence index accompanies the brief.', "small")
    else:
        paragraph(story, 'D1: Aswath Damodaran, <link href="https://pages.stern.nyu.edu/~adamodar/pdfiles/DSV2/Ch3.pdf" color="#146d76">Probabilistic Valuation: Scenario Analysis, Decision Trees and Simulations</link>, NYU Stern. The numerical illustration uses hypothetical assumptions.', "small")
    paragraph(story, "AI-assisted research tooling and writing. No predictive model, validated intent features or incremental investment result has been produced. Existing human-review records and historical outputs are preserved.", "small")


def ml_story():
    story = []
    paragraph(story, "Machine learning for 13D investment selection", "title")
    paragraph(story, "Advanced Machine Learning | Discussion 13 October 2026 | Evidence through 12 October", "meta")
    paragraph(story, "<b>Research question:</b> can a small neural network predict which initial 13D disclosures lead to stronger subsequent benchmark-relative returns, and does LLM-extracted information improve that prediction?")
    paragraph(story, "<b>Current status:</b> a historical following baseline, a candidate feature table and chronological preprocessing are complete. Predictive fitting is next. The class contribution is a controlled comparison of supervised methods and information sets; a negative result remains informative.")
    story.append(ProcessStrip([("Filing evidence", "completed preparation", False), ("Model inputs", "train-only transforms", False), ("Neural prediction", "central planned method", True), ("Investment policy", "economic evaluation", True)]))
    heading(story, "Central model comparison")
    table(story, [
        ["Method", "Purpose in the experiment"],
        ["Training-mean prediction", "Naive reference: predict the mean outcome available in the training set."],
        ["Regularized regression", "Transparent linear comparison with penalties that limit model flexibility."],
        ["Gradient-boosted trees", "Nonlinear comparison that can capture interactions among inputs."],
        ["Small feedforward neural network", "Central method: learn nonlinear combinations of filing and company inputs. Architecture and tuning budget still to freeze."],
    ], [173, 359])
    heading(story, "Prediction target and investment decisions")
    paragraph(story, "The proposed first target is <b>504-session cumulative stock return minus its assigned historical Russell size-segment ETF-proxy return</b>. An illustrative stock return of 30% versus a 10% proxy gives a target of +20 percentage points. This is regression, not an invest/not-invest label.")
    table(story, [
        ["Decision", "First experiment", "Later extension"],
        ["Whether to invest", "Predict relative return; freeze a selection rule", "Utility- or threshold-based policy"],
        ["When to enter", "Existing delayed-entry convention", "Compare explicit entry delays"],
        ["Holding period", "Two years proposed", "Compare additional horizons"],
        ["Position size", "Existing 5% targets and constraints", "Use return/risk estimates for allocation"],
    ], [105, 220, 207], padding=4)
    paragraph(story, "Historical motivation: simple following has not established an investable edge. Across 56 focused two-year events, mean gross Russell-relative excess is +8.66 points, but median excess is -14.91 and the 95% mean interval spans -17.34 to +40.43. Exploratory 2018-2025 research, not an ML result. [E1]", "small")

    page(story, "Data and the broader modeling sample")
    paragraph(story, "The first model includes the broader eligible, covered 13D universe. Activist candidates are a diagnostic subgroup; an unresolved identity does not establish that a filer is a non-hedge-fund or non-activist investor.")
    heading(story, "Two preparation paths with different units")
    table(story, [
        ["Path", "Completed scope", "Interpretation"],
        ["Filing facts", "75,631 archive records; 15,813 initial-filing candidates processed and audited, 2013-2025", "Facts and prior histories; not 15,813 independent investments. [E2]"],
        ["Return-labelled events", "2,107 scheduled two-year events; 694 calculable stock/proxy labels; 667 single-filing feature joins", "Separate scheduling and coverage checks; entry years 2018-2023, follow-up through 2025. [E3-E4]"],
    ], [104, 232, 196])
    paragraph(story, "The 27 remaining calculable events combine multiple filings and need a feature-aggregation rule. Most of the other scheduled events lack a usable Russell assignment. The covered subset may differ from the excluded population.", "small")
    heading(story, "Disjoint groups inside the 667-event feature table")
    table(story, [
        ["Candidate identity group", "Events", "Use in this experiment"],
        ["Focused activist", "55", "Report subgroup results; membership remains a candidate classification."],
        ["Other Event-Driven", "12", "Same broader input preparation."],
        ["Other HFR", "44", "Same broader input preparation."],
        ["Other / unresolved", "556", "Retain observations and identity uncertainty."],
    ], [164, 57, 311], padding=4)
    heading(story, "Ten source-based candidate fields")
    table(story, [
        ["Information set", "Fields and limits"],
        ["Company context | 2", "Security-level market capitalization from a prior snapshot; pre-disclosure industry."],
        ["Ownership / extraction | 3", "Parsed reporting-person count, largest valid reported percentage, percentage-field coverage. Holdings are not summed."],
        ["Disclosure timing | 1", "Calendar lag between cover event and filing date; not a legal-deadline determination."],
        ["Prior activity | 4", "Header reporter count and strictly prior submission/issuer/reporter histories; CIK proxies, not manager skill."],
    ], [160, 372], padding=4)
    paragraph(story, "557/667 events have an ownership-percentage summary; 110 remain missing, including 14 unresolved security-attribution cases. Current HFR labels and retrospective activist classifications are not model inputs. Liquidity, volatility, momentum and fundamentals remain to be assembled. [E4]", "small")

    page(story, "Chronological preparation and evaluation")
    paragraph(story, "A two-year return label enters training only after its outcome window ends. Each prediction year's preprocessing uses earlier available examples. Future inputs do not reset the fill values, numerical scales or industry vocabulary.")
    heading(story, "Completed development input tables")
    table(story, [["Prediction year", "Earlier training events", "Later events", "Encoded inputs"],
        *[[str(f["prediction_year"]), str(f["training_events"]), str(f["later_events"]), str(f["encoded_input_columns"])] for f in prep["folds"]]], [120, 150, 118, 144])
    paragraph(story, "Training sets overlap and their counts must not be added. Later observations are previously examined development history, not an untouched final holdout. Inner tuning folds still need label-maturity and dependence checks. [E5]", "small")
    heading(story, "What the preprocessing does")
    table(story, [
        ["Method", "Implemented rule"],
        ["Log(1+x)", "Compress the numerical spread of company size and count/lag inputs while preserving zero."],
        ["Median imputation", "Fill missing numerical inputs using observed training values; retain missing flags."],
        ["Standardization", "Subtract the training mean and divide by its population standard deviation."],
        ["Industry encoding", "One binary column per training category; unseen later industries use an all-zero category vector and are recorded."],
        ["Constant-column mask", "Remove columns with no training variation; apply the same saved selection later."],
    ], [136, 396], padding=4)
    paragraph(story, "In the 2023 fold, the missing ownership fill is 8.65%, a computational placeholder rather than a factual estimate. Ten original fields become 69 retained inputs, including 58 industry columns. Seven of 86 later events have unseen industries. These dimensions and sparse categories argue for bounded model capacity. [E5]", "small")
    heading(story, "Proposed evaluation and interpretation")
    table(story, [
        ["Measure", "What it asks"],
        ["Prediction error", "Mean absolute error and root mean squared error versus a training-mean reference."],
        ["Ranking usefulness", "Do higher predictions identify stronger subsequent outcomes? Report rank correlation and subgroup coverage."],
        ["Economic relevance", "Apply a frozen selection rule under comparable entry, benchmark, 5% sizing, capacity, costs and cash conventions."],
    ], [136, 396], padding=4)
    paragraph(story, "Source fingerprints, exact quotations, identifier joins and dates pass local checks; preprocessing replays exactly. These checks do not certify semantic extraction. Historical vendor publication timing is unverified, and corporate-action accounting limits affected portfolio comparisons.", "small")

    page(story, "Neural network and incremental LLM experiments")
    heading(story, "A small neural network is the central planned method")
    story.append(ProcessStrip([("Encoded inputs", "69 columns in 2023 fold", False), ("Small hidden layer", "weights + nonlinear activation", True), ("Predicted excess", "continuous return estimate", True)], height=72))
    paragraph(story, "A feedforward network learns weighted combinations of inputs. A nonlinear activation lets those combinations interact; the output estimates relative return. Freeze architecture, loss, regularization, stopping and a modest tuning budget before results. Report variability across training seeds. [M1]")
    heading(story, "Separate information sets within the same model families")
    table(story, [
        ["Experiment", "Inputs", "Question"],
        ["A | deterministic", "Current structured fields and verified additions", "Can supervised selection improve on the references?"],
        ["B | assisted attribution", "A plus validated LLM ownership/identity interpretation", "Does better attribution improve prediction?"],
        ["C | disclosed intentions", "B plus validated Item 4 objectives", "Do stated plans add information beyond the other inputs?"],
    ], [118, 222, 192], padding=4)
    paragraph(story, "Code deterministically parses, checks citations and replays stored outputs. Fresh LLM interpretation can vary: evaluate a bounded repeated-extraction sample under frozen prompts/settings and retain uncertainty. Agreement measures stability, not correctness or calibrated probability. LLM extraction variability is distinct from network training-seed variability.")
    paragraph(story, "Human development references must precede model answers on eligible review cases; assisted practice remains separate. Compare common samples and equal tuning budgets, report coverage changes, and validate extraction before broad feature augmentation. No validated intent accuracy or incremental result exists yet.", "small")
    heading(story, "Next modeling checkpoints")
    paragraph(story, "<b>1.</b> Freeze the target, available features and outcome-mature evaluation; establish naive and regularized comparisons. <b>2.</b> Fit the small network and boosted-tree comparison with honest chronological development reporting. <b>3.</b> Add a validated, bounded LLM feature experiment, then assess after-cost investment relevance.")
    paragraph(story, "A credible unused final sample requires an exposure audit; otherwise final validation should be prospective. A new two-year prospective result extends beyond the course timeline. No prospective collection has begun.", "small")
    evidence(story)
    return story


def private_story():
    story = []
    paragraph(story, "Modeling value creation after a 13D disclosure", "title")
    paragraph(story, "Private Markets Modeling | Discussion 13 October 2026 | Evidence through 12 October", "meta")
    paragraph(story, "<b>Investment question:</b> can a disclosed investor's ownership, influence and value-creation plan support a credible upside/downside valuation and a disciplined public-equity investment decision?")
    paragraph(story, "The investable asset is a public stock. The connection to private-markets modeling is the treatment of governance, operating improvements, capital allocation, realization timing and exit value. ML can help prioritize opportunities; it must connect to an interpretable economic case.")
    story.append(ProcessStrip([("Disclosed plan", "source facts and evidence", False), ("Value drivers", "operating / financing cases", True), ("Scenario values", "probability and timing", True), ("Investment decision", "entry, horizon and risk", True)]))
    heading(story, "Translate a stated plan into economic drivers")
    table(story, [
        ["Disclosed mechanism", "Modeling implication", "Evidence still required"],
        ["Operational improvement", "Revenue growth, margins and reinvestment change future cash flows", "Baseline financials, execution costs, milestones and achievable assumptions"],
        ["Asset sale / separation", "After-tax proceeds, stranded costs and remaining business value", "Asset economics, transaction feasibility and capital deployment"],
        ["Capital return / financing", "Cash, debt, buybacks and share count alter equity value and risk", "Capacity, covenants, funding terms and share-price assumptions"],
        ["Board / governance change", "Changes the probability and timing of strategy execution", "Voting influence, agreements, company response and decision rights"],
    ], [134, 205, 193])
    heading(story, "Current progress and modeling boundary")
    paragraph(story, "The historical following baseline, a 667-event feature table and chronological input preparation are complete. No issuer-specific cash-flow valuation or calibrated scenario probabilities have been produced. The scenario framework below is the next proposed economic layer.")
    paragraph(story, "A disclosed stake does not establish control, and a stated objective does not establish implementation. Related parties may report the same shares. Manager reputation, HFR performance and prior filing activity are candidate context, not validated probabilities of successful value creation.", "small")

    page(story, "Evidence available and what it can support")
    heading(story, "A broad public-disclosure sample")
    table(story, [
        ["Prepared evidence", "What it supports", "Limit"],
        ["15,813 initial candidates, 2013-2025", "Source-backed identifiers, ownership rows and prior disclosure histories", "Factual staging; not a validated investment universe. [E2]"],
        ["667 single-filing two-year events", "Join company characteristics and filing facts to existing stock/proxy outcomes", "Selective coverage from 2,107 scheduled events and 694 calculable labels. [E3-E4]"],
        ["55 focused activist candidates; 556 other/unresolved", "Compare mechanisms across a broader covered universe", "Also 12 other Event-Driven and 44 other HFR candidates; identities remain provisional."],
        ["Dated size, industry and prior activity", "Initial context for opportunity selection", "Valuation fundamentals, liquidity and volatility inputs remain unfinished."],
    ], [172, 183, 177], padding=4)
    heading(story, "Why simple following is insufficient")
    table(story, [
        ["Existing focused two-year evidence", "Result", "Meaning"],
        ["56 calculable events", "+8.66 pp mean excess", "A favorable gross average with a wide uncertainty interval."],
        ["Typical event", "-14.91 pp median excess", "The positive mean does not describe the typical opportunity."],
        ["95% mean interval", "-17.34 to +40.43 pp", "Underperformance remains compatible with the evidence."],
    ], [184, 135, 213], padding=4)
    paragraph(story, "pp = percentage points. 2018-2025 exploratory research window; 504-session holding and modeled delayed opening entry. Equally weighted gross stock-minus-Russell-size-ETF-proxy returns, not account CAGR or risk-adjusted alpha. Horizons changed after earlier outcomes were inspected. This motivates selection and economic modeling, not proof of a repeatable edge. [E1]", "small")
    heading(story, "Ownership and disclosure uncertainty")
    paragraph(story, "Ownership-percentage summaries are present for 557/667 events. The 110 missing cases include 14 unresolved security attributions. Three related reporters each disclosing 8% must not become a fabricated 24% position. The maximum reported percentage is a source summary, not verified aggregate economic influence. [E4]")
    paragraph(story, "LLM processing is proposed to interpret stated relationships and objectives with exact supporting passages. It cannot turn a plan into a realized outcome, infer unsupported control, or supply externally calibrated execution probabilities. Compustat financials and dated manager mappings still need assembly and validation.", "small")

    page(story, "Proposed scenario and valuation model")
    paragraph(story, "For each selected case, establish a current operating baseline, specify the investor's requested changes, and model base, upside and downside paths. Separate value drivers, implementation probability and realization time. Use financial information available when the investment decision is made.")
    table(story, [
        ["Model component", "Proposed treatment"],
        ["Operating cash flows", "Revenue, margins, working capital, capital expenditure and restructuring costs under each path."],
        ["Enterprise to equity value", "Discount operating value; reconcile debt, cash, taxes, contingent claims and dilution. Test terminal assumptions."],
        ["Execution and time", "Evidence-based milestones and explicit uncertainty. Catalyst timing and probability remain assumptions to validate."],
        ["Investor return", "Translate equity value and distributions into per-share investment outcomes under an explicit entry and exit convention."],
    ], [147, 385], padding=4)
    heading(story, "Illustrative calculation only - not an issuer valuation")
    paragraph(story, "Assume an initial investment of 100, a common two-year horizon, and three terminal-wealth scenarios. The values and probabilities below are teaching assumptions; they are not learned, source-estimated or calibrated project results.")
    story.append(ScenarioChart())
    paragraph(story, f"Expected terminal wealth = 0.50 x 120 + 0.25 x 160 + 0.25 x 70 = <b>{EV:.2f}</b>. That is a 17.5% expected cumulative gain before costs. At an illustrative 10% annual required return, present value = 117.5 / 1.10<super>2</super> = <b>{PV:.2f}</b>.")
    paragraph(story, "Expected future wealth above 100 can still be insufficient for the assumed required return. Probability, payoff and timing sensitivities therefore matter together. A forecast is useful only if the economic assumptions and downside are defensible.", "small")
    heading(story, "Separate two kinds of uncertainty")
    paragraph(story, "<b>Economic uncertainty:</b> which operating/transaction path occurs, its payoff and timing. <b>Measurement uncertainty:</b> whether the extracted disclosure correctly identifies the investor, holdings and plan. Repeated LLM agreement measures stability; it does not establish the true probability of a value-creation outcome.")
    paragraph(story, "Acquisitions and delistings need source-backed settlement treatment. Replacement shares or contingent rights are not automatically immediate cash proceeds. Existing accounting exceptions limit some funded-portfolio results.", "small")

    page(story, "From economic forecasts to investment decisions")
    table(story, [
        ["Decision", "First comparison", "Proposed modeling extension"],
        ["Whether to invest", "Relative-return selection under common rules", "Require a credible valuation gap and downside/risk rationale."],
        ["When to enter", "Existing delayed-entry convention", "Compare disclosure reaction and later observable execution milestones."],
        ["How long to hold", "Two-year target proposed", "Relate holding period to catalyst timing and scenario realization."],
        ["How much to allocate", "Existing 5% issuer targets and limits", "Use loss exposure, uncertainty, liquidity and portfolio dependence."],
    ], [111, 193, 228], padding=4)
    paragraph(story, "These decisions jointly define a strategy; they do not automatically create one objectively optimal training label. A joint action model requires an explicit objective, costs and constraints. Initial work isolates selection before changing timing, horizon or sizing.", "small")
    heading(story, "How ML and LLM processing support the model")
    paragraph(story, "A small feedforward neural network is planned to predict benchmark-relative return, compared with a training-mean reference, regularized regression and boosted trees. It may identify patterns across observable company and investor information. Its output is a statistical estimate, not a substitute for a cash-flow explanation.")
    paragraph(story, "Compare deterministic features, then validated LLM ownership/identity information, then disclosed intentions. Hold modeling and investment conventions comparable. Inspect extraction errors and repeated-run variability separately from predictive and economic performance.")
    heading(story, "Completed preparation and the next economic test")
    paragraph(story, "The 2023 development input table has 365 earlier outcome-mature training events, 86 later events and 69 encoded columns. All preprocessing uses earlier inputs. These examined historical data remain development evidence, not a fresh final test. [E5]")
    paragraph(story, "<b>Next:</b> select one source-supported mechanism; assemble dated fundamentals; build a transparent base/upside/downside case; then compare forecasts and investment decisions against the statistical selection model. Evaluate downside, holding time, realized benchmark-relative performance and implementation costs. No issuer-specific valuation or scenario calibration is complete yet.")
    evidence(story, methods=False)
    return story


def build_pdf(name, story, title):
    path = HERE / name
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=34, rightMargin=34,
                            topMargin=36, bottomMargin=41, title=title, author="Jeff Lu",
                            pageCompression=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(path)
    if len(reader.pages) != 4:
        raise ValueError(f"Expected four pages, got {len(reader.pages)}: {name}")
    return path


def notes(ml_path, private_path):
    links = "".join(f'<li>{escape(label)}: <a href="{escape(str(path.relative_to(HERE.parent.parent.parent)), quote=True)}">{escape(path.name)}</a></li>' for label, path in FILES.items())
    # Notes live three levels below project root; links are portable to the checkout.
    links = links.replace('href="research/', 'href="../../../research/')
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D professor discussion speaking notes</title><style>body{{font:17px/1.6 system-ui;color:#19374a;background:#f4f6f8}}main{{max-width:900px;margin:30px auto;padding:26px;background:white}}h2{{color:#146d76;font-size:23px}}a{{color:#146d76}}li{{margin:10px 0}}blockquote{{border-left:4px solid #146d76;padding:8px 18px;margin:16px 0}}</style></head><body><main>
<h1>13D professor discussion speaking notes</h1><p>For October 13, 2026 | Evidence through October 12</p><p><a href="{ml_path.name}">Machine Learning handout</a> · <a href="{private_path.name}">Private Markets Modeling handout</a></p>
<h2>Machine Learning opening</h2><blockquote>I want the class project to center on a small neural network for post-13D investment selection. I now have 667 candidate events with filing and company inputs, plus chronological preprocessing. For the 2023 fold, 365 earlier outcomes are available for training and 86 later events for development evaluation. I plan to compare the network with simpler predictors, then ask whether validated LLM-extracted ownership and intent add information. No predictive model has been fitted yet.</blockquote>
<p>Lead with the model comparison, not the HFR manager-ranking extension. Be ready to explain X versus y, training-only preprocessing, label maturity and why a negative result is useful.</p>
<h2>Questions for the ML professor</h2><ol><li>Is a small feedforward network plus regularized regression and boosted trees an appropriate method scope, or is a different neural architecture expected?</li><li>Does the two-year relative-return target justify the limited matured training sample and sparse industry columns? Should a declared one-year feasibility comparison be included?</li><li>What model-capacity, tuning and extraction-validation evidence is expected for the course?</li><li>Is honest chronological development reporting acceptable if no untouched historical evaluation is defensible? Confirm the submission dates and format.</li></ol>
<h2>Private Markets Modeling opening</h2><blockquote>The investment is a public stock, but I want to model activism with a private-markets value-creation framework: what changes in operations, financing or governance, what that means for cash flows and equity value, and how probability and time affect the investment. The historical following result is mixed. I have prepared the disclosure and market-data foundation, but no issuer-specific cash-flow model or calibrated scenario probabilities yet. I would value your guidance on one economic mechanism and one tractable case.</blockquote>
<h2>Questions for the Private Markets Modeling professor</h2><ol><li>Which mechanism would make the best first valuation case: operating improvement, an asset sale, capital return or governance change?</li><li>What source evidence should support the base/upside/downside assumptions and execution probabilities?</li><li>How should catalyst timing, discount rates, contingent claims and downside feed into selection and position sizing?</li><li>How would you connect a statistical ML return forecast to an economic thesis without mistaking predictive association for causality?</li></ol>
<h2>Keep these distinctions clear</h2><ul><li>667 events are not 667 managers; 556 have other/unresolved identities.</li><li>The ML target is a proposed return estimate. Whether, when, holding period and allocation are investment decisions built around forecasts and constraints.</li><li>Ownership imputation is a computational placeholder. Parser/citation checks do not certify semantic accuracy.</li><li>The private-markets scenario values are explicitly hypothetical teaching assumptions, not a real company valuation or trained probabilities.</li><li>Historical data have been examined; the later folds are development evidence. No alpha or fresh final test is claimed.</li></ul>
<h2>Evidence index</h2><ul>{links}</ul><p>Local sources are retained in the project. AI-assisted writing and tooling; this update runs no new backtest, trains no model and changes no human references.</p><p><a href="../../../START-HERE.html">Project home</a></p></main></body></html>'''
    (HERE / "discussion-notes.html").write_text(html)


def main():
    ml = build_pdf("13D_Machine_Learning_Brief_20261013.pdf", ml_story(), "Machine learning for 13D investment selection")
    private = build_pdf("13D_Private_Markets_Modeling_Brief_20261013.pdf", private_story(), "Modeling value creation after a 13D disclosure")
    notes(ml, private)
    (HERE / "evidence.json").write_text(json.dumps({"source_sha256": SOURCE_HASHES,
        "source_paths": {name: str(path.relative_to(PROJECT)) for name, path in FILES.items()},
        "source_units": "Filing records, staged filing candidates and scheduled investment events are distinct.",
        "scenario_illustration": {"status": "hypothetical teaching assumptions, not research results", "initial_wealth": 100,
                                  "horizon_years": 2, "scenarios": SCENARIOS, "expected_terminal_wealth": EV,
                                  "assumed_required_return": .10, "discounted_value": PV},
        "new_return_estimates": False, "model_fitting": False}, indent=2) + "\n")
    (HERE / "verification.json").write_text(json.dumps({"pdfs": {path.name: {"pages": 4,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in (ml, private)},
        "python": platform.python_version(), "packages": {name: version(name) for name in ("reportlab", "pypdf", "pdfplumber")},
        "checks": "source counts and illustrative scenario arithmetic pinned; rendered review pending",
        "visual_review": "pending"}, indent=2) + "\n")
    print(str(ml))
    print(str(private))


if __name__ == "__main__":
    main()
