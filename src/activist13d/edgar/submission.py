"""Parse complete SEC submissions into source-backed pilot records.

Inputs: raw disseminated SGML bytes. Outputs: header roles, documents, XML
leaf fields, and a candidate Item 4 span. No inferred intent or numeric labels.
Identity: every extracted document comes from one <DOCUMENT> block.
Tier: 1
Run: via scripts/collect_pilot.py; tested offline with explicit fixtures.
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup
from lxml import etree

FORMS = {"SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"}


def _match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.I | re.M)
    return match.group(1).strip() if match else None


def _plain(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for node in soup(["script", "style"]):
        node.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _roles(header: str, role: str) -> list[dict]:
    parties = []
    for block in re.finditer(
        rf"^{role}:\s*\n(.*?)(?=^(?:FILED BY|SUBJECT COMPANY|FILER|REPORTING-OWNER):|\Z)",
        header, re.M | re.S,
    ):
        text = block.group(1)
        parties.append({
            "name": _match(r"COMPANY CONFORMED NAME:\s*([^\n]+)", text),
            "cik": _match(r"CENTRAL INDEX KEY:\s*(\d+)", text),
        })
    return parties


def _xml_root(body: str):
    start = re.search(r"<\?xml\b|<edgarSubmission\b", body)
    if start is None:
        return None
    xml = body[start.start():].strip()
    xml = re.sub(r"</XML>\s*$", "", xml, flags=re.I).strip()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(xml.encode("utf-8"), parser)


def _xml_fields(root) -> dict[str, list[str]]:
    fields = {}
    if root is None:
        return fields
    for node in root.iter():
        if isinstance(node.tag, str) and len(node) == 0 and node.text and node.text.strip():
            fields.setdefault(etree.QName(node).localname, []).append(node.text.strip())
    return fields


def _cover_fields(primary_text: str, root, fields: dict) -> dict:
    """Preserve per-person XML ownership; legacy ownership remains unparsed."""
    people = []
    if root is not None:
        for node in root.xpath("//*[local-name()='reportingPersonInfo']"):
            people.append(_xml_fields(node))
        cusips = fields.get("issuerCUSIP", [])
        event_dates = fields.get("dateOfEvent", [])
        cusip = cusips[0] if len(cusips) == 1 else None
        event_raw = event_dates[0] if len(event_dates) == 1 else None
        date_format = "%m/%d/%Y"
    else:
        # Cover-page labels anchor these candidates; unrelated body numbers do not qualify.
        cusip = _match(r"\b([A-Z0-9]{6}\s*[A-Z0-9]{2}\s*[0-9])\s*\(CUSIP\s+Number\)", primary_text)
        event_raw = _match(
            r"\b([A-Z][a-z]+\s+\d{1,2},\s*\d{4})\s*"
            r"\(Date\s+of\s+Event\s+Which\s+Requires\s+Filing\s+of\s+this\s+Statement\)",
            primary_text,
        )
        date_format = "%B %d, %Y"
        if event_raw is None:
            event_raw = _match(
                r"Date\s+of\s+Event\s+Which\s+Requires\s+Filing\s+of\s+this\s+Statement"
                r"\s*[:)]?\s*(\d{1,2}/\d{1,2}/\d{4})\b", primary_text,
            )
            date_format = "%m/%d/%Y"
    event_date = None
    if event_raw:
        try:
            event_date = datetime.strptime(event_raw, date_format).date().isoformat()
        except ValueError:
            pass
    return {
        "cusip": re.sub(r"\s+", "", cusip) if cusip else None,
        "event_date": event_date,
        "event_date_raw": event_raw,
        "reporting_persons_xml": people,
        "cover_fields_status": "xml_source_fields" if root is not None else "legacy_candidates_needs_review",
        "ownership_status": "per_person_xml_no_aggregation" if people else "not_parsed",
    }


def _item_section(text: str, number: int) -> str | None:
    """Return a source-preserved Item N candidate, refusing ambiguous headings."""
    # A punctuation mark distinguishes a section heading from "see Item 3".
    starts = list(re.finditer(rf"\bItem\s*{number}\s*[.:\-]\s*", text, re.I))
    if len(starts) != 1:
        return None
    following = re.search(r"\bItem\s*[1-9]\s*[.:\-]\s*", text[starts[0].end():], re.I)
    end = starts[0].end() + following.start() if following else len(text)
    value = text[starts[0].end():end].strip()
    return value if len(value) >= 20 else None


def evidence_bundle(record: dict) -> dict:
    """Separate Item 4, explicitly referenced sections, and exhibits.

    This makes no claim that a textual mention identifies a campaign or that an
    incorporated external filing has been recovered.  A reference is marked
    ``located_in_submission`` only where a submitted document can be matched.
    """
    item4 = record.get("item4_text") or ""
    primary = next((doc for doc in record["documents"] if doc["type"] in FORMS), {})
    primary_text = primary.get("text") or ""
    location = f"DOCUMENT[{primary.get('source_document_index', 'unknown')}]: {primary.get('filename')}"
    section_numbers = sorted({int(value) for value in re.findall(r"\bItem\s+([136])\b", item4, re.I)})
    sections = []
    for number in section_numbers:
        text = _item_section(primary_text, number)
        sections.append({
            "reference": f"Item {number}",
            "text": text,
            "source_location": location if text else None,
            "status": "located_in_primary" if text else "unresolved_or_external",
        })
    exhibits = []
    for letter in sorted(set(re.findall(r"\bExhibit\s+([A-Z])\b", item4, re.I))):
        matched = next((doc for doc in record["documents"] if re.search(
            rf"(?:EX-[^.]*\.|EXHIBIT\s*){letter}\b", (doc.get("type") or ""), re.I
        )), None)
        exhibits.append({
            "reference": f"Exhibit {letter.upper()}",
            "text": matched.get("text") if matched else None,
            "source_location": (
                f"DOCUMENT[{matched.get('source_document_index', 'unknown')}]: {matched['filename']}"
                if matched else None
            ),
            "status": "located_in_submission" if matched else "unresolved_or_external",
        })
    return {
        "item4": {
            "text": record.get("item4_text"),
            "source_location": record.get("item4_source_location"),
            "status": record.get("item4_status"),
        },
        "referenced_sections": sections,
        "referenced_exhibits": exhibits,
    }


def parse_submission(payload: bytes) -> dict:
    """Return candidates and source text; ambiguous/missing Item 4 stays null."""
    try:
        source = payload.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        source = payload.decode("cp1252", errors="replace")
        encoding = "cp1252_with_replacement"
    header = source.split("<DOCUMENT>", 1)[0]
    accession = _match(r"ACCESSION NUMBER:\s*([\d-]+)", header)
    if accession is None:
        raise ValueError("Submission accession header missing")
    accepted = _match(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if accepted:
        accepted = datetime.strptime(accepted, "%Y%m%d%H%M%S").isoformat()
    documents = []
    primary_bodies = []
    for document_index, block in enumerate(
        re.findall(r"<DOCUMENT>\s*(.*?)</DOCUMENT>", source, re.S | re.I), start=1
    ):
        form = _match(r"^<TYPE>([^\n]+)", block)
        filename = _match(r"^<FILENAME>([^\n]+)", block)
        body_match = re.search(r"<TEXT>\s*(.*?)</TEXT>", block, re.S | re.I)
        body = body_match.group(1) if body_match else ""
        binary = bool(filename and filename.lower().endswith(
            (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".xlsx")
        ))
        documents.append({
            "source_document_index": document_index,
            "type": form,
            "filename": filename,
            "description": _match(r"^<DESCRIPTION>([^\n]+)", block),
            "text": None if binary else _plain(body),
            "text_status": "binary_in_raw_submission" if binary else "parsed_text",
        })
        # Some submissions include a PDF mirror with the same SC 13D type as
        # the machine-readable primary document. Preserve that binary evidence
        # but do not treat it as a second textual primary.
        if form in FORMS and not binary:
            primary_bodies.append(body)
    if len(primary_bodies) != 1:
        raise ValueError(f"Expected one primary 13D document, found {len(primary_bodies)}")
    body = primary_bodies[0]
    root = _xml_root(body)
    fields = _xml_fields(root)
    primary_text = _plain(body)
    item4 = None
    status = "missing_needs_review"
    # XML names are retained verbatim below even when not yet recognised here.
    purpose = [value for key, values in fields.items()
               if key == "transactionPurpose" for value in values]
    if len(purpose) == 1:
        item4 = _plain(purpose[0])
        status = "xml_field_needs_review"
    elif not fields:
        starts = list(re.finditer(
            r"\bItem\s*4\s*[.:\-]?\s*Purpose\s+of\s+(?:the\s+)?Transaction\b[.:]?",
            primary_text, re.I,
        ))
        candidates = []
        for start in starts:
            end = re.search(r"\bItem\s*5\s*[.:\-]?\s*Interest\b", primary_text[start.end():], re.I)
            if end:
                candidate = primary_text[start.end():start.end() + end.start()].strip()
                if len(candidate) >= 40:
                    candidates.append(candidate)
        if len(candidates) == 1:
            item4 = candidates[0]
            status = "heading_span_needs_review"
        elif candidates:
            status = "ambiguous_needs_review"
    record = {
        "parser_version": "pilot-v1",
        "accession": accession,
        "acceptance_datetime_et": accepted,
        "acceptance_note": "EDGAR acceptance time; executable trading time not yet assigned",
        "filers": _roles(header, "FILED BY"),
        "subjects": _roles(header, "SUBJECT COMPANY"),
        "parser_source": "xml" if fields else "html_or_text",
        "decoded_as": encoding,
        "xml_fields": fields,
        **_cover_fields(primary_text, root, fields),
        "item4_text": item4,
        "item4_status": status,
        "item4_source_location": (
            f"DOCUMENT[{next(doc['source_document_index'] for doc in documents if doc['type'] in FORMS)}]"
            f": {next(doc['filename'] for doc in documents if doc['type'] in FORMS)} / "
            f"{'transactionPurpose XML leaf' if fields else 'Item 4 heading span'}"
            if item4 else None
        ),
        "documents": documents,
    }
    record["evidence_bundle"] = evidence_bundle(record)
    return record
