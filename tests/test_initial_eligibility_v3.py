"""Tier: 2. Refuse boilerplate-based history and foreign amendment false positives."""

from activist13d.initial_eligibility_v3 import classify


def test_blank_cover_and_13g_checkbox_do_not_create_history():
    text = "(Amendment No. ) 1 If the filing person has previously filed a statement on Schedule 13G to report the acquisition that is the subject of this Schedule 13D"
    r = classify(text, ["13D"])
    assert r["status"] == "standalone_initial_candidate" and r["prior_history"] == []


def test_other_contract_amendment_does_not_override_form():
    r = classify("Item 6. Amendment No. 1 to the Rights Agreement was signed.", ["13D"])
    assert r["status"] == "standalone_initial_candidate"


def test_affirmative_amendment_and_previous_group_detected():
    r = classify("(Amendment No. 7)* Issuer", ["13D"])
    assert r["status"] == "amendment" and r["body_overrides_initial"]
    text = "The Investor Group disbanded and ceased filing as a group."
    r = classify(text, ["13D"])
    assert len(r["prior_history"]) == 2
    assert all(text[s["start"] : s["end"]] == s["quote"] for s in r["prior_history"])
    assert classify("Originally filed a statement on Schedule 13D", ["13D"])["prior_history"]


def test_plain_and_hash_cover_and_conversion():
    forms = ["SC 13D"] * 3
    for text in ["SCHEDULE 13D Amendment No. 4 AEMETIS", "SCHEDULE 13D (Amendment #3)"]:
        assert classify(text, forms)["status"] == "amendment"
    assert classify("Amendment No. 1 to Schedule 13G/A on SCHEDULE 13D", forms)["status"] == "unresolved_13g_conversion"
