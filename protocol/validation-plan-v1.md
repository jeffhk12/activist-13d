# Extraction validation plan v1

Status: proposed development plan, 2026-09-16. No scores have been observed and no model/category is accepted.

## Development sequence

1. Use the 32-filing development pack to diagnose field location and refine category boundaries. It balances broad periods/forms with intentional oversampling of missing text, identifiers, references and parser refusals. It is not a representative accuracy estimate.
2. Start with six blank packets. Measure actual review time; finish source-backed human labels before producing model answers for those same examples. Preserve a hash/timestamp of completed labels. Unreviewed values remain null, not negative.
3. Check identifier/date/span correctness against the raw evidence. Inspect errors, including apparently easy cases; record each error and protocol change. Existing 75,631 parsed records are a baseline, not gold labels.
4. Revise categories/prompts/schema together under a new version if development finds problems. No changes in place to v1.
5. Freeze protocol, category acceptance rules, sampling procedure and evidence text transformation before held-out extraction evaluation. Do not select held-out records yet or expose their labels to development agents.

## Proposed acceptance rules to freeze before evaluation

These are starting design choices, not established course requirements or evidence of adequacy. Development can revise them in v2 before evaluation, with the rationale recorded.

- Every accepted output passes schema checks and exact citation-substring checks (100%). This validates provenance/structure, not semantic correctness.
- Each retained intent category targets precision >= 0.90 and recall >= 0.80 on an adequately reviewed held-out sample. Require at least 30 predicted positives and 30 human-reference positives per category for a provisional category assessment; show 95% Wilson intervals. Meeting these counts is not a guarantee of precision or statistical power. Sparse categories remain experimental or are dropped rather than pooled silently.
- Report the confusion matrix, positive and negative denominators, abstention fraction, reference-unknown fraction, and results by form, period and text format. Do not pool diagnostic amendments into initial-disclosure quality claims.
- Recall's denominator includes all human-reference positives, including model abstentions. Precision's denominator includes assessable predicted positives; separately report positives whose references are unknown rather than counting them correct. Report selective accuracy only alongside coverage and an explicit all-record accounting.
- Evaluate fields separately: exact identifier/date agreement, incorrect substitutions, missing fields, boundary correctness, and reference recovery. A returned span containing the wrong section is an error even when the text occurs verbatim.
- Human `cannot_determine` records stay visible but do not become reference negatives. Use a separately logged adjudication/re-review process for uncertain cases; never edit references merely to match a model.

## Evaluation sample and leakage controls

Use a separate sample after development. Exclude development accessions, their obvious issuer/reporting-party relatives, and previously exposed examples; report how uncertain campaign linkage limits this separation. Stratify initial filings across years and formats. If rare categories need enrichment, report enrichment separately and use sampling weights only when inclusion probabilities are known; do not call enriched precision a population estimate.

Record random seed, eligible sampling frame hash, selected accession hashes, exclusions, strata and dates. The sample size follows expected category prevalence and review capacity measured in development; no held-out record count is promised now. Freeze scores and acceptance decisions before investment-model development uses retained categories. Final-test investment returns never guide extraction tuning.

## Deliverables

A field-error inventory, versioned human references, archived model inputs/outputs, category-level metric tables with uncertainty, reviewer throughput, reference-gap counts, and a documented decision to retain, revise, abstain on, or drop each category. A failed or inconclusive evaluation is an acceptable research result.
