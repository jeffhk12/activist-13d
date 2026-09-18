"""Pins for form.idx parsing.

The fixture is REAL — copied verbatim from 2024 QTR1's form.idx, including its
trailing whitespace. An earlier version of this file used a hand-written
fixture in an assumed fixed-width layout; every test passed and the parser was
wrong against live data, which is exactly the failure STANDARDS.md section 3a
warns about. Fixtures for a format you do not control come from the format.

No network. The fetch path is exercised only under the `network` marker.

Tier: 1
"""

from __future__ import annotations

import pandas as pd
import pytest

from activist13d.edgar import index

# Verbatim rows from data/raw/edgar/index/form-2024-QTR1.idx. Chosen for the
# cases that break naive parsing: a comma and a slash in a company name, an
# amendment, a 13G, a non-13 form, and one accession appearing twice under two
# different CIKs.
FIXTURE = """Description:           Master Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    March 31, 2024
Comments:              webmaster@sec.gov

Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------
SC 13D           127 Capital, LLC/TX                                           1991003     2024-01-02  edgar/data/1991003/0001839882-24-000053.txt         
SC 13D           Rimini Street, Inc.                                           1635282     2024-01-02  edgar/data/1635282/0001839882-24-000053.txt         
SC 13D/A         10000 DAYS CAPITAL MANAGEMENT LLC                             1760739     2024-01-19  edgar/data/1760739/0000919574-24-000471.txt         
SC 13G           1 800 FLOWERS COM INC                                         1084869     2024-02-09  edgar/data/1084869/0000354204-24-003025.txt         
10-K             10x Genomics, Inc.                                            1770787     2024-02-15  edgar/data/1770787/0001770787-24-000017.txt         
"""


# --- the grain contract -----------------------------------------------------

def test_estimator_declares_the_grain():
    """Row grain and filing grain differ, and confusing them doubles the
    universe count. Both are declared so a change fails loudly."""
    assert "one row per (filing, party)" in index.ESTIMATOR["row_grain"]
    assert "accession" in index.ESTIMATOR["filing_grain"]
    assert "submission header" in index.ESTIMATOR["party_roles"]


# --- parsing ----------------------------------------------------------------

def test_parse_returns_every_data_row():
    df = index.parse_index(FIXTURE)
    assert len(df) == 5
    assert list(df.columns) == ["form", "company", "cik", "date_filed", "path", "accession"]


def test_activist_filter_takes_13d_and_amendments_only():
    """Three 13D-family rows. The 13G and the 10-K must not appear."""
    rows = index.schedule_13(FIXTURE)
    assert len(rows) == 3
    assert set(rows["form"]) == {"SC 13D", "SC 13D/A"}


def test_passive_filter_takes_13g_only():
    rows = index.schedule_13(FIXTURE, passive=True)
    assert len(rows) == 1
    assert rows.loc[0, "form"] == "SC 13G"


def test_company_names_with_commas_and_slashes_survive():
    """'127 Capital, LLC/TX' carries both a comma and a slash. Splitting on a
    delimiter, or mis-measuring a fixed width, shifts every later field and
    corrupts the CIK and the date silently."""
    rows = index.schedule_13(FIXTURE)
    r = rows[rows["cik"] == 1991003].iloc[0]
    assert r["company"] == "127 Capital, LLC/TX"
    assert r["date_filed"] == pd.Timestamp("2024-01-02")


def test_dates_parse_and_cik_is_numeric():
    rows = index.schedule_13(FIXTURE)
    # Assert the kind, not the resolution: the unit is a pandas implementation
    # detail, not a project convention.
    assert pd.api.types.is_datetime64_any_dtype(rows["date_filed"])
    assert not rows["date_filed"].isna().any()
    assert str(rows["cik"].dtype) == "Int64"


def test_accession_is_derived_from_the_path():
    rows = index.schedule_13(FIXTURE)
    assert set(rows["accession"]) == {"0001839882-24-000053", "0000919574-24-000471"}
    assert not rows["accession"].str.endswith(".txt").any()


# --- the grain itself -------------------------------------------------------

def test_one_filing_appears_under_both_parties():
    """A 13D is indexed under the filer AND the subject company, sharing one
    accession. Counting index rows overstates the universe by roughly 2x."""
    rows = index.schedule_13(FIXTURE)
    assert len(rows) == 3
    assert rows["accession"].nunique() == 2


def test_distinct_filings_collapses_to_the_accession():
    """Both CIKs are kept, because the later header fetch needs the pair to
    assign filer versus subject."""
    filings = index.distinct_filings(index.schedule_13(FIXTURE))
    assert len(filings) == 2
    pair = filings[filings["accession"] == "0001839882-24-000053"].iloc[0]
    assert pair["ciks"] == [1635282, 1991003]
    assert pair["n_parties"] == 2
    assert "Rimini Street, Inc." in pair["parties"]


# --- refuse, don't fabricate ------------------------------------------------

def test_missing_header_rule_raises():
    """A layout change must fail loudly. An empty frame is indistinguishable
    from a genuinely quiet quarter until the whole panel comes up short."""
    with pytest.raises(ValueError, match="header rule"):
        index.parse_index("no rule line here\njust text\n")


def test_unparsable_body_raises_rather_than_returning_empty():
    text = "header\n" + "-" * 30 + "\nnot a filing row at all\n"
    with pytest.raises(ValueError, match="no parsable rows"):
        index.parse_index(text)


def test_quarters_enumerates_inclusively():
    qs = list(index.quarters(2013, 2026))
    assert len(qs) == 14 * 4
    assert qs[0] == (2013, 1)
    assert qs[-1] == (2026, 4)


@pytest.mark.network
def test_live_index_matches_every_row(tmp_path):
    """Manual probe. Run with `pytest -m network`."""
    text = index.fetch_index(2024, 1, tmp_path)
    parsed = index.parse_index(text)
    non_blank = sum(1 for ln in text.splitlines()[10:] if ln.strip())
    assert len(parsed) == non_blank, "regex missed rows the file contains"


# --- the 2024 form-type rename ----------------------------------------------

RENAMED = """head
----------------------------------------------------------------------------
SCHEDULE 13D     ACME TARGET CORP                                              111111      2025-04-02  edgar/data/111111/0001111111-25-000001.txt
SCHEDULE 13D     BIG ACTIVIST LP                                               222222      2025-04-02  edgar/data/222222/0001111111-25-000001.txt
SCHEDULE 13D/A   OTHER TARGET INC                                              333333      2025-05-13  edgar/data/333333/0002222222-25-000009.txt
SCHEDULE 13G     PASSIVE HOLDER LLC                                            444444      2025-05-20  edgar/data/444444/0003333333-25-000004.txt
"""


def test_post_2024_form_spelling_is_recognised():
    """The form-type string changed from 'SC 13D' to 'SCHEDULE 13D' with the
    18 Dec 2024 structured-data mandate. Accepting only the old spelling
    silently drops the entire post-rule-change sample — the exact period Q2
    measures. 2024 QTR4 carries both spellings; by 2025 the old one is gone."""
    rows = index.schedule_13(RENAMED)
    assert len(rows) == 3
    assert set(rows["form"]) == {"SCHEDULE 13D", "SCHEDULE 13D/A"}


def test_form_canon_erases_the_rename_for_downstream_code():
    both = index.schedule_13(FIXTURE + RENAMED.split("----\n", 1)[-1])
    assert set(both["form_canon"]) <= {"13D", "13D/A"}
    assert index.FORM_CANON["SC 13D"] == index.FORM_CANON["SCHEDULE 13D"] == "13D"


def test_passive_filter_recognises_both_spellings():
    assert len(index.schedule_13(RENAMED, passive=True)) == 1
    assert len(index.schedule_13(FIXTURE, passive=True)) == 1
