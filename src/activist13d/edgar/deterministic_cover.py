"""Extract source-backed Schedule 13D cover facts without interpretation.

Inputs: a frozen canonical evidence bundle and its verified raw SEC submission.
Outputs: separate reporting-person, ownership and security rows, plus field issues.
Identity: one ownership row belongs to one disclosed person and security; holdings
are never added across persons. Text offsets index the exact saved Unicode text.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_deterministic_cover.py
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from activist13d.edgar.submission import FORMS, _xml_root

RULE = "deterministic-cover-v1"
STATUS_MISSING = "not_found_in_supplied_text"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _empty(rule: str, status: str = STATUS_MISSING) -> dict:
    return {
        "raw_value": None,
        "value": None,
        "status": status,
        "rule": f"{RULE}:{rule}",
        "evidence": [],
    }


def _text_evidence(document: dict, start: int, end: int) -> dict:
    text = document["text"]
    return {
        "document_id": document["document_id"],
        "text_sha256": document["text_sha256"],
        "start": start,
        "end": end,
        "quote": text[start:end],
    }


def _text_field(
    document: dict, candidates: list[tuple[int, int]], rule: str, normalize=lambda s: s.strip()
) -> dict:
    values = []
    for start, end in candidates:
        raw = document["text"][start:end]
        try:
            value = normalize(raw)
        except (ValueError, InvalidOperation):
            value = None
        values.append(
            {"raw_value": raw, "value": value, "evidence": [_text_evidence(document, start, end)]}
        )
    if not values:
        return _empty(rule)
    valid = [v for v in values if v["value"] is not None]
    if not valid:
        return {**_empty(rule, "invalid_format"), "alternatives": values}
    unique = {str(v["value"]) for v in valid}
    if len(unique) != 1 or len(valid) != len(values):
        return {**_empty(rule, "ambiguous"), "alternatives": values}
    return {
        "raw_value": valid[0]["raw_value"],
        "value": valid[0]["value"],
        "status": "present",
        "rule": f"{RULE}:{rule}",
        "evidence": [e for v in valid for e in v["evidence"]],
    }


def _xml_field(
    nodes: list, document: dict, root, source_hash: str, rule: str, normalize=lambda s: s.strip()
) -> dict:
    values = []
    for node in nodes:
        raw = (node.text or "").strip()
        try:
            value = normalize(raw)
        except (ValueError, InvalidOperation):
            value = None
        evidence = {
            "document_id": document["document_id"],
            "element_path": root.getroottree().getpath(node),
            "raw_value": raw,
            "representation": "raw_xml_fragment_utf8",
            "representation_sha256": source_hash,
        }
        values.append({"raw_value": raw, "value": value, "evidence": [evidence]})
    if not values:
        return _empty(rule)
    valid = [v for v in values if v["value"] is not None]
    if not valid:
        return {**_empty(rule, "invalid_format"), "alternatives": values}
    if len(valid) != len(values) or len({str(v["value"]) for v in valid}) != 1:
        return {**_empty(rule, "ambiguous"), "alternatives": values}
    return {
        "raw_value": valid[0]["raw_value"],
        "value": valid[0]["value"],
        "status": "present",
        "rule": f"{RULE}:{rule}",
        "evidence": [e for v in valid for e in v["evidence"]],
    }


def _integer(raw: str) -> int:
    value = _numeric_source(raw)
    if re.fullmatch(r"-\s*0\s*-", value):
        return 0
    match = re.fullmatch(r"((?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.0+)?", value)
    if match is None:
        raise ValueError("invalid reported share count")
    return int(Decimal(value.replace(",", "")))


def _percent(raw: str) -> str:
    value = _numeric_source(raw).removesuffix("%")
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise ValueError("invalid percent")
    if Decimal(value) > 100:
        raise ValueError("percent above 100")
    return value


def _numeric_source(raw: str) -> str:
    """Admit only a complete reported quantity plus bounded footnote text."""
    value = raw.strip()
    value = re.sub(r"^\(\s*see\s+Item\s+\d+\s*\)\s*", "", value, flags=re.I)
    value = re.sub(r"\s*\(\s*see\s+Item\s+\d+\s*\)\s*$", "", value, flags=re.I)
    value = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", value)
    value = re.sub(r"\s*\*+\s*$", "", value)
    value = re.sub(
        r"\s+shares?(?:\s+of\s+(?:the\s+)?(?:Common|Class\s+[A-Z])\s+Stock)?\s*$",
        "",
        value,
        flags=re.I,
    )
    return value.strip()


def _cusip(raw: str) -> str:
    value = re.sub(r"\s+", "", raw).upper()
    if not re.fullmatch(r"[A-Z0-9*@#]{9}", value):
        raise ValueError("invalid CUSIP syntax")
    return value


def _date(raw: str) -> str:
    for fmt in ("%B %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError("date format unresolved")


def _matches(text: str, pattern: str, lo: int, hi: int, flags=re.I) -> list[tuple[int, int]]:
    return [
        (lo + m.start(1), lo + m.end(1))
        for m in re.finditer(pattern, text[lo:hi], flags)
        for _ in [0]
        if m.group(1) is not None
    ]


def _label_value(
    text: str, block_start: int, block_end: int, label: str, following: str
) -> list[tuple[int, int]]:
    block = text[block_start:block_end]
    matches = []
    for match in re.finditer(label, block, re.I):
        rest = re.search(following, block[match.end() :], re.I)
        if rest is None:
            continue
        start = block_start + match.end()
        end = start + rest.start()
        # Instructions and explanatory footnotes follow labels or values in
        # many flattened HTML covers; do not turn either into a numeric value.
        while True:
            instruction = re.match(r"\s*\(\s*See Instructions\s*\)\s*", text[start:end], re.I)
            if instruction is None:
                break
            start += instruction.end()
        while start < end and text[start] in ":. ":
            start += 1
        value = text[start:end]
        lead = len(value) - len(value.lstrip())
        tail = len(value) - len(value.rstrip())
        start += lead
        end -= tail
        if start < end:
            matches.append((start, end))
    return matches


_LABELS = [
    r"(?<!\w)\(?1\)?\.?\s+NAMES?\s+OF\s+(?:THE\s+)?REPORTING\s+PERSONS?\.?(?:\s*/?\s*(?:OR\s+)?I\.?R\.?S\.?\s+IDENTIFICATION\s+NOS?\.?\s+OF\s+ABOVE\s+PERSONS?(?:\s*\(entities only\))?:?)?",
    r"(?<!\w)\(?2\)?\.?\s+CHECK\s+THE\s+APPROPRIATE\s+BOX\b",
    r"(?<!\w)\(?3\)?\.?\s+SEC\s+USE\s+ONLY\b",
    r"(?<!\w)\(?4\)?\.?\s+SOURCE\s+OF\s+FUNDS?\b",
    r"(?<!\w)\(?5\)?\.?\s+CHECK(?:\s+(?:THE|BOX))?\s+IF\s+DISCLOSURE\b",
    r"(?<!\w)\(?6\)?\.?\s+CITIZENSHIP\s+OR\s+PLACE\s+OF\s+ORGANIZATION\b",
    r"(?<!\w)\(?7\)?\.?\s+SOLE\s+VOTING\s+POWER\b",
    r"(?<!\w)\(?8\)?\.?\s+SHARED\s+VOTING\s+POWER\b",
    r"(?<!\w)\(?9\)?\.?\s+SOLE\s+DISPOSITIVE\s+POWER\b",
    r"(?<!\w)\(?10\)?\.?\s+SHARED\s+DISPOSITIVE\s+POWER\b",
    r"(?<!\w)\(?11\)?\.?\s+AGGREGATE\s+AMOUNT\s+BENEFICIALLY\s+OWNED(?:\s+BY\s+EACH\s+(?:REPORTING\s+)?PERSON)?\b",
    r"(?<!\w)\(?12\)?\.?\s+CHECK(?:\s+BOX)?\s+IF\s+THE\s+AGGREGATE\s+AMOUNT\b",
    r"(?<!\w)\(?13\)?\.?\s+PERCENT\s+OF\s+CLASS\s+REPRESENTED(?:\s+BY\s+AMOUNT\s+IN\s+ROW\s*\(?\d+\)?)?",
    r"(?<!\w)\(?14\)?\.?\s+TYPE\s+OF\s+REPORTING\s+PERSON\b",
]


def _codes(text: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = []
    for lo, hi in spans:
        segment = text[lo:hi]
        match = re.match(r"\s*([A-Z]{2,3}\b(?:(?:\s*[,;/-]\s*|\s+)[A-Z]{2,3}\b)*)", segment)
        if match:
            for code in re.finditer(r"[A-Z]{2,3}", segment[match.start(1) : match.end(1)]):
                out.append((lo + match.start(1) + code.start(), lo + match.start(1) + code.end()))
        elif segment.strip():
            out.append((lo, hi))
    return out


def _fund_code(raw: str) -> str:
    value = raw.strip().upper()
    if value not in {"AF", "WC", "PF", "BK", "OO", "SC"}:
        raise ValueError("unrecognized source-of-funds code")
    return value


def _person_code(raw: str) -> str:
    value = raw.strip().upper()
    if value not in {
        "BD",
        "BK",
        "IC",
        "IV",
        "IA",
        "EP",
        "HC",
        "SA",
        "CP",
        "PN",
        "IN",
        "OO",
        "CO",
        "FI",
    }:
        raise ValueError("unrecognized reporting-person code")
    return value


def _name_and_tax(document: dict, spans: list[tuple[int, int]]) -> tuple[dict, dict]:
    name_spans = []
    tax_spans = []
    for lo, hi in spans:
        source = document["text"][lo:hi]
        tax = re.search(r"\b\d{2}-\d{7}\b", source)
        if tax:
            tax_spans.append((lo + tax.start(), lo + tax.end()))
        caption = re.search(
            r"\bI\.?R\.?S\.?\s+IDENTIFICATION\s+NOS?\.?\s+OF\s+ABOVE\s+PERSON", source, re.I
        )
        absent = re.search(r"\s*\(No IRS Identification No\.\)\s*$", source, re.I)
        if caption:
            hi = lo + caption.start()
        elif absent:
            hi = lo + absent.start()
        elif tax:
            hi = lo + tax.start()
            ein_label = re.search(r"\bEIN\s*[-:]?\s*$", document["text"][lo:hi], re.I)
            if ein_label:
                hi = lo + ein_label.start()
        while lo < hi and document["text"][lo] in ":. ":
            lo += 1
        while hi > lo and document["text"][hi - 1] in " *":
            hi -= 1
        if hi > lo:
            name_spans.append((lo, hi))
    return (
        _text_field(document, name_spans, "cover_row_1_name"),
        _text_field(
            document,
            tax_spans,
            "cover_row_1_tax_id",
            lambda s: s if re.fullmatch(r"\d{2}-\d{7}", s) else None,
        ),
    )


def _legacy(document: dict, accession: str) -> dict:
    text = document["text"]
    starts = list(re.finditer(_LABELS[0], text, re.I))
    first_cover = starts[0].start() if starts else len(text)
    preamble = text[:first_cover]
    cover_fields = {
        "issuer_name": _text_field(
            document,
            _matches(
                text,
                r"(?:\b1934|\(Amendment\s+No\.[^)]*\)\s*[*\d]*)\s+([^()]{1,180}?)\s*\(Name of Issuer\)",
                0,
                first_cover,
            ),
            "issuer_name_after_form_heading",
        ),
        "security_title": _text_field(
            document,
            _matches(text, r"([^()]{1,180}?)\s*\(Title of Class of Securities\)", 0, first_cover),
            "security_title_from_labeled_cover",
        ),
        "cusip": _text_field(
            document,
            _matches(
                text,
                r"\b([A-Z0-9*@#]{6}\s*[A-Z0-9*@#]{2}\s*[A-Z0-9*@#])\s*\(CUSIP Number\)",
                0,
                first_cover,
            ),
            "cusip_from_labeled_cover",
            _cusip,
        ),
        "event_date": _text_field(
            document,
            _matches(
                text,
                r"\b([A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4})\s*\(Date of Event which Requires Filing of this (?:Statement|Schedule)\)",
                0,
                first_cover,
            ),
            "event_date_from_labeled_cover",
            _date,
        ),
    }
    # Long preambles can include other labels; the complete labeled cover
    # candidate is preferred only when it is unique, never by plausibility.
    if cover_fields["cusip"]["status"] == STATUS_MISSING:
        page_cusips = [
            (m.start(1), m.end(1))
            for m in re.finditer(r"\bCUSIP\s*NO\.?\s*([A-Z0-9*@#]{9})\b", preamble, re.I)
        ]
        cover_fields["cusip"] = _text_field(
            document, page_cusips, "cusip_from_page_heading", _cusip
        )
    people, ownership = [], []
    security_id = f"{accession}:S01"
    for index, start_match in enumerate(starts, 1):
        start = start_match.start()
        end = starts[index].start() if index < len(starts) else len(text)
        if index == len(starts):
            item = re.search(r"\bItem\s+1\s*[.:-]\s*Security\b", text[start:end], re.I)
            if item:
                end = start + item.start()
        # A cover needs row 14 to close it. Otherwise later prose may be
        # swallowed into a person's fields and must be refused.
        final_row = re.search(_LABELS[13], text[start:end], re.I)
        if final_row is None:
            continue
        end = min(end, start + final_row.end() + 300)

        def row(n: int, first=start, last=end) -> list[tuple[int, int]]:
            return _label_value(text, first, last, _LABELS[n - 1], _LABELS[n])

        person_id = f"{accession}:P{index:02d}"
        name, tax_id = _name_and_tax(document, row(1))
        citizenship = _text_field(
            document,
            row(6),
            "cover_row_6_citizenship",
            lambda s: re.sub(r"\s+NUMBER OF SHARES.*", "", s, flags=re.I).strip(),
        )
        # Row 6 to row 7 includes the printed ownership-grid heading.
        funds = _text_field(document, _codes(text, row(4)), "cover_row_4_funds", _fund_code)
        code_spans = _label_value(
            text, start, end, _LABELS[13], r"\b(?:CUSIP\s*NO\.?|Item\s+1\s*[.:-]\s*Security|$)"
        )
        if not code_spans:
            code_spans = [
                (start + m.end(), min(end, start + m.end() + 50))
                for m in re.finditer(_LABELS[13], text[start:end], re.I)
            ]
        code = _text_field(document, _codes(text, code_spans), "cover_row_14_type", _person_code)
        people.append(
            {
                "accession": accession,
                "person_id": person_id,
                "name": name,
                "cik": _empty("legacy_cover_has_no_cik"),
                "tax_id": tax_id,
                "person_code": code,
                "citizenship": citizenship,
                "source_of_funds": funds,
            }
        )
        amounts = {}
        for field, number in (
            ("sole_voting_power", 7),
            ("shared_voting_power", 8),
            ("sole_dispositive_power", 9),
            ("shared_dispositive_power", 10),
            ("aggregate_shares", 11),
        ):
            amounts[field] = _text_field(
                document, row(number), f"cover_row_{number}_{field}", _integer
            )
        amounts["percent_of_class"] = _text_field(
            document, row(13), "cover_row_13_percent", _percent
        )
        ownership.append(
            {"accession": accession, "person_id": person_id, "security_id": security_id, **amounts}
        )
    return {
        "reporting_persons": people,
        "ownership": ownership,
        "securities": [
            {
                "accession": accession,
                "security_id": security_id,
                "title": cover_fields["security_title"],
                "cusip": cover_fields["cusip"],
            }
        ],
        "cover_fields": cover_fields,
    }


def _xml(document: dict, accession: str, root, source_hash: str) -> dict:
    def field(nodes, rule, norm=str.strip):
        return _xml_field(nodes, document, root, source_hash, rule, norm)

    def xpath(node, key):
        return node.xpath(f"./*[local-name()='{key}']")

    headers = root.xpath("//*[local-name()='coverPageHeader']")
    head = headers[0] if len(headers) == 1 else root
    issuers = xpath(head, "issuerInfo")
    issuer = issuers[0] if len(issuers) == 1 else head
    cover_fields = {
        "issuer_name": field(xpath(issuer, "issuerName"), "xml_cover_issuer_name"),
        "security_title": field(xpath(head, "securitiesClassTitle"), "xml_cover_security_title"),
        "cusip": field(xpath(issuer, "issuerCUSIP"), "xml_cover_cusip", _cusip),
        "event_date": field(xpath(head, "dateOfEvent"), "xml_cover_event_date", _date),
    }
    security_id = f"{accession}:S01"
    people, ownership = [], []
    for index, node in enumerate(root.xpath("//*[local-name()='reportingPersonInfo']"), 1):
        person_id = f"{accession}:P{index:02d}"
        people.append(
            {
                "accession": accession,
                "person_id": person_id,
                "name": field(xpath(node, "reportingPersonName"), "xml_person_name"),
                "cik": field(
                    xpath(node, "reportingPersonCIK"),
                    "xml_person_cik",
                    lambda s: s if re.fullmatch(r"\d{10}", s) else None,
                ),
                "tax_id": _empty("xml_cover_tax_id_unavailable"),
                "person_code": field(xpath(node, "typeOfReportingPerson"), "xml_person_type"),
                "citizenship": field(xpath(node, "citizenshipOrOrganization"), "xml_citizenship"),
                "source_of_funds": field(xpath(node, "fundType"), "xml_fund_type"),
            }
        )
        ownership.append(
            {
                "accession": accession,
                "person_id": person_id,
                "security_id": security_id,
                **{
                    key: field(xpath(node, tag), f"xml_{tag}", norm)
                    for key, tag, norm in (
                        ("sole_voting_power", "soleVotingPower", _integer),
                        ("shared_voting_power", "sharedVotingPower", _integer),
                        ("sole_dispositive_power", "soleDispositivePower", _integer),
                        ("shared_dispositive_power", "sharedDispositivePower", _integer),
                        ("aggregate_shares", "aggregateAmountOwned", _integer),
                        ("percent_of_class", "percentOfClass", _percent),
                    )
                },
            }
        )
    return {
        "reporting_persons": people,
        "ownership": ownership,
        "securities": [
            {
                "accession": accession,
                "security_id": security_id,
                "title": cover_fields["security_title"],
                "cusip": cover_fields["cusip"],
            }
        ],
        "cover_fields": cover_fields,
    }


def extract_cover(bundle: dict, payload: bytes) -> dict:
    """Extract cover facts from the verified raw source and immutable text bundle.

    The caller remains responsible for checking raw source SHA-256. This method
    also checks it when a source hash is supplied and checks the chosen text hash.
    """
    accession = bundle["accession"]
    expected = bundle.get("source_sha256")
    if expected and hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("Raw source SHA-256 differs from bundle")
    primaries = [
        d for d in bundle["documents"] if d.get("type") in FORMS and d.get("text") is not None
    ]
    if len(primaries) != 1:
        raise ValueError(f"Expected one readable primary 13D document, found {len(primaries)}")
    primary = primaries[0]
    if _sha(primary["text"]) != primary["text_sha256"]:
        raise ValueError("Canonical text SHA-256 differs")
    decoded = payload.decode("utf-8", errors="replace")
    raw_primaries = []
    for block in re.findall(r"<DOCUMENT>\s*(.*?)</DOCUMENT>", decoded, re.S | re.I):
        kind = re.search(r"^<TYPE>\s*([^\r\n]+)", block, re.M | re.I)
        filename = re.search(r"^<FILENAME>\s*([^\r\n]+)", block, re.M | re.I)
        if (
            kind
            and kind[1].strip() in FORMS
            and filename
            and filename[1].strip() == primary["filename"]
        ):
            body = re.search(r"<TEXT>\s*(.*?)</TEXT>", block, re.S | re.I)
            if body:
                raw_primaries.append(body[1])
    if len(raw_primaries) != 1:
        raise ValueError("Primary raw document cannot be matched uniquely")
    root = _xml_root(raw_primaries[0])
    if root is not None:
        result = _xml(primary, accession, root, _sha(raw_primaries[0]))
    else:
        result = _legacy(primary, accession)
    issues = []
    for field, value in result["cover_fields"].items():
        if value["status"] != "present":
            issues.append(
                {
                    "accession": accession,
                    "field": field,
                    "issue_type": value["status"],
                    "alternatives": value.get("alternatives", []),
                }
            )
    if not result["reporting_persons"]:
        issues.append(
            {
                "accession": accession,
                "field": "reporting_persons",
                "issue_type": STATUS_MISSING,
                "alternatives": [],
            }
        )
    for person in result["reporting_persons"]:
        for key in ("name", "person_code", "citizenship", "source_of_funds"):
            value = person[key]
            if value["status"] != "present":
                issues.append(
                    {
                        "accession": accession,
                        "person_id": person["person_id"],
                        "field": key,
                        "issue_type": value["status"],
                        "alternatives": value.get("alternatives", []),
                    }
                )
    for row in result["ownership"]:
        for key in (
            "aggregate_shares",
            "percent_of_class",
            "sole_voting_power",
            "shared_voting_power",
            "sole_dispositive_power",
            "shared_dispositive_power",
        ):
            value = row[key]
            if value["status"] != "present":
                issues.append(
                    {
                        "accession": accession,
                        "person_id": row["person_id"],
                        "field": key,
                        "issue_type": value["status"],
                        "alternatives": value.get("alternatives", []),
                    }
                )
    result["issues"] = issues
    return result
