"""Tier: 2. Form evidence and strictly historical campaign conventions."""

from activist13d.initial_eligibility import classify, mark_history


def record(a, day, keys=("CIK:1",), status="standalone_initial_candidate", history=None):
    return dict(
        accession=a,
        accepted=day + "T12:00:00",
        filing_date=day,
        issuers=["issuer"],
        identity_keys=list(keys),
        status=status,
        prior_history=history or [],
    )


def test_cover_and_xml_override_metadata():
    r = classify("SCHEDULE 13D (Amendment No. 2)* Issuer", ["13D", "SC 13D"])
    assert r["status"] == "amendment" and r["body_overrides_initial"]
    assert (
        classify("(Amendment No. ) 1 Issuer", ["13D"])["status"] == "standalone_initial_candidate"
    )
    assert classify("Issuer", ["13D"], "2")["status"] == "amendment"
    assert classify("Issuer", ["13D/A"])["status"] == "amendment"
    assert classify("", ["13D"])["status"] == "unresolved_primary_or_form"


def test_prior_amendment_blocks_new_campaign_and_changed_group():
    rows = [
        record("a", "2017-01-01", status="amendment"),
        record("b", "2018-01-01", keys=("CIK:1", "CIK:2")),
    ]
    result = mark_history(rows)
    assert result[1]["campaign_status"] == "previously_observed_pair"
    assert result[1]["prior_accessions"] == ["a"]
    assert mark_history(rows[:1])[0] == result[0]


def test_no_future_leakage_and_tied_acceptances():
    a = record("a", "2018-01-01")
    b = record("b", "2018-01-01")
    result = mark_history([b, a, record("c", "2019-01-01")])
    assert [r["campaign_status"] for r in result[:2]] == ["first_observed_pair"] * 2
    assert result[2]["campaign_status"] == "previously_observed_pair"
    assert mark_history([b, a]) == result[:2]
    assert (
        mark_history([record("d", "2019-01-01", history=[{"quote": "prior"}])])[0][
            "campaign_status"
        ]
        == "prior_history_in_document"
    )
