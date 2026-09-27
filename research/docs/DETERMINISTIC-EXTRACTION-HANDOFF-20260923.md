# Codex handoff: deterministic 13D data extraction first

## Start here

Work in `/Users/jefflu/Projects/activist-13d`.

The user’s latest decision is to clean and extract standard filing attributes deterministically before continuing LLM extraction or intent classification. Audit and improve the existing parser, run it over the fixed 52-filing development sample, and produce a source-backed factual dataset that the user can inspect. Begin the work; this is not a request for another planning-only response.

This handoff supersedes the immediate next steps in `EXTRACTION-AGENT-BRIEF-20260923.md`. Keep the earlier agent work as history. Do not resume semantic labeling, model calls, backtesting, or broad data collection as part of this task.

## Working context and inputs

Read the project’s `AGENTS.md`, `STANDARDS.md`, `research/WORKSPACE-STANDARD.md`, and `research/protocol/extraction-workflow-v1.md` before implementing changes. Use `.venv/bin/python` with `PYTHONNOUSERSITE=1` and `PYTHONIOENCODING=utf-8`.

Use these inputs:

- `review/drafts/human-first-52/bundles/*.json`: the fixed 52-accession sample and canonical document evidence. This is a purposively selected development sample, not a representative evaluation set.
- Raw SEC submissions referenced by those bundles. Resolve historical paths with `src/activist13d/local_paths.py`; verify source hashes before processing.
- `src/activist13d/edgar/submission.py`: existing submission/header parsing, XML cover fields, Item 4 extraction, and evidence inventories.
- Existing tests under `tests/` and `scripts/extraction_protocol/`; inspect the relevant tests before adding new ones.
- `review/drafts/reading-room-20260923/`: a readable source companion. Its reading breaks are presentation aids, not original paragraph boundaries.

Important implementation finding: `_cover_fields` currently preserves per-person XML fields but explicitly leaves legacy ownership unparsed. `_item_section` uses generic Item-number matching and refuses multiple heading candidates. These are investigation starting points, not proof of every failure’s cause.

Preserve the current 200-filing review pack, the original 52-candidate pack, human answers, raw data, and prior run outputs. The repository has pre-existing uncommitted changes; inspect and preserve them. Do not reset, reorganize, or commit unrelated work.

## Definition of deterministic extraction

Use fixed parsing and normalization rules, with no LLM or discretionary economic interpretation. The same frozen input and parser version must reproduce the same extracted content. A syntactically extracted value remains a reported value or candidate; it is not independently verified corporate identity, ownership, or campaign status.

Use structured SEC header/XML fields where available. For legacy HTML/text, use document structure, cover-page labels, and bounded section rules. Preserve alternatives and refuse uncertain assignments instead of guessing.

## Attributes and data relationships

Build related tables rather than one flattened row that loses reporting-person detail:

| Table | Required attributes |
|---|---|
| Filings | Accession, source form, initial/amendment indicator, filing date, acceptance timestamp, event date, source URL/path/hash, parsing status |
| Issuers | Issuer name as disclosed, issuer CIK, filing accession, and provenance; support multiple subjects or flag ambiguity |
| Reporting persons | Filing entity separately from other reporting persons; source name, disclosed CIK if available, cover-page reporting-person code, citizenship/place of organization, source page/document |
| Securities and ownership | Security title, CUSIP, each reporting person’s beneficial shares, percentage, sole/shared voting power, sole/shared dispositive power, source-of-funds code |
| Documents and sections | Document ID/type/filename, readable/unavailable status, Items 1–7 as located spans, signatures/schedules where reliably identified, embedded exhibit inventory |
| Quality issues | Accession, field/person/document, issue type, competing candidates, and source locations |

Keep raw names intact. A normalized display name may standardize whitespace/case, but must not merge legal entities or assert a fund-to-manager relationship. Names, issuer CIK, filing-entity CIK and other reporting-person CIKs are distinct attributes.

Record an ownership denominator and its as-of date only when a deterministic source rule locates them. Treat any recomputed percentage as a separate diagnostic with an explicit formula; preserve the filed percentage.

Detect referenced exhibits and agreements mechanically where possible. Distinguish embedded/located, referenced-but-unresolved, and unreadable. No detected reference is not proof of completeness. External retrieval is outside this first pass.

## Field and provenance contract

Every extracted field must carry:

- Raw source value and normalized value, with the normalization rule identified.
- Status: `present`, `not_found_in_supplied_text`, `ambiguous`, `unavailable`, or `invalid_format`.
- Parser/rule version, document ID, canonical-text hash and exact quotation with zero-based Unicode `[start,end)` offsets where text is available.
- For structured XML, retain the element path and raw value; use a clearly defined source representation rather than inventing canonical-text offsets.
- All relevant alternatives when conflicting source locations provide different values.

Missing values are null, not zero, false, or negative findings. Do not sum overlapping holdings across funds, managers, general partners and controlling persons. Keep one ownership record per disclosed person and security, linked to the filing.

CIKs and CUSIPs remain strings with leading zeros preserved. A CUSIP syntax/check-digit check is a separate flag, not a CRSP match. Normalize dates only when the source format is unambiguous. Preserve the source timestamp and its timezone convention; do not silently label Eastern time as UTC. Event date, filing date, acquisition date and campaign-start date are not interchangeable.

Do not alter frozen canonical text to make quotes match. If a new text representation is necessary, create a separately versioned representation with its own hash and mapping. Preserve the old bundles and protocols byte-for-byte.

## Work sequence and completion checks

1. **Baseline.** Inventory all 52 accessions, verify available input hashes, and record current parser coverage/failures by field and document format. Retain every accession, including failures. Identify whether this sample actually contains XML; do not claim XML coverage from legacy filings alone.
2. **Contract.** Define a new versioned deterministic output schema and normalization rules. Keep it separate from the existing completed semantic extraction schema. Existing protocol files are immutable.
3. **Parser improvements.** Reuse existing modules. Prioritize issuer/header fields, reporting-person boundaries, cover-page ownership, security identifiers, dates, and section/exhibit inventories. Preserve source disagreements rather than silently resolving them. Do not use the earlier model output to populate the dataset.
4. **Verification.** Add focused offline tests for meaningful parser changes: multi-person ownership, shared holdings, leading-zero identifiers, malformed/missing values, repeated Item references versus true headings, multiple securities/alternatives, and exact citation parity. Use existing cached or invented XML fixtures if the 52-file sample lacks XML. Pin expected values to inspected source examples, not the parser’s own output.
5. **Run and replay.** Process the same 52 inputs into a new dated directory. Rerun and compare extracted payloads, allowing separately recorded run timestamps to differ. Check every stored text citation against its exact source substring. Report field coverage, ambiguity and failure counts with denominators; these are availability/processing measures, not semantic accuracy estimates.
6. **Human handoff.** Provide a readable factual table, a queue of missing/conflicting fields, and source links. Start the user’s inspection with the first filing. Keep interpretive review columns blank and report what remains unsupported.

## Useful source checks for the first filing

Accession `0000899140-19-000386`, MidSouth Bancorp / Basswood, filed 2019-05-09:

- The submission contains an SEC header, the main Schedule 13D and two exhibits.
- The cover pages name 11 reporting persons. Basswood Capital Management’s reported position is 1,641,562 shares and 9.82%; those holdings overlap other reporting persons’ rows.
- The security is common stock, par value $0.10; CUSIP 598039105. The cover event date is April 30, 2019.
- The attached support agreement describes 221,523 shared-voting shares separately. Cover-page ownership and transaction-specific voting obligations must not be collapsed into the same field.

Recheck these against raw/canonical source before using them as test expectations. An exploratory model extraction already exists at `research/runs/chat-extraction-20260923-filing01/`. It is not ground truth or a parser input. This accession has been exposed to model interpretation and cannot serve as an unexposed semantic evaluation case.

## Deliverables and locations

- Focused source changes and offline tests in the existing implementation/test locations.
- A new versioned deterministic schema and rule specification, without editing existing frozen versions.
- A separately dated run under `research/runs/deterministic-extraction/`, containing the input manifest, parser/rule hashes, normalized JSON/JSONL, reviewable related tables, quality issues, coverage report and verification results.
- If creating a human-facing pack, build it under `review/drafts/`, preserve existing packs, and add a clearly labeled link to `START-HERE.html`. Do not replace `review/current/` merely to publish this pilot.
- A concise final handoff with absolute file links, what was extracted, how it was checked, and unresolved limitations.

Do not infer activist status, hedge-fund status, outside-investor eligibility, intent categories, economic outcomes, campaign identity, or investment merit. Those are later stages after factual extraction has been reviewed. No paid APIs or live downloads are needed for this task.
