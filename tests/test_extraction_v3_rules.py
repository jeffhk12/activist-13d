"""Synthetic v3 policy/schema guards; no source filings or model calls.

Inputs: invented policy cases, v3 builder and preserved v2 category IDs.
Outputs: assertions. Identity: all three role policies are byte-identical;
schema preserves nine categories, qualified funding and intervention gates.
Tier: 1 support. Run project Python -m pytest tests/test_extraction_v3_rules.py.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts/extraction_protocol"))
import build_extraction_v3 as build  # noqa: E402


def intent(status, basis):
    return {"status": status, "qualification_basis": basis, "actor": "Aster", "target": "Orion",
            "evidence_status": "sufficient_supplied_evidence", "rationale": "Invented example.",
            "evidence": [{"document_id": "one", "quote": "source"}]}


def validator_at(schema, key):
    return Draft202012Validator({"$defs": schema["$defs"], **schema["properties"][key]})


def test_role_common_rules_are_byte_identical_and_generation_replays():
    result = build.artifacts()
    assert result == build.artifacts()
    common = result["extraction-common-rules-v3.md"]
    for role in ["extractor", "blind", "critic"]:
        prompt = result[f"extraction-role-{role}-v3.txt"]
        assembled = build.role_instructions(role).encode()
        assert assembled[:len(common)] == common
        assert assembled[len(common)+1:] == prompt
        assert b"primary_control_bid" not in prompt  # Semantic policy lives in shared file.
    # All roles see the general all-category gate and preservation of routine facts.
    assert b"Routine terms alone do not become extra objectives" in common
    assert b"Transaction row count is excluded from the first ranking model" in common


def test_nine_category_ids_and_meanings_preserved():
    old = json.loads((ROOT / "research/protocol/categories-stability-v2.json").read_text())
    new = build.categories()
    assert new["categories"] == old["categories"]
    assert len(new["categories"]) == 9
    schema = build.extraction_schema()
    Draft202012Validator.check_schema(schema)
    assert set(schema["properties"]["intent"]["required"]) == {c["id"] for c in old["categories"]}


def test_merger_and_separate_nomination_examples_have_different_qualification():
    schema = build.extraction_schema()
    examples = {c["id"]: c for c in build.example_cases()}
    merger = examples["merger_mechanics"]["labels"]
    nomination = examples["independent_nomination"]["labels"]
    assert merger["sale_of_company"] == ("present", "primary_control_bid")
    assert merger["board_representation"] == ("not_stated", "nonqualifying_facts")
    assert nomination["board_representation"] == ("present", "separate_intervention")
    # The referenced letter leaves the current position itself unavailable, not
    # merely the nominee names/details of an already explicit nomination plan.
    assert examples["missing_specific_letter"]["labels"]["board_representation"] == ("cannot_determine", "uncertain")
    all_labels = {c["id"]: intent("not_stated", "none") for c in build.categories()["categories"]}
    for key, (status, basis) in merger.items():
        all_labels[key] = intent(status, basis)
    v = validator_at(schema, "intent")
    v.validate(all_labels)
    invalid = copy.deepcopy(all_labels)
    invalid["board_representation"]["status"] = "present"
    with pytest.raises(ValidationError):
        v.validate(invalid)  # Nonqualifying mechanics cannot be labelled present.
    invalid["board_representation"] = intent("present", "primary_control_bid")
    with pytest.raises(ValidationError):
        v.validate(invalid)  # A control bid cannot manufacture board labels.
    all_labels["board_representation"] = intent(*nomination["board_representation"])
    v.validate(all_labels)


def test_qualified_funding_and_security_specific_ownership_are_required():
    schema = build.extraction_schema()
    component = {"actor": "Aster", "type": "borrowed_funds", "certainty": "possible",
                 "acquisition_link": "future_possible", "description": "May borrow later.",
                 "evidence": [{"document_id": "one", "quote": "may borrow"}]}
    funding = {"status": "present", "summary": "Available facility; actual use unestablished.",
               "components": [component], "evidence": component["evidence"]}
    v = validator_at(schema, "funding")
    v.validate(funding)
    invalid = copy.deepcopy(funding)
    invalid["components"][0]["certainty"] = "confirmed_actual"
    with pytest.raises(ValidationError):
        v.validate(invalid)  # Future availability is not confirmed current financing.
    invalid["components"][0].update(certainty="historical_indirect", acquisition_link="current_acquisition")
    with pytest.raises(ValidationError):
        v.validate(invalid)
    owner = {"reporting_party": "Aster", "security": "common", "shares": "100", "percent_of_class": 10,
             "ownership_role": "deemed", "overlap": "overlapping", "evidence": component["evidence"]}
    ov = validator_at(schema, "ownership")
    ov.validate([owner, {**owner, "ownership_role": "group_aggregate"}])
    missing = copy.deepcopy(owner)
    del missing["security"]
    with pytest.raises(ValidationError):
        ov.validate([missing])


def test_unknown_intent_cannot_be_a_missing_reference_negative():
    schema = build.extraction_schema()
    v = Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/intent"})
    record = intent("cannot_determine", "uncertain")
    record["evidence_status"] = "material_reference_missing"
    v.validate(record)
    record.update(status="not_stated", qualification_basis="none")
    with pytest.raises(ValidationError):
        v.validate(record)
    record.update(status="cannot_determine", qualification_basis="uncertain", evidence_status="definition_ambiguous")
    v.validate(record)
    record.update(status="not_stated", qualification_basis="none")
    with pytest.raises(ValidationError):
        v.validate(record)


def test_disclaimer_cannot_erase_a_positive_deemed_holding():
    schema = build.extraction_schema()
    v = validator_at(schema, "ownership")
    owner = {"reporting_party": "Aster manager", "security": "common", "shares": "5000",
             "percent_of_class": 5, "ownership_role": "deemed", "overlap": "overlapping",
             "evidence": [{"document_id": "one", "quote": "deemed ownership; disclaims beneficial interest"}]}
    v.validate([owner])  # Disclaimed beneficial interest can coexist with disclosed deemed holdings.
    owner["ownership_role"] = "none_disclaimed"
    with pytest.raises(ValidationError):
        v.validate([owner])
    owner["percent_of_class"] = 0
    with pytest.raises(ValidationError):
        v.validate([owner])  # Zero percent does not excuse a positive share amount.
    owner["shares"] = "0"
    v.validate([owner])
    owner.update(percent_of_class=None, shares=None)
    v.validate([owner])


def test_critic_wrapper_resolves_evidence_and_requires_conclusive_support():
    schema = build.critic_schema()
    Draft202012Validator.check_schema(schema)
    row = {"claim_id": "one", "verdict": "supported", "rationale": "Source supports qualified claim.",
           "issue_codes": [], "evidence": [{"document_id": "one", "quote": "source"}]}
    record = {"review_status": "complete_readable_bundle", "reviewed_document_ids": ["one"],
              "evidence_gaps": [], "reviews": [row]}
    v = Draft202012Validator(schema)
    v.validate(record)
    row["evidence"] = []
    with pytest.raises(ValidationError):
        v.validate(record)
    row["verdict"] = "insufficient_evidence"
    v.validate(record)
