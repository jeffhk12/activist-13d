"""Offline pins for deterministic header attribution and source refusal.

Inputs: invented SEC headers and small canonical bundles. Outputs: assertions
on distinct issuer/filer identities, dates, and evidence validation. Identity:
each extracted quote equals its original Unicode text slice; source bytes and
canonical document hashes must match before extraction.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_deterministic.py
"""

import hashlib

import pytest

from activist13d.edgar.deterministic import (
    cusip_check_digit,
    extract,
    field,
    header_tables,
    verify_citations,
)


def test_cusip_check_digit_is_not_an_identity_match():
    # Disclosed Basswood security, known check digit 5; one-digit corruption fails.
    assert cusip_check_digit("598039105") is True
    assert cusip_check_digit("598039106") is False
    # Eight zeros produce check digit zero; preserve the string, not integer zero.
    assert cusip_check_digit("000000000") is True
    assert cusip_check_digit("123") is False


ACCESSION = "0000000123-25-000001"
HEADER = (
    "<ACCEPTANCE-DATETIME>20250102163742\n"
    f"ACCESSION NUMBER: {ACCESSION}\n"
    "CONFORMED SUBMISSION TYPE: SC 13D/A\n"
    "FILED AS OF DATE: 20250102\n"
    "SUBJECT COMPANY:\n"
    "COMPANY DATA:\n"
    "COMPANY CONFORMED NAME: Issuer Inc.\n"
    "CENTRAL INDEX KEY: 123\n"
    "FILED BY:\n"
    "COMPANY DATA:\n"
    "COMPANY CONFORMED NAME: Manager LLC\n"
    "CENTRAL INDEX KEY: 45\n"
)


def document(text):
    return {
        "document_id": "SEC-HEADER",
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def bundle(text=HEADER, payload=b"invented submission"):
    return {
        "accession": ACCESSION,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "documents": [document(text)],
    }


def test_header_keeps_issuer_and_filer_separate_with_leading_zero_ciks():
    source = bundle()
    filing, issuers, filers = header_tables(source)
    assert filing["source_form"]["value"] == "SC 13D/A"
    assert filing["initial_or_amendment"]["value"] == "amendment"
    assert filing["filing_date"]["value"] == "2025-01-02"
    assert filing["acceptance_datetime_et"]["value"] == "2025-01-02T16:37:42"
    assert filing["acceptance_datetime_et"]["raw_value"] == "20250102163742"
    assert [row["name"]["value"] for row in issuers] == ["Issuer Inc."]
    assert [row["name"]["value"] for row in filers] == ["Manager LLC"]
    assert issuers[0]["cik"]["value"] == "0000000123"
    assert filers[0]["cik"]["value"] == "0000000045"
    assert verify_citations([filing, issuers, filers], source) > 0


def test_repeated_header_field_preserves_both_candidates():
    source = document("FILED AS OF DATE: 20250102\nFILED AS OF DATE: 20250103\n")
    value = field(source, r"FILED AS OF DATE:\s*([^\r\n]+)", "test-date")
    assert value["status"] == "ambiguous"
    assert [candidate["value"] for candidate in value["alternatives"]] == ["20250102", "20250103"]
    assert verify_citations(value, {"documents": [source]}) == 2


def test_raw_and_canonical_hash_mismatches_refuse_before_parsing():
    payload = b"invented submission"
    source = bundle(payload=payload)
    with pytest.raises(ValueError, match="Raw source SHA mismatch"):
        extract(source, payload + b" changed")
    source["documents"][0]["text_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Canonical source SHA mismatch"):
        extract(source, payload)


def test_citation_tampering_is_rejected():
    source = bundle()
    filing, _, _ = header_tables(source)
    citation = filing["filing_date"]["evidence"][0]
    citation["quote"] = "20250103"
    with pytest.raises(ValueError, match="Citation parity failed"):
        verify_citations(filing, source)
