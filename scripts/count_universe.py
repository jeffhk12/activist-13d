"""Week-1 action: count the universe before building anything on top of it.

Enumerates every Schedule 13D and 13D/A across the sample window and reports
the campaign count by filer, so the sample-size assumption behind the whole
method stack can be checked in an afternoon rather than in November.

Why this runs first
-------------------
The method choices — competing risks over graph learning, causal forests over
large-data deep learning — all rest on an estimate of roughly 3,000-4,000
fund-initiated campaigns, with ~600 after February 2024. If the real number is
800, the argument changes, and it should change before a line of the extraction
pipeline exists.

Inputs   EDGAR quarterly form.idx, 2013-2026 (cached to data/raw/edgar/index)
Outputs  data/interim/filing_index.parquet
         a printed summary: filings by year, top filers, post-rule-change count
Tier: 1
Run:  set PYTHONNOUSERSITE=1, PYTHONIOENCODING=utf-8
      set EDGAR_USER_AGENT="Your Name your.email@example.edu"
      python scripts/count_universe.py [start_year] [end_year]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from activist13d.dates import RULE_CHANGE  # noqa: E402
from activist13d.edgar import index  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "edgar" / "index"
OUT = ROOT / "data" / "interim" / "filing_index.parquet"


def collect(start_year: int, end_year: int) -> pd.DataFrame:
    frames = []
    for year, quarter in index.quarters(start_year, end_year):
        try:
            # A future or in-progress quarter may 404, or exist with no
            # parsable rows. Both are "not yet", not a defect.
            q = index.schedule_13(index.fetch_index(year, quarter, CACHE))
        except Exception as exc:
            print(f"  {year} QTR{quarter}: skipped ({type(exc).__name__})")
            continue
        frames.append(q)
        print(f"  {year} QTR{quarter}: {q['accession'].nunique():>5} filings "
              f"({len(q):>5} index rows)")
    if not frames:
        raise SystemExit("No index files retrieved. Is EDGAR_USER_AGENT set?")
    return pd.concat(frames, ignore_index=True)


def summarise(rows: pd.DataFrame, filings: pd.DataFrame) -> None:
    """`rows` is (filing, party) grain; `filings` is one row per accession.

    Every headline count is on `filings`. form.idx indexes a 13D under both
    the filer and the subject company, so counting rows overstates by ~2x.
    Form labels are canonical ("13D"), because the form-type string was
    renamed at the 2024-12-18 mandate.
    """
    initial = filings[filings["form"] == "13D"]
    amendments = filings[filings["form"] == "13D/A"]
    cut = pd.Timestamp(RULE_CHANGE)
    post = filings[filings["date_filed"] >= cut]
    post_initial = initial[initial["date_filed"] >= cut]

    print("\n--- universe (distinct filings, not index rows) ---")
    print(f"index rows                     {len(rows):>8,}")
    print(f"distinct 13D-family filings    {len(filings):>8,}")
    print(f"  initial 13D                  {len(initial):>8,}")
    print(f"  amendments 13D/A             {len(amendments):>8,}")
    print(f"distinct CIKs (either role)    {rows['cik'].nunique():>8,}")
    print(f"filed on/after {RULE_CHANGE}      {len(post):>8,}")
    print(f"  of which initial 13D         {len(post_initial):>8,}")

    print("\n--- initial 13D filings by year ---")
    per_year = initial.groupby(initial["date_filed"].dt.year).size()
    peak = per_year.max()
    for year, n in per_year.items():
        print(f"  {year}  {n:>5,}  {'#' * int(n / peak * 44)}")

    # Party roles are absent from form.idx, so this measures how concentrated
    # 13D activity is across ALL parties, not a filer league table. The large
    # names at the top are a mix of repeat filers and repeatedly-targeted
    # issuers; separating them needs the submission header.
    pairs = rows[rows["form_canon"] == "13D"].drop_duplicates(["accession", "cik"])
    by_cik = pairs.groupby("cik").size().sort_values(ascending=False)
    print("\n--- concentration across all parties (filers AND subjects) ---")
    for n in (50, 100, 150, 300, 500):
        if len(by_cik) >= n:
            share = by_cik.head(n).sum() / len(initial) * 100
            print(f"  top {n:>3} CIKs appear on {by_cik.head(n).sum():>6,} "
                  f"initial filings ({share:>4.1f}% of all)")

    print("\n--- top 25 CIKs by appearance on initial 13D ---")
    names = pairs.drop_duplicates("cik").set_index("cik")["company"]
    top = by_cik.head(25).rename("filings").reset_index()
    top["party"] = top["cik"].map(names)
    print(top.to_string(index=False))

    print("\n--- read this before scoping ---")
    print(f"Initial 13D filings, all parties, {initial['date_filed'].dt.year.min()}"
          f"-{initial['date_filed'].dt.year.max()}: {len(initial):,}")
    print(f"Post-{RULE_CHANGE} initial filings: {len(post_initial):,}")
    print()
    print("DESIGN-RECORD.md section 4 assumes ~3,000-4,000 fund-initiated campaigns")
    print("and ~600 post-rule-change, AFTER curating to activist managers. The")
    print("counts above include insiders, PE sponsors, strategic acquirers and")
    print("closed-end-fund arbitrageurs, so expect curation to cut them hard.")
    print()
    print("NEXT: filer-vs-subject roles are not in form.idx. Assigning them needs")
    print("the submission header (FILED BY / SUBJECT COMPANY) per accession.")


def main() -> None:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 2013
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    print(f"Enumerating Schedule 13D filings, {start}-{end}")
    rows = collect(start, end)
    filings = index.distinct_filings(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(OUT, index=False)
    summarise(rows, filings)
    print(f"\nWROTE {OUT}  ({len(rows):,} index rows -> {len(filings):,} filings)")


if __name__ == "__main__":
    main()
