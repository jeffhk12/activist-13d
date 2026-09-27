"""Offline cover extraction pins for exact source attribution and refusal.

Inputs: independently inspected Basswood filing and small synthetic submissions.
Outputs: assertions on fields and exact evidence. Identity: same person row owns
its own reported figures; no cross-person share aggregation is performed.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_deterministic_cover.py
"""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from activist13d.edgar.deterministic_cover import extract_cover
from activist13d.local_paths import resolve_project_path

ROOT = Path(__file__).resolve().parents[1]


def test_space_separated_funds_codes_preserve_both():
    from activist13d.edgar.deterministic_cover import _codes, _fund_code, _text_field

    bundle, _ = synthetic("WC PF")
    doc = bundle["documents"][0]
    result = _text_field(doc, _codes(doc["text"], [(0, 5)]), "fund-codes-test", _fund_code)
    assert result["status"] == "ambiguous"
    assert [v["value"] for v in result["alternatives"]] == ["WC", "PF"]
    assert_citations(result, bundle)


def first_filing():
    path = ROOT / "review/drafts/human-first-52/bundles/0000899140-19-000386.json"
    bundle = json.loads(path.read_text())
    return bundle, resolve_project_path(bundle["source_path"], ROOT).read_bytes()


def test_farpoint_name_excludes_ein_caption():
    path = ROOT / "review/drafts/human-first-52/bundles/0001096906-13-001801.json"
    bundle = json.loads(path.read_text())
    result = extract_cover(bundle, resolve_project_path(bundle["source_path"], ROOT).read_bytes())
    assert result["reporting_persons"][0]["name"]["value"] == "Farpoint Capital Management, LLC"
    assert result["ownership"][0]["aggregate_shares"]["value"] == 680000
    assert result["ownership"][0]["percent_of_class"]["value"] == "5.17"
    assert_citations(result, bundle)


def synthetic(primary: str, kind: str = "SC 13D"):
    source = (
        "ACCESSION NUMBER: 0000000000-25-000001\n"
        f"<DOCUMENT>\n<TYPE>{kind}\n<FILENAME>primary.xml\n"
        f"<TEXT>{primary}</TEXT>\n</DOCUMENT>"
    ).encode()
    soup = BeautifulSoup(primary, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).split())
    document = {
        "document_id": "DOCUMENT[1]",
        "type": kind,
        "filename": "primary.xml",
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    return {
        "accession": "0000000000-25-000001",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "documents": [document],
    }, source


def assert_citations(result, bundle):
    docs = {d["document_id"]: d for d in bundle["documents"]}
    stack = [result]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "quote" in node:
                document = docs[node["document_id"]]
                assert document["text_sha256"] == node["text_sha256"]
                assert document["text"][node["start"] : node["end"]] == node["quote"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)


def test_basswood_eleven_people_and_overlapping_shares():
    bundle, source = first_filing()
    result = extract_cover(bundle, source)
    assert len(result["reporting_persons"]) == 11
    assert len(result["ownership"]) == 11
    assert result["cover_fields"]["issuer_name"]["value"] == "MidSouth Bancorp, Inc."
    assert result["cover_fields"]["security_title"]["value"] == "Common Stock, Par Value $0.10"
    assert result["cover_fields"]["cusip"]["value"] == "598039105"
    assert result["cover_fields"]["event_date"]["value"] == "2019-04-30"
    first = result["reporting_persons"][0]
    assert first["name"]["value"] == "Basswood Capital Management, L.L.C."
    assert first["person_code"]["value"] == "IA"
    assert first["citizenship"]["value"] == "Delaware"
    first_ownership = result["ownership"][0]
    assert first_ownership["aggregate_shares"]["value"] == 1641562
    assert first_ownership["percent_of_class"]["value"] == "9.82"
    assert first_ownership["shared_voting_power"]["value"] == 1641562
    assert first_ownership["sole_voting_power"]["value"] == 0
    assert result["ownership"][9]["aggregate_shares"]["value"] == 1641562
    assert result["ownership"][10]["aggregate_shares"]["value"] == 1641562
    assert result["ownership"][1]["aggregate_shares"]["value"] == 456831
    assert result["ownership"][2]["aggregate_shares"]["value"] == 403749
    assert_citations(result, bundle)
    assert all(
        e["document_id"] == "DOCUMENT[1]"
        for row in result["ownership"]
        for field in row.values()
        if isinstance(field, dict)
        for e in field.get("evidence", [])
    )


def test_missing_and_malformed_values_refuse():
    base = (
        "Issuer (Name of Issuer) Common Stock (Title of Class of Securities) "
        "000123456 (CUSIP Number) January 1, 2025 "
        "(Date of Event which Requires Filing of this Statement) "
        "1 NAME OF REPORTING PERSON A 2 CHECK THE APPROPRIATE BOX "
        "3 SEC USE ONLY 4 SOURCE OF FUNDS WC 5 CHECK IF DISCLOSURE "
        "6 CITIZENSHIP OR PLACE OF ORGANIZATION Delaware "
        "7 SOLE VOTING POWER unknown 8 SHARED VOTING POWER 100 "
        "9 SOLE DISPOSITIVE POWER 0 10 SHARED DISPOSITIVE POWER 100 "
        "11 AGGREGATE AMOUNT BENEFICIALLY OWNED 100 "
        "12 CHECK IF THE AGGREGATE AMOUNT 13 PERCENT OF CLASS REPRESENTED ?? "
        "14 TYPE OF REPORTING PERSON IN Item 1. Security and the Issuer"
    )
    bundle, source = synthetic(base)
    result = extract_cover(bundle, source)
    assert result["cover_fields"]["cusip"]["value"] == "000123456"
    row = result["ownership"][0]
    assert row["sole_voting_power"]["status"] == "invalid_format"
    assert row["percent_of_class"]["status"] == "invalid_format"
    assert row["shared_voting_power"]["value"] == 100
    assert_citations(result, bundle)


def test_xml_uses_paths_and_raw_value_with_leading_zero_cik():
    xml = (
        "<edgarSubmission><formData><coverPageHeader>"
        "<securitiesClassTitle>Common Stock</securitiesClassTitle>"
        "<dateOfEvent>01/22/2025</dateOfEvent><issuerInfo>"
        "<issuerCUSIP>000123456</issuerCUSIP><issuerName>Example Inc.</issuerName>"
        "</issuerInfo></coverPageHeader><reportingPersons>"
        "<reportingPersonInfo><reportingPersonCIK>0000012345</reportingPersonCIK>"
        "<reportingPersonName>A</reportingPersonName><fundType>WC</fundType>"
        "<citizenshipOrOrganization>DE</citizenshipOrOrganization>"
        "<soleVotingPower>0.00</soleVotingPower><sharedVotingPower>100.00</sharedVotingPower>"
        "<soleDispositivePower>0.00</soleDispositivePower>"
        "<sharedDispositivePower>100.00</sharedDispositivePower>"
        "<aggregateAmountOwned>100.00</aggregateAmountOwned><percentOfClass>6.1</percentOfClass>"
        "<typeOfReportingPerson>IA</typeOfReportingPerson></reportingPersonInfo>"
        "</reportingPersons></formData></edgarSubmission>"
    )
    bundle, source = synthetic(xml, "SCHEDULE 13D")
    result = extract_cover(bundle, source)
    assert result["reporting_persons"][0]["cik"]["value"] == "0000012345"
    assert result["ownership"][0]["aggregate_shares"]["value"] == 100
    assert result["ownership"][0]["percent_of_class"]["value"] == "6.1"
    evidence = result["reporting_persons"][0]["name"]["evidence"][0]
    assert evidence["element_path"].endswith("/reportingPersonName")
    assert evidence["raw_value"] == "A"
    assert "start" not in evidence


def test_conflicting_labeled_cusips_are_ambiguous_and_preserved():
    text = (
        "Issuer (Name of Issuer) Stock (Title of Class of Securities) "
        "000123456 (CUSIP Number) 000123457 (CUSIP Number) "
        "January 1, 2025 (Date of Event which Requires Filing of this Statement)"
    )
    bundle, source = synthetic(text)
    result = extract_cover(bundle, source)
    field = result["cover_fields"]["cusip"]
    assert field["status"] == "ambiguous"
    assert {v["value"] for v in field["alternatives"]} == {"000123456", "000123457"}
    assert_citations(result, bundle)


def test_hash_mismatch_refuses():
    bundle, source = synthetic("some text")
    try:
        extract_cover(bundle, source + b"altered")
    except ValueError as error:
        assert "Raw source SHA-256" in str(error)
    else:
        raise AssertionError("tampered source accepted")


def test_broadfin_footnotes_and_source_funds_are_bounded():
    path = ROOT / "review/drafts/human-first-52/bundles/0000921895-15-002053.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    assert result["cover_fields"]["issuer_name"]["value"] == "Cardica, Inc."
    first = result["ownership"][0]
    assert first["aggregate_shares"]["value"] == 8874992, first["aggregate_shares"]
    assert first["percent_of_class"]["value"] == "9.98"
    assert first["shared_voting_power"]["value"] == 0
    assert result["reporting_persons"][0]["source_of_funds"]["value"] == "WC"
    assert_citations(result, bundle)


def test_irs_caption_is_not_part_of_person_name():
    path = ROOT / "review/drafts/human-first-52/bundles/0001104659-24-077375.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    first = result["reporting_persons"][0]
    assert first["name"]["value"] == "Wynnefield Partners Small Cap Value, L.P. I"
    assert first["tax_id"]["value"] == "13-3953291"
    assert first["source_of_funds"]["value"] == "WC"
    assert_citations(result, bundle)


def test_multiple_reporting_codes_and_invalid_numeric_do_not_choose_first():
    text = (
        "1 NAME OF REPORTING PERSON A 2 CHECK THE APPROPRIATE BOX "
        "3 SEC USE ONLY 4 SOURCE OF FUNDS WC 5 CHECK IF DISCLOSURE "
        "6 CITIZENSHIP OR PLACE OF ORGANIZATION Delaware "
        "7 SOLE VOTING POWER 1,23 8 SHARED VOTING POWER - 0 - "
        "9 SOLE DISPOSITIVE POWER 0 10 SHARED DISPOSITIVE POWER 0 "
        "11 AGGREGATE AMOUNT BENEFICIALLY OWNED 1 234 "
        "12 CHECK IF THE AGGREGATE AMOUNT 13 PERCENT OF CLASS REPRESENTED <1% "
        "14 TYPE OF REPORTING PERSON IA, PN"
    )
    bundle, source = synthetic(text)
    result = extract_cover(bundle, source)
    person = result["reporting_persons"][0]
    assert person["person_code"]["status"] == "ambiguous"
    assert {v["value"] for v in person["person_code"]["alternatives"]} == {"IA", "PN"}
    row = result["ownership"][0]
    for key in ("sole_voting_power", "aggregate_shares", "percent_of_class"):
        assert row[key]["status"] == "invalid_format"
    assert row["shared_voting_power"]["value"] == 0
    assert_citations(result, bundle)


def test_all_52_frozen_bundles_keep_exact_text_citations():
    paths = sorted((ROOT / "review/drafts/human-first-52/bundles").glob("*.json"))
    assert len(paths) == 52
    empty_people = []
    for path in paths:
        bundle = json.loads(path.read_text())
        source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
        result = extract_cover(bundle, source)
        if not result["reporting_persons"]:
            empty_people.append(bundle["accession"])
        assert result["cover_fields"].keys() == {
            "issuer_name",
            "security_title",
            "cusip",
            "event_date",
        }
        assert_citations(result, bundle)
    assert not empty_people, empty_people


def test_parenthesized_rows_and_name_caption():
    path = ROOT / "review/drafts/human-first-52/bundles/0001062993-15-006284.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    assert result["reporting_persons"][0]["name"]["value"] == "Birch Run Capital Advisors, LP"
    assert result["ownership"][0]["aggregate_shares"]["value"] == 7474587
    assert result["ownership"][0]["percent_of_class"]["value"] == "19.8"
    assert_citations(result, bundle)


def test_row_9_percent_reference_and_three_fund_codes():
    path = ROOT / "review/drafts/human-first-52/bundles/0001213900-23-094576.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    assert result["ownership"][0]["aggregate_shares"]["value"] == 1842087
    assert result["ownership"][0]["percent_of_class"]["value"] == "12.4"
    funds = result["reporting_persons"][0]["source_of_funds"]
    assert funds["status"] == "ambiguous"
    assert {v["value"] for v in funds["alternatives"]} == {"PF", "AF", "OO"}
    assert_citations(result, bundle)


def test_irs_caption_after_name_is_removed_and_tax_kept():
    path = ROOT / "review/drafts/human-first-52/bundles/0001104659-18-021860.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    first = result["reporting_persons"][0]
    assert first["name"]["value"] == "Sagard Capital Partners, L.P."
    assert first["tax_id"]["value"] == "20-3332164"
    assert_citations(result, bundle)


def test_slash_irs_caption_does_not_pollute_name():
    path = ROOT / "review/drafts/human-first-52/bundles/0001144204-15-038283.json"
    bundle = json.loads(path.read_text())
    source = resolve_project_path(bundle["source_path"], ROOT).read_bytes()
    result = extract_cover(bundle, source)
    first = result["reporting_persons"][0]
    assert first["name"]["value"] == "Roumell Asset Management, LLC"
    assert first["tax_id"]["value"] == "52-2145132"
    assert result["ownership"][0]["aggregate_shares"]["value"] == 1184510
    assert result["ownership"][0]["percent_of_class"]["value"] == "5.5"
    assert_citations(result, bundle)
