"""Tier: 2. Audit focused disclosure forms, dominant relationships and exposures.
Inputs: frozen focused schedules, verified SEC submissions, pre-disclosure SIC.
Outputs: canonical evidence, bounded relationship notes, sensitivity report.
Identity: source bytes/hash exact; citations=text[start:end]; returns unchanged.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_disclosure_validation.py
"""

import hashlib
import html
import json
import re
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.disclosure_audit import cover_amendments, exposure
from activist13d.edgar.submission import parse_submission
from activist13d.phase1_baseline import summarize

BASE = ROOT / "research/runs/phase1-baseline/20260924-russell-returns-v1"
CONC = BASE.parent / "20260924-concentration-v1"
CHAR = BASE.parent / "20260924-benchmark-inputs-v1"
REG = BASE.parent / "20260924-feasibility-v2/event-candidates.jsonl"
OUT = BASE.parent / "20260924-disclosure-validation-v1"
PROTOCOL = ROOT / "research/protocol/phase1-disclosure-validation-v1.md"
BBB = "0001193805-20-000442"
NOTES = {
    BBB: "Item 2 expressly identifies Legion Partners Asset Management as investment adviser to the named funds. Item 4 describes a May 2019 cooperation agreement and subsequent investor-group dissolution. This supports the relationship, but the April 2020 filing is not evidence of a newly initiated campaign.",
    "0000921895-19-002974": "Item 2 expressly identifies Engine Capital Management as investment manager of Engine Capital and Engine Jet. This supports the fund-manager relationship; it does not establish that activist action caused the subsequent stock return.",
    "0001193805-22-001434": "Item 2 expressly identifies Starboard Value LP as investment manager of the listed funds and account. This supports the relationship; investor identity alone does not establish a specific intervention or its success.",
    "0000921895-20-000943": "Item 2 expressly identifies Legion Partners Asset Management as investment adviser of Legion Partners I and II. This supports the relationship; the filing remains separate from proof of a successful intervention.",
    "0000928464-20-000019": "The cover states Amendment No. 2, and Item 4 describes a share-class conversion after a planned spin-off did not occur. Item 5 identifies Icahn entities and Mr. Icahn as holders/controllers. The association is supported, but this is not a new initial disclosure.",
}


def cite(text, start, end, doc):
    return dict(
        document_id=doc["source_document_index"],
        filename=doc["filename"],
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        start=start,
        end=end,
        quote=text[start:end],
    )


def pct(v):
    return "—" if v is None else f"{100 * v:+.2f}"


def table(headers, rows):
    return (
        '<div class="scroll"><table><tr>'
        + "".join("<th>" + html.escape(str(x)) + "</th>" for x in headers)
        + "</tr>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(x)) + "</td>" for x in row) + "</tr>"
            for row in rows
        )
        + "</table></div>"
    )


def page(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + html.escape(title)
        + "</title><style>body{font:17px/1.65 system-ui;background:#f3f6f8;color:#243b50}main{max-width:1200px;margin:30px auto;padding:20px}section{background:white;padding:25px;margin:22px 0;border:1px solid #ddd}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}table{border-collapse:collapse;width:100%;font-size:15px}.scroll{overflow:auto}a{color:#155b91}.text{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style></head><body><main><h1>"
        + html.escape(title)
        + "</h1>"
        + body
        + "</main></body></html>"
    )


def main():
    assert (
        digest(BASE / "outcomes.json")
        == json.loads((BASE / "provenance.json").read_text())["outputs"]["outcomes.json"]
    )
    assert (
        digest(CONC / "events.json")
        == json.loads((CONC / "provenance.json").read_text())["outputs"]["events.json"]
    )
    freeze(OUT / "protocol.md", PROTOCOL.read_bytes())
    for p in [
        Path(__file__),
        ROOT / "src/activist13d/disclosure_audit.py",
        ROOT / "src/activist13d/edgar/submission.py",
        ROOT / "tests/test_disclosure_audit.py",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    registry = {
        r["accession"]: r for line in REG.read_text().splitlines() if (r := json.loads(line))
    }
    outcomes = json.loads((BASE / "outcomes.json").read_text())
    events = json.loads((CONC / "events.json").read_text())
    accessions = sorted(
        {a for rows in outcomes.values() for r in rows if r["focused"] for a in r["accessions"]}
    )
    audits = []
    raw_hashes = {}
    reviews = []
    for accession in accessions:
        r = registry[accession]
        source = ROOT / r["source_path"]
        raw = source.read_bytes()
        assert (
            len(raw) == r["source_bytes"] and hashlib.sha256(raw).hexdigest() == r["source_sha256"]
        )
        raw_hashes[r["source_path"]] = r["source_sha256"]
        parsed = parse_submission(raw)
        assert parsed["accession"] == accession
        docs = parsed["documents"]
        primary = [
            d
            for d in docs
            if d["type"] in {"SC 13D", "SCHEDULE 13D", "SC 13D/A", "SCHEDULE 13D/A"} and d["text"]
        ]
        assert len(primary) == 1
        doc = primary[0]
        text = doc["text"]
        flags = cover_amendments(text)
        for d in docs:
            d["text_sha256"] = (
                hashlib.sha256(d["text"].encode()).hexdigest() if d["text"] is not None else None
            )
        freeze(
            OUT / "documents" / f"{accession}.json",
            encode(
                dict(
                    accession=accession,
                    raw_source=r["source_path"],
                    raw_sha256=r["source_sha256"],
                    documents=docs,
                )
            ),
        )
        body_hits = [
            cite(text, m.start(), min(len(text), m.end() + 220), doc)
            for m in re.finditer(r"(?:This\s+)?Amendment\s+No\.?\s*\d+", text, re.I)
        ]
        audit = dict(
            accession=accession,
            company=" / ".join(s["name"] for s in r["subjects"]),
            metadata_form=r["form"],
            document_form=doc["type"],
            source_sha256=r["source_sha256"],
            source_bytes=len(raw),
            source_path=r["source_path"],
            cover_flags=[
                cite(text, f["start"], f["end"], doc) | {"number": f["number"]} for f in flags
            ],
            numbered_body_mentions=body_hits,
            excluded_amendment=bool(flags or doc["type"].endswith("/A")),
            limitation="No detected amendment does not certify first campaign or complete document eligibility.",
        )
        audits.append(audit)
        if accession in NOTES:
            citations = []
            for pat in [
                r"Item\s*2\.?\s*Identity",
                r"Item\s*4\.?\s*Purpose",
                r"Item\s*5\.?\s*Interest",
            ]:
                m = re.search(pat, text, re.I)
                if m:
                    citations.append(cite(text, m.start(), min(len(text), m.start() + 3500), doc))
            review = dict(
                accession=accession,
                company=audit["company"],
                review_type="outcome_aware_assistant_source_interpretation",
                reviewer="OpenAI Codex; exact model version unavailable",
                instruction="Validate named contemporaneous fund/manager relationship and initial-disclosure eligibility; no intent codebook labels.",
                note=NOTES[accession],
                citations=citations,
                cover_flags=audit["cover_flags"],
            )
            reviews.append(review)
        reader = (
            '<p><a href="../index.html">Audit report</a></p><p>Accession '
            + accession
            + " · source SHA-256 "
            + r["source_sha256"]
            + "</p>"
        )
        if accession in NOTES:
            reader += (
                "<section><h2>Outcome-aware assistant review</h2><p>"
                + html.escape(NOTES[accession])
                + "</p><p>This is a bounded relationship/eligibility review, not a human reference or intent label.</p></section>"
            )
        for d in docs:
            reader += (
                "<section><details><summary>"
                + html.escape(str(d["filename"]) + " — " + str(d["type"]))
                + '</summary><div class="text">'
                + html.escape(
                    d["text"] or "[Binary or unreadable attachment retained in raw submission]"
                )
                + "</div></details></section>"
            )
        freeze(OUT / "documents" / f"{accession}.html", page(audit["company"], reader))
    bad = {r["accession"] for r in audits if r["excluded_amendment"]}
    observations = json.loads((CHAR / "observations.json").read_text())
    chars = {(r["accession"], r["entry"]): r for r in observations}
    sensitivity = {}
    exposures = {}
    tagged = {}
    for h, rows in events.items():
        clean = [r for r in rows if not set(r["accessions"]) & bad]
        variants = {
            "original": rows,
            "exclude_numbered_amendments": clean,
            "also_exclude_prior_BBBY_campaign": [r for r in clean if BBB not in r["accessions"]],
            "clean_exclude_2020": [r for r in clean if r["year"] != "2020"],
            "clean_exclude_2020Q2": [
                r for r in clean if not "2020-04-01" <= r["entry"] <= "2020-06-30"
            ],
        }
        sensitivity[h] = {k: summarize(v) for k, v in variants.items()}
        if h == "252":
            for name, sub in [("original", rows), ("exclude_numbered_amendments", clean)]:
                enriched = []
                for r in sub:
                    obs = chars.get((r["accession"], r["entry"]))
                    if obs:
                        assert obs["characteristics_date"] < r["entry"]
                    enriched.append(
                        dict(
                            r,
                            industry=obs["industry_2digit"]
                            if obs and obs["industry_2digit"]
                            else "missing",
                            siccd=obs["fields"]["siccd"] if obs else None,
                            characteristics_date=obs["characteristics_date"] if obs else None,
                            quarter=r["entry"][:4] + "Q" + str((int(r["entry"][5:7]) - 1) // 3 + 1),
                        )
                    )
                tagged[name] = enriched
                exposures[name] = {
                    key: exposure(enriched, key) for key in ["industry", "year", "quarter"]
                }
    for name, value in [
        ("filing-audit.json", audits),
        ("relationship-reviews.json", reviews),
        ("sensitivity.json", sensitivity),
        ("exposures.json", exposures),
        ("exposure-events.json", tagged),
    ]:
        freeze(OUT / name, encode(value))
    body = f'<nav><a href="../../../../START-HERE.html">Project home</a></nav><p>24 September 2026 · Development audit · Earlier results preserved</p><section><h2>A material eligibility issue</h2><p>Across {len(audits)} unique scheduled focused accessions, {len(bad)} documents explicitly identify themselves as amendments despite the initial-form metadata. These must not be treated as fresh initial disclosures. The comparisons below remove them from existing schedules; they are sensitivities, not a fully rebuilt baseline.</p>'
    body += (
        table(
            ["Company", "Accession", "Cover evidence"],
            [
                [r["company"], r["accession"], "; ".join(f["quote"] for f in r["cover_flags"])]
                for r in audits
                if r["excluded_amendment"]
            ],
        )
        + "</section>"
    )
    body += (
        "<section><h2>How the result changes</h2><p>Gross mean stock-minus-assigned-Russell-ETF returns, in percentage points. Original timing, return calculation and other eligibility rules are unchanged. Six months remains primary. Exclusions do not create replacement trades.</p>"
        + table(
            ["Sensitivity", "3-month n / excess", "6-month n / excess", "12-month n / excess"],
            [
                [
                    k,
                    *[
                        str(sensitivity[h][k]["calculated"])
                        + " / "
                        + pct(sensitivity[h][k].get("mean_excess"))
                        for h in ["63", "126", "252"]
                    ],
                ]
                for k in sensitivity["252"]
            ],
        )
        + "<p>Bed Bath &amp; Beyond is shown separately because its April 2020 disclosure describes prior 2019 cooperation and a disbanded investor group. This is a first-campaign sensitivity; its standalone initial form is not thereby reclassified as an amendment.</p></section>"
    )
    body += "<section><h2>Relationships behind the five largest twelve-month winners</h2><p>These source-based assistant reviews support the particular disclosed associations; they do not validate the complete HFR manager universe, establish first-ever campaigns or create NLP intent labels.</p>"
    for review in reviews:
        body += (
            '<p><a href="documents/'
            + review["accession"]
            + '.html">'
            + html.escape(review["company"])
            + "</a>: "
            + html.escape(review["note"])
            + "</p>"
        )
    body += "</section><section><h2>Industry and entry-period concentration</h2><p>Two-digit SIC uses the saved pre-disclosure CRSP classification. These are broad industry groups, not GICS sectors or an industry-adjusted return model. Tables below exclude the numbered amendments. Contributions sum to that sample’s mean excess; removing a group recalculates the average over remaining events.</p>"
    for key in ["industry", "year", "quarter"]:
        body += (
            "<h3>"
            + key.title()
            + "</h3>"
            + table(
                [
                    key,
                    "Events",
                    "Mean excess (pp)",
                    "Contribution (pp)",
                    "Mean excluding group (pp)",
                ],
                [
                    [k, v["n"], pct(v["mean"]), pct(v["contribution"]), pct(v["leave_out"]["mean"])]
                    for k, v in sorted(
                        exposures["exclude_numbered_amendments"][key].items(),
                        key=lambda x: -x[1]["contribution"],
                    )
                ],
            )
        )
    body += """<p>See the <a href="https://www.osha.gov/data/sic-manual">official SIC manual</a> for code definitions. Concentration in a year or industry does not establish that exposure explains the return causally; no sector-matched benchmark or factor regression was run.</p></section><section><h2>Implications</h2><p>The headline is provisional until initial/amended forms and prior campaign history are resolved across the full event universe. A manager appearing in the disclosure is different from a newly launched activist campaign. In particular, the largest winner already had a disclosed cooperation history.</p><p>Next, rebuild initial-event eligibility across the universe with body/header conflicts resolved and distinguish standalone initial forms from first manager–issuer campaigns. Then perform industry/time-matched comparisons and portfolio accounting before fresh-data evaluation. Do not promote these outcome-aware reviews to human labels or tune the investor list to the winners.</p><p>All earlier uncertainty remains: selected Russell membership coverage, lagged monthly assignments, unresolved vendor row totals, retrospective supplemental manager selection and unverified HFR availability. Entries cover March 2018–December 2022, outcomes through 2023; later outcomes and human-review issuers remain protected. Entry is the second exchange-session open after acceptance, with 63/126/252-session closing exits. Shared overlap exclusions and delisting-to-zero-cash handling are unchanged. These are equally weighted gross event returns, not funded portfolio results; trading costs and capital constraints are omitted.</p></section><section><details><summary>Evidence</summary><p><a href="filing-audit.json">All audited filings and exact amendment spans</a> · <a href="relationship-reviews.json">Relationship evidence and assistant interpretations</a> · <a href="sensitivity.json">Return sensitivities and uncertainty</a> · <a href="exposures.json">Industry/year/quarter statistics</a> · <a href="exposure-events.json">Dated SIC inputs per event</a> · <a href="provenance.json">Hashes and sources</a> · <a href="../../../protocol/phase1-disclosure-validation-v1.md">Frozen rules</a></p><p>Canonical documents and exact offsets are preserved. Unreadable attachments remain explicitly marked. This review does not certify complete incorporated-reference coverage.</p></details></section>"""
    freeze(
        OUT / "index.html", page("Validating the activist signal: disclosures and exposures", body)
    )
    sources = [
        BASE / "outcomes.json",
        CONC / "events.json",
        CHAR / "observations.json",
        REG,
        PROTOCOL,
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in sources},
                raw_sources=raw_hashes,
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    print("AUDITED", len(audits), "AMENDMENTS", sorted(bad))
    for h, variants in sensitivity.items():
        print(
            h,
            {
                k: (v["calculated"], round(v.get("mean_excess", 0) * 100, 2))
                for k, v in variants.items()
            },
        )
    print("EXPOSURES", encode(exposures["exclude_numbered_amendments"]))


if __name__ == "__main__":
    main()
