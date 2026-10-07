"""Build a discussion handout from preserved research; performs no new analysis."""
from pathlib import Path
from html import escape
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
for name, filename in [("Arial", "Arial.ttf"), ("ArialBold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + filename))
NAVY = colors.HexColor("#18364a")
TEAL = colors.HexColor("#146d76")
styles = {
    "title": ParagraphStyle("title", fontName="ArialBold", fontSize=19, leading=22, textColor=NAVY, spaceAfter=5),
    "meta": ParagraphStyle("meta", fontName="Arial", fontSize=9, leading=11, textColor=colors.HexColor("#596b77"), spaceAfter=10),
    "head": ParagraphStyle("head", fontName="ArialBold", fontSize=10.7, leading=13, textColor=TEAL, spaceBefore=7, spaceAfter=3, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="Arial", fontSize=10.2, leading=12.7, textColor=NAVY, spaceAfter=3),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8.2, leading=10.5, textColor=colors.HexColor("#51616c"), spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=9.5, leading=12, textColor=NAVY),
    "cellhead": ParagraphStyle("cellhead", fontName="ArialBold", fontSize=9.4, leading=12, textColor=colors.white),
}

question = "Can investor identity, ownership and stated plans help an outside investor select better investments after an initial Schedule 13D becomes public?"
takeaway = "I have built a historical following baseline and prepared filing data. Simple following has not established a reliable investable edge. The next test is whether information available at disclosure improves selection."
completed = [
    "<b>Historical baseline:</b> screened initials versus amendments, linked historical stocks and measured post-disclosure returns. Funded simulations use 5% issuer targets, at most 20 issuers, liquidity limits, modeled costs and cash interest.",
    "<b>Structured preparation:</b> processed and audited 15,813 initial-filing candidates (2013-2025) from 75,631 archive records, with source-backed ownership and prior-disclosure histories. These are not independent campaigns or validated managers.",
    "<b>Manager research:</b> built descriptive scorecards from 35 HFR snapshots (2018 Q1-2026 Q3). Fund performance differs from disclosure-following returns. No selection model or validated intent-NLP result exists yet.",
]
results = [
    ["Exploratory focused activist-candidate sample", "Result / interpretation"],
    ["Approximately 24 months; 56 calculable events", "Mean excess +8.66 percentage points; median -14.91; 41.1% beat the proxy. 95% interval for mean: -17.34 to +40.43 points."],
    ["24-month industry/year/size controls; 17 matches", "-8.08 percentage points versus controls. The smaller matched comparison does not support the positive overall mean."],
]
limits = "2018-2025 exploratory research window; modeled entry at the open on the second exchange session after acceptance; 504-session holding. Equally weighted gross stock-minus-Russell-size-ETF returns, not risk-adjusted alpha. Only 56 of 67 scheduled focused events were calculable; the 17 matches overlap that sample. Horizons were revised after inspecting earlier results. Funded accounts prevent concurrent duplicate issuer positions; primary $100k 18/24/36-month accounts remain incomplete at an acquisition-settlement exception."
hypotheses = [
    "<b>Who:</b> dated manager identity and completed prior disclosure-following outcomes; separately test HFR fund-performance ranks. Does either predict subsequent opportunities?",
    "<b>What and why:</b> attributable ownership plus specific board, sale, capital-return or restructuring plans, conditioned on valuation and balance-sheet risk. Does intent add value beyond structured data?",
    "<b>When:</b> later public stake or intent changes as a separate strategy extension. Can they improve entry/exit decisions after costs? This has not been tested.",
]
questions = [
    "<b>Value creation:</b> which activism mechanisms are most worth modeling, and what would indicate credible upside that is not already priced in at disclosure?",
    "<b>Signal choice:</b> would you prioritize investor track record, ownership/influence, or a specific catalyst? Is reported fund performance a useful proxy for this question?",
    "<b>Modeling:</b> should I begin with a scenario valuation of upside, downside and time to realization, or a 12-24-month benchmark-relative return target?",
    "<b>Evidence bar:</b> how would you distinguish a selection edge from factor exposures, concentrated winners and overlapping events in a chronological, after-cost test?",
]
next_step = "Validate dated identities and availability; freeze one selection rule and evaluation design. Compare information sets under common trading rules, using only facts and completed outcomes known at each cutoff."

story = []
def p(text, kind="body"):
    story.append(Paragraph(text, styles[kind]))
def head(text):
    p(text, "head")
p("Can public 13D disclosures become useful signals?", "title")
p("Jeff Lu, CFA | Discussion with Professor Michael Sternberg | October 5, 2026", "meta")
p("<b>Investment question.</b> " + question)
p(takeaway)
head("What I have completed")
for text in completed:
    p(text)
head("What the baseline actually says")
cells = [[Paragraph(text, styles["cellhead" if i == 0 else "cell"]) for text in row] for i, row in enumerate(results)]
table = Table(cells, colWidths=[195, 337], hAlign="LEFT")
table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY),
    ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#f1f5f7")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("LINEBELOW", (0,1), (-1,-1), 0.5, colors.white),
]))
story.append(table)
story.append(Spacer(1,5))
p(limits, "small")
head("Candidate signals to test - hypotheses, not findings")
for text in hypotheses:
    p(text)
head("Questions I would value your perspective on")
for i, text in enumerate(questions, 1):
    p(f"{i}. {text}")
p("<b>Next experiment.</b> " + next_step, "small")
p("Sources: Phase 1 conclusion/results (Sept 24); Phase 2 progress (Sept 25); HFR scorecards/protocol (Sept 30). Links in companion notes. AI-assisted synthesis; no new backtest.", "small")
pdf = ROOT / "Jeff_Lu_13D_Professor_Discussion_20261005.pdf"
SimpleDocTemplate(str(pdf), pagesize=letter, rightMargin=40, leftMargin=40, topMargin=32, bottomMargin=30, title="13D research - professor discussion", author="Jeff Lu").build(story)
reader = PdfReader(str(pdf))
assert len(reader.pages) == 1, f"Expected one page, got {len(reader.pages)}"
assert "15,813" in reader.pages[0].extract_text()

sources = [
    ("Phase 1 conclusion", PROJECT / "research/docs/PHASE1-FINAL-CONCLUSION-20260924.md"),
    ("Long-horizon evidence", PROJECT / "research/docs/PHASE1-LONG-HORIZON-RESULTS-20260924.md"),
    ("Phase 2 data preparation", PROJECT / "research/docs/PHASE2-DETAILED-PROGRESS-20260925.md"),
    ("HFR ranking definitions and limits", PROJECT / "research/protocol/hfr-percentiles-v1.md"),
    ("HFR scorecards", PROJECT / "research/runs/hfr-performance/20260930-v1/index.html"),
    ("September 30 research explainer", PROJECT / "research/docs/13d-research-explainer-20260930.html"),
]
assert all(path.is_file() for _, path in sources)
source_links = "".join(f'<li><a href="{escape(str(path.relative_to(PROJECT)), quote=True)}">{escape(label)}</a></li>' for label, path in sources)
# Relative links are rooted back at the project, preserving portability.
source_links = source_links.replace('href="research/', 'href="../../../research/')
paper_url = "https://business.columbia.edu/sites/default/files-efs/pubfiles/4132/jiang_activism.pdf"
notes = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>13D professor discussion - speaking notes</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;color:#18364a;background:#f3f6f8;margin:0}}main{{max-width:850px;margin:35px auto;padding:28px;background:white}}h1{{line-height:1.2}}h2{{font-size:22px;color:#146d76}}blockquote{{border-left:4px solid #146d76;margin:16px 0;padding:8px 20px;background:#f1f5f7}}a{{color:#146d76}}li{{margin:10px 0}}.meta{{color:#596b77;font-size:14px}}</style>
<main><h1>13D project: conversation with Michael Sternberg</h1><p class="meta">Prepared October 4 for October 5, 2026 | Research evidence through the September 30 update | Private Markets Modeling</p>
<p><a href="{pdf.name}">Print the one-page handout</a> | <a href="../../../START-HERE.html">Project start page</a></p>
<p>Fordham identifies Michael Sternberg as a Managing Director and head of Aladdin Financial Engineering at BlackRock. His listed background spans quantitative analytics and risk analytics. That suggests emphasizing target definition, scenario modeling and credible validation in this conversation; it does not establish a particular view on activism or his involvement with the MASS role. <a href="https://www.fordham.edu/gabelli-school-of-business/academic-programs-and-admissions/graduate-programs/academic-programs/ms-programs/quantitative-finance/msqf-advisory-board/">Fordham MSQF Advisory Board profile</a> (checked October 4, 2026).</p>
<h2>A 45-second opening</h2><blockquote>I've been researching whether an outside investor can use initial 13D disclosures to choose better investments. I've built a historical following baseline, prepared about 15,800 filing candidates, and recently added historical manager scorecards. Simple following has not shown a reliable edge: the two-year average is positive, but the median is negative and matched controls are weaker. My next question is whether who is investing, their economic ownership, and the specific value-creation plan can distinguish better opportunities using information available at disclosure. Given this class's focus on modeling, I'd value your view on which mechanism and next experiment are worth pursuing.</blockquote>
<h2>Lead with one question, then follow his answer</h2><p>Ask: <b>"If you were evaluating this as an investment research project, which piece would you test next to determine whether there is a real economic opportunity?"</b> Show the handout as context. The four questions on it are prompts, not a script to finish before class.</p>
<h2>How it connects to private-markets modeling</h2><p>The investable security here is a public equity. The connection to this class is a value-creation framework: a change in governance, operations, asset sales or capital allocation could alter cash flows, financing and exit value. Ask how to turn a disclosed plan into scenarios with execution probability, timing and downside. A filing's objective alone does not supply those probabilities or establish that its upside is absent from the price.</p>
<h2>Three proposed tests, in a practical order</h2><ol>
<li><b>Investor information:</b> compare following everyone eligible with a fixed rule using historically available manager information. Keep HFR fund-return rankings separate from a manager's prior post-disclosure target-stock outcomes. Fund returns can reflect other positions, hedges and fee structures; they are not the outside investor's replication return. The new scorecards are descriptive preparation, with unverified availability dates and incomplete dead-fund coverage.</li>
<li><b>Intent plus company economics:</b> compare a structured model with the same model plus evidence-backed disclosed objectives. Candidate inputs include specificity of the plan, voting influence, prior engagement, valuation, leverage and liquidity. These are proposals; lagged market features and validated intent extraction have not been completed.</li>
<li><b>Amendment updates:</b> separately investigate public stake increases/reductions or changed intentions. Freeze trade timing and exit rules first. This changes the fixed-holding strategy and cannot be presented as an existing baseline result.</li></ol>
<h2>The central distinction to discuss</h2><p>Announcement-window evidence does not establish returns available after our delayed purchase. Earlier research finds substantial price moves around activism announcements, including movement before the filing. Its results motivate the question but do not validate our newer sample or strategy. <a href="{paper_url}">Brav, Jiang, Partnoy and Thomas, The Returns to Hedge Fund Activism (2008), pp. 1-2</a>.</p>
<p>Our post-disclosure rule enters at the observed opening price on the second exchange session after acceptance under the frozen calendar convention. That is a modeled execution assumption. Ask whether any plausible advantage comes from underappreciated value creation, execution quality, or simply exposure to known risks. The project has not distinguished those explanations.</p>
<h2>If he challenges the positive average</h2><blockquote>That is exactly why I haven't claimed alpha. Across 56 calculable two-year focused events, mean gross excess is +8.66 percentage points, but median excess is -14.91, only 41.1% outperform, and the interval is wide. In 17 matched cases, the difference versus controls is -8.08 points. It motivates testing selection; it does not show that I could identify the winners in advance.</blockquote>
<p>Those 56 events are part of a 67-event scheduled focused subset in the 2018-2025 research window. The full schedule has 2,107 events, of which 694 have calculable benchmark comparisons. Counts from different horizons overlap. None is a count of independent managers. Event results are gross cumulative stock-minus-Russell-ETF-proxy returns, not account CAGR or risk-adjusted alpha.</p>
<h2>If he asks what is unfinished</h2><p>Historical manager identities and availability dates still need validation. Filing checks verify provenance and internal consistency, not complete semantic extraction. Ownership overlap needs careful attribution. Predictive models have not been fitted; intent extraction has no validated accuracy result. Primary $100k 18/24/36-month portfolios stop at Aratana's replacement-share/contingent-right settlement exception. The historical data have already been examined, so honest development tests and a separately frozen final or prospective evaluation are required.</p>
<h2>What you want to leave with</h2><p>One prioritized economic mechanism; one feasible signal or target; and the evidence he would require before treating a favorable result as investable. If he is interested, offer a short follow-up after implementing that specific test. Keep the career conversation as a separate, direct ask after the research discussion.</p>
<h2>Source record</h2><ul>{source_links}</ul><p class="meta">AI-assisted writing and project tooling. This brief introduces no new return calculations, signals, model results, human labels or protocol changes. No material has been sent to the professor. Existing independent-review packets remain unchanged.</p></main></html>"""
(ROOT / "discussion-notes.html").write_text(notes, encoding="utf-8")
(ROOT / "verification.json").write_text(json.dumps({"pages":len(reader.pages), "source_paths_exist":True, "research_status":"discussion synthesis; no new calculations", "evidence_updates_through":"2026-09-30", "visual_review":"pending"}, indent=2) + "\n")
print(str(pdf))
print("One-page PDF and discussion notes created; visual review pending.")
