"""Produce the fixed 52-source deterministic dataset and a factual HTML review.

Inputs: verified baseline manifest, frozen sources, deterministic-v1 modules/schema.
Outputs: per-filing JSON, related JSONL tables, coverage, provenance, review HTML.
Identity: present coverage=count(status=='present') / field opportunities;
all52 retained, exact citations match source, repeated extraction payloads equal.
Tier: 1. No model or network calls. No semantic labels or automatic aggregation.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/run_deterministic.py
"""

import json
import platform
import sys
from collections import Counter, defaultdict
from html import escape
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from jsonschema import Draft202012Validator  # noqa: E402

from activist13d.edgar.deterministic import VERSION, extract, sha, verify_citations  # noqa: E402
from activist13d.local_paths import resolve_project_path  # noqa: E402

OUT = ROOT / "research/runs/deterministic-extraction/20260923-v1"
PACK = ROOT / "review/drafts/deterministic-52-20260923"
TABLES = [
    "filings",
    "issuers",
    "filing_entities",
    "reporting_persons",
    "securities",
    "ownership",
    "documents",
    "sections",
    "references",
    "quality_issues",
]
SCHEMA = json.loads((ROOT / "research/protocol/deterministic-schema-v1.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
FIELD_VALIDATOR = Draft202012Validator(SCHEMA["$defs"]["field"])


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def fields(node, path=""):
    if isinstance(node, dict):
        if {"raw_value", "value", "status", "rule", "evidence"} <= node.keys():
            yield path, node
        else:
            for key, child in node.items():
                yield from fields(child, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for child in node:
            yield from fields(child, path)


def validate(record, bundle):
    VALIDATOR.validate(record)
    for _, value in fields(record):
        FIELD_VALIDATOR.validate(value)
    people = {x["person_id"] for x in record["reporting_persons"]}
    securities = {x["security_id"] for x in record["securities"]}
    assert len(people) == len(record["reporting_persons"])
    assert len(securities) == len(record["securities"])
    for row in record["ownership"]:
        assert row["person_id"] in people and row["security_id"] in securities
    return verify_citations(record, bundle)


STYLE = "body{font:16px/1.55 system-ui,sans-serif;color:#203448;background:#f4f6f8;margin:0}main{max-width:1300px;margin:auto;padding:32px}section{background:white;border:1px solid #dce3e9;padding:24px;margin:20px 0;border-radius:8px}h1{font-size:32px}h2{font-size:24px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9;overflow-wrap:anywhere}th{background:#eaf1f6}a{color:#155c99}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;max-height:450px;overflow:auto}.muted{color:#647587}.warning{background:#fff3dc;padding:15px}.scroll{overflow-x:auto}details{margin:8px 0}summary{cursor:pointer}code{overflow-wrap:anywhere}td.value{max-width:480px}.status{white-space:nowrap}textarea{width:100%;min-height:70px}@media print{body{background:white}main{padding:0}section{border:0}details{break-inside:avoid}}"


def page(title, content):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + escape(title)
        + "</title><style>"
        + STYLE
        + "</style></head><body><main>"
        + content
        + "</main></body></html>"
    )


def show(value):
    if value is None:
        return '<span class="muted">null</span>'
    return escape(str(value))


def evidence_html(value):
    evidence = value.get("evidence", [])
    out = []
    for e in evidence:
        out.append(
            "<details><summary>"
            + escape(str(e.get("document_id", "XML")))
            + " "
            + escape(str(e.get("start", e.get("element_path", ""))))
            + "</summary><pre>"
            + escape(json.dumps(e, indent=2, ensure_ascii=False))
            + "</pre></details>"
        )
    if value.get("alternatives"):
        out.append(
            "<details><summary>Competing candidates</summary><pre>"
            + escape(encode(value["alternatives"]))
            + "</pre></details>"
        )
    return "".join(out)


def record_page(record, bundle):
    accession = record["accession"]
    content = (
        '<a href="index.html">← All 52 filings</a><h1>'
        + accession
        + "</h1><p>Deterministic candidates—not verified ownership, entity matches or investment judgments. Holdings can overlap; do not sum reporting people.</p>"
    )
    content += (
        '<p><a href="'
        + escape(bundle["source_url"], quote=True)
        + '">SEC raw submission</a> · <a href="../reading-room-20260923/'
        + accession
        + '.html">Readable source companion</a> · <a href="../../../research/runs/deterministic-extraction/20260923-v1/records/'
        + accession
        + '.json">Complete factual JSON</a></p>'
    )
    content += (
        '<p class="warning">The first Basswood filing has previously been exposed to model interpretation. This pack does not use those answers. No interpretive labels are supplied.</p>'
        if accession == "0000899140-19-000386"
        else ""
    )
    content += '<section><h2>Cover-page ownership at a glance</h2><p>Each row is a separate disclosed person. Null means unresolved or not extracted; it is not zero. Expand the related records below for exact quotations and alternatives.</p><div class="scroll"><table><tr><th>Reporting person</th><th>Type code</th><th>Citizenship / organization</th><th>Beneficial shares</th><th>Filed %</th><th>Sole voting</th><th>Shared voting</th><th>Sole disposition</th><th>Shared disposition</th></tr>'
    for person in record["reporting_persons"]:
        holdings = [row for row in record["ownership"] if row["person_id"] == person["person_id"]]
        for holding in holdings:
            values = [
                person["name"],
                person["person_code"],
                person["citizenship"],
                *[
                    holding[k]
                    for k in [
                        "aggregate_shares",
                        "percent_of_class",
                        "sole_voting_power",
                        "shared_voting_power",
                        "sole_dispositive_power",
                        "shared_dispositive_power",
                    ]
                ],
            ]
            content += (
                "<tr>"
                + "".join(
                    "<td>"
                    + show(v["value"])
                    + (
                        ""
                        if v["status"] == "present"
                        else "<br><small>" + escape(v["status"]) + "</small>"
                    )
                    + "</td>"
                    for v in values
                )
                + "</tr>"
            )
    content += "</table></div></section>"
    for table in TABLES:
        rows = record[table]
        content += "<section><h2>" + table.replace("_", " ").title() + "</h2>"
        if not rows:
            content += "<p>No rows extracted; this does not establish absence in the filing.</p>"
        for number, row in enumerate(rows, 1):
            content += (
                "<details"
                + (
                    " open"
                    if table
                    in [
                        "filings",
                        "issuers",
                        "filing_entities",
                        "securities",
                    ]
                    else ""
                )
                + "><summary>Record "
                + str(number)
                + " "
                + escape(str(row.get("person_id", row.get("document_id", ""))))
                + "</summary><table><tr><th>Field</th><th>Normalized value</th><th>Status / rule</th><th>Source evidence</th></tr>"
            )
            for key, value in row.items():
                if isinstance(value, dict) and "raw_value" in value and "status" in value:
                    rendered = show(value["value"])
                    if len(rendered) > 650:
                        rendered = (
                            "<details><summary>Full extracted span</summary><pre>"
                            + rendered
                            + "</pre></details>"
                        )
                    content += (
                        "<tr><td>"
                        + escape(key)
                        + '</td><td class="value">'
                        + rendered
                        + "</td><td>"
                        + show(value["status"])
                        + "<br><small>"
                        + show(value["rule"])
                        + "</small></td><td>"
                        + evidence_html(value)
                        + "</td></tr>"
                    )
                else:
                    content += (
                        "<tr><td>"
                        + escape(key)
                        + '</td><td colspan="3">'
                        + (
                            ("<pre>" + escape(encode(value)) + "</pre>")
                            if isinstance(value, (dict, list))
                            else show(value)
                        )
                        + "</td></tr>"
                    )
            content += "</table></details>"
        content += "</section>"
    content += '<section><h2>Interpretive review</h2><table><tr><th>Activist / hedge-fund / eligibility / intent / investment assessment</th><td></td></tr></table><p class="muted">Intentionally blank. This read-only factual report does not collect or overwrite human answers.</p></section>'
    return page(accession, content)


def main():
    if (OUT / "FINALIZED.json").exists():
        raise SystemExit(
            "Run already handed off. Preserve it; use a new dated/versioned output for changed code or inputs."
        )
    manifest = json.loads((OUT / "input-manifest.json").read_text())
    baseline = json.loads((OUT / "baseline.json").read_text())
    assert len(manifest) == 52 and len({r["accession"] for r in manifest}) == 52
    records = []
    bundles = {}
    citations = 0
    failures = []
    coverage = defaultdict(Counter)
    issues = []
    frozen_inputs = {}
    for item in manifest:
        path = ROOT / item["bundle_path"]
        assert sha(path.read_bytes()) == item["bundle_sha256"]
        bundle = json.loads(path.read_text())
        accession = bundle["accession"]
        bundles[accession] = bundle
        source = resolve_project_path(bundle["source_path"], ROOT)
        frozen_inputs[str(path)] = sha(path.read_bytes())
        frozen_inputs[str(source)] = sha(source.read_bytes())
        try:
            record = extract(bundle, source.read_bytes())
            citations += validate(record, bundle)
            replay = extract(bundle, source.read_bytes())
            assert encode(record) == encode(replay), "Non-deterministic extraction"
        except Exception as exc:
            failures.append(
                {"accession": accession, "error": str(exc), "exception_type": type(exc).__name__}
            )
            record = {"parser_version": VERSION, "accession": accession, **{k: [] for k in TABLES}}
            record["filings"] = [
                {
                    "accession": accession,
                    "parsing_status": "failed",
                    "source_sha256": bundle["source_sha256"],
                }
            ]
            record["quality_issues"] = [
                {"accession": accession, "issue_type": "processing_failure", "detail": str(exc)}
            ]
        for table in TABLES:
            if table == "quality_issues":
                continue
            for row_no, row in enumerate(record[table]):
                for key, value in fields(row):
                    coverage[table + "." + key][value["status"]] += 1
                    if value["status"] != "present":
                        record["quality_issues"].append(
                            {
                                "accession": accession,
                                "table": table,
                                "row": row_no,
                                "person_id": row.get("person_id"),
                                "field": key,
                                "issue_type": value["status"],
                                "candidates": value.get("alternatives", []),
                                "evidence": value.get("evidence", []),
                            }
                        )
        # Normalize only issue metadata; do not change quoted source or extracted values.
        for issue in record["quality_issues"]:
            issue.setdefault("accession", accession)
        records.append(record)
        issues += record["quality_issues"]
    coverage_rows = [
        {
            "field": key,
            "denominator": sum(counts.values()),
            "statuses": dict(sorted(counts.items())),
        }
        for key, counts in sorted(coverage.items())
    ]
    summary = {
        "sample_size": 52,
        "sample_type": "purposive development sample; all legacy HTML/text",
        "processed": 52 - len(failures),
        "failures": failures,
        "text_citations_verified": citations,
        "replay": "all successfully extracted records reproduced byte-identical payloads before quality-queue expansion",
        "row_counts": {table: sum(len(r[table]) for r in records) for table in TABLES},
        "filing_coverage": {
            "denominator": 52,
            "with_detected_cover_people": sum(bool(r["reporting_persons"]) for r in records),
            "with_any_aggregate_shares": sum(
                any(x["aggregate_shares"]["status"] == "present" for x in r["ownership"])
                for r in records
            ),
            "with_all_detected_person_aggregate_shares": sum(
                bool(r["ownership"])
                and all(x["aggregate_shares"]["status"] == "present" for x in r["ownership"])
                for r in records
            ),
            "section_present": {
                f"ITEM {n}": sum(
                    any(
                        s["section"] == f"ITEM {n}" and s["field"]["status"] == "present"
                        for s in r["sections"]
                    )
                    for r in records
                )
                for n in range(1, 8)
            },
            "note": "Detected-person counts do not certify every person was located.",
        },
        "baseline": baseline["coverage"],
        "field_coverage": coverage_rows,
        "limitation": "Availability, not semantic accuracy. No empirical XML coverage in this sample.",
    }
    for path, digest in frozen_inputs.items():
        assert sha(Path(path).read_bytes()) == digest
    for directory in [OUT / "records", OUT / "tables", PACK]:
        directory.mkdir(parents=True, exist_ok=True)
    for record in records:
        (OUT / "records" / f"{record['accession']}.json").write_text(encode(record))
        (PACK / f"{record['accession']}.html").write_text(
            record_page(record, bundles[record["accession"]])
        )
    for table in TABLES:
        (OUT / "tables" / f"{table}.jsonl").write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for r in records
                for row in r[table]
            )
        )
    (OUT / "coverage.json").write_text(encode(summary))
    source_files = [
        Path(__file__),
        ROOT / "scripts/extraction_protocol/deterministic_baseline.py",
        ROOT / "scripts/extraction_protocol/verify_deterministic_run.py",
        *sorted((ROOT / "tests").glob("test_deterministic*.py")),
        *sorted((ROOT / "src/activist13d/edgar").glob("deterministic*.py")),
        ROOT / "src/activist13d/edgar/submission.py",
        ROOT / "src/activist13d/local_paths.py",
        ROOT / "research/protocol/deterministic-schema-v1.json",
        ROOT / "research/protocol/deterministic-rules-v1.md",
    ]
    provenance = {
        "parser_version": VERSION,
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "input_manifest_sha256": sha((OUT / "input-manifest.json").read_bytes()),
        "source_hashes": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in source_files},
        "input_preservation": "all 52 raw sources and bundles unchanged after extraction",
        "model_calls": 0,
        "network_calls": 0,
        "review_pack": str(PACK),
    }
    (OUT / "provenance.json").write_text(encode(provenance))
    (OUT / "environment.json").write_text(
        encode(
            sorted(
                [{"name": d.metadata["Name"], "version": d.version} for d in distributions()],
                key=lambda d: (d["name"] or "").lower(),
            )
        )
    )
    (OUT / "code").mkdir(exist_ok=True)
    for path in source_files:
        target = OUT / "code" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    content = (
        '<a href="../../../START-HERE.html">← Project start</a><h1>52-filing deterministic facts</h1><p>Source-backed parser candidates. No LLM labels, investment outcomes or inferred campaign identities.</p><p><b>'
        + str(summary["processed"])
        + "/52 processed; "
        + str(len(failures))
        + ' failures.</b> All 52 are legacy HTML/text. XML is fixture-tested separately. Coverage describes availability, not correctness.</p><p><a href="0000899140-19-000386.html">Start with filing 1: MidSouth / Basswood</a> · <a href="issues.html">Missing/conflicting field queue</a> · <a href="../../../research/runs/deterministic-extraction/20260923-v1/coverage.json">Full coverage JSON</a></p><p><code>'
        + str(PACK)
        + "</code></p><section><h2>Baseline and current coverage</h2><p>Original parser: CUSIP 50/52; event date 46/52; Item 4 51/52; legacy ownership 0/52. Current counts below retain ambiguities and missing fields.</p><table><tr><th>Attribute</th><th>Present</th><th>Opportunities</th><th>Other statuses</th></tr>"
    )
    for row in coverage_rows:
        if row["field"].startswith(("filings.", "ownership.", "reporting_persons.", "securities.")):
            content += (
                "<tr><td>"
                + escape(row["field"])
                + "</td><td>"
                + str(row["statuses"].get("present", 0))
                + "</td><td>"
                + str(row["denominator"])
                + "</td><td>"
                + escape(str({k: v for k, v in row["statuses"].items() if k != "present"}))
                + "</td></tr>"
            )
    content += "</table></section><section><h2>All filings</h2><table><tr><th>Accession</th><th>Header issuer</th><th>Cover people</th><th>Ownership rows</th><th>Quality issues</th></tr>"
    for record in records:
        name = "; ".join(str(r["name"]["value"]) for r in record["issuers"])
        content += (
            '<tr><td><a href="'
            + record["accession"]
            + '.html">'
            + record["accession"]
            + "</a></td><td>"
            + escape(name)
            + "</td><td>"
            + str(len(record["reporting_persons"]))
            + "</td><td>"
            + str(len(record["ownership"]))
            + "</td><td>"
            + str(len(record["quality_issues"]))
            + "</td></tr>"
        )
    content += "</table></section><section><h2>Limits</h2><p>Unresolved references were not downloaded. Cover ownership is never aggregated and is separate from voting obligations in agreements. Reporting-person CIKs are not inferred from name similarity. Missing denominator/date rules remain unsupported. Some visible numeric disclosures remain invalid under these conservative rules, including fractional shares, ordinary-share wording and unusual footnote markers. Their source candidates remain in the quality queue. Person-level coverage denominators refer to detected rows, not independently certified complete person counts. First filing has prior model exposure; no earlier model answers were used. This draft does not replace the ready 200-filing pack or any human answers.</p></section>"
    (PACK / "index.html").write_text(page("52-filing deterministic facts", content))
    queue = '<a href="index.html">← All filings</a><h1>Missing and conflicting facts</h1><p>Processing issues and unresolved fields; not negative findings about the filings. Repeated issues can refer to the same underlying missing evidence.</p><table><tr><th>Filing</th><th>Field / issue</th><th>Details</th></tr>'
    for issue in issues:
        accession = issue["accession"]
        queue += (
            '<tr><td><a href="'
            + accession
            + '.html">'
            + accession
            + "</a></td><td>"
            + escape(str(issue.get("field", "")))
            + "<br>"
            + escape(str(issue.get("issue_type", issue.get("type", ""))))
            + "</td><td><details><summary>Source candidates / details</summary><pre>"
            + escape(encode(issue))
            + "</pre></details></td></tr>"
        )
    (PACK / "issues.html").write_text(page("Quality queue", queue + "</table>"))
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in ["field_coverage", "baseline"]}, indent=2
        )
    )
    if failures:
        raise SystemExit("Processing failures retained; inspect coverage.json before handoff.")


if __name__ == "__main__":
    main()
