# Ownership and identity NLP pilot v1 — 25 September 2026

Purpose: assess whether source-grounded language interpretation can improve the
structured ownership and identity inputs for Phase 2. This is development, not
held-out evaluation or a return test. Intent prediction remains a separate question.

Six distinct issuer candidates are selected from the completed nonprotected initial
filing extraction. Two per mechanical stratum: multiple extracted people with complete
percentages; multiple people with incomplete percentages; one person with incomplete
percentage. Each stratum has one 2013–2020 and one 2021–2025 filing. Sort candidates
by SHA-256 of identity-pilot-v1:accession; take the first unused, unambiguous issuer.
No returns, successful investors or HFR strategy labels determine selection. The
sample is deliberately difficult/varied and cannot estimate population accuracy.

Inputs: the frozen same-accession source bundle, raw-source hash and preserved
canonical document text. No future amendments, external campaign knowledge or paid
model API. Binary or external evidence remains a gap. Names alone do not establish
manager-family identity, and equal share counts do not establish overlap.

Human review first: the reviewer identifies parties/roles/relationships, lists
reported shares and percentages and explains overlap or uncertainty, then states
remaining evidence gaps. Each material conclusion needs an exact supporting passage
and document identifier, preferably canonical hash and Unicode character offsets.
No model answers, suggested labels or returns enter the human pack. Browser drafts
are conveniences only; exported JSON is the submission artifact.

On receipt of a completed human answer, validate accession/bundle/source hashes,
reviewer/time/independent-review declaration, nonblank answers and evidence. Check
exact quotes/offsets against the frozen bundle; clarify unsupported references.
Freeze the original export bytes and SHA-256 with receipt time in a new run path.
Only then generate the model answer for that case, without supplying human answers
to the model. A case may progress independently; no need to finish all six first.

Model output: entities with source names and stated roles; directed relationships;
separate per-person holdings; explicit overlap claims and uncertainties; evidence
for every conclusion. Do not sum ownership without explicit support. Do not infer
zero ownership from a missing value or independent investors from different CIKs.
Archive the prompt hash, bundle hash, available model identity/settings (unknown
values explicitly unavailable), timestamp and full response. Treat as model judgment,
never a human label. Paid APIs remain off.

Comparison: list each claim as supported, unsupported or unresolved after source
review; record missing relationships, false merges, double-counting errors, correctly
preserved uncertainty and human/model disagreements. Human references can also be
wrong: preserve originals and date any adjudication. No confidence score, population
accuracy or investment-edge claim from six development examples. Scale only after
reviewing errors and freezing a separate evaluation protocol/sample.
