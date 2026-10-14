"""Refocus the Private Markets discussion on 13D data and signal design.

Build a two-page leave-behind and one-page, five-minute speaking guide from
preserved project evidence. No research estimator, data change or API call.
Run with the bundled PDF-runtime Python; render and inspect both PDFs afterward.
The earlier four-page briefs remain byte-for-byte preserved.
"""

import hashlib
import json
import re
from html import escape
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from reportlab.platypus import SimpleDocTemplate, Spacer

import build_briefs as b

HERE = Path(__file__).resolve().parent
PROJECT = b.PROJECT
BRIEF = HERE / "13D_Data_Research_Discussion_20261013.pdf"
NOTES = HERE / "13D_Five_Minute_Speaking_Notes_20261013.pdf"
WEB_NOTES = HERE / "five-minute-discussion.html"
SOURCES = {
    "HFR": ("HFR strategy definitions", "https://www.hfr.com/hfr-indices/hfr-hedge-fund-strategy-classifications/"),
    "13D Monitor": ("13D Monitor: About Us", "https://www.13dmonitor.com/AboutUs.aspx"),
    "BlackRock Systematic": ("BlackRock: How AI is Transforming Investing", "https://www.blackrock.com/sg/en/insights/ai-investing"),
    "Aladdin / eFront": ("Aladdin: Turning Tables on Automation", "https://www.blackrock.com/aladdin/discover/blog/nlp-aladdin-private-markets-blog"),
}
EXTRA_INPUTS = {
    "archive and sample bridge": PROJECT / "research/docs/professor-discussion-20261005/visual-assets/chart-evidence.json",
    "HFR matching summary": PROJECT / "research/runs/hfr-all-managers/20260924-v1/summary.json",
    "HFR matching qualifications": PROJECT / "research/docs/HFR-ALL-MANAGERS-HANDOFF-20260924.md",
}
bridge = json.loads(EXTRA_INPUTS["archive and sample bridge"].read_text())["phase1_sample_bridge"]
hfr = json.loads(EXTRA_INPUTS["HFR matching summary"].read_text())
assert (bridge["metadata_initial_registry"], bridge["basic_screened_records"], bridge["first_pair_records"], bridge["scheduled_24_month_events"]) == (17795, 4673, 4440, 2107)
assert 17795 - sum(bridge["base_exclusions"].values()) == 4673
assert 4673 - sum(bridge["history_exclusions"].values()) == 4440
assert 4440 - sum(bridge["schedule_exclusions"].values()) - bridge["merged_record_reduction"] == 2107
assert hfr["snapshot_count"] == 35 and hfr["matched_firm_ids"] == 180
assert hfr["verified_economic_manager_count"] is None

PITCH = [
    ("0:00-0:35 | The idea", "I am building a machine learning class project around 13D filings. The question is whether information about who is investing, their ownership and their stated plans can help select stocks after disclosure. I want to test a potential source of alpha, rather than assume that following an activist creates an edge."),
    ("0:35-1:15 | What I have done", "I have a source-audited archive of about 75,600 filing records and have processed about 15,800 initial-filing candidates for factual extraction. Separately, the current return-data and feature checks leave 667 initial-event candidates. I have built ten structured inputs and prepared chronological training data. No predictive model has been trained, and the earlier simple-following work has not established a reliable edge."),
    ("1:15-1:50 | How I identify investors", "I use 35 historical HFR snapshots to find candidate manager matches and distinguish activist, other Event-Driven and other strategies. I am concerned that a firm's strategy label does not necessarily describe a particular filing, and legal vehicles complicate identity. Most current observations remain other or unresolved; I am keeping them in scope."),
    ("1:50-2:25 | How filings become observations", "My current row represents an eligible initial disclosure linked to a stock and a subsequent return window. The existing cuts include market-data coverage, prior investor-company history and overlapping positions. I want your view on which cuts are appropriate for learning a signal. Amendments may provide additional information, but they cannot be counted as independent new investments or used before they became public."),
    ("2:25-3:00 | Where I go next", "First I will train a small neural network and simpler comparisons using rule-based facts. Then I will test whether validated LLM extraction of ownership relationships and stated intentions adds information. BlackRock publicly describes LLM-based investment text analysis, and specialist 13D research already exists. I would like to understand where you think a student project could make a useful contribution."),
]
MAIN_QUESTION = "Would you change the HFR investor definition or the way I construct observations, and where would you look for information the market may not already price in?"
FOLLOW_UPS = [
    "Investor definition: HFR categories, validated manager identities, or intent in each filing?",
    "Observation design: retain a broader initial-event panel, with amendments as separately timed updates?",
    "Industry practice: which extraction or signal questions would make this a useful, realistic project?",
]


def linked(key):
    title, url = SOURCES[key]
    return f'<link href="{url}" color="#146d76">{title}</link>'


def brief_story():
    s = []
    b.paragraph(s, "Can 13D disclosures become a useful investment signal?", "title")
    b.paragraph(s, "Private Markets Modeling discussion | 13 October 2026 | Data and research design", "meta")
    b.paragraph(s, "<b>Idea:</b> combine public ownership disclosures with dated market data to test whether investor characteristics and stated plans help select stocks after disclosure. The central class deliverable is a neural-network experiment; LLM extraction supplies additional candidate inputs. Alpha is the hypothesis, not a finding.")
    s.append(b.ProcessStrip([
        ("A | Structured facts", "data ready; ML next", False),
        ("B | + Ownership", "LLM features planned", True),
        ("C | + Stated intent", "LLM features planned", True),
    ], height=60))
    b.heading(s, "What is ready today")
    b.table(s, [
        ["Evidence", "What it means"],
        ["75,631 filing records\n2013-September 2026", "Source-audited archive, including initial filings, amendments and unresolved records. A filing count is not a count of independent investments."],
        ["15,813 initial candidates\n2013-2025", "Factual staging completed. Separate from the narrower return-analysis sample; not all have usable stock or benchmark data."],
        ["667 joined event candidates\nEntries 2018-2023", "Ten structured inputs; outcomes extend through 2025. Ownership summaries exist for 557, with 110 missing. Chronological preprocessing is complete; no predictive model fitted."],
    ], [151, 381], padding=5)
    b.paragraph(s, "Existing inputs cover dated company size and industry, reporting-person counts, reported-percentage summaries, filing/event lag and prior disclosure activity. Rule-based parsing is repeatable, but it does not resolve every ownership relationship or verify total economic ownership.")
    b.heading(s, "HFR is a starting investor screen")
    b.paragraph(s, "The screen uses <b>35 supplied historical HFR snapshots (2018 Q1-2026 Q3)</b>, exact normalized firm/fund-name matches and seven fixed supplemental activist groups. It finds 180 historical HFR firm-ID candidates, not 180 validated economic managers. HFR categories describe strategies offered by a firm; they do not establish an individual filing's intent. [1]")
    b.paragraph(s, "Use the latest prior supplied snapshot; delivery-folder dates are an unverified availability proxy. Earlier archive years lack HFR coverage. Unmatched does not mean non-hedge-fund or passive. <b>HFR groups currently support diagnostics, not model inputs</b>, pending identity and historical-availability validation.")
    b.heading(s, "The experiment I propose")
    b.paragraph(s, "Predict the subsequent 504-trading-session stock return minus its assigned Russell benchmark. Compare a small neural network with regularized regression and boosted trees. Start with rule-based facts, then add validated ownership/identity interpretation, then stated intent, using comparable samples and chronological evaluation. Selection, timing, horizon and sizing are later investment-policy decisions.")
    b.paragraph(s, "The 2023 input preparation has only 365 earlier events with matured outcomes, so model capacity must be constrained. Current historical results are development evidence, not an untouched test. Benchmark-relative return is the initial target; risk adjustment and trading costs still matter before claiming alpha. Simple following has not established a reliable edge.", "small")
    b.page(s, "From filing records to model observations")
    b.paragraph(s, "<b>Current unit:</b> an eligible initial-disclosure event linked to a historical stock, entry date and subsequent return window. The sample below inherits portfolio-following rules; whether each rule belongs in the ML panel is a discussion point.")
    b.table(s, [
        ["Separate return-sample path", "Why the count changes"],
        ["17,795 metadata initial records", "Older metadata registry; not the source-audited initial count or the 15,813 factual-staging cohort."],
        ["4,673 screened records", "2018-2025 entry window, review exclusions, standalone/source, security and basic trading checks."],
        ["4,440 first-pair records", "Remove 233 prior investor-issuer history records; first observed in this archive is not necessarily first ever."],
        ["2,107 two-year scheduled events", "Remove 1,995 for overlap / multiple securities / insufficient calendar; same-entry, same-issuer merges reduce records by 338."],
        ["694 calculable benchmark labels", "712 assigned benchmarks, less 18 return refusals. Another 1,395 scheduled events lack the required historical benchmark match."],
        ["667 single-filing feature rows", "Defer 27 merged events until their aggregation rule is defined. All 667 join to prepared facts."],
    ], [168, 364], padding=4)
    b.paragraph(s, "The 75,631-record archive, 15,813-candidate staging cohort and this return-sample path serve different purposes; they are not one sequential funnel.", "small")
    b.heading(s, "Keep the broader covered universe")
    b.table(s, [
        ["Focused activist*", "Other Event-Driven", "Other HFR", "Other / unresolved"],
        ["55", "12", "44", "556"],
    ], [133, 133, 133, 133], padding=4)
    b.paragraph(s, "*Disjoint groups sum to 667; the focused group includes the fixed supplements. These are candidate labels. The 556 other/unresolved events remain in scope; missing identity is not a reason to call them passive or exclude them.", "small")
    b.paragraph(s, "All archived filings can support factual preparation and disclosure histories. Supervised learning needs usable stock links and observed outcomes; missing returns cannot become zero-return labels. Amendments can become context or separately timed update observations. Future amendments must never enter an earlier row. <b>Proposed review:</b> retain overlaps in a broader ML panel with issuer/time safeguards, rather than automatically inheriting the portfolio non-overlap filter.")
    b.heading(s, "What industry already does - and what remains open")
    b.paragraph(s, "13D Monitor sells qualitative activism research and describes screening 13D filings. [2] BlackRock Systematic describes LLM analysis of financial text for investment forecasting. [3] Aladdin describes NLP extraction from private-market reports in eFront Insight. [4] These are related precedents; they do not verify this exact 13D-to-ML pipeline or establish its incremental alpha.")
    b.paragraph(s, "<b>Input sought:</b> an appropriate investor definition, defensible observation rules, and a tractable information question that would make this a useful investment-data project.")
    b.paragraph(s, f"Public sources, checked 12 October 2026: [1] {linked('HFR')}; [2] {linked('13D Monitor')}; [3] {linked('BlackRock Systematic')}; [4] {linked('Aladdin / eFront')}.", "small")
    b.paragraph(s, "Local evidence and exact source hashes: companion speaking-notes page. Data preparation and proposed research design; no trained predictive model or measured LLM contribution. AI-assisted preparation.", "small")
    return s


def speaking_story():
    s = []
    b.paragraph(s, "13D data idea: a five-minute conversation", "title")
    b.paragraph(s, "Speaking guide | 13 October 2026 | Explain for 3 minutes; invite feedback for 2", "meta")
    for cue, script in PITCH:
        b.heading(s, cue)
        b.paragraph(s, script)
    b.heading(s, "3:00-5:00 | Ask, then pause")
    b.paragraph(s, f"<b>{MAIN_QUESTION}</b>")
    b.paragraph(s, "Follow only the thread he picks; use these prompts if needed:", "small")
    for question in FOLLOW_UPS:
        b.paragraph(s, question, "small")
    b.paragraph(s, "The two-page handout contains the sample cuts and public-source links. Leave it with him; do not read the sample table aloud. If interrupted, move directly to the main question.", "small")
    b.paragraph(s, "Remember: an observation is one model row; inputs are facts available at that date; the target is the later return. Repeatable rule-based extraction can still be wrong. LLM output can vary, so repeatability and source accuracy need separate checks.", "small")
    return s


def build_pdf(path, story, pages):
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(b.RULE)
        canvas.line(40, 29, 572, 29)
        canvas.setFont("Brief", 8)
        canvas.setFillColor(b.GRAY)
        canvas.drawRightString(572, 17, f"{doc.page} / {pages}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=b.letter, leftMargin=34, rightMargin=34, topMargin=36, bottomMargin=41,
                           title="13D Data Research Discussion" if pages == 2 else "13D Five Minute Speaking Notes", author="Jeff Lu")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(path)
    assert len(reader.pages) == pages, (path.name, len(reader.pages))
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            body = [c for c in page.chars if c["top"] < 750]
            assert body and all(38 <= c["x0"] and c["x1"] <= 575 and c["bottom"] < 750 for c in body), (path.name, number)
    return " ".join(" ".join(p.extract_text().split()) for p in reader.pages)


def write_html():
    scripts = "".join(f"<h2>{escape(cue)}</h2><p>{escape(script)}</p>" for cue, script in PITCH)
    followups = "".join(f"<li>{escape(q)}</li>" for q in FOLLOW_UPS)
    links = "".join(f'<li><a href="{url}">{escape(title)}</a></li>' for title, url in SOURCES.values())
    local_inputs = {**b.FILES, **EXTRA_INPUTS}
    evidence = "".join(f'<li><a href="../../../{path.relative_to(PROJECT)}">{escape(name)}</a></li>' for name, path in local_inputs.items())
    WEB_NOTES.write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>13D data idea - five-minute professor discussion</title><style>
body{{max-width:900px;margin:36px auto;padding:0 24px;font:17px/1.65 Arial,sans-serif;color:#19374a;background:#f7fafb}}h1{{line-height:1.2}}h2{{font-size:21px;color:#146d76;margin-top:28px}}a{{color:#146d76}}.lead,blockquote{{background:#edf4f6;padding:16px 20px;border-left:4px solid #146d76}}small{{color:#576b78}}@media print{{body{{font-size:12px;margin:0}}details{{display:none}}}}
</style><h1>13D data idea: a five-minute conversation</h1><p>Private Markets Modeling discussion, 13 October 2026. Evidence through 12 October.</p>
<p><a href="{BRIEF.name}">Two-page data handout</a> · <a href="{NOTES.name}">One-page speaking guide</a> · <a href="13D_Machine_Learning_Brief_20261013.pdf">Machine Learning brief</a> · <a href="../../../START-HERE.html">Project home</a></p>
<div class="lead"><b>Use three minutes to explain; leave two for feedback.</b> The main question is whether the investor definition and observation construction are sensible, and where extracted information might add value. The older four-page valuation version remains available as an earlier draft.</div>
{scripts}<h2>3:00-5:00 | Ask, then pause</h2><blockquote>{escape(MAIN_QUESTION)}</blockquote><p>Follow the thread he picks. Optional prompts:</p><ul>{followups}</ul><p>Do not read every count in the handout aloud. If interrupted, move directly to the main question.</p>
<h2>Concepts to keep straight</h2><p>An <b>observation</b> is one model row: here, an eligible initial disclosure with a stock, date and later return. A <b>feature</b> is an input known by that date. The <b>target</b> is the later return being predicted. The four investment decisions are downstream uses of predictions, not automatically four labels combined into one target.</p>
<p><b>Deterministic</b> means the same code and input give the same result; it does not mean the result is true. An LLM can interpret relationships and language beyond fixed parsing rules, but may vary across runs. Repeated runs test stability; comparison with human source-based references tests accuracy. Those are different questions.</p>
<p>All records can inform the archive and history, while only covered, properly timed observations with outcomes enter supervised learning. Amendments can support a future update panel, without importing future information into initial rows. The inherited portfolio non-overlap rule is proposed for review, not already changed.</p>
<h2>Industry context and sources</h2><p>Public evidence confirms specialist 13D/activism research, financial-text LLM investment analysis, and private-market document NLP extraction. It does not verify this exact pipeline or establish alpha. The question to the professor is where a tractable contribution lies.</p><ul>{links}</ul>
<p>The <a href="https://www.fordham.edu/gabelli-school-of-business/academic-programs-and-admissions/graduate-programs/academic-programs/ms-programs/quantitative-finance/msqf-advisory-board/">Fordham profile</a> identifies Michael Sternberg as head of Aladdin Financial Engineering at BlackRock. Ask for his investment-data perspective without assuming he can describe a proprietary 13D strategy. Public sources checked 12 October 2026.</p>
<details><summary>Local evidence and verification</summary><ul>{evidence}</ul><p><a href="data-discussion-evidence.json">Source hashes and build receipt</a> · <a href="data-discussion-verification.json">Final rendering verification</a></p><p>Frozen inputs preserved. No predictive fit, LLM run, return recomputation or changes to human-review records.</p></details></html>''', encoding="utf-8")


def main():
    preserved = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in
                 ("13D_Machine_Learning_Brief_20261013.pdf", "13D_Private_Markets_Modeling_Brief_20261013.pdf")}
    brief_text = build_pdf(BRIEF, brief_story(), 2)
    notes_text = build_pdf(NOTES, speaking_story(), 1)
    for value in ("75,631", "15,813", "667", "17,795", "4,673", "4,440", "2,107", "694", "556"):
        assert value in brief_text, value
    assert "no predictive model fitted" in brief_text.lower()
    assert "3:00-5:00" in notes_text
    spoken_words = len(re.findall(r"\S+", " ".join(text for _, text in PITCH)))
    assert spoken_words <= 360, spoken_words
    write_html()
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in {**b.FILES, **EXTRA_INPUTS}.items()}
    for name, digest in preserved.items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
    receipt = {
        "discussion_date": "2026-10-13", "evidence_as_of": "2026-10-12",
        "purpose": "Refocus Private Markets professor discussion on investment data and signal research",
        "outputs": {BRIEF.name: {"pages": 2}, NOTES.name: {"pages": 1}, WEB_NOTES.name: {}},
        "source_sha256": hashes, "preserved_earlier_pdf_sha256": preserved,
        "spoken_pitch_words": spoken_words, "speaking_budget": "3 minutes explanation + 2 minutes discussion",
        "public_sources": {key: {"title": title, "url": url, "checked": "2026-10-12"} for key, (title, url) in SOURCES.items()},
        "predictive_model_fitted": False, "llm_extraction_run": False, "research_data_changed": False,
        "visual_qa": "pending final page rendering and inspection",
    }
    (HERE / "data-discussion-evidence.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"brief_pages": 2, "notes_pages": 1, "spoken_pitch_words": spoken_words, "text_bounds": "pass", "previous_pdfs": "preserved"}))


if __name__ == "__main__":
    main()
