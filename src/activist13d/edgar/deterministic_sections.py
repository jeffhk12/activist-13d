"""Locate 13D section headings and document references in frozen bundles.

Inputs: one evidence bundle with canonical document texts and hashes. Outputs:
section, exhibit/agreement reference, and quality-issue rows. Identity: every
reported quote equals canonical_text[start:end] in Unicode character offsets.
No reference or heading is inferred from economic context.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_deterministic_sections.py
"""

from __future__ import annotations

import hashlib
import re

RULE = "deterministic-sections-v1"
PRIMARY_TYPES = {"SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"}

# Heading titles provide a boundary that an ordinary "see Item 4" reference lacks.
# The canonical representation collapses HTML layout, so a repeated complete
# title is still ambiguous and must be retained as an alternative.
ITEM_TITLES = {
    1: r"Securit(?:y|ies)\s+and\s+(?:the\s+)?Issuer",
    2: r"Identity\s+and\s+Background",
    3: r"Source\s+(?:and|or)\s+Amount\s+of\s+Funds(?:\s+or\s+Other\s+Consideration)?",
    4: r"Purpose\s+of\s+(?:the\s+)?Transaction",
    5: r"Interest\s+in\s+(?:the\s+)?Securities(?:\s+of\s+(?:the\s+)?Issuer)?",
    6: r"(?:Contracts?|Contacts),\s*Arrangements?,\s*Understandings?\s+or\s+Relationships?",
    7: r"(?:Material(?:s)?\s+to\s+be\s+(?:Filed|Files)\s+as\s+(?:an?\s+)?Exhibits?|Exhibits?)",
}
EXHIBIT = re.compile(r"\bExhibit\s+(?P<key>(?:\d{1,3}(?:\.\d{1,3})?|[A-Z]))\b", re.I)
AGREEMENT = re.compile(
    r"\b(?:[A-Z][\w'-]*\s+){1,7}(?:Agreement|Agreements)\b"
)


def _evidence(doc: dict, start: int, end: int) -> dict:
    source = doc["text"]
    return {
        "document_id": doc["document_id"],
        "text_sha256": doc["text_sha256"],
        "start": start,
        "end": end,
        "quote": source[start:end],
    }


def _field(status: str, evidence: list[dict], raw: str | None = None) -> dict:
    return {
        "raw_value": raw,
        "value": raw,
        "status": status,
        "rule": RULE,
        "evidence": evidence,
    }


def _verified_documents(bundle: dict) -> list[dict]:
    documents = bundle.get("documents", [])
    for doc in documents:
        source = doc.get("text")
        if source is not None and hashlib.sha256(source.encode("utf-8")).hexdigest() != doc.get("text_sha256"):
            raise ValueError(f"Canonical text hash mismatch: {doc.get('document_id')}")
    return documents


def _title_candidates(text: str) -> dict[int, list[re.Match]]:
    return {
        number: list(re.finditer(
            rf"\bItem\s+{number}\s*(?:\([a-z]\)\s+and\s+\([a-z]\))?\s*[.:-]?\s*{title}\b", text, re.I
        ))
        for number, title in ITEM_TITLES.items()
    }


def _auxiliary_candidates(text: str, label: str) -> list[re.Match]:
    if label == "SIGNATURES":
        return list(re.finditer(r"\bSIGNATURES?\s+After\s+reasonable\s+inquiry\b", text, re.I))
    if label == "SCHEDULE":
        return list(re.finditer(
            r"\bSchedule\s+(?:[IVX]+|[A-Z])\s+Transaction\s+Type\b", text, re.I
        ))
    raise ValueError(label)


def _sections(bundle: dict, doc: dict) -> tuple[list[dict], list[dict]]:
    text = doc["text"]
    accession = bundle["accession"]
    candidates = _title_candidates(text)
    auxiliary = {label: _auxiliary_candidates(text, label) for label in ("SIGNATURES", "SCHEDULE")}
    starts = sorted(match.start() for matches in candidates.values() for match in matches)
    starts += [match.start() for matches in auxiliary.values() for match in matches]
    starts.sort()
    rows = []
    issues = []
    for number, matches in candidates.items():
        label = f"ITEM {number}"
        proofs = [_evidence(doc, match.start(), match.end()) for match in matches]
        status = "present" if len(matches) == 1 else ("ambiguous" if matches else "not_found_in_supplied_text")
        row = {"accession": accession, "document_id": doc["document_id"], "section": label,
               "field": _field(status, proofs, matches[0].group() if len(matches) == 1 else None),
               "span": None}
        if len(matches) == 1:
            start = matches[0].start()
            later = [candidate for candidate in starts if candidate > start]
            end = later[0] if later else len(text)
            row["span"] = {"start": start, "end": end} if end > start else None
        elif len(matches) > 1:
            issues.append({"accession": accession, "document_id": doc["document_id"],
                           "field": label, "issue_type": "ambiguous_heading",
                           "candidates": proofs})
        rows.append(row)
    for label, matches in auxiliary.items():
        # A signature or schedule label is credible only after the numbered body.
        numbered = [m.start() for group in candidates.values() for m in group]
        matches = [m for m in matches if numbered and m.start() > min(numbered)]
        proofs = [_evidence(doc, m.start(), m.end()) for m in matches]
        status = "present" if len(matches) == 1 else ("ambiguous" if matches else "not_found_in_supplied_text")
        rows.append({"accession": accession, "document_id": doc["document_id"], "section": label,
                     "field": _field(status, proofs, matches[0].group() if len(matches) == 1 else None),
                     "span": None})
        if len(matches) > 1:
            issues.append({"accession": accession, "document_id": doc["document_id"],
                           "field": label, "issue_type": "ambiguous_heading", "candidates": proofs})
    return rows, issues


def _exhibit_matches(key: str, documents: list[dict]) -> list[dict]:
    matches = []
    for doc in documents:
        form = (doc.get("type") or "").upper()
        filename = (doc.get("filename") or "").upper()
        description = (doc.get("description") or "").upper()
        if not form.startswith("EX-"):
            continue
        # Numbered exhibits require the exact submitted document type. A
        # lettered exhibit requires an explicit metadata label, not a guess
        # from a filename or the contents of an unrelated exhibit.
        if key.isdigit() or re.fullmatch(r"\d+\.\d+", key):
            found = form == f"EX-{key}"
        else:
            found = bool(re.search(rf"\bEXHIBIT\s+{re.escape(key)}\b", description)
                         or re.search(rf"\bEXHIBIT\s+{re.escape(key)}\b", filename))
        if found:
            matches.append(doc)
    return matches


def _reference_rows(bundle: dict, primary: dict, documents: list[dict]) -> tuple[list[dict], list[dict]]:
    text = primary["text"]
    rows = []
    issues = []
    for match in EXHIBIT.finditer(text):
        key = match.group("key").upper()
        candidates = _exhibit_matches(key, documents)
        if len(candidates) == 1:
            target = candidates[0]
            status = "embedded_unreadable" if target.get("text") is None else "embedded_located"
            targets = [target["document_id"]]
        else:
            status = "ambiguous" if candidates else "referenced_unresolved"
            targets = [d["document_id"] for d in candidates]
        evidence = _evidence(primary, match.start(), match.end())
        rows.append({"accession": bundle["accession"], "document_id": primary["document_id"],
                     "reference_type": "exhibit", "key": key,
                     "field": _field("present", [evidence], match.group()),
                     "resolution_status": status, "target_document_ids": targets})
        if status != "embedded_located":
            issues.append({"accession": bundle["accession"], "document_id": primary["document_id"],
                           "field": "exhibit_reference", "issue_type": status,
                           "candidates": [evidence], "target_document_ids": targets})
    for match in AGREEMENT.finditer(text):
        quote = match.group()
        # An exact phrase appearing in just one exhibit is a deterministic
        # location hint, not proof the exhibit is complete or legally operative.
        targets = [d for d in documents if (d.get("type") or "").upper().startswith("EX-")
                   and d.get("text") is not None and quote.casefold() in d["text"].casefold()]
        target_ids = [d["document_id"] for d in targets]
        status = "embedded_located" if len(targets) == 1 else (
            "ambiguous" if len(targets) > 1 else "referenced_unresolved"
        )
        evidence = _evidence(primary, match.start(), match.end())
        rows.append({"accession": bundle["accession"], "document_id": primary["document_id"],
                     "reference_type": "agreement", "key": quote,
                     "field": _field("present", [evidence], quote),
                     "resolution_status": status, "target_document_ids": target_ids})
    return rows, issues


def extract_sections(bundle: dict) -> dict:
    """Return factual section and reference rows from verified canonical text.

    Missing text yields unavailable section rows. A complete title repeated in
    canonical text yields ambiguous alternatives; none is silently selected.
    """
    documents = _verified_documents(bundle)
    primary = [d for d in documents if (d.get("type") or "").upper() in PRIMARY_TYPES]
    output = {"sections": [], "references": [], "issues": []}
    readable = [d for d in primary if d.get("text") is not None]
    # A PDF mirror may bear the same SC 13D type as the text document. Keep
    # that unreadable document in the bundle, but use the sole readable text.
    if len(readable) == 1:
        primary = readable
    if len(primary) != 1:
        output["issues"].append({"accession": bundle["accession"], "document_id": None,
                                 "field": "primary_document", "issue_type": "ambiguous" if primary else "unavailable",
                                 "candidates": [d["document_id"] for d in primary]})
        return output
    doc = primary[0]
    if doc.get("text") is None:
        for label in [*(f"ITEM {n}" for n in range(1, 8)), "SIGNATURES", "SCHEDULE"]:
            output["sections"].append({"accession": bundle["accession"], "document_id": doc["document_id"],
                                       "section": label, "field": _field("unavailable", []), "span": None})
        return output
    output["sections"], output["issues"] = _sections(bundle, doc)
    output["references"], reference_issues = _reference_rows(bundle, doc, documents)
    output["issues"].extend(reference_issues)
    return output
