"""Six-page visual synthesis of preserved 13D evidence.

Inputs: frozen return summaries, filing ledger, selection/coverage audits.
Outputs: six figures, six-page PDF and a provenance/verification record.
Identity: archive = selected + priority exclusions; no new return estimator.
Tier: 2 presentation of preserved reported estimates (not a new backtest).
Run with project Python and `charts`, then PDF-runtime Python without arguments.
"""
from pathlib import Path
import json
import hashlib
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
ASSETS = ROOT / "visual-assets"
ASSETS.mkdir(exist_ok=True)
BASE = PROJECT / "research/runs/phase1-baseline/20260924-long-horizon-analysis-v1"
source_files = {
    "returns": BASE / "summary.json",
    "controls": BASE / "matched-summary.json",
    "coverage": PROJECT / "research/runs/phase2-readiness/20260924-full-v1/field-coverage.json",
    "universe": PROJECT / "research/runs/phase1-baseline/20260924-universe-rebuild-v3/eligibility.jsonl",
    "selection": PROJECT / "research/runs/phase2-overnight/20260924-full-v1/progress.json",
    "protection": PROJECT / "research/runs/phase1-baseline/20260924-development-v4/human-review-protection.json",
    "funded_account": PROJECT / "research/docs/PHASE1-LONG-HORIZON-RESULTS-20260924.md",
    "phase1_selection": PROJECT / "research/runs/phase1-baseline/20260924-long-horizon-inputs-v1/selection.json",
    "phase1_registry_summary": PROJECT / "research/runs/phase1-baseline/20260924-feasibility-v2/summary.json",
    "hfr_matching": PROJECT / "research/runs/hfr-all-managers/20260924-v1/summary.json",
    "hfr_match_rules": PROJECT / "research/runs/hfr-all-managers/20260924-v1/code/hfr_all_match.py",
    "hfr_cohort_rules": BASE / "code/expanded_hfr_returns.py",
}
summary = json.loads(source_files["returns"].read_text())
focused = [summary["first_observed"][h]["russell"]["focused"] for h in ("252", "378", "504", "756")]
controls = json.loads(source_files["controls"].read_text())["first_observed"]["504"]["comparison"]
coverage = {row["field"]: row for row in json.loads(source_files["coverage"].read_text()) if row["year"] == "all"}
ledger = [json.loads(line) for line in source_files["universe"].read_text().splitlines()]
progress = json.loads(source_files["selection"].read_text())
protection = json.loads(source_files["protection"].read_text())
blocked = set(protection["issuers"]) | {"0001287808"}
protected_accessions = set(protection["accessions"])
reproduced = Counter()
selected_dates = []
for row in ledger:
    if set(row.get("issuers", [])) & blocked or row["accession"] in protected_accessions:
        reproduced["protected_or_user_excluded"] += 1
    elif not row.get("accepted"):
        reproduced["missing_acceptance"] += 1
    elif row["accepted"][:10] > "2025-12-31":
        reproduced["after_2025"] += 1
    elif row["status"] == "unresolved_source_or_primary":
        reproduced["unresolved_source_or_primary"] += 1
    elif row["status"] != "standalone_initial_candidate":
        reproduced["not_initial_candidate"] += 1
    else:
        selected_dates.append(row["accepted"])
assert dict(reproduced) == progress["selection_exclusions"]
assert len(selected_dates) == progress["selected_initial_filings"] == 15813
assert len(ledger) == 75631 == len(selected_dates) + sum(reproduced.values())
assert min(row["accepted"] for row in ledger)[:10] == "2013-01-02"
assert max(row["accepted"] for row in ledger)[:10] == "2026-09-11"
assert max(selected_dates)[:10] == "2025-12-31"
year_counts = Counter(row["accepted"][:4] for row in ledger)
year_initial = Counter(row["accepted"][:4] for row in ledger if row["status"] == "standalone_initial_candidate")
assert sum(year_counts.values()) == 75631
assert sum(year_initial.values()) == 17420
assert abs(focused[2]["mean_excess"] - .08664106840384729) < 1e-12
assert abs(focused[2]["median_excess"] + .1490506980465715) < 1e-12
assert abs(controls["mean_excess"] + .0808) < .0001
phase1_selection = json.loads(source_files["phase1_selection"].read_text())
registry_summary = json.loads(source_files["phase1_registry_summary"].read_text())
hfr_summary = json.loads(source_files["hfr_matching"].read_text())
base_drops = Counter(r["reason"] for r in phase1_selection["base_exclusions"])
history_drops = Counter(r["reason"] for r in phase1_selection["exclusions"]["first_observed"]["eligibility"])
schedule_drops = Counter(r["reason"] for r in phase1_selection["exclusions"]["first_observed"]["schedule"]["504"])
first_pair_records = phase1_selection["selected"]["first_observed"]
plans24 = phase1_selection["plans"]["first_observed"]["504"]
assert registry_summary["form_counts"]["13D"] == 17795
assert 17795 - sum(base_drops.values()) == len(phase1_selection["selected"]["standalone"]) == 4673
assert 4673 - sum(history_drops.values()) == len(first_pair_records) == 4440
assert len(plans24) == 2107 and sum(len(e["accessions"]) for e in plans24) == 2445
assert len(first_pair_records) == sum(schedule_drops.values()) + 2445
assert sum(r["focused"] for r in first_pair_records) == 89
assert sum(e["focused"] for e in plans24) == 67
assert dict(Counter(r["reason"] for r in phase1_selection["exclusions"]["first_observed"]["schedule"]["504"] if r["focused"])) == {"overlapping_issuer_position":9,"insufficient_calendar":13}
def assigned(row):
    return row["scheduled"] - sum(v for k,v in row["statuses"].items() if k.startswith("assignment:"))
group24 = summary["first_observed"]["504"]["russell"]
disjoint_keys = ["focused", "other_event_driven", "new_other_hfr", "other_unresolved"]
assert sum(group24[k]["calculated"] for k in disjoint_keys) == group24["all"]["calculated"] == 694
assert sum(group24[k]["calculated"] for k in disjoint_keys[:3]) == group24["expanded"]["calculated"] == 116
assert [assigned(r) for r in focused] == [65,62,58,52]
facts = {
    "horizons_months": [12, 18, 24, 36],
    "focused": focused,
    "matched_24_month": controls,
    "filing_coverage": {key: coverage[key] for key in ("filing_entities.cik", "securities.cusip", "ownership.percent_of_class", "reporting_persons.cik")},
    "source_sha256": {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in source_files.items()},
    "status": "rendered preserved statistics; no new return calculation",
    "universe_by_year": dict(sorted(year_counts.items())),
    "archive_records": len(ledger),
    "archive_initial_candidates_before_staging_filters": sum(year_initial.values()),
    "staging_selection": {"selected": len(selected_dates), "exclusions": dict(reproduced)},
    "archive_accepted_dates": [min(row["accepted"] for row in ledger), max(row["accepted"] for row in ledger)],
    "selected_accepted_dates": [min(selected_dates), max(selected_dates)],
    "phase1_sample_bridge": {"metadata_initial_registry":17795,"basic_screened_records":4673,"first_pair_records":4440,"scheduled_24_month_events":2107,"focused_before_schedule":89,"focused_scheduled":67,"focused_assigned":58,"focused_calculated":56,"base_exclusions":dict(base_drops),"history_exclusions":dict(history_drops),"schedule_exclusions":dict(schedule_drops),"merged_record_reduction":338},
    "cohort_returns_24_month": {k:group24[k] for k in disjoint_keys+["expanded","all"]},
    "hfr_matching_summary": hfr_summary,
}
(ASSETS / "chart-evidence.json").write_text(json.dumps(facts, indent=2) + "\n")
NAVY, TEAL, AMBER, GRAY = "#18364a", "#146d76", "#bd6b36", "#62727c"

if sys.argv[1:] == ["charts"]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "axes.spines.top":False, "axes.spines.right":False, "axes.labelcolor":NAVY, "xtick.color":NAVY, "ytick.color":NAVY, "text.color":NAVY, "axes.edgecolor":"#c8d4da", "savefig.facecolor":"white"})
    def finish(fig, name):
        fig.savefig(ASSETS / name, dpi=250, bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)
    years=sorted(year_counts)
    fig,ax=plt.subplots(figsize=(7.4,1.95))
    initial=[year_initial[y] for y in years]
    remaining=[year_counts[y]-year_initial[y] for y in years]
    ax.bar(years,initial,color=TEAL,label="Standalone initial candidates")
    ax.bar(years,remaining,bottom=initial,color="#b4c5ce",label="Amendments / unresolved records")
    ax.set_ylabel("Parsed filing records",fontsize=9)
    ax.set_ylim(0,7600);ax.set_yticks([0,2000,4000,6000]);ax.set_xticks(range(len(years)),[y[2:]+("*" if y=="2026" else "") for y in years])
    ax.yaxis.grid(True,alpha=.16);ax.set_axisbelow(True)
    ax.legend(loc="upper left",frameon=False,ncol=2,fontsize=8.5)
    fig.tight_layout(pad=.3);finish(fig,"archive-by-year.png")

    fig,ax=plt.subplots(figsize=(7.4,1.65))
    ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off")
    ax.text(.5,.88,"75,631 source-audited filing records",ha="center",va="center",fontsize=11,fontweight="bold",bbox={"boxstyle":"round,pad=.5","fc":"#e8eff2","ec":"none"})
    branches=[(.18,"17,420 initial candidates","15,813 staged candidates\n2013-2025",TEAL),(.53,"58,166 amendments","Information extraction\nand position updates: planned",TEAL),(.85,"45 unresolved records","Source / document\nreview needed",AMBER)]
    for xx,label,status,col in branches:
        ax.annotate("",xy=(xx,.54),xytext=(.5,.75),arrowprops={"arrowstyle":"->","color":"#8ba2ae","lw":1.4})
        ax.text(xx,.45,label,ha="center",va="center",fontsize=9,color=col,fontweight="bold")
        ax.text(xx,.19,status,ha="center",va="center",fontsize=8.7,color=GRAY)
    fig.tight_layout(pad=.25);finish(fig,"archive-routing.png")

    fig,ax=plt.subplots(figsize=(7.4,2.0))
    x=np.arange(4)
    for offset,values,label,col in [(-.25,[r["scheduled"] for r in focused],"Scheduled", "#b4c5ce"),(0,[assigned(r) for r in focused],"ETF assigned",TEAL),(.25,[r["calculated"] for r in focused],"Returns calculable",AMBER)]:
        bars=ax.bar(x+offset,values,.23,label=label,color=col)
        for bar in bars:ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,str(int(bar.get_height())),ha="center",fontsize=8.5)
    ax.set_xticks(x,["12 months","18 months","24 months","36 months"]);ax.set_ylabel("Focused events",fontsize=9)
    ax.set_ylim(0,100);ax.set_yticks([0,25,50,75]);ax.yaxis.grid(True,alpha=.16);ax.set_axisbelow(True)
    ax.legend(frameon=False,ncol=3,loc="upper left",fontsize=8.5)
    fig.tight_layout(pad=.3);finish(fig,"focused-sample-coverage.png")

    fig,ax=plt.subplots(figsize=(7.4,2.15))
    x=np.arange(4)
    for offset,key,label,col in [(-.18,"mean_excess","Mean excess",TEAL),(.18,"median_excess","Median excess",AMBER)]:
        bars=ax.bar(x+offset,[group24[k][key]*100 for k in disjoint_keys],.34,label=label,color=col)
        for bar in bars:
            v=bar.get_height();ax.text(bar.get_x()+bar.get_width()/2,v+(2 if v>=0 else -2),f"{v:+.2f}",ha="center",va="bottom" if v>=0 else "top",fontsize=8.5)
    ax.axhline(0,color=GRAY,lw=.8);ax.set_ylim(-50,87);ax.set_yticks([-40,-20,0,20,40,60,80])
    ax.set_xticks(x,["Focused activist\nn=56","Other event-driven\nn=14","Other HFR\nn=46","Other / unresolved\nn=578"])
    ax.set_ylabel("24-month excess (pp)",fontsize=9);ax.yaxis.grid(True,alpha=.16);ax.set_axisbelow(True)
    ax.legend(frameon=False,ncol=2,loc="upper left",fontsize=8.5)
    fig.tight_layout(pad=.3);finish(fig,"cohort-return-comparison.png")
    fig, ax = plt.subplots(figsize=(7.4,2.25))
    x=np.arange(4); means=[r["mean_excess"]*100 for r in focused]; medians=[r["median_excess"]*100 for r in focused]
    bars1=ax.bar(x-.18,means,.34,color=TEAL,label="Mean excess")
    bars2=ax.bar(x+.18,medians,.34,color=AMBER,label="Median excess")
    ax.axhline(0,color=GRAY,lw=.8)
    ax.set_xticks(x,[f"{h} months\nn={r['calculated']} events" for h,r in zip([12,18,24,36],focused)])
    ax.set_ylabel("Cumulative excess (pp)")
    ax.set_ylim(-40,32); ax.set_yticks([-30,-15,0,15,30]); ax.yaxis.grid(True,alpha=.16); ax.set_axisbelow(True)
    for bars in (bars1,bars2):
        for bar in bars:
            v=bar.get_height(); ax.text(bar.get_x()+bar.get_width()/2,v+(1.7 if v>=0 else -1.7),f"{v:+.2f}",ha="center",va="bottom" if v>=0 else "top",fontsize=9)
    ax.legend(loc="upper left",frameon=False,ncol=2,fontsize=9)
    fig.tight_layout(pad=.3); finish(fig,"horizon-returns.png")

    fig,ax=plt.subplots(figsize=(7.4,1.25))
    for y,row,col in [(1,focused[2],TEAL),(0,controls,AMBER)]:
        mu=row["mean_excess"]*100; lo,hi=[v*100 for v in row["issuer_bootstrap_95"]]
        ax.errorbar(mu,y,xerr=[[mu-lo],[hi-mu]],fmt="o",color=col,lw=2.2,capsize=5,markersize=6)
        ax.text(mu,y+.20,f"{mu:+.2f} [{lo:+.2f}, {hi:+.2f}]",ha="center",fontsize=8.8,color=col)
    ax.axvline(0,color=GRAY,lw=.8,ls="--")
    ax.set_yticks([1,0],["Focused vs. ETF (n=56)","Versus controls (n=17)"])
    ax.set_xlim(-40,50); ax.set_ylim(-.42,1.45); ax.set_xlabel("24-month mean difference and 95% interval (pp)",fontsize=9)
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y",length=0,labelsize=9)
    fig.tight_layout(pad=.2); finish(fig,"uncertainty.png")

    keys=["filing_entities.cik","securities.cusip","ownership.percent_of_class","reporting_persons.cik"]
    labels=["Header filer ID", "Security CUSIP", "Ownership percentage*", "Cover-person ID*"]
    values=[coverage[k]["files_with_present"] for k in keys]; denominator=15813
    fig,ax=plt.subplots(figsize=(7.4,1.65))
    y=np.arange(4); percentages=[100*v/denominator for v in values]
    ax.barh(y,[100]*4,color="#e8eff2",height=.56)
    ax.barh(y,percentages,color=[TEAL,TEAL,TEAL,AMBER],height=.56)
    for yy,v,pct in zip(y,values,percentages): ax.text(103,yy,f"{v:,} / 15,813 ({pct:.1f}%)",va="center",fontsize=9)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlim(0,151); ax.set_xticks([0,25,50,75,100],["0%","25%","50%","75%","100%"])
    ax.tick_params(axis="y",length=0,labelsize=9); ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_bounds(0,100)
    fig.tight_layout(pad=.2); finish(fig,"field-coverage.png")
    print("Current brief uses five data charts and one routing diagram; sample counts reconciled.")
    sys.exit(0)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
import shutil
for name,filename in [("BriefArial","Arial.ttf"),("BriefBold","Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name,"/System/Library/Fonts/Supplemental/"+filename))
pdfmetrics.registerFontFamily("BriefArial",normal="BriefArial",bold="BriefBold",italic="BriefArial",boldItalic="BriefBold")
styles={
    "title":ParagraphStyle("title",fontName="BriefBold",fontSize=18,leading=21,textColor=colors.HexColor(NAVY),spaceAfter=5),
    "meta":ParagraphStyle("meta",fontName="BriefArial",fontSize=8.7,leading=11,textColor=colors.HexColor(GRAY),spaceAfter=8),
    "body":ParagraphStyle("body",fontName="BriefArial",fontSize=10,leading=12.6,textColor=colors.HexColor(NAVY),spaceAfter=5),
    "head":ParagraphStyle("head",fontName="BriefBold",fontSize=11.2,leading=14,textColor=colors.HexColor(TEAL),spaceBefore=7,spaceAfter=4,keepWithNext=True),
    "small":ParagraphStyle("small",fontName="BriefArial",fontSize=8.1,leading=10.2,textColor=colors.HexColor(GRAY),spaceAfter=4),
    "cell":ParagraphStyle("cell",fontName="BriefArial",fontSize=9,leading=11.3,textColor=colors.HexColor(NAVY)),
    "th":ParagraphStyle("th",fontName="BriefBold",fontSize=9,leading=11.3,textColor=colors.white),
}
story=[]
def p(text,kind="body"):story.append(Paragraph(text,styles[kind]))
def heading(text):p(text,"head")
def figure(name,height):
    story.append(Image(str(ASSETS/name),width=532,height=height,kind="proportional",hAlign="LEFT"))
def table(rows,widths,padding=5):
    cells=[[Paragraph(s,styles["th" if i==0 else "cell"]) for s in row] for i,row in enumerate(rows)]
    t=Table(cells,colWidths=widths,hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f5f7"),colors.white]),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),padding),("BOTTOMPADDING",(0,0),(-1,-1),padding),("LINEBELOW",(0,1),(-1,-1),.5,colors.HexColor("#dce5e9"))]))
    story.append(t)
def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor("#dce5e9"));canvas.line(40,30,572,30)
    canvas.setFont("BriefArial",8);canvas.setFillColor(colors.HexColor(GRAY))
    canvas.drawRightString(572,18,f"{doc.page} / 6");canvas.restoreState()

p("13D research: ML, NLP and long-term active risk","title")
p("<b>Investment aim:</b> use machine learning (ML) and natural language processing (NLP) to uncover long-term alpha signals in public companies backed by high-quality event-driven or activist hedge funds, then take active risk in several selected, potentially concentrated positions.")
p("<b>Status:</b> the historical simple-following baseline has not established a reliable investable edge. Filing preparation and manager scorecards are underway; predictive ML and incremental intent NLP have not been evaluated.")
p("The intended output is a ranked set of company opportunities with an economic thesis, catalyst, downside case and position rationale. Manager reputation and a disclosed plan are candidate inputs; their value must be tested using information available before purchase.")
heading("Three phases - baseline, selection and disclosed intentions")
table([
    ["Phase / purpose", "Information and comparison", "What has been done"],
    ["<b>1. Simple following</b><br/>Measure post-disclosure returns.", "Initial 13D events and manager groups; stock returns versus Russell size-segment ETF proxies.", "Historical gross event-return baseline evaluated; reliable investable edge not established."],
    ["<b>2. Structured ML</b><br/>Rank stronger opportunities.", "Investor history, ownership, company size, liquidity, volatility and prior returns; fundamentals planned.", "15,813 candidates audited; HFR scorecards prepared. Dated joins/features unfinished; no fitted model."],
    ["<b>3. Incremental NLP</b><br/>Add the investor's stated plan.", "Item 4 objectives and specificity; compare structured ML with ML plus text on the same sample.", "Planned. No validated intent/alpha result. Ownership/identity extraction is preparation work."],
], [142,198,192])
heading("Data sources and their role")
table([
    ["Source", "Information", "Use / status"],
    ["<b>SEC EDGAR</b>", "13D/13D-A documents, public acceptance times, filer/issuer identities, stakes and Item 4 text.", "Cached source-audited filing archive; factual extraction and future intent NLP. [E2]"],
    ["<b>CRSP via WRDS</b>", "Daily stock/ETF prices, returns, volume, historical security IDs and delisting fields.", "Market data behind the reported historical event-return tests. [E1, E4]"],
    ["<b>FTSE Russell<br/>via WRDS</b>", "Historical Russell constituent snapshots; ETF returns come from CRSP.", "Stock-appropriate size-segment ETF benchmark assignments. [E4]"],
    ["<b>HFR</b>", "35 supplied quarterly snapshots, 2018 Q1-2026 Q3: manager/fund names, strategy, reported returns and assets.", "Candidate manager/strategy links in Phase 1; descriptive peer scorecards. Predictive quality untested. [E3, E6]"],
    ["<b>Compustat<br/>via WRDS</b>", "Fundamentals for valuation, leverage, profitability and balance-sheet features.", "Planned features. A historically available, joined ML panel is unfinished. [E4]"],
], [112,215,205])
p("<b>WRDS</b> = Wharton Research Data Services, the access platform for the separate CRSP, FTSE Russell and Compustat datasets.","small")
p("HFR fund performance is different from target-stock returns available to an outside follower. Dated manager identities, availability and incomplete dead-fund coverage need validation before the scorecards can become signals. [E3]","small")
heading("Proposed extension: amendments for position adjustments")
table([
    ["Amendment disclosure", "Potential use and observability"],
    ["<b>Stake increases / reductions</b>", "Compare Item 5 shares, issuer ownership percentages and transactions. Percentage changes may reflect issuer share-count changes; ownership percentage is not fund portfolio weight."],
    ["<b>Exit / reporting threshold</b>", "Item 5(e) dates a fall to 5% or less, which is not necessarily zero. Confirm a full disposition explicitly or leave the full-exit date unknown. [E5]"],
], [137,395],padding=4)

story.append(PageBreak())
p("From about 75,000 filings to 15,813 candidates","title")
p("Cached SEC archive: January 2, 2013-September 11, 2026 | Unit: parsed filing records","meta")
p("The audited archive contains <b>75,631 records</b>, including <b>58,166 amendments</b>, <b>17,420 standalone initial-filing candidates</b> and <b>45 unresolved records</b>. These are filing records, not unique companies, managers or independently validated campaigns. [E2]")
heading("Archive coverage by acceptance year")
figure("archive-by-year.png",135)
p("Years shown as 13-26. *2026 is partial through September 11. The initial-candidate segment is before the staging exclusions below. This is the project's cached, parsed archive, not a completeness claim about every SEC filing. [E2]","small")
heading("Two research streams: initial entries and amendment information")
figure("archive-routing.png",111)
table([
    ["Initial-entry preparation step", "Set aside", "Remaining"],
    ["Source-audited archive", "-", "75,631"],
    ["Protect review records/issuers; apply other user exclusions", "3,107", "72,524"],
    ["Restrict acceptance dates to December 31, 2025 or earlier", "3,613", "68,911"],
    ["Remove unresolved source/primary-document cases", "28", "68,883"],
    ["Retain initial candidates; keep other records as separate streams", "53,070", "<b>15,813</b>"],
], [358,87,87])
p("Set aside means outside the initial-entry cohort, not discarded from the archive. Counts reconcile across the full archive in priority order. The 53,070 includes remaining amendments and other non-initial records after earlier checks; it differs from the raw 58,166 amendment count. [E2]","small")
p("<b>What the 15,813 represent:</b> initial-filing candidates accepted in 2013-2025, all processed by the factual staging audit. They are not yet a validated hedge-fund universe or a tradable ML panel. Protected review samples remain independent.")
p("<b>Amendment stream:</b> retain and classify disclosures for ownership, intent, campaign and exit information (page 6). Bucket counts and a validated amendment feature panel are not yet measured. Apply the same date limits and independent-review protections before modeling.","small")
p("<b>Separate return-study sample:</b> Phase 1 uses a 2018-2025 schedule and further security, history, benchmark and return checks. The 15,813-record factual-staging audit is a later preparation exercise, not a direct sequential parent of the return sample. Page 3 reconstructs the actual Phase 1 selection. [E1, E6]","small")

story.append(PageBreak())
p("How the sample becomes 50-65 focused observations","title")
p("Phase 1 first-observed manager/party-issuer pairs | Record counts become scheduled investment events","meta")
heading("HFR identifies candidate managers; screening determines the sample")
table([
    ["Manager identification step", "What we actually did"],
    ["<b>Dated HFR name matching</b>", "Use the latest prior quarterly snapshot under delivery-date proxies. Match exact normalized firm/fund names and firm names without legal suffixes; group HFR offerings by Firm_ID."],
    ["<b>Focused activist candidates</b>", "HFR firms with an Event-Driven / Activist offering, plus seven fixed supplemental investor groups. This is a candidate classification, not proof of the intent in each filing or manager quality."],
], [159,373])
p("HFR strategy labels describe a manager's offerings. Historical delivery-date proxies and identity links remain imperfect; supplements were selected retrospectively. No list revision to historical winners. [E6]","small")
heading("Actual path to the 24-month result")
table([
    ["Stage / unit", "Count", "Why the count changes"],
    ["Original metadata-initial registry / records", "17,795", "Original parsed-form 13D registry, before the later body/source eligibility audit."],
    ["Window, protections and basic readiness / records", "4,673", "Set aside 8,396 outside entry dates, 490 protected/user-excluded, 187 not standalone and 4,049 failing basic readiness."],
    ["First-observed pairs / records", "4,440", "Exclude 196 previously observed pairs and 37 with prior-history references."],
    ["24-month nonoverlapping schedule / events", "2,107", "Set aside 1,114 without enough calendar, 878 overlapping-issuer records and 3 multiple-security cases; merge 338 same-entry/issuer records."],
    ["Focused activist-candidate subset / events", "67", "HFR Activist plus supplements. Before scheduling: 89 focused records; 9 overlap and 13 lack calendar."],
    ["Historical Russell ETF assigned / focused events", "58", "8 lack constituent matches; 1 lacks historical security data."],
    ["Calculable stock/ETF returns / focused events", "<b>56</b>", "2 have missing or invalid stock total returns; keep the coverage loss visible."],
], [173,47,312],padding=4)
p("Basic readiness requires hash-checked sources, one issuer, a dated common-stock link, an observed entry open and valid trading conditions. The 17,795 registry differs from the 17,420 source-audited initial candidates and the later 15,813 staging set: these are different versions and checks. First observed is archive-relative, not first ever. [E6]","small")
heading("Longer horizons leave fewer scheduled and calculable events")
figure("focused-sample-coverage.png",135)
p("12/18/24/36 months use 252/378/504/756 exchange sessions, with planned exits by December 31, 2025. Different, overlapping samples; counts are events, not managers. Future return availability does not select the schedule, but missing data reduces the reported comparison. [E1, E6]","small")

story.append(PageBreak())
p("Historical returns: positive averages, weak medians","title")
p("Phase 1 exploratory development | 2018-2025 research window | Focused activist-candidate subset","meta")
heading("Focused returns by holding period")
figure("horizon-returns.png",185)
table([
    ["Hold", "n", "Stock<br/>mean", "ETF<br/>mean", "Excess<br/>mean", "Excess<br/>median", "Beat ETF", "Mean excess<br/>95% interval"],
] + [
    [f"{h} mo", str(r["calculated"]), f'{r["mean_stock"]*100:+.2f}%', f'{r["mean_benchmark"]*100:+.2f}%', f'{r["mean_excess"]*100:+.2f} pp', f'{r["median_excess"]*100:+.2f} pp', f'{r["fraction_beating_benchmark"]*100:.1f}%<br/>({round(r["fraction_beating_benchmark"]*r["calculated"])}/{r["calculated"]})', f'{r["issuer_bootstrap_95"][0]*100:+.2f} to {r["issuer_bootstrap_95"][1]*100:+.2f} pp']
    for h,r in zip([12,18,24,36],focused)
], [46,32,60,60,68,68,68,130],padding=6)
p("Gross, cumulative, equally weighted event returns; excess = stock minus its Russell size-segment ETF proxy; pp = percentage points. Horizons use different, overlapping calculable samples, so higher means do not establish an optimal holding period. Intervals use the saved issuer bootstrap. [E1]","small")
heading("What the table establishes and what remains to test")
table([
    ["Observation", "Investment meaning"],
    ["24-month mean +8.66 pp; median -14.91 pp; 23/56 beat the ETF", "A positive average coexists with underperformance in most measured events. Selection must identify attractive opportunities before the outcome is known."],
    ["36-month mean +20.83 pp; median -31.74 pp; 16/50 beat the ETF", "Longer-horizon gains are uneven. A favorable average does not establish broad replication or a better holding rule."],
    ["Every saved focused 95% interval crosses zero", "These estimates remain uncertain. Gross benchmark excess is not risk-adjusted alpha or a validated ML/NLP signal."],
], [222,310])
p("Entry convention: observed opening price on the second exchange session after SEC acceptance; observed prices do not guarantee fills. Returns are gross of strategy costs. Historical stock/benchmark coverage is selective and monthly membership dates have availability limits.","small")
p("Longer horizons and a broader history were adopted after earlier results were examined. These are exploratory development results; prior exposure, changing sample composition and shared issuer/manager/market risks limit inference. [E1]","small")

story.append(PageBreak())
p("How the manager groups compare at 24 months","title")
p("Same Phase 1 rules | Descriptive cohort comparison, not a controlled estimate of manager skill","meta")
heading("Four mutually exclusive candidate groups")
table([
    ["Group", "Classification rule"],
    ["<b>Focused activist</b>", "HFR Event-Driven / Activist offering, or one of the seven fixed supplemental investor groups."],
    ["<b>Other event-driven</b>", "Other Event-Driven manager candidates, excluding the focused group."],
    ["<b>Other HFR</b>", "Remaining HFR-linked candidates, outside focused/other event-driven groups."],
    ["<b>Other / unresolved</b>", "No qualifying HFR/supplemental link under these rules. This does not establish that the filer is passive."],
], [145,387],padding=4)
heading("Means and medians tell different stories")
figure("cohort-return-comparison.png",156)
labels={"focused":"Focused activist","other_event_driven":"Other event-driven","new_other_hfr":"Other HFR","other_unresolved":"Other / unresolved","expanded":"Aggregate: HFR + supplements*","all":"Aggregate: all screened events*"}
table([
    ["Group", "n", "Mean<br/>excess", "Median<br/>excess", "Beat ETF", "Mean excess<br/>95% interval"],
] + [
    [labels[k],str(group24[k]["calculated"]),f'{group24[k]["mean_excess"]*100:+.2f} pp',f'{group24[k]["median_excess"]*100:+.2f} pp',f'{group24[k]["fraction_beating_benchmark"]*100:.1f}%',f'{group24[k]["issuer_bootstrap_95"][0]*100:+.2f} to {group24[k]["issuer_bootstrap_95"][1]*100:+.2f} pp']
    for k in disjoint_keys+["expanded","all"]
], [159,40,71,71,60,131],padding=4)
p("The first four rows are disjoint: 56 + 14 + 46 + 578 = 694 calculable events. *Aggregates overlap: HFR + supplements = the first three rows (116); all = the first four (694). Do not add all six rows. These are stock-minus-assigned-ETF excess returns, not HFR fund returns. [E1, E6]","small")
p("<b>Meaning:</b> other HFR has the highest mean but a negative median and a very wide interval. All four groups have negative medians; none establishes a reliable selection advantage. Manager groups differ in companies, sectors, timing and data coverage, so raw cohort differences do not isolate skill.","small")

story.append(PageBreak())
p("From prepared data to an investable selection test","title")
p("Next research steps | Candidate mechanisms, not demonstrated alpha signals","meta")
heading("Extraction coverage is substantial; economic links need work")
figure("field-coverage.png",110)
p("15,813 selected 2013-2025 filings. *At least one extracted value, not complete person/ownership coverage. Bars overlap. Header IDs/CUSIPs do not establish validated fund/stock links; presence does not measure extraction accuracy. [E2]","small")
heading("Proposed signals and their investment mechanism")
table([
    ["Candidate signal", "Economic hypothesis", "Evidence needed"],
    ["<b>Manager quality / history</b><br/>Dated HFR peers; prior target-stock outcomes.", "Repeated execution skill may distinguish managers whose plans create value.", "Validate historical identities and availability; separate fund returns from outside-follower returns."],
    ["<b>Company economics</b><br/>Valuation, leverage, cash flow, liquidity.", "A credible catalyst may have more upside where value and financial capacity support it.", "Build dated fundamentals/market features; test against size, industry and risk explanations."],
    ["<b>Disclosed intent (NLP)</b><br/>Board change, asset sale, capital return; plan specificity.", "A concrete, feasible plan may change cash flows or capital allocation beyond what prices reflect.", "Validate text labels against source spans; compare ML with and without NLP on identical events."],
], [162,177,193])
heading("Proposed amendment buckets for extracting new information")
table([
    ["Information bucket", "Candidate fields / use"],
    ["<b>Ownership change</b>", "Shares, ownership %, dated buys/sales; distinguish additions/reductions from issuer share-count changes."],
    ["<b>Intent or campaign development</b>", "Changed Item 4 plans, board representation, settlements, asset sales or agreements; update thesis/catalyst evidence."],
    ["<b>Exit / reporting transition</b>", "Keep confirmed full exits, 5%-or-less disclosures and reporting-regime changes distinct; unresolved full-exit dates stay unknown."],
    ["<b>Identity / technical update</b>", "Reporting-person/group changes and corrections; improve attribution without assuming a trade."],
    ["<b>Unclear or incomplete</b>", "Preserve evidence and missingness for review; do not infer no activity from incomplete extraction."],
], [168,364],padding=4)
p("Proposed buckets are overlapping labels, not measured mutually exclusive counts. One amendment may change both stake and intent. Link it to prior filings, carry forward unchanged facts, and preserve source spans plus transaction/disclosure dates. This panel and full-exit labels are unfinished.","small")
p("<b>Next validation:</b> freeze dated inputs and compare simple following, structured ML, ML plus NLP, then amendment-driven adjustments under common trading/cost rules. Trade after disclosure; test downside, liquidity and shared exposures before concentrated sizing. Reserve unexposed or prospective evaluation; inspected history is development data.","small")
p("<b>Evidence:</b> E1: Sept 24 long-horizon return summary. E2: universe/staging/coverage audits. E3: Sept 30 HFR protocol/scorecards. E4: CRSP/FTSE sources and WRDS records. E5: <link href=\"https://www.sec.gov/divisions/corpfin/guidance/reg13d-interp.htm\" color=\"#146d76\">SEC guidance</link> and <link href=\"https://www.sec.gov/files/rules/final/2023/33-11253.pdf\" color=\"#146d76\">2023 final rule</link>. E6: frozen HFR matching/cohort code, Phase 1 registry and selection. Direct links in <link href=\"discussion-notes.html\" color=\"#146d76\">companion notes</link>.","small")
p("Prepared October 4, 2026 from preserved project evidence. AI-assisted synthesis and graphics; no new backtest, trained model, intent labels or changes to independent human-review materials.","small")

pdf=ROOT/"13D_Research_Brief_20261005_v3.pdf"
archive=ROOT/"versions/20261004-two-page-phases-sources.pdf"
if pdf.exists() and not archive.exists():
    archive.parent.mkdir(exist_ok=True);shutil.copy2(pdf,archive)
SimpleDocTemplate(str(pdf),pagesize=letter,leftMargin=40,rightMargin=40,topMargin=34,bottomMargin=40,title="13D research - visual professor discussion",author="Jeff Lu").build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(str(pdf));assert len(reader.pages)==6,f"Expected six pages, got {len(reader.pages)}"
text="\n".join(page.extract_text() for page in reader.pages)
for required in ("15,813","75,631","2013","23/56","694","Three phases","SEC EDGAR","CRSP via WRDS","Compustat"):
    assert required in text,required
assert "Questions for Professor" not in text
assert "Jeff Lu, CFA |" not in text and "Professor Michael Sternberg" not in text
assert "Hill" not in text
assert "Yahoo" not in text and "yfinance" not in text
assert "A funded account is a separate test" not in text and "-8.08" not in text and "Aratana" not in text
assert "Item 5(e)" in text and "full-exit date unknown" in text
for alias in ("Jeff_Lu_13D_Professor_Discussion_20261005.pdf", "Jeff_Lu_13D_Four_Page_Brief_20261005.pdf", "13D_Research_Brief_20261005_Revised.pdf"):
    shutil.copy2(pdf, ROOT/alias)
(ROOT/"verification.json").write_text(json.dumps({"pages":6,"figures":6,"data_graphs":5,"schematics":1,"tables":12,"source_hashes":facts["source_sha256"],"selection_reproduced":dict(reproduced),"phase1_sample_bridge":facts["phase1_sample_bridge"],"research_status":facts["status"],"visual_review":"pending"},indent=2)+"\n")
print(f"Created six-page PDF with 5 graphs, 1 routing diagram and 12 tables: {pdf}")
