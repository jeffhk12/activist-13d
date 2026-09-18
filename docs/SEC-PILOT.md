# SEC collection pilot

First live collection completed on 2026-09-09 using the user-approved SEC contact.
Ten complete submissions and two quarterly indexes are cached locally.
See `output/SEC-PILOT-REPORT.md` for the inventory and individual review sheets.

## Scope

Collect five initial 13D filings from 2024 Q1 and five from 2025 Q1, selected
at evenly spaced positions after sorting distinct accessions by date and accession.
This is an unscreened parser-validation sample, not a representative activism
sample or a count of distinct campaigns. Corporate/CEF screening, manager
curation, and amendment-chain construction remain separate tasks.

Download complete submission text, which includes submitted documents and
exhibits. Preserve binary exhibit content in the raw submission; the pilot does
not decode binary exhibits, run OCR, or follow externally incorporated documents.

## macOS setup and run

The original Windows-specific execution-zone instructions apply to the original
machine. This workspace uses an isolated `.venv` under the project root.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-ci.txt
export PYTHONNOUSERSITE=1
export PYTHONIOENCODING=utf-8
export EDGAR_USER_AGENT='Jeff Lu YOUR_REAL_CONTACT_EMAIL'
.venv/bin/python scripts/collect_pilot.py
```

SEC's declared-contact guidance and request-rate limit:
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

This collector runs sequentially at no more than two requests per second.
An HTTP error stops collection; it does not silently skip the quarter or filing.
Successful raw responses have a URL, UTC retrieval time, byte count, and SHA-256
sidecar. Cached evidence is checked before reuse and never refreshed in place.
Run only one collector process at a time.

## Outputs

- `data/raw/edgar/pilot/index/`: quarterly indexes and provenance sidecars.
- `data/raw/edgar/pilot/filings/<accession>/submission.txt`: complete filings.
- `data/interim/pilot/filings.jsonl`: one parsed record per initial accession.
- `data/interim/pilot/audit.json`: sample selection and extraction coverage counts.
- `output/SEC-PILOT-REPORT.md`: readable inventory and links to filing review sheets.
- `output/pilot-filings/`: Item 4 text and attached exhibit text for human review.

The JSONL retains document text, source identifiers, header party roles, the
acceptance timestamp in Eastern time, candidate CUSIP/event date, raw XML leaf values, and a candidate Item 4
passage. All Item 4 passages require review. Missing/ambiguous spans remain
explicitly flagged. XML leaf values are not yet a normalized ownership table;
multiple reporting-person values must not be added together. Per-person XML
records also preserve the relationship between each name and its reported holdings.

The pilot does not infer intent, calculate outcomes, assign an executable trading
timestamp, or call any LLM. These steps follow evidence validation. An LLM judge
can later assess extraction against the source text and a frozen codebook.

## Verification

```sh
.venv/bin/python -m pytest -m 'not network'
.venv/bin/python -m ruff check .
# After a successful live collection:
.venv/bin/python scripts/collect_pilot.py --offline
.venv/bin/python scripts/verify_pilot.py
```

Final check: 34 offline tests passed; one live-network test deselected; lint
passed. New tests cover synthetic header roles and Item 4 boundaries, exhibits,
XML values, deterministic parsing, missing contact, cache integrity, offline
replay, and refusal of partially parsed indexes. The live pilot produced 10/10
Item 4 candidates, 10/10 filer/subject pairs, 10/10 event-date candidates, and
9/10 CUSIP candidates. The Bulldog filing does not contain a CUSIP, so it remains
missing rather than being inferred. Its Item 4 refers to Exhibit B, which is
included in the raw submission, JSONL, and review sheet. All semantic labels
and full-text completeness still require human validation.

Offline replay reproduced identical JSONL and audit hashes. Source hashes were
verified for all ten submissions, with cover-page fields pinned to two manually
inspected source examples. `requirements-pilot-lock.txt` records this macOS/Python 3.14 environment;
it is not a lock for the unimplemented model-training dependencies.
