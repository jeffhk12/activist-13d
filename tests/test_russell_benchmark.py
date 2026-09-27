"""Tier: 2. Pin historical membership precedence and conservative refusal rules."""

from activist13d.russell_benchmark import ETFS, assign, compare


def row(large="N", small="N", mid="N"):
    return dict(
        russell1000=large,
        russell2000=small,
        russellmc=mid,
        r1000_wt=0.001 if large == "Y" else None,
        r2000_wt=0.001 if small == "Y" else None,
        rmidc_wt=0.001 if mid == "Y" else None,
    )


def test_membership_precedence():
    assert assign([row("Y", "N", "Y")]) == ("IWR", "matched")
    assert assign([row("Y")]) == ("IWB", "matched")
    assert assign([row("N", "Y")]) == ("IWM", "matched")


def test_missing_and_ambiguous_refused():
    assert assign([]) == (None, "no_constituent_match")
    assert assign([row(), row()]) == (None, "ambiguous_constituent_match")
    assert assign([row()]) == (None, "no_supported_segment")


def test_inconsistent_membership_refused():
    assert assign([row("Y", "Y")])[1] == "conflicting_size_membership"
    assert assign([row("N", "N", "Y")])[1] == "conflicting_size_membership"
    assert assign([dict(row("Y"), r1000_wt=None)])[1] == "inconsistent_membership_flags_weights"
    assert assign([dict(row(), russell1000=None)])[1] == "inconsistent_membership_flags_weights"
    assert assign([dict(row(), r1000_wt=0.1)])[1] == "inconsistent_membership_flags_weights"


def test_paired_return_hand_pin_and_replay():
    # Stock 20%, SPY 10%, selected ETF 110/100-1=10%, IWV 105/100-1=5%.
    event = dict(
        stock_return=0.2, benchmark_return=0.1, excess=0.1, status="calculated_full_window"
    )

    def observation(close):
        return dict(
            dlyopen=100,
            dlyclose=close,
            dlyvol=1,
            conditionaltype="RW",
            tradingstatusflg="A",
            dlydelflg="N",
        )

    panel = {ETFS["IWM"]: {"day": observation(110)}, ETFS["IWV"]: {"day": observation(105)}}
    assignment = dict(etf="IWM", status="matched")
    actual = compare(event, assignment, ["day"], panel)
    assert abs(actual["excess"] - 0.1) < 1e-12
    assert actual["stock_return"] == 0.2 and actual["spy_excess"] == 0.1
    assert abs(actual["broad_russell_return"] - 0.05) < 1e-12
    assert actual == compare(event, assignment, ["day"], panel)
    assert event["benchmark_return"] == 0.1  # Input unmodified.


def test_common_sample_refusals():
    event = dict(
        stock_return=0.2, benchmark_return=0.1, excess=0.1, status="calculated_full_window"
    )
    assert (
        compare(event, dict(etf=None, status="no_constituent_match"), ["day"], {})["excess"] is None
    )
    assert compare(event, dict(etf="IWM", status="matched"), ["day"], {})["status"].startswith(
        "etf:"
    )
    invalid = dict(event, excess=None, stock_return=None, status="stock:missing")
    assert (
        compare(invalid, dict(etf="IWM", status="matched"), ["day"], {})["status"]
        == "original:stock:missing"
    )
