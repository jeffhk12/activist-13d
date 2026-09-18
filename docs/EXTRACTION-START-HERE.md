# Start the SEC extraction pilot

We have downloaded the filings. This pilot checks whether we can reliably find the relevant information and classify what the investor actually states.

## What to open

1. Open [the development review index](../output/extraction-prep/development-20260916/index.html). Start with its first six filings. All records in this pack are development examples; there is no held-out evaluation set yet.
2. Read [the draft codebook](../protocol/intent-codebook-v1.md). It defines the nine categories using invented examples, not suggested answers for your filings.
3. In each packet, review the full source text and record your answers in the blank worksheet. Copy the exact supporting passage and its document ID. If you cannot find or interpret something, leave it uncertain and explain why.

First locate the company, investor, CUSIP, relevant dates and Item 4. Then record any stated objectives. A generic reservation of rights does not automatically establish a demand. Amendments in this pack test extraction; we will not use later amendment information as an initial-filing investment signal.

Check the displayed source form first. Deliberately included failure cases may have a different form from the old index classification. Record that discrepancy in your notes and leave intent unassessed until the applicable document and scope are resolved. The completed v1 extraction validator rejects unsupported source forms.

Your answers are the reference for comparing the extraction process. Complete and save them before viewing AI answers for those examples. No AI intent answers are included in this pack. A worksheet left blank remains unreviewed, not negative.

The packets are reading aids. Preserve the `human-labels.jsonl` blank template; save your completed answers in a separate dated file. Free-form notes with accession, document ID, quote and rationale are sufficient for the first six; they can then be converted into the strict schema and checked without changing your judgments.

## What the files do

| File | Purpose |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Rules for the coding agent working in this project. |
| [Extraction workflow](../protocol/extraction-workflow-v1.md) | Ordered steps for source recovery, human review, model trial and evaluation. |
| [Intent codebook](../protocol/intent-codebook-v1.md) | What the categories mean and what qualifies. |
| [Validation plan](../protocol/validation-plan-v1.md) | How we will test accuracy before scaling; thresholds are proposed, not passed. |
| [Output schema](../protocol/schema-v1.json) | Structure required for a completed extraction record. |

The category definitions live in `protocol/categories-v1.yaml`; the codebook and model prompt are generated from that single source. Existing versions are preserved when rules change.

## What happens after the first batch

We check field locations and supporting quotations, measure review time, and identify confusing category boundaries. Then we can run a small model-assisted comparison on the examples you have already labeled, keeping those results separate from your references. We refine the protocol before evaluating an unexposed sample. Paid model APIs remain off; no bulk intent classification is running.

Technical checks verify schema, hashes and exact quoted substrings. They do not certify that a passage supports a label; that still requires source-based evaluation.

Preparation note (2026-09-16): the original bulk download manifest was missing at preparation time. The development sample instead uses the completed overnight SQLite records and their source hashes; selected raw bytes, sidecars, accession and date were rechecked. This alternate provenance is recorded in the sample manifest. The old review packets were not edited; see `final-audit.json` in the development folder for the latest preservation-check status. The missing download manifest still needs locating, potentially on the external drive.
