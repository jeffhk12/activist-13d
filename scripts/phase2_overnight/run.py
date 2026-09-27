"""Tier: 1. Offline Phase 2 factual staging, not a trained or approved model panel.
Inputs: frozen eligibility, raw SEC submissions, human protection list.
Outputs: source bundles, schema/citation-checked facts, strictly prior CIK history,
coverage and resumable progress. Identity: selected = processed + failed + pending;
history counts only submissions accepted strictly before the current acceptance.
Run: project Python scripts/phase2_overnight/run.py --output RUN [--pilot 12].
"""

import argparse
import gzip
import hashlib
import json
import platform
import shutil
import signal
import socket
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from importlib.metadata import distributions
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/extraction_protocol")]
from run_deterministic import fields, validate

from activist13d.edgar.deterministic import extract
from activist13d.edgar.submission import parse_submission
from activist13d.local_paths import resolve_project_path

BASE = ROOT / "research/runs/phase1-baseline"
INPUT = BASE / "20260924-universe-rebuild-v3/eligibility.jsonl"
PROTECTION = BASE / "20260924-development-v4/human-review-protection.json"
GUARD = BASE / "20260924-completion-integration-v1/protected-assets.json"
PROTOCOL = ROOT / "research/protocol/phase2-factual-staging-v1.md"
PHONE = Path(
    "/Users/jefflu/Library/CloudStorage/OneDrive-Personal/Project-Transfer/Activist-13D/2026-09-24-Phase-2-Preparation"
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def guard():
    expected = json.loads(GUARD.read_text())
    for rel, sha in expected.items():
        if digest(ROOT / rel) != sha:
            raise ValueError("Protected asset changed: " + rel)
    return len(expected)


def histories(rows):
    """Header CIK proxies only; excludes same-timestamp disclosures from history."""
    past_filings = Counter()
    past_issuers = defaultdict(set)
    issuer_reporters = defaultdict(set)
    result = {}
    valid = [r for r in rows if r.get("accepted")]
    for accepted, batch_iter in groupby(
        sorted(valid, key=lambda r: (r["accepted"], r["accession"])), key=lambda r: r["accepted"]
    ):
        batch = list(batch_iter)
        for r in batch:
            reporters, issuers = set(r.get("reporter_ciks", [])), set(r.get("issuers", []))
            result[r["accession"]] = {
                "available_at_acceptance_et": accepted,
                "reporter_history": [
                    {
                        "cik": c,
                        "prior_submission_count": past_filings[c],
                        "prior_distinct_issuer_count": len(past_issuers[c]),
                        "prior_other_issuer_count": len(past_issuers[c] - issuers),
                    }
                    for c in sorted(reporters)
                ],
                "issuer_history": [
                    {
                        "cik": c,
                        "prior_distinct_reporter_ciks": len(issuer_reporters[c]),
                        "prior_reporter_ciks_outside_current_group": len(
                            issuer_reporters[c] - reporters
                        ),
                    }
                    for c in sorted(issuers)
                ],
            }
        for r in batch:
            for c in set(r.get("reporter_ciks", [])):
                past_filings[c] += 1
                past_issuers[c].update(r.get("issuers", []))
            for c in set(r.get("issuers", [])):
                issuer_reporters[c].update(r.get("reporter_ciks", []))
    return result


def offline(*args, **kwargs):
    raise RuntimeError("Network disabled in Phase 2 factual staging")


def timeout(*args):
    raise TimeoutError("90-second per-filing processing limit")


def process(row, out):
    source = resolve_project_path(row["source_path"], ROOT)
    if not source.is_relative_to((ROOT / "data/raw/edgar").resolve()):
        raise ValueError("Source outside raw SEC cache")
    if source.stat().st_size > 20 * 1024**2:
        raise ValueError("Raw source exceeds 20 MiB limit")
    payload = source.read_bytes()
    sha = hashlib.sha256(payload).hexdigest()
    meta_path = source.with_suffix(source.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text())
    if (
        sha != row["source_sha256"]
        or meta.get("sha256") != sha
        or meta.get("bytes") != len(payload)
        or meta.get("url") != row["source_url"]
        or len(payload) != row["source_bytes"]
        or digest(meta_path) != row["sidecar_sha256"]
    ):
        raise ValueError("Raw source / sidecar provenance mismatch")
    parsed = parse_submission(payload)
    if parsed["accession"] != row["accession"]:
        raise ValueError("Accession mismatch")
    decoded = (
        payload.decode("utf-8")
        if parsed["decoded_as"] == "utf-8"
        else payload.decode("cp1252", errors="replace")
    )
    header = decoded.split("<DOCUMENT>", 1)[0]
    docs = [
        {
            "document_id": "SEC-HEADER",
            "type": "SEC-HEADER",
            "filename": None,
            "text": header,
            "status": "parsed_text",
            "text_sha256": hashlib.sha256(header.encode()).hexdigest(),
        }
    ]
    for d in parsed["documents"]:
        docs.append(
            {
                **d,
                "document_id": f"DOCUMENT[{d['source_document_index']}]",
                "status": d["text_status"],
                "text_sha256": hashlib.sha256(d["text"].encode()).hexdigest()
                if d["text"] is not None
                else None,
            }
        )
    bundle = {
        k: row[k]
        for k in ["accession", "source_path", "source_url", "source_sha256", "filing_date"]
    }
    bundle.update(
        documents=docs, transformation_sha256=digest(ROOT / "src/activist13d/edgar/submission.py")
    )
    record = extract(bundle, payload)
    validate(record, bundle)
    # Independently pin acceptance/date to the source-audited universe fields.
    # Specific field names are verified through raw header to avoid guessing schema keys.
    import re

    date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", header)
    accept_match = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if not date_match or date_match[1] != row["filing_date"].replace("-", ""):
        raise ValueError("Filing date mismatch")
    if (
        not accept_match
        or datetime.strptime(accept_match[1], "%Y%m%d%H%M%S").isoformat() != row["accepted"]
    ):
        raise ValueError("Acceptance time missing or mismatched")
    for folder, value in [("bundles", bundle), ("facts", record)]:
        path = out / folder / (row["accession"] + ".json.gz")
        raw = json.dumps(value, sort_keys=True).encode()
        if len(raw) > 32 * 1024**2:
            raise ValueError("Output exceeds 32 MiB cap")
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(raw, mtime=0))
        tmp.replace(path)
    statuses = Counter(f["status"] for _, f in fields(record))
    return {
        "status": "processed",
        "source_sha256": sha,
        "field_statuses": dict(statuses),
        "reporting_person_rows": len(record["reporting_persons"]),
        "ownership_rows": len(record["ownership"]),
        "quality_issue_count": len(record["quality_issues"]),
        "facts_sha256": digest(out / "facts" / (row["accession"] + ".json.gz")),
        "bundle_sha256": digest(out / "bundles" / (row["accession"] + ".json.gz")),
    }


def report(out, selected, results, exclusions, state, sync):
    counts = Counter(r["status"] for r in results.values())
    summary = {
        "status": state,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "selected_initial_filings": len(selected),
        "processed": counts["processed"],
        "failed": counts["failed"],
        "pending": len(selected) - len(results),
        "selection_exclusions": dict(exclusions),
        "failure_reasons": dict(
            Counter(
                r.get("error", "").split(":")[0]
                for r in results.values()
                if r["status"] == "failed"
            )
        ),
        "field_statuses": dict(
            sum((Counter(r.get("field_statuses", {})) for r in results.values()), Counter())
        ),
    }
    assert (
        summary["selected_initial_filings"]
        == summary["processed"] + summary["failed"] + summary["pending"]
    )
    save(out / "progress.json", summary)
    message = f"""Phase 2 preparation — {state}
Updated: {summary["updated_utc"]}

Investment question: Can information available at the initial disclosure help us choose better opportunities than following every eligible filing?

This job prepares source-backed filing facts; it does not estimate an investment edge or train a model.
Selected initial filings: {len(selected):,}
Successfully parsed with schema and citation checks: {summary["processed"]:,}
Explicit processing failures: {summary["failed"]:,}
Pending: {summary["pending"]:,}

What is being prepared: separate reporting-person ownership records, identifiers, disclosure timestamps, source evidence, and counts of earlier disclosures by header reporting-party CIK. Missing and conflicting values remain visible. Earlier activity in company B does not establish a position in company A. Counts do not prove current positions, independent investors, validated managers, or campaigns. History starts in 2013 and excludes protected issuers and Hill International, so it is incomplete.

Scope: source-audited standalone initial candidates accepted through 2025; no filter on returns, manager success, tradability or price availability. This is factual staging, not the final eligible stock universe. Known protected review issuers/accessions are excluded. 2026 is not processed by this job; that does not certify an untouched holdout. Previously examined samples remain development data.

Next: review failures and factual extraction accuracy; build lagged market features; validate dated HFR identities and availability; freeze the return target, benchmark and chronological training rules (including waiting for each training return to mature). Then compare a simple model with the Phase 1 baseline. Existing delisting/accounting issues remain unresolved. No return targets, HFR strategy labels, NLP intent labels, winner lists or model tuning were used in this run.

Local evidence: {out}
Cloud note: this report is copied into the local OneDrive folder; remote upload is not independently verified.
"""
    (out / "MORNING-REPORT.txt").write_text(message)
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Phase 2 preparation</title><style>body{max-width:850px;margin:30px auto;padding:18px;font:17px/1.6 system-ui}pre{white-space:pre-wrap}</style><pre>'
        + escape(message)
        + "</pre>"
    )
    if sync:
        PHONE.mkdir(parents=True, exist_ok=True)
        for name in ["MORNING-REPORT.txt", "index.html", "progress.json"]:
            target = PHONE / name
            tmp = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(out / name, tmp)
            tmp.replace(target)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--pilot", type=int, default=0)
    p.add_argument("--hours", type=float, default=8)
    p.add_argument("--sync", action="store_true")
    args = p.parse_args()
    socket.socket.connect = offline
    socket.create_connection = offline
    signal.signal(signal.SIGALRM, timeout)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ["facts", "bundles", "receipts"]:
        (out / name).mkdir(exist_ok=True)
    guard()
    codepaths = [
        Path(__file__),
        Path(__file__).with_name("launch.py"),
        PROTOCOL,
        INPUT,
        PROTECTION,
        GUARD,
        Path(__file__).with_name("test_staging.py"),
        ROOT / "src/activist13d/local_paths.py",
        ROOT / "scripts/extraction_protocol/run_deterministic.py",
        ROOT / "research/protocol/deterministic-schema-v1.json",
    ]
    codepaths += sorted((ROOT / "src/activist13d/edgar").glob("*.py"))
    provenance = {
        "inputs_and_code": {str(f.relative_to(ROOT)): digest(f) for f in codepaths},
        "python": platform.python_version(),
        "pilot": args.pilot,
        "end_date": "2025-12-31",
        "packages": sorted((d.metadata["Name"], d.version) for d in distributions()),
    }
    # JSON normalization preserves the same structure on resume.
    provenance = json.loads(json.dumps(provenance))
    prov = out / "provenance.json"
    if prov.exists() and json.loads(prov.read_text()) != provenance:
        raise ValueError("Inputs/code changed; use a new run directory")
    save(prov, provenance)
    for path in codepaths:
        if path.suffix in {".py", ".md"}:
            target = out / "code" / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and digest(target) != digest(path):
                raise ValueError("Frozen code snapshot changed")
            if not target.exists():
                shutil.copyfile(path, target)
    protection = json.loads(PROTECTION.read_text())
    blocked = set(protection["issuers"]) | {"0001287808"}
    protected_acc = set(protection["accessions"])
    rows, selected, exclusions = [], [], Counter()
    for line in INPUT.open():
        r = json.loads(line)
        reason = None
        if set(r.get("issuers", [])) & blocked or r["accession"] in protected_acc:
            reason = "protected_or_user_excluded"
        elif not r.get("accepted"):
            reason = "missing_acceptance"
        elif r["accepted"][:10] > "2025-12-31":
            reason = "after_2025"
        elif r["status"] == "unresolved_source_or_primary":
            reason = "unresolved_source_or_primary"
        if reason:
            exclusions[reason] += 1
            continue
        rows.append(r)
        if r["status"] == "standalone_initial_candidate":
            selected.append(r)
        else:
            exclusions["not_initial_candidate"] += 1
    selected.sort(key=lambda r: (r["accepted"], r["accession"]))
    if args.pilot:
        # Evenly spaced across chronology; deterministic, no outcome selection.
        selected = [
            selected[i * (len(selected) - 1) // max(1, args.pilot - 1)]
            for i in range(min(args.pilot, len(selected)))
        ]
    hist = histories(rows)
    save(
        out / "selection.json",
        [
            {
                "accession": r["accession"],
                "accepted": r["accepted"],
                "source_sha256": r["source_sha256"],
                "eligibility_audit_only": r["campaign_status"],
            }
            for r in selected
        ],
    )
    with (out / "prior-header-cik-history.jsonl").open("w") as f:
        for r in selected:
            f.write(
                json.dumps({"accession": r["accession"], **hist[r["accession"]]}, sort_keys=True)
                + "\n"
            )
    results = {}
    for r in selected:
        receipt = out / "receipts" / (r["accession"] + ".json")
        if receipt.exists():
            result = json.loads(receipt.read_text())
            if result["status"] == "processed":
                for folder, key in [("facts", "facts_sha256"), ("bundles", "bundle_sha256")]:
                    if digest(out / folder / (r["accession"] + ".json.gz")) != result[key]:
                        raise ValueError("Checkpoint file changed")
            results[r["accession"]] = result
    start = time.monotonic()
    report(out, selected, results, exclusions, "running", args.sync)
    for r in selected:
        if r["accession"] in results:
            continue
        if (
            time.monotonic() - start > args.hours * 3600
            or shutil.disk_usage(out).free < 20 * 1024**3
        ):
            report(out, selected, results, exclusions, "paused_at_resource_limit", args.sync)
            guard()
            return
        try:
            signal.alarm(90)
            result = process(r, out)
        except Exception as exc:
            result = {"status": "failed", "error": type(exc).__name__ + ": " + str(exc)[:500]}
        finally:
            signal.alarm(0)
        save(out / "receipts" / (r["accession"] + ".json"), result)
        results[r["accession"]] = result
        if len(results) % 25 == 0:
            report(out, selected, results, exclusions, "running", args.sync)
            print(json.dumps({"completed": len(results), "selected": len(selected)}), flush=True)
    guard()
    report(
        out,
        selected,
        results,
        exclusions,
        "completed_with_explicit_failures"
        if any(r["status"] == "failed" for r in results.values())
        else "completed",
        args.sync,
    )


if __name__ == "__main__":
    main()
