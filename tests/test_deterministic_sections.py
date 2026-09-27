"""Offline section and reference extraction pins against inspected text.

Inputs: small frozen-text fixtures. Outputs: cited section and reference rows.
Identity: Unicode text[start:end] == quote and SHA-256 is exact.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_deterministic_sections.py
"""

import hashlib
import json
from pathlib import Path

import pytest

from activist13d.edgar.deterministic_sections import extract_sections


def document(index, kind, text, description=None):
    return {"document_id": f"DOCUMENT[{index}]", "type": kind,
            "filename": f"d{index}.htm", "description": description,
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None}


def bundle(text, extras=()):
    return {"accession": "0000000000-26-000001",
            "documents": [document(1, "SC 13D", text), *extras]}


def test_references_are_not_headings_and_offsets_are_exact():
    text = ("Item 1. Security and Issuer Common shares. "
            "See Item 3, Item 4 and Item 5 for related details. "
            "Item 2. Identity and Background Two reporting persons. "
            "Item 3. Source and Amount of Funds Cash. "
            "Item 4. Purpose of Transaction Agreement described in Item 6. "
            "Item 5. Interest in Securities of the Issuer Five percent. "
            "Item 6. Contracts, Arrangements, Understandings or Relationships Joint Filing Agreement. "
            "Item 7. Material to be Filed as Exhibits Exhibit 99.1. "
            "SIGNATURES After reasonable inquiry, we certify. "
            "Schedule I Transaction Type Buy")
    result = extract_sections(bundle(text, [document(2, "EX-99.1", "Joint Filing Agreement")]))
    assert [row["field"]["status"] for row in result["sections"][:7]] == ["present"] * 7
    assert result["sections"][3]["span"]["start"] == text.index("Item 4. Purpose")
    assert result["sections"][3]["span"]["end"] == text.index("Item 5. Interest")
    assert result["sections"][7]["field"]["status"] == "present"
    assert result["sections"][8]["field"]["status"] == "present"
    assert any(row["key"] == "99.1" and row["resolution_status"] == "embedded_located"
               for row in result["references"])
    for row in result["sections"] + result["references"]:
        for proof in row["field"]["evidence"]:
            assert text[proof["start"]:proof["end"]] == proof["quote"]
            assert proof["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()


def test_repeated_full_heading_is_ambiguous_with_both_alternatives():
    text = ("Contents: Item 4. Purpose of Transaction page 8. "
            "Item 4. Purpose of Transaction We plan to communicate.")
    result = extract_sections(bundle(text))
    row = result["sections"][3]
    assert row["field"]["status"] == "ambiguous"
    assert row["span"] is None
    assert len(row["field"]["evidence"]) == 2
    assert any(issue["issue_type"] == "ambiguous_heading" for issue in result["issues"])


def test_unresolved_exhibit_is_preserved_without_completeness_claim():
    text = "Item 7. Material to be Filed as Exhibits See Exhibit B and Exhibit 99.7."
    result = extract_sections(bundle(text, [document(2, "EX-99.1", "Other material")]))
    assert [row["resolution_status"] for row in result["references"]] == [
        "referenced_unresolved", "referenced_unresolved"
    ]
    assert len([issue for issue in result["issues"] if issue["issue_type"] == "referenced_unresolved"]) == 2


def test_unreadable_exhibit_and_missing_primary_text():
    text = "Item 7. Material to be Filed as Exhibits Exhibit 99.1"
    unreadable = document(2, "EX-99.1", None)
    result = extract_sections(bundle(text, [unreadable]))
    assert result["references"][0]["resolution_status"] == "embedded_unreadable"
    result = extract_sections({"accession": "a", "documents": [document(1, "SC 13D", None)]})
    assert all(row["field"]["status"] == "unavailable" for row in result["sections"])


def test_pdf_mirror_with_same_primary_type_does_not_hide_readable_sections():
    source = bundle("Item 4. Purpose of Transaction Text.", [document(2, "SC 13D", None)])
    result = extract_sections(source)
    assert result["sections"][3]["field"]["status"] == "present"
    assert result["sections"][3]["document_id"] == "DOCUMENT[1]"


def test_hash_mismatch_refuses_citation():
    source = bundle("Item 4. Purpose of Transaction Text")
    source["documents"][0]["text_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        extract_sections(source)


def test_basswood_frozen_bundle_has_cited_item4_and_attached_exhibits():
    path = (Path(__file__).resolve().parents[1] / "review/drafts/human-first-52/bundles"
            / "0000899140-19-000386.json")
    source = json.loads(path.read_text(encoding="utf-8"))
    result = extract_sections(source)
    item4 = result["sections"][3]
    assert item4["field"]["status"] == "present"
    assert item4["span"] is not None
    assert any(row["key"] == "99.1" and row["resolution_status"] == "embedded_located"
               for row in result["references"])
    assert any(row["key"] == "99.2" and row["resolution_status"] == "embedded_located"
               for row in result["references"])
    by_id = {doc["document_id"]: doc["text"] for doc in source["documents"]}
    for row in result["sections"] + result["references"]:
        for proof in row["field"]["evidence"]:
            assert by_id[proof["document_id"]][proof["start"]:proof["end"]] == proof["quote"]
