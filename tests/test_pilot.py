"""Offline contract tests for pilot evidence collection and parsing.

Inputs: synthetic SGML fixtures, stubbed HTTP. Outputs: explicit assertions.
Identity: one initial document plus one exhibit equals two source documents.
Tier: 1
Run: .venv/bin/python -m pytest tests/test_pilot.py
"""

import hashlib
import json

import pytest

from activist13d.edgar.client import SecClient
from activist13d.edgar.index import parse_index
from activist13d.edgar.submission import evidence_bundle, parse_submission

HEADER = """<SEC-DOCUMENT>
<SEC-HEADER>
<ACCEPTANCE-DATETIME>20240102163000
ACCESSION NUMBER: 0001234567-24-000001
SUBJECT COMPANY:
 COMPANY DATA:
  COMPANY CONFORMED NAME: TEST TARGET
  CENTRAL INDEX KEY: 0000000111
FILED BY:
 COMPANY DATA:
  COMPANY CONFORMED NAME: TEST FILER
  CENTRAL INDEX KEY: 0000000222
</SEC-HEADER>
"""


def submission(body, form="SC 13D", filename="main.htm"):
    return (HEADER + f"""<DOCUMENT>
<TYPE>{form}
<FILENAME>{filename}
<TEXT>{body}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-99
<FILENAME>letter.htm
<TEXT><p>This is the board letter.</p></TEXT>
</DOCUMENT>
""").encode()


def test_roles_item4_and_exhibit_are_preserved():
    intent = "We request that the issuer appoint two additional independent directors."
    raw = submission(f"<p>Item 4. Purpose of Transaction</p><p>{intent}</p>"
                     "<p>Item 5. Interest in Securities</p><p>Other text.</p>")
    result = parse_submission(raw)
    assert result["filers"] == [{"name": "TEST FILER", "cik": "0000000222"}]
    assert result["subjects"] == [{"name": "TEST TARGET", "cik": "0000000111"}]
    assert result["acceptance_datetime_et"] == "2024-01-02T16:30:00"
    assert result["item4_text"] == intent
    assert len(result["documents"]) == 2
    assert result["documents"][1]["text"] == "This is the board letter."
    assert parse_submission(raw) == result


def test_missing_heading_is_not_invented():
    result = parse_submission(submission("<p>We own some shares.</p>"))
    assert result["item4_text"] is None
    assert result["item4_status"] == "missing_needs_review"


def test_binary_duplicate_primary_document_does_not_displace_html_schedule():
    """A PDF copy filed under SC 13D is evidence, not a second parse target."""
    intent = "We request that the issuer appoint two independent directors."
    raw = (HEADER + f"""<DOCUMENT>
<TYPE>SC 13D
<FILENAME>main.htm
<TEXT><p>Item 4. Purpose of Transaction</p><p>{intent}</p>
<p>Item 5. Interest in Securities</p><p>Other text.</p></TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>SC 13D
<FILENAME>filed-copy.pdf
<TEXT>%PDF-1.4 binary evidence retained in raw submission</TEXT>
</DOCUMENT>
""").encode()
    result = parse_submission(raw)
    assert result["item4_text"] == intent
    assert result["documents"][1]["text_status"] == "binary_in_raw_submission"


def test_xml_leaf_fields_preserve_multiple_reporting_person_values():
    xml = """<XML><edgarSubmission><transactionPurpose>We seek board representation.</transactionPurpose>
<dateOfEvent>01/02/2025</dateOfEvent><issuerCUSIP>123456789</issuerCUSIP>
<reportingPersonInfo><reportingPersonName>A</reportingPersonName><percentOfClass>6.1</percentOfClass></reportingPersonInfo>
<reportingPersonInfo><reportingPersonName>B</reportingPersonName><percentOfClass>6.1</percentOfClass></reportingPersonInfo>
</edgarSubmission></XML>"""
    result = parse_submission(submission(xml, "SCHEDULE 13D", "primary_doc.xml"))
    assert result["parser_source"] == "xml"
    assert result["xml_fields"]["percentOfClass"] == ["6.1", "6.1"]
    assert result["item4_text"] == "We seek board representation."
    assert result["event_date"] == "2025-01-02"
    assert result["reporting_persons_xml"][1]["reportingPersonName"] == ["B"]
    assert result["reporting_persons_xml"][1]["percentOfClass"] == ["6.1"]


def test_legacy_cover_uses_label_anchors():
    result = parse_submission(submission(
        "<p>60743G 100 (CUSIP Number)</p><p>December 21, 2023</p>"
        "<p>(Date of Event Which Requires Filing of this Statement)</p>"
    ))
    assert result["cusip"] == "60743G100"
    assert result["event_date"] == "2023-12-21"
    assert result["ownership_status"] == "not_parsed"


def test_legacy_date_after_label_and_absent_cusip():
    result = parse_submission(submission(
        "<pre>DATE OF EVENT WHICH REQUIRES FILING OF THIS STATEMENT\n1/17/2024</pre>"
    ))
    assert result["event_date"] == "2024-01-17"
    assert result["cusip"] is None


def test_partial_index_is_refused():
    raw = ("header\n------------------------------\n"
           "SC 13D  TEST TARGET  111  2024-01-02  edgar/data/111/0001234567-24-000001.txt\n"
           "SC 13D  corrupted row\n")
    with pytest.raises(ValueError, match="unparsed rows"):
        parse_index(raw)


def test_fetch_requires_contact_before_network(tmp_path, monkeypatch):
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)
    with pytest.raises(ValueError, match="contact email"):
        SecClient().fetch("https://www.sec.gov/test", tmp_path / "raw.txt")


def test_cache_verification_and_offline_replay(tmp_path, monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Test Fixture test@university.edu")
    payload = b"raw filing evidence"
    calls = []

    class Response:
        content = payload
        headers = {"Content-Type": "text/plain"}

        def raise_for_status(self):
            pass

    def fetch(*args, **kwargs):
        calls.append(args)
        return Response()

    monkeypatch.setattr("activist13d.edgar.client.requests.get", fetch)
    url = "https://www.sec.gov/test"
    destination = tmp_path / "raw.txt"
    assert SecClient().fetch(url, destination) == payload
    assert SecClient(offline=True).fetch(url, destination) == payload
    assert len(calls) == 1
    meta = json.loads((tmp_path / "raw.txt.meta.json").read_text())
    assert meta["sha256"] == hashlib.sha256(payload).hexdigest()
    destination.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="provenance mismatch"):
        SecClient(offline=True).fetch(url, destination)


def test_missing_offline_cache_is_refused(tmp_path):
    with pytest.raises(FileNotFoundError, match="Offline cache missing"):
        SecClient(offline=True).fetch("https://www.sec.gov/test", tmp_path / "missing")


def test_evidence_bundle_keeps_item4_section_and_exhibit_separate():
    """A textual cross-reference must not overwrite Item 4 or become inferred text."""
    raw = submission(
        "<p>Item 3. Source and Amount of Funds</p><p>Cash was used for the purchase.</p>"
        "<p>Item 4. Purpose of Transaction</p><p>See Item 3 and Exhibit B for our proposal.</p>"
        "<p>Item 5. Interest in Securities</p><p>Other text.</p>"
    )
    result = parse_submission(raw)
    result["documents"][1]["type"] = "EX-7.B"
    bundle = evidence_bundle(result)
    assert bundle["item4"]["text"] == "See Item 3 and Exhibit B for our proposal."
    assert bundle["referenced_sections"] == [{
        "reference": "Item 3", "text": "Source and Amount of Funds Cash was used for the purchase.",
        "source_location": "DOCUMENT[1]: main.htm", "status": "located_in_primary",
    }]
    assert bundle["referenced_exhibits"][0]["reference"] == "Exhibit B"
    assert bundle["referenced_exhibits"][0]["text"] == "This is the board letter."
    assert bundle["referenced_exhibits"][0]["status"] == "located_in_submission"


def test_streamed_response_limit_refuses_before_cache_write(tmp_path, monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Test Fixture test@university.edu")

    class Response:
        headers = {"Content-Type": "text/plain"}

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"1234"
            yield b"5678"

    monkeypatch.setattr("activist13d.edgar.client.requests.get", lambda *args, **kwargs: Response())
    destination = tmp_path / "raw.txt"
    with pytest.raises(ValueError, match="per-response size"):
        SecClient(max_response_bytes=7).fetch("https://www.sec.gov/test", destination)
    assert not destination.exists()
