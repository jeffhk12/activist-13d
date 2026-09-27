"""Versioned deterministic filing/party extraction and evidence verification.

Inputs: a frozen canonical bundle and verified raw submission. Output: related
factual tables; no semantic classifications. Identity: every canonical citation
equals text[start:end]; header parties are never merged with cover people.
Tier: 1. Run via scripts/extraction_protocol/run_deterministic.py; offline tests.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

VERSION = "deterministic-v1"
STATUSES = {"present", "not_found_in_supplied_text", "ambiguous", "unavailable", "invalid_format"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def field(doc, pattern, rule, normalize=lambda s: s, bounds=None):
    text = doc.get("text")
    result = {
        "raw_value": None,
        "value": None,
        "status": "not_found_in_supplied_text",
        "rule": rule,
        "parser_version": VERSION,
        "evidence": [],
    }
    if text is None:
        result["status"] = "unavailable"
        return result
    start, end = bounds or (0, len(text))
    matches = list(re.finditer(pattern, text[start:end], re.I | re.M))
    candidates = []
    for match in matches:
        a, b = start + match.start(1), start + match.end(1)
        raw = text[a:b]
        try:
            value = normalize(raw)
            status = "present"
        except (ValueError, TypeError):
            value = None
            status = "invalid_format"
        candidates.append(
            {
                "raw_value": raw,
                "value": value,
                "status": status,
                "rule": rule,
                "parser_version": VERSION,
                "evidence": [
                    {
                        "document_id": doc["document_id"],
                        "text_sha256": doc["text_sha256"],
                        "start": a,
                        "end": b,
                        "quote": raw,
                    }
                ],
            }
        )
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        result.update(status="ambiguous", alternatives=candidates)
    return result


def normalize_cik(value):
    value = value.strip()
    if not re.fullmatch(r"\d{1,10}", value):
        raise ValueError("invalid CIK")
    return value.zfill(10)


def cusip_check_digit(value):
    """Syntax/check digit only; no historical instrument verification."""
    if not re.fullmatch(r"[A-Z0-9*@#]{8}\d", value):
        return False
    total = 0
    for i, char in enumerate(value[:8]):
        number = (
            int(char)
            if char.isdigit()
            else (ord(char) - 55 if char.isalpha() else {"*": 36, "@": 37, "#": 38}[char])
        )
        number *= 1 + (i % 2)
        total += number // 10 + number % 10
    return (10 - total % 10) % 10 == int(value[-1])


def header_tables(bundle):
    doc = next(
        (x for x in bundle["documents"] if x["document_id"] == "SEC-HEADER"),
        {"document_id": "SEC-HEADER", "text": None},
    )
    text = doc.get("text") or ""
    accession = bundle["accession"]
    filing = {
        "accession": accession,
        "accession_field": field(doc, r"ACCESSION NUMBER:\s*([^\r\n]+)", "header-accession"),
        "source_form": field(
            doc, r"CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)", "header-form", str.strip
        ),
        "filing_date": field(
            doc,
            r"FILED AS OF DATE:\s*([^\r\n]+)",
            "header-date-YYYYMMDD",
            lambda s: datetime.strptime(s.strip(), "%Y%m%d").date().isoformat(),
        ),
        "acceptance_datetime_et": field(
            doc,
            r"<ACCEPTANCE-DATETIME>([^\r\n<]+)",
            "header-acceptance-YYYYMMDDhhmmss-America_New_York",
            lambda s: datetime.strptime(s.strip(), "%Y%m%d%H%M%S").isoformat(),
        ),
    }
    form = filing["source_form"]
    filing["initial_or_amendment"] = {
        **form,
        "rule": "header-form-suffix-A",
        "value": None
        if form["status"] != "present"
        else ("amendment" if form["value"].endswith("/A") else "initial"),
    }
    filing["acceptance_timezone_convention"] = (
        "America/New_York; source has no explicit UTC offset; no execution session assigned"
    )
    issuers, filing_entities = [], []
    for match in re.finditer(
        r"^(SUBJECT COMPANY|FILED BY|FILER|REPORTING-OWNER):[^\n]*\n(.*?)(?=^(?:SUBJECT COMPANY|FILED BY|FILER|REPORTING-OWNER):|\Z)",
        text,
        re.M | re.S,
    ):
        role = match.group(1)
        row = {
            "accession": accession,
            "header_role": role,
            "name": field(
                doc,
                r"COMPANY CONFORMED NAME:[ \t]*([^\r\n]+)",
                "header-party-name-verbatim",
                bounds=match.span(2),
            ),
            "cik": field(
                doc,
                r"CENTRAL INDEX KEY:[ \t]*([^\r\n]+)",
                "header-cik-zfill10",
                normalize_cik,
                match.span(2),
            ),
        }
        target = issuers if role == "SUBJECT COMPANY" else filing_entities
        row["entity_id"] = (
            f"{accession}:{'I' if role == 'SUBJECT COMPANY' else 'F'}{len(target) + 1:02d}"
        )
        target.append(row)
    return filing, issuers, filing_entities


def stamp_fields(value):
    if isinstance(value, dict):
        if {"raw_value", "value", "status", "rule", "evidence"} <= value.keys():
            value.setdefault("parser_version", VERSION)
        for child in value.values():
            stamp_fields(child)
    elif isinstance(value, list):
        for child in value:
            stamp_fields(child)


def verify_citations(value, bundle):
    docs = {d["document_id"]: d for d in bundle["documents"]}
    count = 0

    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            if {"start", "end", "quote", "document_id"} <= node.keys():
                doc = docs[node["document_id"]]
                text = doc.get("text")
                if (
                    text is None
                    or not isinstance(node["start"], int)
                    or not isinstance(node["end"], int)
                ):
                    raise ValueError("Unusable citation")
                if not 0 <= node["start"] <= node["end"] <= len(text):
                    raise ValueError("Citation bounds")
                if (
                    text[node["start"] : node["end"]] != node["quote"]
                    or doc["text_sha256"] != node["text_sha256"]
                ):
                    raise ValueError("Citation parity failed")
                count += 1
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return count


def extract(bundle, payload):
    from activist13d.edgar.deterministic_cover import extract_cover
    from activist13d.edgar.deterministic_sections import extract_sections
    from activist13d.edgar.submission import parse_submission

    if sha(payload) != bundle["source_sha256"]:
        raise ValueError("Raw source SHA mismatch")
    for doc in bundle["documents"]:
        if doc.get("text") is not None and sha(doc["text"].encode()) != doc["text_sha256"]:
            raise ValueError("Canonical source SHA mismatch")
    parsed = parse_submission(payload)
    originals = {f"DOCUMENT[{d['source_document_index']}]": d for d in parsed["documents"]}
    decoded = (
        payload.decode("utf-8")
        if parsed["decoded_as"] == "utf-8"
        else payload.decode("cp1252", errors="replace")
    )
    for doc in bundle["documents"]:
        if doc["document_id"] == "SEC-HEADER":
            if doc.get("text") not in decoded.split("<DOCUMENT>", 1)[0]:
                raise ValueError("Frozen header differs from raw header")
            continue
        original = originals.get(doc["document_id"])
        if original is None or any(
            doc.get(k) != original.get(k) for k in ["filename", "type", "text"]
        ):
            raise ValueError("Raw-to-canonical document parity failed: " + doc["document_id"])
    filing, issuers, entities = header_tables(bundle)
    if filing["accession_field"]["value"] != bundle["accession"]:
        raise ValueError("Accession mismatch")
    cover = extract_cover(bundle, payload)
    sections = extract_sections(bundle)
    filing.update(
        event_date=cover["cover_fields"]["event_date"],
        source_url=bundle["source_url"],
        source_path=bundle["source_path"],
        source_sha256=bundle["source_sha256"],
        source_provenance="frozen input bundle; SHA verified against local raw bytes",
        parsing_status="processed",
        body_issuer_name=cover["cover_fields"]["issuer_name"],
    )
    docs = []
    for doc in bundle["documents"]:
        docs.append(
            {
                "accession": bundle["accession"],
                **{
                    k: doc.get(k)
                    for k in ["document_id", "type", "filename", "status", "text_sha256"]
                },
                "is_embedded_exhibit": bool((doc.get("type") or "").startswith("EX-")),
                "metadata_provenance": "frozen canonical bundle; raw and canonical hashes verified",
            }
        )
    result = {
        "parser_version": VERSION,
        "accession": bundle["accession"],
        "filings": [filing],
        "issuers": issuers,
        "filing_entities": entities,
        "reporting_persons": cover["reporting_persons"],
        "securities": cover["securities"],
        "ownership": cover["ownership"],
        "documents": docs,
        "sections": sections["sections"],
        "references": sections["references"],
        "quality_issues": cover["issues"] + sections["issues"],
    }
    if len(issuers) != 1:
        result["quality_issues"].append(
            {
                "accession": bundle["accession"],
                "field": "issuer",
                "issue_type": "multiple_or_missing_header_subjects",
                "candidates": issuers,
            }
        )
    if len(issuers) == 1:
        body = filing["body_issuer_name"]
        header = issuers[0]["name"]
        if (
            body["status"] == "present"
            and header["status"] == "present"
            and " ".join(body["value"].upper().split()) != " ".join(header["value"].upper().split())
        ):
            result["quality_issues"].append(
                {
                    "accession": bundle["accession"],
                    "field": "issuer_name",
                    "issue_type": "header_body_name_difference_unresolved",
                    "candidates": [header, body],
                }
            )
    for person in result["reporting_persons"]:
        person.setdefault(
            "cik",
            {
                "raw_value": None,
                "value": None,
                "status": "not_found_in_supplied_text",
                "rule": "no-header-to-cover-entity-merge",
                "evidence": [],
            },
        )
    for security in result["securities"]:
        cusip = security["cusip"]
        security["cusip_check_digit_valid"] = {
            **cusip,
            "rule": "cusip-alternate-double-digit-sum-mod10-not-security-match",
            "value": cusip_check_digit(cusip["value"]) if cusip["status"] == "present" else None,
        }
        if cusip["status"] == "present" and not security["cusip_check_digit_valid"]["value"]:
            result["quality_issues"].append(
                {
                    "accession": bundle["accession"],
                    "field": "cusip",
                    "issue_type": "check_digit_failed_not_identity_determination",
                    "candidates": [cusip],
                }
            )
    stamp_fields(result)
    verify_citations(result, bundle)
    return result
