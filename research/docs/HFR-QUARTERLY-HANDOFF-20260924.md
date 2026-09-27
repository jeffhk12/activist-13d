# Quarterly HFR continuation — 24 September 2026

Active project: `/Users/jefflu/Projects/activist-13d`.
This note continues [the earlier handoff](HFR-ACTIVIST-RESEARCH-HANDOFF-20260924.md).
The earlier statement that historical HFR snapshots were not supplied is now superseded.

## Completed

Imported the user-supplied `Downloads/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip`.
The original is preserved byte-for-byte under `data/raw/hfr/2026-09-24-quarterly/`.
SHA-256: `5f0f8b59dbb2d1de5aa46ed62ba9769a4080112c533324c384e90cf70ee0a841`.
The 35 snapshots cover every quarter from 2018 Q1 through 2026 Q3, with
217,954 fund-row observations. All nested members
were read (ZIP CRC checked) and SHA-256 inventoried, including returns and assets.
Only Fund identity/classification fields were extracted; return/asset panels were not built.
Each extracted observation retains its source row; the per-snapshot metadata retains
workbook member, sheet, field-to-column mapping and source hash. Missing columns remain null.
Source date-added values remain raw Excel serial strings, not availability dates.

Across snapshots there are **393 Event-Driven Firm_IDs and 44 Activist Firm_IDs**.
The latest snapshot has 173 and 24 respectively. Thus 220 historical ED IDs and
20 historical Activist IDs are outside the corresponding latest sets. An ID absent
from the latest strategy subset is not necessarily a closed firm or absent from all HFR.
No deduplication of legal managers across different Firm_IDs has been established.

## Dating contract

These are within-quarter vendor deliveries, mostly mid-month, not literal quarter-end
observations. Preserve vendor DATESTAMP, supplied delivery-folder date, source file
mtime and local ingest date separately. Delivery-folder dates are **unverified historical
availability proxies**. Actual historical receipt/publication timestamps are unknown.
Example: 2018 Q1 has vendor DATESTAMP 15 March and delivery-folder date 16 March.
The supplied 2018 Q4 file mtime is 20 December while its folder date is 21 December.
Do not collapse either discrepancy. No snapshots before 2018 Q1 are supplied.

The exploratory SEC screen selects the latest whole snapshot whose delivery proxy
is strictly earlier than the filing date. Same-day delivery is excluded because no
time-of-day evidence exists. Names/classifications come only from that snapshot.
Managers absent there are not carried forward from earlier snapshots. The selection
prevents later-snapshot leakage conditional on the proxy; it does not certify point-in-time availability.

## Dated SEC name screen

| Measure | Count |
|---|---:|
| Local 13D / 13D-A metadata records | 75,631 |
| Records with a strictly prior supplied delivery proxy | 46,185 |
| Records without a prior snapshot | 29,446 |
| ED candidate manager IDs | 64 |
| ED candidate accessions | 1,750 |
| ED initials / amendments | 241 / 1,509 |
| Activist candidate manager IDs | 15 |
| Activist candidate accessions | 1,261 |
| Activist initials / amendments | 160 / 1,101 |
| Accessions matching multiple manager IDs | 10 |
| Candidate raw-source paths missing after historical-path resolution | 1 |
| Verified cross-database identifier links | 0 |

ED candidates represent 3.79%
of the 46,185 records with prior snapshot proxies.
Counts are unique accessions, not campaigns. Name rules match normalized firm names,
then legal-suffix-reduced firm names, then normalized fund names; no fuzzy/substring matches.
Cross-manager ambiguity is retained. Initial and amendment records remain separate.
These counts are not directly comparable to the old 2,011/1,482 current-snapshot counts:
the eligible dates and classification rule differ. Raw-source existence was checked;
individual filing hashes were not reverified by this screen.

## Historical Activist IDs outside the latest Activist subset

First/last below mean observed in the supplied quarterly sample, not inception/exit.

| HFR ID | Source manager names | First observed | Last observed | Dated activist candidate filings |
|---|---|---|---|---:|
| 10179 | Northern Right Capital Management, L.P. | 2018Q1 | 2018Q2 | 1 |
| 10807 | Cartica Management, LLC | 2018Q1 | 2018Q4 | 0 |
| 10961 | Voce Capital Management LLC | 2018Q1 | 2023Q4 | 21 |
| 11039 | Alantra EQMC Asset Management; N+1 Asset Management | 2018Q1 | 2023Q2 | 0 |
| 11795 | GO Investment Partners LLP | 2018Q1 | 2022Q2 | 0 |
| 12026 | Coast Capital Management, LP | 2018Q1 | 2018Q2 | 0 |
| 12030 | Legion Partners Asset Management, LLC | 2018Q1 | 2025Q1 | 112 |
| 12347 | Hudson Executive Capital | 2020Q1 | 2024Q1 | 23 |
| 12428 | Stilwell Group | 2019Q3 | 2020Q1 | 0 |
| 12558 | Harbert Management Corporation | 2021Q3 | 2023Q4 | 0 |
| 12662 | Patria Investimentos Ltda | 2020Q3 | 2022Q1 | 0 |
| 12946 | Bluebell Capital Partners Limited | 2024Q2 | 2024Q4 | 0 |
| 3473 | JANA Partners, LLC | 2018Q1 | 2019Q1 | 10 |
| 529 | Lawndale Capital Management, LLC | 2018Q1 | 2024Q4 | 6 |
| 6828 | Trian Fund Management, L.P. | 2018Q1 | 2021Q4 | 35 |
| 769 | SPARX Group | 2018Q1 | 2019Q3 | 0 |
| 7934 | Toscafund Asset Management LLP | 2018Q1 | 2021Q1 | 2 |
| 8501 | Crescendo Partners | 2018Q1 | 2025Q1 | 0 |
| 8534 | Taiyo Pacific Partners LP | 2024Q3 | 2025Q3 | 0 |
| 9045 | Lutetia Capital | 2020Q4 | 2023Q1 | 0 |

## Validation and files

The targeted offline tests cover share-class counts, missing IDs, duplicate IDs,
strict-prior/same-day selection, no carry-forward, ambiguous names and frozen-output refusal.
All 35 snapshot totals reconcile; zero missing/duplicate Fund_IDs were found.
Legacy XLS files emit xlrd's `SSCS size is 0 but SSAT size is non-zero` OLE warning.
They were readable without repair or source modification; the warning remains a source-format caveat.
The legacy reader is pinned in `requirements-hfr-quarterly.txt` (`xlrd==2.0.2`).

- [Historical coverage report](../runs/hfr-quarterly/20260924-v1/index.html)
- [Manager review and candidate counts](../runs/hfr-quarterly/20260924-v1/manager-review.html)
- [Source inventory](../runs/hfr-quarterly/20260924-v1/manifest.json)
- [Validation and missing-source/ambiguity lists](../runs/hfr-quarterly/20260924-v1/validation.json)
- [160 candidate activist initial filings](../runs/hfr-quarterly/20260924-v1/sec-screen/activist-initial-candidates.json)

Full run directory: `/Users/jefflu/Projects/activist-13d/research/runs/hfr-quarterly/20260924-v1/`.
Code: `scripts/data_collection/ingest_hfr_quarterly.py`, `screen_hfr_quarterly.py`,
`report_hfr_quarterly.py`. Use the project venv and environment settings in AGENTS.md.
Re-running refuses differing frozen outputs; behavior changes require a new run directory.

## Next work

1. Verify the 15 dated activist manager candidates using dated regulatory evidence,
   preserving adviser/fund/GP distinctions. Review the ten ambiguous accessions first.
2. Reconcile unavailable raw sources, manager aliases and amendment chains before
   constructing events. Review issuer/security types and manager concentration.
3. Confirm historical delivery availability where possible. Keep the 2013–2017
   coverage gap explicit or obtain earlier snapshots. Do not backfill 2018 classifications.
4. Freeze event eligibility, timing, re-entry and evaluation rules before a price study.

Human review answers, prior runs and current review packs remain preserved.
No paid models, semantic labels, returns backtest or external identity certification was added.
