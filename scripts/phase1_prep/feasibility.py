"""Offline identifier readiness and cached WRDS schema feasibility inventory.

Inputs: completed prep records and frozen WRDS v1 envelopes; no credentials.
Outputs: dated JSON counts, field metadata, source hashes and an evidence report.
Identity: readiness rate = records with a syntactic identifier / all records.
Readiness is not an identifier match rate or corporate campaign eligibility.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_prep/feasibility.py
"""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "research/runs/phase1-prep/20260914T003050627334Z"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readiness(records):
    rows = []
    for record in records:
        value = record.get("cusip")
        # Preserve original values: no truncation, correction, or inferred CUSIP.
        syntax = bool(isinstance(value, str) and re.fullmatch(r"[A-Z0-9*@#]{9}", value))
        rows.append({"accession": record["accession"], "cusip": value,
                     "cusip_nine_character_syntax": syntax,
                     "issuer_ciks": sorted({s["cik"] for s in record.get("subjects", []) if s.get("cik")}),
                     "filing_date_unvalidated_prior": record.get("index_filing_date"),
                     "historical_link_status": "not_attempted"})
    n = len(rows)
    present = sum(bool(r["cusip"]) for r in rows)
    syntactic = sum(r["cusip_nine_character_syntax"] for r in rows)
    return {"n_filings": n, "cusip_present": present, "cusip_missing": n - present,
            "cusip_syntactic": syntactic, "cusip_syntactic_rate": syntactic / n if n else None,
            "filings_with_issuer_cik": sum(bool(r["issuer_ciks"]) for r in rows),
            "distinct_issuer_ciks": len({c for r in rows for c in r["issuer_ciks"]}),
            "by_prior_filing_year": dict(sorted(Counter((r["filing_date_unvalidated_prior"] or "missing")[:4] for r in rows).items())),
            "historical_link_attempts": 0, "historical_match_rate": None}, rows


def envelope(path):
    data = json.loads(path.read_text())
    if hashlib.sha256(data["raw_response"].encode()).hexdigest() != data["sha256"]:
        raise ValueError("WRDS cache response hash mismatch")
    request_hash = hashlib.sha256(json.dumps(data["request"], sort_keys=True).encode()).hexdigest()
    if path.stem != request_hash:
        raise ValueError("WRDS cache request hash mismatch")
    return data, json.loads(data["raw_response"])


def directory_candidates(path, metadata_path):
    meta = json.loads(metadata_path.read_text())
    if sha(path) != meta.get("sha256") or meta.get("status") != 200:
        raise ValueError("WRDS directory cache failed verification")
    directory = json.loads(path.read_text())
    candidates = {"crsp.dsenames": "historical security-name and identifier metadata candidate",
                  "crsp.stocknames": "alternate security-name metadata candidate",
                  "crsp.dsedelist": "delisting metadata candidate",
                  "crsp.ccmxpf_lnkhist": "historical CRSP/Compustat link metadata candidate"}
    return {"source_path": str(path), "sha256": sha(path), "retrieved_at": meta["retrieved_at"],
            "tables": [{"table": table, "purpose_hypothesis": purpose, "listed_in_cached_directory": table in directory,
                        "schema_access": "not_tested", "historical_coverage": "not_tested"}
                       for table, purpose in candidates.items()]}


def main():
    path = PREP / "reparsed-records.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summary, rows = readiness(records)
    manifest_path = ROOT / "data/interim/overnight/sample-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    summary["sample_not_representative"] = manifest.get("not_representative")
    sources = {str(path.relative_to(ROOT)): sha(path), str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
               str(manifest_path.relative_to(ROOT)): sha(manifest_path)}
    schemas, probes = {}, {}
    for cached in sorted((ROOT / "data/raw/wrds/v1").glob("*.json")):
        data, payload = envelope(cached)
        sources[str(cached.relative_to(ROOT))] = sha(cached)
        table = data["request"]["url"].rstrip("/").rsplit("/", 1)[1]
        provenance = {"source_path": str(cached.relative_to(ROOT)), "response_sha256": data["sha256"], "retrieved_at": data["retrieved_at"]}
        if data["request"]["method"] == "OPTIONS":
            schemas[table] = {**provenance, "fields": payload["fields"], "n_fields": len(payload["fields"])}
        else:
            probes[table] = {**provenance, "request": data["request"], "downloaded_rows": len(payload["results"]),
                             "reported_matching_count": payload.get("count"),
                             "non_null_fields": [[k for k, v in row.items() if v is not None] for row in payload["results"]]}
    directory_path = ROOT / "data/raw/wrds/inspect-20260913T212655342031Z/2.response"
    directory_meta = directory_path.with_suffix(".json")
    next_metadata = directory_candidates(directory_path, directory_meta)
    sources[str(directory_path.relative_to(ROOT))] = sha(directory_path)
    sources[str(directory_meta.relative_to(ROOT))] = sha(directory_meta)
    run = ROOT / "research/runs/phase1-prep" / ("feasibility-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir()
    for name, payload in {"summary": summary, "identifier-readiness": rows, "cached-schemas": schemas, "cached-probes": probes,
                          "next-metadata-candidates": next_metadata,
                          "provenance": {"source_hashes": sources, "network_calls": 0, "model_api_calls": 0}}.items():
        (run / (name + ".json")).write_text(json.dumps(payload, indent=2) + "\n")
    lines = ["# Phase 1 cached-data feasibility", "", "Offline evidence inventory; no corporate eligibility or intent labels. No identifier joins attempted. The frozen manifest identifies this as a nonrepresentative discovery sample; do not extrapolate these rates to the full filing universe.", "",
             "```json", json.dumps(summary, indent=2), "```", "", "## Cached WRDS evidence", ""]
    for table, schema in schemas.items():
        fields = schema["fields"]
        lines.append(f"- `{table}`: {len(fields)} fields; filterable: {', '.join(k for k, v in fields.items() if v.get('filter_field'))}. Source: `{schema['source_path']}`; pull: {schema['retrieved_at']}.")
    lines += ["", "## Limits and next bounded checks", "",
              "CUSIP presence is parser output, and nine-character syntax does not verify its check digit, security class, or historical validity. Counts by year use prior filing dates; consult the separate filing-date audit before relying on those dates. No exclusions or sample attrition have yet been applied. Corporate eligibility, manager identity, and campaign chains remain unvalidated; the confirmed campaign count is unknown.", "",
              "The frozen CRSP schema should be inspected for the exact execution fields below. A field's existence does not establish populated historical coverage, units, adjustment conventions, or an executable opening price. The one-row development probe cannot establish period coverage.", ""]
    dsf = schemas.get("crsp.dsf", {}).get("fields", {})
    for field in ("permno", "permco", "cusip", "ncusip", "date", "prc", "openprc", "vol", "ret", "retx", "cfacpr", "cfacshr", "dlret", "dlstcd"):
        lines.append(f"- `{field}`: {'present' if field in dsf else 'absent from inspected crsp.dsf schema'}.")
    lines += ["", "The following candidate names appear in the hash-checked cached WRDS directory, pulled " + next_metadata["retrieved_at"] + ". Purposes below are working hypotheses from names, not verified table definitions. No schema access or coverage tests were performed:", ""]
    for candidate in next_metadata["tables"]:
        lines.append(f"- `{candidate['table']}`: listed={candidate['listed_in_cached_directory']}; {candidate['purpose_hypothesis']}.")
    lines += ["", "Historical CUSIP-to-PERMNO intervals and delisting evidence require additional metadata/table access. The existing WRDS client requires an already known PERMNO for CRSP, so it cannot presently resolve this discovery sample. Do not substitute issuer names or a current identifier for a historical crosswalk.", "",
              "Compustat's cached probe has multiple matching rows for the same GVKEY/year when its reported count exceeds its downloaded row count; format/consolidation conventions must precede a fundamentals join. Fiscal year is not public availability time. The cached schema alone does not establish point-in-time fundamentals.", "",
              "Audit Analytics classification column names and one dated probe do not establish category definitions, historical completeness, coding process, or amendment handling. Obtain the data dictionary and coverage metadata before mapping categories or treating them as a reference set.", "",
              "Benchmark returns, cash rates, delisting treatment, and full opening-price coverage are not established by these caches. Next work is bounded metadata discovery for historical security names/links, delistings, and field definitions, followed by a small predeclared issuer/date probe. Full panel extraction and Phase 1's campaign-count gate remain pending.", "",
              "Original packets and raw evidence were opened read-only. This script has no network or provider client imports."]
    (run / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(run)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
