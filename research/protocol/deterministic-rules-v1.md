# Deterministic filing facts v1

Created September 23, 2026. Separate development contract from semantic v1;
no intent, activism, campaign or investment labels. The fixed 52-accession sample
is purposive and entirely legacy HTML/text; XML support requires fixture tests.

## Representation and relationships

Raw submissions and frozen canonical bundles remain byte-for-byte unchanged.
Verify raw SHA-256 and every available canonical text hash before extraction.
Header fields use the frozen `SEC-HEADER` document. Header subjects, filing
entities and cover reporting people are separate tables; no name-based merge.
Keep each person/security ownership row separate; do not sum holdings. Keep the
body issuer name independently of the header name and flag differing strings.

Output tables: filings, issuers, filing_entities, reporting_persons, securities,
ownership, documents, sections, references and quality_issues. Technical keys,
source URLs/paths/hashes, bundle document metadata and processing states are
provenance metadata, not inferred filing attributes. Their source is the hashed
input manifest and bundle. Each extracted attribute is a field object.

## Field contract

Every field contains raw_value, value, status, rule, parser_version and evidence.
Status is present, not_found_in_supplied_text, ambiguous, unavailable or
invalid_format. Non-present normalized values are null. Alternatives retain
source candidates; no selection based on economic plausibility. An absent field
has no invented citation. Optional denominator fields remain unextracted unless
a dedicated deterministic rule establishes their stated value/date.

Text evidence stores document_id, text_sha256, exact quote and zero-based Unicode
[start,end) offsets. Each stored citation must equal the immutable substring.
XML evidence instead stores element path, raw value and a hash identifying the
defined XML source representation; no manufactured text offsets. Parser-specific
rules and representation definitions live in the version-hashed source snapshot.

The JSON schema validates the related-table envelope. The runner also applies
its field subschema recursively to every field object and verifies all text
citations. Relational person/security keys are checked independently.

## Normalization rules

- Keep disclosed names intact. Whitespace normalization is display-only, never
  entity merging. Cover-name matching to header CIKs is not inferred.
- CIKs are strings, up to ten decimal digits padded to ten. CUSIPs remain strings;
  remove permitted display whitespace without losing leading zeros. Syntax and
  check-digit diagnostics are distinct from security matching.
- Numeric ownership parsing is label-bounded within a reporting-person cover
  block. Footnote markers are not holdings. Unsupported or conflicting forms
  remain invalid/ambiguous. Preserve reported percentage; no recomputed values.
- Header date YYYYMMDD and acceptance YYYYMMDDhhmmss normalize only if valid.
  Acceptance is EDGAR Eastern-time convention (America/New_York), not UTC.
  Cover dates use explicit supported patterns; no campaign-date inference.
- Section extraction requires supported full heading titles and document
  boundaries. Ordinary Item references are not headings. Multiple defensible
  heading candidates are ambiguous rather than silently selected.
- Signature/schedule boundaries and exhibit references are mechanical candidates.
  Embedded documents are inventoried separately. A title/type match is a candidate
  resolution, not proof that every incorporated external reference was supplied.

## Processing and review

Retain every accession even on parser failure, with a quality issue and explicit
failure status. Record the original parser baseline, field-status counts and
denominators, manifest, source/rule hashes, environment and deterministic replay.
Coverage measures processing availability, not accuracy or population prevalence.
No external retrieval, model calls, return data or model-generated labels enter
the run. Inspect source-backed facts first; interpretive answers remain blank.

Run outputs are immutable once handed off; changed inputs/rules require a new
versioned directory. Human edits belong in separate files and are never overwritten
by rerunning the factual dataset builder.
