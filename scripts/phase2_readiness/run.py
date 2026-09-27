"""Tier: 1. Offline feature coverage and independent chronology audit.
Inputs: frozen Phase 2 facts, bundles, receipts, original sources and eligibility.
Outputs: per-filing readiness, field coverage by year, exceptions and phone report.
Identity: file coverage=count(files with >=1 present value)/audited files;
prior history uses bisect over independently indexed strict-earlier timestamps.
Run: project Python scripts/phase2_readiness/run.py --output RUN [--pilot 12].
"""

import argparse
import bisect
import gzip
import json
import shutil
import signal
import socket
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts/extraction_protocol")]
from run_deterministic import fields, validate
from scripts.phase2_overnight.run import INPUT, PROTECTION, digest, guard, offline, save, timeout

from activist13d.local_paths import resolve_project_path

SOURCE = ROOT / "research/runs/phase2-overnight/20260924-full-v1"
PHONE = Path(
    "/Users/jefflu/Library/CloudStorage/OneDrive-Personal/Project-Transfer/Activist-13D/2026-09-24-Phase-2-Readiness"
)
PROTOCOL = ROOT / "research/protocol/phase2-readiness-audit-v1.md"


def index_history(rows):
    filings = defaultdict(list)
    pairs = defaultdict(dict)
    issuer_pairs = defaultdict(dict)
    for r in rows:
        t = r["accepted"]
        for c in set(r.get("reporter_ciks", [])):
            filings[c].append(t)
            for issuer in set(r.get("issuers", [])):
                pairs[c][issuer] = min(t, pairs[c].get(issuer, t))
                issuer_pairs[issuer][c] = min(t, issuer_pairs[issuer].get(c, t))
    return {c: sorted(v) for c, v in filings.items()}, pairs, issuer_pairs


def independent_history(row, index):
    filings, pairs, issuer_pairs = index
    t = row["accepted"]
    reporters = set(row.get("reporter_ciks", []))
    issuers = set(row.get("issuers", []))
    return {
        "available_at_acceptance_et": t,
        "reporter_history": [
            dict(
                cik=c,
                prior_submission_count=bisect.bisect_left(filings.get(c, []), t),
                prior_distinct_issuer_count=sum(v < t for v in pairs.get(c, {}).values()),
                prior_other_issuer_count=sum(
                    v < t and i not in issuers for i, v in pairs.get(c, {}).items()
                ),
            )
            for c in sorted(reporters)
        ],
        "issuer_history": [
            dict(
                cik=c,
                prior_distinct_reporter_ciks=sum(v < t for v in issuer_pairs.get(c, {}).values()),
                prior_reporter_ciks_outside_current_group=sum(
                    v < t and r not in reporters for r, v in issuer_pairs.get(c, {}).items()
                ),
            )
            for c in sorted(issuers)
        ],
    }


def file_fields(record):
    result = defaultdict(Counter)
    for path, field in fields(record):
        result[path][field["status"]] += 1
    return dict(result)


def ownership_coverage(rows):
    return {
        key: {
            "rows": len(rows),
            "present": sum(r.get(key, {}).get("status") == "present" for r in rows),
            "all_present": bool(rows)
            and all(r.get(key, {}).get("status") == "present" for r in rows),
        }
        for key in ["aggregate_shares", "percent_of_class"]
    }


def audit(row, history, index):
    a = row["accession"]
    receipt = json.loads((SOURCE / "receipts" / (a + ".json")).read_text())
    if receipt["status"] != "processed":
        raise ValueError("Source processing not complete")
    loaded = {}
    for folder, key in [("facts", "facts_sha256"), ("bundles", "bundle_sha256")]:
        path = SOURCE / folder / (a + ".json.gz")
        if digest(path) != receipt[key]:
            raise ValueError("Artifact hash mismatch")
        loaded[folder] = json.loads(gzip.decompress(path.read_bytes()))
    record, bundle = loaded["facts"], loaded["bundles"]
    validate(record, bundle)
    source = resolve_project_path(bundle["source_path"], ROOT)
    if not source.is_relative_to((ROOT / "data/raw/edgar").resolve()):
        raise ValueError("Source outside cache")
    if digest(source) != bundle["source_sha256"] or bundle["source_sha256"] != row["source_sha256"]:
        raise ValueError("Raw source hash mismatch")
    payload = source.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("cp1252", errors="replace")
    header = next(d["text"] for d in bundle["documents"] if d["document_id"] == "SEC-HEADER")
    if header != text.split("<DOCUMENT>", 1)[0]:
        raise ValueError("Header raw-source mismatch")
    expected = independent_history(row, index)
    if {k: v for k, v in history.items() if k != "accession"} != expected:
        raise ValueError("Independent history mismatch")
    issues = []
    for table, key in [("issuers", "issuers"), ("filing_entities", "reporter_ciks")]:
        actual = {r["cik"]["value"] for r in record[table] if r["cik"]["status"] == "present"}
        if actual != set(row.get(key, [])):
            issues.append(key + "_header_vs_eligibility_difference")
    return dict(
        accession=a,
        year=row["accepted"][:4],
        status="audited",
        fields=file_fields(record),
        ownership=ownership_coverage(record["ownership"]),
        identity_exceptions=issues,
        reporting_person_rows=len(record["reporting_persons"]),
        quality_issue_types=dict(Counter(r["issue_type"] for r in record["quality_issues"])),
    )


def publish(out, selected, results, state, sync):
    audited = [r for r in results.values() if r["status"] == "audited"]
    coverage = defaultdict(
        lambda: {"opportunities": Counter(), "files_with_field": 0, "files_with_present": 0}
    )
    years = Counter(r["year"] for r in audited)
    for r in audited:
        for field, counts in r["fields"].items():
            for year in ["all", r["year"]]:
                c = coverage[(year, field)]
                c["opportunities"].update(counts)
                c["files_with_field"] += 1
                c["files_with_present"] += counts.get("present", 0) > 0
    save(
        out / "field-coverage.json",
        [
            dict(year=y, field=f, denominator_filings=len(audited) if y == "all" else years[y], **v)
            for (y, f), v in sorted(coverage.items())
        ],
    )
    summary = dict(
        status=state,
        updated_utc=datetime.now(timezone.utc).isoformat(),
        selected=len(selected),
        audited=len(audited),
        failed=sum(r["status"] == "failed" for r in results.values()),
        pending=len(selected) - len(results),
        identity_disagreement_filings=sum(bool(r["identity_exceptions"]) for r in audited),
        ownership_all_rows_present={
            key: sum(r["ownership"][key]["all_present"] for r in audited)
            for key in ["aggregate_shares", "percent_of_class"]
        },
    )
    assert summary["selected"] == summary["audited"] + summary["failed"] + summary["pending"]
    save(out / "progress.json", summary)
    text = f"""Phase 2 feature-readiness audit — {state}
Updated: {summary["updated_utc"]}

Question: Is the information prepared for selecting 13D investments consistent and sufficiently complete to develop a model?

Initial-filing candidates selected: {len(selected):,}
Audited: {len(audited):,}; failures: {summary["failed"]:,}; pending: {summary["pending"]:,}.
Header identity differences requiring review: {summary["identity_disagreement_filings"]:,} of {len(audited):,} audited filings.
Filings with a reported ownership percentage for every extracted ownership row: {summary["ownership_all_rows_present"]["percent_of_class"]:,} of {len(audited):,} audited filings. This is parser coverage, not accuracy; missing reporting-person rows may remain undetected.

This pass checks source and artifact hashes, exact citations, identifiers against the eligibility ledger, and prior-disclosure counts using an independent chronological calculation. The detailed local report breaks field availability down by year. Ownership is kept separate for each reporting person; shared holdings are never added together.

These checks do not validate manager identities, historical positions, security eligibility or the meaning of every extracted value. Zero failures does not mean all fields are complete or accurate. Earlier involvement in another company does not establish a position in the current company. History is restricted to the source cache and excludes protected issuers and Hill International.

Next: inspect the largest coverage gaps and identity exceptions, then build lagged market features and dated manager mappings. Freeze the target and chronological training rules before fitting models. No outcomes, investor winner selection, semantic labels or model training are used in this audit. This is preparation, not evidence of an investment edge.

Local evidence: {out}
Phone copies are in the local OneDrive sync folder; remote delivery is not independently verified.
"""
    (out / "MORNING-REPORT.txt").write_text(text)
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 2 readiness</title><style>body{max-width:900px;margin:30px auto;padding:16px;font:17px/1.6 system-ui}pre{white-space:pre-wrap}</style><pre>'
        + escape(text)
        + "</pre>"
    )
    if sync:
        PHONE.mkdir(parents=True, exist_ok=True)
        for name in ["MORNING-REPORT.txt", "index.html", "progress.json"]:
            tmp = PHONE / (name + ".tmp")
            shutil.copyfile(out / name, tmp)
            tmp.replace(PHONE / name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", type=int, default=0)
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    socket.socket.connect = offline
    socket.create_connection = offline
    signal.signal(signal.SIGALRM, timeout)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipts").mkdir(exist_ok=True)
    guard()
    original = json.loads((SOURCE / "provenance.json").read_text())
    for rel, sha in original["inputs_and_code"].items():
        if digest(ROOT / rel) != sha:
            raise ValueError("Original input/code changed: " + rel)
    paths = [
        Path(__file__),
        Path(__file__).with_name("launch.py"),
        Path(__file__).with_name("test_readiness.py"),
        PROTOCOL,
        SOURCE / "provenance.json",
        SOURCE / "selection.json",
        SOURCE / "prior-header-cik-history.jsonl",
    ]
    manifest = {
        "pilot": args.pilot,
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in paths},
    }
    target = out / "provenance.json"
    if target.exists() and json.loads(target.read_text()) != manifest:
        raise ValueError("Changed run inputs; use a new directory")
    save(target, manifest)
    for p in paths:
        if p.suffix in {".py", ".md"}:
            dest = out / "code" / p.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copyfile(p, dest)
    protection = json.loads(PROTECTION.read_text())
    blocked = set(protection["issuers"]) | {"0001287808"}
    rows = [json.loads(s) for s in INPUT.read_text().splitlines()]
    rows = [
        r
        for r in rows
        if not set(r.get("issuers", [])) & blocked
        and r["accession"] not in set(protection["accessions"])
        and r.get("accepted")
        and r["accepted"][:10] <= "2025-12-31"
        and r["status"] != "unresolved_source_or_primary"
    ]
    index = index_history(rows)
    by_acc = {r["accession"]: r for r in rows}
    selected = json.loads((SOURCE / "selection.json").read_text())
    if args.pilot:
        selected = [
            selected[i * (len(selected) - 1) // max(1, args.pilot - 1)] for i in range(args.pilot)
        ]
    histories = {
        r["accession"]: r
        for r in map(
            json.loads, (SOURCE / "prior-header-cik-history.jsonl").read_text().splitlines()
        )
    }
    results = {p.stem: json.loads(p.read_text()) for p in (out / "receipts").glob("*.json")}
    save(out / "selection.json", selected)
    publish(out, selected, results, "running", args.sync)
    start = time.monotonic()
    for selected_row in selected:
        a = selected_row["accession"]
        if a in results:
            continue
        if time.monotonic() - start > 8 * 3600 or shutil.disk_usage(out).free < 20 * 1024**3:
            guard()
            publish(out, selected, results, "paused_at_resource_limit", args.sync)
            return
        try:
            signal.alarm(90)
            result = audit(by_acc[a], histories[a], index)
        except Exception as exc:
            result = dict(
                accession=a, status="failed", error=type(exc).__name__ + ": " + str(exc)[:400]
            )
        finally:
            signal.alarm(0)
        save(out / "receipts" / (a + ".json"), result)
        results[a] = result
        if len(results) % 250 == 0:
            publish(out, selected, results, "running", args.sync)
            print("Audited/checkpointed", len(results), flush=True)
    guard()
    publish(
        out,
        selected,
        results,
        "completed_with_exceptions"
        if any(r["status"] == "failed" or r.get("identity_exceptions") for r in results.values())
        else "completed",
        args.sync,
    )


if __name__ == "__main__":
    main()
