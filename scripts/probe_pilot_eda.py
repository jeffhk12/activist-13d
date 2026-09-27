"""Describe the ten cached pilot filings without network or inference API calls.

Inputs: pilot JSONL, frozen submissions, and the dated preliminary triage note.
Outputs: Markdown EDA and JSON metrics with source and calculation provenance.
Identity: gap_cd = filing date - candidate event date; coverage = present / n;
          text length = Unicode characters; percentages are never summed.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/probe_pilot_eda.py
"""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
# Exploratory grouping of the dated triage judgments; not a production taxonomy.
# Each span must match the cached Item 4 or the explicitly named exhibit.
TRIAGE = {
    "0001104659-24-000323": ("Sponsor / distribution", "Chavant Capital expects to distribute to its members", None),
    "0001398344-24-000853": ("Concrete governance proposal", "The stockholders urge the Board to seek stockholder approval", "fp0086902-1_ex7b.htm"),
    "0001104659-24-024047": ("Insider / compensation / control", "his position as Interim Principal Executive Officer", None),
    "0001493152-24-008748": ("Investment / no specific current demand", "no present intention of doing so", None),
    "0001193125-24-081594": ("Transaction context unresolved", "lock-up period as part of the Transaction", None),
    "0000807249-25-000003": ("Investment / no specific current demand", "may suggest or take a position", None),
    "0001640334-25-000152": ("Insider / compensation / control", "as an officer and director of PreCheck", None),
    "0001104659-25-014424": ("Sponsor / distribution", "newly organized blank check company", None),
    "0000950142-25-000685": ("Insider / compensation / control", "the Issuer's Chief Executive Officer", None),
    "0001477932-25-002177": ("Insider / compensation / control", "sole director of the Issuer", None),
}


def calendar_gap(event, filed):
    """Return descriptive calendar days; missing events remain missing."""
    return (date.fromisoformat(filed) - date.fromisoformat(event)).days if event else None


def summarize(values):
    """Describe nonmissing values without imputing absent observations."""
    present = [v for v in values if v is not None]
    return {"n": len(present), "min": min(present) if present else None,
            "median": median(present) if present else None,
            "max": max(present) if present else None}


def build(records):
    """Compute facts and attach explicitly preliminary, source-checked judgments."""
    accessions = [r["accession"] for r in records]
    if len(set(accessions)) != len(accessions) or set(accessions) != set(TRIAGE):
        raise ValueError("This probe requires exactly the ten distinct pilot accessions")
    rows = []
    for r in sorted(records, key=lambda r: (r["index_filing_date"], r["accession"])):
        kind, span, exhibit = TRIAGE[r["accession"]]
        evidence = r["item4_text"] if exhibit is None else next(
            d["text"] for d in r["documents"] if d["filename"] == exhibit)
        if span not in (evidence or ""):
            raise ValueError(f"Supporting span missing for {r['accession']}")
        rows.append({
            "accession": r["accession"], "filer": "; ".join(p["name"] for p in r["filers"]),
            "subject": "; ".join(p["name"] for p in r["subjects"]),
            "filing_date": r["index_filing_date"], "event_date_candidate": r["event_date"],
            "calendar_gap": calendar_gap(r["event_date"], r["index_filing_date"]),
            "format": r["parser_source"], "cusip_candidate": r["cusip"],
            "item4_characters": len(r["item4_text"]) if r["item4_text"] else None,
            "documents": len(r["documents"]),
            "exhibits": sum((d["type"] or "").startswith("EX-") for d in r["documents"]),
            "ownership_status": r["ownership_status"],
            "reporting_persons_xml": r["reporting_persons_xml"],
            "preliminary_kind": kind, "judgment_status": "model_assisted_not_validated",
            "supporting_span": span, "evidence_location": exhibit or "Item 4 candidate",
            "source_url": r["source_url"], "source_path": r["source_path"],
            "source_sha256": r["source_sha256"],
        })
    return {
        "n": len(rows), "sample": "five evenly spaced initial filings in each of 2024 Q1 and 2025 Q1",
        "not_chronological_first_ten": True, "not_representative": True,
        "judgment_note": "Derived from dated Codex triage, not frozen-protocol labels; model version and original prompt hash unavailable. Not eligible for training or independent validation.",
        "kinds": dict(Counter(r["preliminary_kind"] for r in rows)),
        "formats": dict(Counter(r["format"] for r in rows)),
        "coverage": {"cusip": sum(bool(r["cusip_candidate"]) for r in rows),
                     "item4": sum(r["item4_characters"] is not None for r in rows),
                     "event_date": sum(r["event_date_candidate"] is not None for r in rows),
                     "xml_ownership_filings": sum(bool(r["reporting_persons_xml"]) for r in rows),
                     "filings_with_exhibits": sum(r["exhibits"] > 0 for r in rows)},
        "calendar_gap": summarize([r["calendar_gap"] for r in rows]),
        "item4_characters": summarize([r["item4_characters"] for r in rows]),
        "rows": rows,
    }


def render(result):
    """Render the descriptive probe, preserving source links and limitations."""
    n = result["n"]
    lines = ["# EDA — ten Schedule 13D pilot filings", "",
             "These are the ten already collected pilot filings, **not the earliest ten filings in EDGAR**: five evenly spaced initial accessions from 2024 Q1 and five from 2025 Q1. The sample is unscreened and nonrepresentative.", "",
             "## What kind of filings?", "",
             "The following mutually exclusive buckets summarize preliminary model-assisted reading, not verified campaign labels. Insider, sponsor, and investment contexts can overlap; grouping here is exploratory. A negative bucket does not prove no activism occurred.", "",
             "| Preliminary context | Filings | Share of pilot |", "|---|---:|---:|"]
    for kind, count in result["kinds"].items():
        lines.append(f"| {kind} | {count}/{n} | {100 * count / n:.0f}% |")
    lines += ["", "Bulldog has a concrete shareholder governance proposal in Exhibit B. The remaining records require context review; generic language about influencing management or possible mergers is insufficient by itself. This is a small-sample hypothesis about screening needs, not a population result.", "",
              "## Filing-by-filing probe", "",
              "Gap is filing date minus candidate cover-page event date in calendar days. It is neither campaign duration nor a legal timeliness determination.", "",
              "| Filer → subject (source) | Filed | Event candidate | Gap, days | Item 4 chars | Preliminary context |",
              "|---|---|---|---:|---:|---|"]
    for r in result["rows"]:
        lines.append(f"| [{r['filer']} → {r['subject']}](pilot-filings/{r['accession']}.md) | {r['filing_date']} | {r['event_date_candidate']} | {r['calendar_gap']} | {r['item4_characters']} | {r['preliminary_kind']} |")
    lines += ["", "## Data coverage and distributions", "",
              "| Field | Available filings |", "|---|---:|"]
    for field, count in result["coverage"].items():
        lines.append(f"| {field} | {count}/{n} |")
    for name in ("calendar_gap", "item4_characters"):
        s = result[name]
        lines += ["", f"{name} (n={s['n']}): min **{s['min']}**, median **{s['median']}**, max **{s['max']}**."]
    lines += ["", f"Formats: {result['formats']}. Format and cohort coincide in this pilot, so differences cannot be attributed to format independently of time or sample composition.", "",
              "Ownership coverage is parser availability, not economic missingness: legacy percentages have not been normalized. Per-person XML fields are retained below and in JSON, without summing overlapping ownership. No whole-sample ownership average is defensible yet.", "",
              "## Per-person XML ownership fields", ""]
    for r in result["rows"]:
        if r["reporting_persons_xml"]:
            lines += [f"### {r['accession']}", "", "Source-preserved strings; reported persons may share the same underlying shares. Blank/ambiguous fields are not imputed.", "",
                      "| Reporting person | Aggregate shares reported | Percent of class reported | Excludes shares flag |",
                      "|---|---:|---:|---|"]
            for person in r["reporting_persons_xml"]:
                cells = [" / ".join(person.get(key, [])) or "Missing" for key in (
                    "reportingPersonName", "aggregateAmountOwned", "percentOfClass", "isAggregateExcludeShares")]
                lines.append("| " + " | ".join(cell.replace("|", "/") for cell in cells) + " |")
            lines.append("")
    lines += ["## Interpretation and next probes", "",
              "- The baseline of treating every initial 13D as an activist campaign is not supported by this review. Keep filing eligibility separate from demand classification.",
              "- Bulldog's short Item 4 points to Exhibit B. Text length measures extraction size, not intent strength or evidence completeness.",
              "- Long calendar gaps need raw cover-page and transaction-context review before use as a disclosure-delay variable. Do not silently trim or reinterpret them.",
              "- Review incorporated Items 3/6 and the Explanatory Note; resolve manager/issuer identities, then assemble amendments. Campaign outcomes and returns are not in this pilot.",
              "- Keep model-assisted exploratory judgments out of the independent human validation sample.", "",
              "## Evidence for preliminary judgments", ""]
    for r in result["rows"]:
        lines += [f"- [{r['accession']}]({r['source_url']}), {r['evidence_location']}: “{r['supporting_span']}”. Context: **{r['preliminary_kind']}** (model judgment)."]
    lines += ["", "Rationales and unresolved evidence: [dated triage](../docs/PILOT-TRIAGE-2026-09-09.md). Source hashes, individual records, calculation definitions, and script/input hashes are in [EDA JSON](PILOT-EDA.json). Reproduce with `.venv/bin/python scripts/probe_pilot_eda.py`; no network calls.", ""]
    return "\n".join(lines)


def main():
    input_path = ROOT / "data/interim/pilot/filings.jsonl"
    records = [json.loads(line) for line in input_path.read_text().splitlines()]
    for r in records:
        if hashlib.sha256((ROOT / r["source_path"]).read_bytes()).hexdigest() != r["source_sha256"]:
            raise ValueError(f"Source hash mismatch: {r['accession']}")
    result = build(records)
    result["provenance"] = {
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "triage_sha256": hashlib.sha256((ROOT / "research/docs/PILOT-TRIAGE-2026-09-09.md").read_bytes()).hexdigest(),
        "formulas": {"calendar_gap": "filing_date - event_date_candidate, calendar days",
                     "coverage": "number of present values / ten filings",
                     "item4_characters": "len(parsed Item 4 string), Unicode characters"},
    }
    output = ROOT / "research/runs"
    output.mkdir(exist_ok=True)
    (output / "PILOT-EDA.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    (output / "PILOT-EDA.md").write_text(render(result))
    print(json.dumps({k: v for k, v in result.items() if k not in {"rows", "provenance"}}, indent=2))


if __name__ == "__main__":
    main()
