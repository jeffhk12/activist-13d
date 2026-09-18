"""Offline source-backed triage of Phase 1 parser exceptions.

Reads the completed exception list and reparsed records plus cached raw
submissions; writes exploratory field candidates with exact source spans,
hashes, rationale, and uncertainty. No research intent, economic, or
eligibility labels are produced.

Identity: every proposed value must be a literal substring of one cached
document text and its raw submission hash must equal the recorded hash.
Tier: 1
Run: set PYTHONNOUSERSITE=1, PYTHONIOENCODING=utf-8; python scripts/phase1_prep/triage.py
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "output/phase1-prep/20260914T003050627334Z"
PROMPT = Path(__file__).with_name("triage_prompt_v1.txt")
MODEL = "gpt-5.6-luna"
PROVIDER = "Codex subagent"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def span(doc: dict, needle: str, document_index: int, *, context: int = 180) -> dict | None:
    text = doc.get("text") or ""
    pos = text.lower().find(needle.lower())
    if pos < 0:
        return None
    lo, hi = max(0, pos - context), min(len(text), pos + len(needle) + context)
    return {"document_index": document_index,
            "filename": doc.get("filename"), "start": pos,
            "end": pos + len(needle), "context_start": lo,
            "context_end": hi, "text": text[pos:pos + len(needle)], "context_text": text[lo:hi]}


def first_doc(record: dict, pattern: str) -> tuple[dict, re.Match[str]] | None:
    rx = re.compile(pattern, re.I | re.S)
    for index, doc in enumerate(record.get("documents", []), 1):
        match = rx.search(doc.get("text") or "")
        if match:
            return doc, match, index
    return None


def evidence(record: dict, field: str) -> tuple[str | None, dict | None, str, str]:
    docs = record.get("documents", [])
    if field == "cusip":
        vals = []
        for document_index, doc in enumerate(docs, 1):
            text = doc.get("text") or ""
            for m in re.finditer(r"\bCUSIP(?:\s+(?:Number|No\.?))?\b.{0,320}?\b([0-9A-Z]{8}[0-9])\b", text, re.I | re.S):
                token = m.group(1).upper()
                if token not in {v[0] for v in vals}:
                    vals.append((token, doc, document_index))
        if len(vals) == 1:
            token, doc, document_index = vals[0]
            source_span = span(doc, token, document_index)
            return source_span["text"] if source_span else None, source_span, "single literal nine-character CUSIP token found in bounded CUSIP context", "medium; cover formatting and multiple classes require human review"
        if len(vals) > 1:
            return None, None, "multiple distinct CUSIP tokens found; bounded mechanical triage cannot choose", "high"
        return None, None, "no unambiguous CUSIP token in cached document text", "high"
    if field == "event_date":
        found = first_doc(record, r"Date\s+of\s+Event.{0,320}")
        if found:
            doc, m, document_index = found
            raw = m.group(0)
            dm = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b", raw, re.I)
            if dm:
                return dm.group(0), span(doc, dm.group(0), document_index), "literal date adjacent to Date of Event heading", "medium; date semantics remain for human review"
        return None, None, "no unambiguous event date adjacent to the filing heading", "high"
    if field == "item4":
        found = first_doc(record, r"(?:ITEM|Item)\s*4\.?\s*[^\n]{0,100}")
        if found:
            doc, m, document_index = found
            text = doc.get("text") or ""
            start = m.start()
            while start < len(text) and text[start].isspace():
                start += 1
            nxt = re.search(r"(?:^|\s)(?:ITEM|Item)\s*5\s*[.:]", text[start + 5:])
            if not nxt:
                return None, None, "Item 4 has no clear Item 5 boundary in cached text", "high"
            end = start + 5 + nxt.start()
            body = text[start:end]
            return body, {"document_index": document_index, "filename": doc.get("filename"), "start": start, "end": end, "text": body, "context_text": body}, "literal Item 4 heading and bounded following section excerpt recovered from cached document", "medium; section boundary may require human review"
        return None, None, "Item 4 heading/body absent from cached document text", "high"
    if field == "references":
        return None, None, "detected reference has no uniquely resolved target in cached evidence bundle; cannot determine", "high; detector may miss plural or explanatory references"
    return None, None, "binary or unsupported exception requires human review", "high"


def main() -> None:
    records = {json.loads(line)["accession"]: json.loads(line) for line in (PREP / "reparsed-records.jsonl").read_text().splitlines()}
    exceptions = json.loads((PREP / "exceptions.json").read_text())
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out = ROOT / "output/phase1-prep" / ("triage-" + timestamp.replace("-", "").replace(":", "").replace(".", ""))
    prompt_hash = sha256(PROMPT)
    rows = []
    for ex in exceptions:
        acc = ex["accession"]
        rec = records[acc]
        raw_path = ROOT / rec["source_path"]
        raw_hash = sha256(raw_path) if raw_path.exists() else None
        recorded = rec.get("source_sha256")
        hash_ok = raw_hash == recorded
        for flag in ex["flags"]:
            field = {"missing_cusip": "cusip", "missing_event_date": "event_date", "missing_item4_text": "item4", "unresolved_detected_references": "references"}.get(flag, "binary")
            value, source_span, rationale, uncertainty = evidence(rec, field)
            if not hash_ok:
                value, source_span = None, None
                rationale = "raw source hash does not match recorded hash; cannot determine"
                uncertainty = "high"
            rows.append({"accession": acc, "flag": flag, "field": field, "candidate": value,
                         "status": "candidate_for_human_review" if value is not None else "cannot_determine",
                         "source_span": source_span, "source_path": str(rec["source_path"]),
                         "source_sha256_recorded": recorded, "source_sha256_observed": raw_hash,
                         "source_hash_verified": hash_ok, "model_judgment": True,
                         "model": MODEL, "provider": PROVIDER, "timestamp_utc": timestamp,
                         "prompt_sha256": prompt_hash, "rationale": rationale, "uncertainty": uncertainty})
    assert len(rows) == sum(len(ex["flags"]) for ex in exceptions)
    assert all(row["source_hash_verified"] for row in rows)
    for row in rows:
        if row["source_span"] is not None:
            assert row["source_span"]["start"] >= 0
            assert row["source_span"]["end"] >= row["source_span"]["start"]
            assert row["source_span"]["text"]
            doc = records[row["accession"]]["documents"][row["source_span"]["document_index"] - 1]
            source_text = doc.get("text") or ""
            assert source_text[row["source_span"]["start"]:row["source_span"]["end"]] == row["source_span"]["text"], (row["accession"], row["field"], repr(source_text[row["source_span"]["start"]:row["source_span"]["end"]]), repr(row["source_span"]["text"]))
            if row["field"] != "item4":
                assert source_text[row["source_span"]["context_start"]:row["source_span"]["context_end"]] == row["source_span"]["context_text"]
            if row["candidate"] is not None:
                assert row["candidate"] in source_text[row["source_span"]["start"]:row["source_span"]["end"]] if row["field"] == "item4" else row["candidate"] in row["source_span"]["text"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "task_prompt.txt").write_text(PROMPT.read_text())
    (out / "triage.json").write_text(json.dumps({"metadata": {"model": MODEL, "provider": PROVIDER, "timestamp_utc": timestamp, "prompt_sha256": prompt_hash, "prompt_path": str(PROMPT), "script_sha256": sha256(Path(__file__)), "input_hashes": {"exceptions_sha256": sha256(PREP / "exceptions.json"), "records_sha256": sha256(PREP / "reparsed-records.jsonl")}, "offline": True, "human_packets_modified": False, "supersedes": "output/phase1-prep/triage-20260914T003050627334Z"}, "records": rows}, indent=2) + "\n")
    counts = {}
    for row in rows:
        counts.setdefault(row["flag"], {"n": 0, "candidate": 0, "cannot_determine": 0})
        counts[row["flag"]]["n"] += 1
        counts[row["flag"]][row["status"].replace("candidate_for_human_review", "candidate")] += 1
    overlap = {acc: len(ex["flags"]) for acc, ex in ((e["accession"], e) for e in exceptions) if len(ex["flags"]) > 1}
    report = ["# Exploratory Phase 1 exception triage", "", "Offline, source-backed mechanical triage. Exploratory model judgments are not facts and do not alter blank human-review packets.", "", f"Model: `{MODEL}`; provider: `{PROVIDER}`; timestamp UTC: `{timestamp}`; prompt SHA-256: `{prompt_hash}`", "", "## Counts", "", "```json", json.dumps(counts, indent=2), "```", "", f"There are {len(rows)} flag rows across {len(exceptions)} exception filings; {len(overlap)} filings carry overlapping flags ({sum(overlap.values())} flag instances). Overlaps are counted per filing and per flag.", "", "Each row in `triage.json` carries an accession, exact cached-document offsets, source hashes, rationale, uncertainty, and the model-judgment marker. Binary-document flags are explicitly `cannot_determine`. No intent, economic, eligibility, or campaign labels were generated.", ""]
    (out / "REPORT.md").write_text("\n".join(report))


if __name__ == "__main__":
    main()
