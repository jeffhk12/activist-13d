"""EDGAR filing enumeration from the quarterly full-index files.

The spine of the pipeline. Reads
``Archives/edgar/full-index/{year}/QTR{n}/form.idx`` -- a stable, complete
listing of every filing accepted in that quarter -- and returns the Schedule
13D/G rows.

Deliberately NOT the full-text search endpoint (``efts.sec.gov``). That one is
undocumented, publishes no schema and carries no stability commitment; it is
fine for targeted lookups and wrong as the enumeration spine.

Two facts about form.idx that the layout hides
----------------------------------------------
1. It is NOT reliably fixed-width across the archive. Column starts drift, and
   a colspec measured on one year silently corrupts another -- the date lands
   in the path column and parses as NaT. Every row is therefore matched with a
   regex anchored on the three things that are genuinely invariant: a numeric
   CIK, an ISO date, and a path beginning ``edgar/``. Validated against all
   370,318 rows of 2024 QTR1 with zero misses.

2. A Schedule 13D appears TWICE -- once under the filer's CIK and once under
   the subject company's -- sharing one accession number. In 2024 QTR1 that is
   3,265 index rows for 1,640 distinct filings. form.idx does not say which
   party is which; that requires the submission header (``FILED BY`` versus
   ``SUBJECT COMPANY``). Count filings with :func:`distinct_filings`, never by
   counting rows.

Inputs   year, quarter
Outputs  DataFrame[form, company, cik, date_filed, path, accession]
Tier: 1
Run:  set PYTHONNOUSERSITE=1, PYTHONIOENCODING=utf-8
      set EDGAR_USER_AGENT="Your Name your.email@example.edu"
      python -m activist13d.edgar.index 2024 1
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.sec.gov/Archives/edgar/full-index"

# A declared User-Agent carrying a real contact address is mandatory and
# enforced -- requests without one are blocked, not throttled.
USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT",
    "Fordham GBS research (set EDGAR_USER_AGENT to your name and email)",
)

# SEC asks for no more than ~10 requests/second aggregate across sec.gov.
MIN_INTERVAL = 0.12

# The form-type STRING changed with the 18 Dec 2024 structured-data mandate:
# "SC 13D" became "SCHEDULE 13D". 2024 QTR4 is the transition quarter and
# carries both (445 SC 13D and 114 SCHEDULE 13D); by 2025 QTR2 the old
# spelling is down to 3 stragglers. Filtering on the old string alone silently
# drops the entire post-2024 sample -- which is exactly the period Q2 needs.
ACTIVIST_FORMS = ("SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A")
PASSIVE_FORMS = ("SC 13G", "SC 13G/A", "SCHEDULE 13G", "SCHEDULE 13G/A")

# Normalised labels, so downstream code never has to know about the rename.
FORM_CANON = {
    "SC 13D": "13D", "SCHEDULE 13D": "13D",
    "SC 13D/A": "13D/A", "SCHEDULE 13D/A": "13D/A",
    "SC 13G": "13G", "SCHEDULE 13G": "13G",
    "SC 13G/A": "13G/A", "SCHEDULE 13G/A": "13G/A",
}

# Anchored on the right, where the format is invariant. The form type may
# itself contain single spaces ("SC 13D/A"), so the form/company boundary is
# two-or-more spaces; company names contain commas, ampersands and slashes.
ROW = re.compile(
    r"^(?P<form>\S+(?: \S+)*?)\s{2,}"
    r"(?P<company>.*?)\s+"
    r"(?P<cik>\d+)\s+"
    r"(?P<date_filed>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<path>edgar/\S+)\s*$"
)

ESTIMATOR = {
    "row_grain": "one row per (filing, party) -- filer and subject both appear",
    "filing_grain": "accession number; use distinct_filings() to count filings",
    "party_roles": "not in form.idx; requires the submission header",
    "form_rename": "SC 13D -> SCHEDULE 13D at the 2024-12-18 mandate; both accepted",
}

_last_call = 0.0


def _throttle() -> None:
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def fetch_index(year: int, quarter: int, cache_dir: Path | None = None) -> str:
    """Raw form.idx text for one quarter, cached to disk.

    The cache is not an optimisation. The pipeline must re-run offline from
    data/raw, and re-fetching during iteration is both slow and rude.
    """
    name = f"form-{year}-QTR{quarter}.idx"
    if cache_dir is not None and (cache_dir / name).exists():
        return (cache_dir / name).read_text(encoding="latin-1")

    _throttle()
    resp = requests.get(
        f"{BASE}/{year}/QTR{quarter}/form.idx",
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.content.decode("latin-1")

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / name).write_text(text, encoding="latin-1")
    return text


def parse_index(text: str) -> pd.DataFrame:
    """Parse form.idx text into a frame. Pure -- no network, so it is testable.

    Raises if the dashed header rule is absent or if no row matches: either
    means the layout moved, and an empty frame would be indistinguishable from
    a genuinely quiet quarter until the whole panel came up short.
    """
    marker = text.find("-" * 20)
    if marker == -1:
        raise ValueError("form.idx header rule not found; the layout may have changed")

    records = []
    rejected = []
    for line in text[text.index("\n", marker) + 1:].splitlines():
        if not line.strip():
            continue
        m = ROW.match(line)
        if m:
            records.append(m.groupdict())
        else:
            rejected.append(line)

    if not records:
        raise ValueError("form.idx produced no parsable rows; the layout may have changed")
    if rejected:
        raise ValueError(f"form.idx contains {len(rejected)} unparsed rows; refusing partial index")

    df = pd.DataFrame.from_records(records)
    df["cik"] = pd.to_numeric(df["cik"], errors="coerce").astype("Int64")
    df["date_filed"] = pd.to_datetime(df["date_filed"], format="%Y-%m-%d")
    df["accession"] = df["path"].str.rsplit("/", n=1).str[-1].str.removesuffix(".txt")
    return df


def schedule_13(text: str, passive: bool = False) -> pd.DataFrame:
    """The 13D (or 13G) index rows from one quarter.

    One row per (filing, party) -- see the module docstring. To count filings,
    pass the result to :func:`distinct_filings`.
    """
    forms = PASSIVE_FORMS if passive else ACTIVIST_FORMS
    df = parse_index(text)
    out = df[df["form"].isin(forms)].reset_index(drop=True)
    out["form_canon"] = out["form"].map(FORM_CANON)
    return out


def distinct_filings(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse (filing, party) rows to one row per filing.

    Collects every CIK and company name that appeared for the accession, so
    the pair is preserved for the later header fetch that assigns roles.
    """
    grouped = df.groupby("accession", as_index=False).agg(
        form=("form_canon", "first"),
        date_filed=("date_filed", "first"),
        path=("path", "first"),
        ciks=("cik", lambda s: sorted(set(s.dropna()))),
        parties=("company", lambda s: sorted(set(s))),
    )
    grouped["n_parties"] = grouped["ciks"].str.len()
    return grouped.sort_values("date_filed").reset_index(drop=True)


def quarters(start_year: int, end_year: int):
    """(year, quarter) pairs, inclusive of both years."""
    for y in range(start_year, end_year + 1):
        for q in (1, 2, 3, 4):
            yield y, q


if __name__ == "__main__":  # pragma: no cover - manual probe
    import sys

    y, q = int(sys.argv[1]), int(sys.argv[2])
    cache = Path(__file__).resolve().parents[3] / "data" / "raw" / "edgar" / "index"
    rows = schedule_13(fetch_index(y, q, cache))
    filings = distinct_filings(rows)
    print(f"{y} QTR{q}: {len(rows):,} index rows -> {len(filings):,} distinct 13D filings")
    print(filings.head(8).to_string(index=False))
