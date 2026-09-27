"""Offline evidence audit and blank human-review packets for the cached sample.

Inputs: frozen 100-record manifest, prior JSONL, raw submissions and sidecars.
Outputs: isolated dated run, hash audit, candidate inventory, HTML review packets.
Identity: n verified = sum(raw SHA-256 equals record and sidecar SHA-256).
Matching filer/issuer CIK sets are candidate groups, never verified campaigns.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/phase1_prep/run.py
"""

import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from activist13d.edgar.submission import parse_submission  # noqa: E402


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verify(path, expected=None, url=None):
    metadata = path.with_suffix(path.suffix + ".meta.json")
    if not path.is_file() or not metadata.is_file():
        return {"status": "missing_source_or_sidecar"}
    meta = json.loads(metadata.read_text())
    actual = digest(path)
    valid = actual == meta.get("sha256") and path.stat().st_size == meta.get("bytes")
    if expected is not None:
        valid = valid and actual == expected
    if url is not None:
        valid = valid and url == meta.get("url")
    return {"status": "verified" if valid else "integrity_failure", "sha256": actual,
            "bytes": path.stat().st_size, "sidecar_sha256": digest(metadata)}


def candidate_key(record):
    filers = sorted({r.get("cik") for r in record.get("filers", []) if r.get("cik")})
    subjects = sorted({r.get("cik") for r in record.get("subjects", []) if r.get("cik")})
    if not filers or not subjects:
        return None
    return "filers=" + ",".join(filers) + "|subjects=" + ",".join(subjects)


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def packet(record, inventory):
    esc = lambda value: html.escape(str(value))  # noqa: E731
    body = ["<!doctype html><meta charset='utf-8'><title>Filing review</title>",
            "<style>body{max-width:1000px;margin:40px auto;font:16px/1.5 Georgia;padding:0 20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h2{margin-top:2em}</style>",
            f"<h1>{esc(record['accession'])}</h1>",
            "<p>Unscreened filing. Blank review aid, not an AI label set or a confirmed campaign. "
            "All document text is included below; parser completeness requires review. "
            "No investment outcomes are supplied.</p>",
            f"<p>Raw source: {esc(inventory['source_path'])}<br>SHA-256: {esc(inventory['source_sha256'])}</p>",
            f"<p>Filed: {esc(inventory['filing_date'])}; form: {esc(inventory['form'])}<br>"
            f"Filers: {esc(record['filers'])}<br>Subjects: {esc(record['subjects'])}</p>",
            "<h2>Blank reviewer worksheet</h2><p>Reviewer and date: __________<br>"
            "Corporate eligibility and rationale: __________<br>"
            "Stated demand and supporting passage/location: __________<br>"
            "Missing evidence or cannot determine: __________<br>"
            "Do not assign formal intent categories until the codebook is frozen.</p>",
            f"<h2>Mechanical review flags</h2><pre>{esc(inventory['flags'])}</pre>",
            f"<h2>Candidate Item 4</h2><p>{esc(record.get('item4_source_location'))}</p>"
            f"<pre>{esc(record.get('item4_text') or '[No unique Item 4 candidate]')}</pre>",
            "<h2>Existing reference detector output</h2><p>This detector is incomplete; a clean "
            "result does not establish that every incorporated reference was recovered.</p>"
            f"<pre>{esc(json.dumps(record['evidence_bundle'], indent=2))}</pre>"]
    for index, doc in enumerate(record["documents"], 1):
        body.append(f"<h2 id='document-{index}'>Document {index}: {esc(doc.get('filename'))}</h2>"
                    f"<p>Type: {esc(doc.get('type'))}; status: {esc(doc.get('text_status'))}</p>"
                    f"<pre>{esc(doc.get('text') or '[Binary or unavailable text; inspect raw source]')}</pre>")
    return "\n".join(body)


def main():
    run = ROOT / "research/runs/phase1-prep" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True)
    (run / "packets").mkdir()
    print(f"Run directory: {run}", flush=True)
    status = {"status": "running", "network_calls": 0, "model_api_calls": 0, "processed": 0}
    write_json(run / "progress.json", status)
    try:
        manifest_path = ROOT / "data/interim/overnight/sample-manifest.json"
        records_path = ROOT / "data/interim/overnight/records.jsonl"
        source = records_path.read_bytes()
        prior = [json.loads(line) for line in source.splitlines() if line.strip()]
        manifest = json.loads(manifest_path.read_text())["records"]
        counts = Counter(r["accession"] for r in prior)
        manifest_counts = Counter(r["accession"] for r in manifest)
        if counts != manifest_counts or any(v != 1 for v in counts.values()):
            raise ValueError("Manifest and records must have identical unique accession sets")
        provenance = {"manifest_sha256": digest(manifest_path), "records_sha256": digest(records_path),
                      "worker_sha256": digest(Path(__file__)),
                      "parser_sha256": digest(ROOT / "src/activist13d/edgar/submission.py"),
                      "python": sys.version, "n_manifest": len(manifest)}
        write_json(run / "provenance.json", provenance)
        inventory, exceptions, fresh = [], [], []
        groups = defaultdict(list)
        for old in prior:
            accession = old["accession"]
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                raise ValueError("Invalid accession")
            row = {"accession": accession, "source_path": old["source_path"],
                   "source_sha256": old["source_sha256"], "filing_date": old.get("index_filing_date"),
                   "flags": [], "candidate_campaign_status": "not_validated"}
            path = (ROOT / old["source_path"]).resolve()
            if not path.is_relative_to((ROOT / "data/raw/edgar").resolve()):
                raise ValueError("Source path outside approved raw cache")
            try:
                row["integrity"] = verify(path, old["source_sha256"], old["source_url"])
                if row["integrity"]["status"] != "verified":
                    raise ValueError(row["integrity"]["status"])
                raw = path.read_bytes()
                record = parse_submission(raw)
                if record["accession"] != accession:
                    raise ValueError("Accession differs from raw source")
                header = raw.split(b"<DOCUMENT>", 1)[0].decode("latin-1")
                form = re.search(r"CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)", header)
                row["form"] = form.group(1).strip() if form else None
                row["is_amendment"] = row["form"].endswith("/A") if row["form"] else None
                row["filers"], row["subjects"] = record["filers"], record["subjects"]
                for key in ("item4_text", "event_date", "cusip", "acceptance_datetime_et", "filers", "subjects"):
                    if not record.get(key):
                        row["flags"].append("missing_" + key)
                row["changed_fields"] = [key for key in ("item4_text", "item4_source_location", "cusip", "event_date", "filers", "subjects") if record.get(key) != old.get(key)]
                refs = record["evidence_bundle"]["referenced_sections"] + record["evidence_bundle"]["referenced_exhibits"]
                row["unresolved_detected_references"] = [r["reference"] for r in refs if not r.get("text")]
                if row["unresolved_detected_references"]:
                    row["flags"].append("unresolved_detected_references")
                if any(d["text_status"] != "parsed_text" for d in record["documents"]):
                    row["flags"].append("binary_document_requires_review")
                key = candidate_key(record)
                row["candidate_party_key"] = key
                if key:
                    groups[key].append(accession)
                record.update({k: old[k] for k in ("source_path", "source_url", "source_sha256", "index_filing_date")})
                fresh.append(record)
                (run / "packets" / (accession + ".html")).write_text(packet(record, row))
                row["packet"] = "packets/" + accession + ".html"
                if row["flags"]:
                    exceptions.append({"accession": accession, "kind": "review", "flags": row["flags"]})
            except (ValueError, OSError, KeyError) as error:
                row["flags"].append("source_or_parser_failure")
                exceptions.append({"accession": accession, "kind": "failure", "error": str(error)})
            inventory.append(row)
            status["processed"] = len(inventory)
            write_json(run / "progress.json", status)
            if len(inventory) % 10 == 0:
                print(f"Processed {len(inventory)}/{len(prior)}", flush=True)
        indexes = []
        for path in sorted((ROOT / "data/raw/edgar/overnight/index").glob("form-*.idx")):
            indexes.append({"path": str(path.relative_to(ROOT)), **verify(path)})
        write_json(run / "index-audit.json", indexes)
        write_json(run / "candidate-inventory.json", inventory)
        write_json(run / "exceptions.json", exceptions)
        write_json(run / "candidate-overlaps.json", {k: v for k, v in groups.items() if len(v) > 1})
        (run / "reparsed-records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fresh))
        flags = Counter(flag for r in inventory for flag in r["flags"])
        failures = sum(e["kind"] == "failure" for e in exceptions)
        summary = {"n": len(prior), "verified_submissions": sum(r.get("integrity", {}).get("status") == "verified" for r in inventory),
                   "packets": len(fresh), "failures": failures, "review_flags": dict(flags),
                   "records_with_parser_changes": sum(bool(r.get("changed_fields")) for r in inventory),
                   "index_files": len(indexes), "verified_indexes": sum(r["status"] == "verified" for r in indexes),
                   "candidate_overlap_groups": sum(len(v) > 1 for v in groups.values()),
                   "forms": dict(Counter(r.get("form") for r in inventory))}
        write_json(run / "summary.json", summary)
        lines = ["# Offline Phase 1 preparation", "", "Unscreened discovery sample; no confirmed campaign counts or AI intent labels.", "", "```json", json.dumps(summary, indent=2), "```", "", "## Review packets", "", "All parsed document text is included without truncation. Binary content remains in the raw submissions. Review fields are blank. Reference detection is incomplete, so no detected exceptions does not establish complete evidence.", ""]
        lines.extend(f"- [{r['accession']}]({r['packet']})" for r in inventory if "packet" in r)
        (run / "REPORT.md").write_text("\n".join(lines) + "\n")
        status.update(status="completed_with_exceptions" if failures or len(indexes) != 55 or summary["verified_indexes"] != len(indexes) else "completed", summary=summary)
        write_json(run / "progress.json", status)
        print(json.dumps(summary, indent=2), flush=True)
    except Exception as error:
        status.update(status="failed", error=f"{type(error).__name__}: {error}")
        write_json(run / "progress.json", status)
        raise


if __name__ == "__main__":
    main()
