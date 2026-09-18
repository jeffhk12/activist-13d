# WRDS access smoke layer

This chat owns only `wrds_access/` (source, documentation, isolated tests) and
`data/raw/wrds/` (ignored licensed responses). Keep the other chat out of those
folders. No existing project source, dependencies, tests, or research documents
were changed. This local checkout has no `.git` directory, so Git status and
tracking could not be verified; the existing `.gitignore` excludes `.env` and
all these data files.

From the repository root:

```sh
export PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
.venv/bin/python wrds_access/run.py schema --online
.venv/bin/python wrds_access/run.py sample --online
# Replay exactly the frozen responses; no credentials or network needed:
.venv/bin/python wrds_access/run.py schema
.venv/bin/python wrds_access/run.py sample
.venv/bin/python -m unittest discover -s wrds_access -p 'test_*.py'
.venv/bin/python -m ruff check wrds_access
```

Requires Python 3.10+ and `requests` (already a project dependency). Each cache
envelope records the Python and requests versions actually used. The live check
used the project's `.venv`; no dependency installation was needed.

`Client(cache=..., online=False)` exposes `schema(table)` and
`sample(table, filters, limit=1)`. Import as `from wrds_access.client import Client`
when the repository root is on the Python path. Online access must be explicit.
The credential loader reads only `WRDS_API_KEY` from the environment or root
`.env`; an explicitly empty environment value disables credential-file fallback.
It does not execute shell syntax or interpolate environment variables.

Requests use the HTTPS endpoint `https://wrds-api.wharton.upenn.edu/data/`,
`Authorization: Token ...`, and only OPTIONS for schema / GET for samples.
The authenticated API's OPTIONS responses supply filter names and types.
The [official API entry point](https://wrds-api.wharton.upenn.edu/) links to
tutorials, but those tutorial pages redirected to browser login with token auth.

The client permits only the three authorized tables, requires a company and
exact date/year for CRSP/Compustat or an exact filing date for Audit Analytics,
and caps each sample at five rows (CLI: one). There is no SQL, pagination,
redirect following, table discovery, broad extract command, or automatic retry.
An additional one-megabyte response cap bounds unexpected responses. Unsupported
filters and returned rows outside the exact requested scope are refused. API
`count` is the number of matches, not the sample size. Samples are an unordered
first page, not representative draws; empty results are valid.

The raw UTF-8 JSON, exact method/URL/parameters, UTC pull time, and SHA-256 are
stored together under `data/raw/wrds/v1/`, keyed by the canonical request hash.
Cache hits are verified and replayed even with `--online`. Existing evidence is
never refreshed or overwritten. Use a new cache directory explicitly through
`Client(cache=...)` if a new vendor vintage is needed. Do not delete old evidence.
Byte caps, transport failures, credential echoes and HTTP errors are not cached.
JSON responses that fail later scope validation remain frozen as diagnostic
evidence and are refused again on replay. No Authorization headers are stored.

## Verified on 2026-09-13

| Table | Columns | Supported filters | Final smoke scope | Rows |
|---|---:|---|---|---:|
| `crsp.dsf` | 20 | cusip, date, hsiccd, permco, permno | permno=14593, date=2024-01-03 | 1 |
| `comp.funda` | 949 | cusip, fyear, gvkey, tic | gvkey=001690, fyear=2023 | 1 |
| `audit.feed31_shareholder_activism` | 223 | company_fkey, iss_file_date | iss_file_date=2024-01-03 | 1 |

Six table observations total were downloaded during development: three initial
one-row probes and three final one-row checks. No next-page links were followed.
Initial endpoint discovery also retrieved the API table-name directory (metadata
only); the final client has no directory-discovery operation. Initial evidence
lives in `data/raw/wrds/inspect-*`; the schema inspection run ending
`212709033649Z` used OPTIONS (its early manifests omitted that method).
`summarize_probe.py` reads those initial caches without network access.

The initial Compustat probe demonstrated silent filter ignoring: `datadate`
was supplied as 2023-09-30 but the returned row had 1980-09-30 for the correct
GVKEY. OPTIONS marks `datadate` as non-filterable. The final query uses `fyear`
and verifies every returned filter value. No Compustat format conventions have
been chosen: `indfmt`, `datafmt`, `consol`, and `popsrc` remain raw fields.

Audit metadata includes filing identifiers, filing dates, ownership values,
and paired classification keys/text such as concerns, control, dispute, support,
and agreements. Access is confirmed; coverage, coding meaning, amendment
handling, and validity as a human-coded validation set remain unassessed.
CRSP's inspected daily table exposes `cusip` but not `ncusip` or delisting fields;
this layer makes no historical-identifier or delisting joins. No campaign
construction, outcomes, label mappings, modeling choices, or research design
changes were made.
