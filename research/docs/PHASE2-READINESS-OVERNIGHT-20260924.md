# Phase 2 second overnight pass: feature readiness

The first pass extracted facts for 15,813 initial-filing candidates. The second
asks whether those facts are consistent and complete enough to consider for model
inputs. Successful parsing alone does not answer that question.

This offline pass independently recalculates prior-disclosure counts, checks
source and saved-artifact hashes and citations, compares header identifiers with
the eligibility ledger, and measures field coverage by year. Ownership remains
separate for each reporting person. Missing values and disagreements stay explicit.
No returns or future manager success determine selection or acceptance.

The output is a diagnostic report and a review queue. It is not a trained model,
an accuracy certificate, or an investment result. Next work reviews the largest
gaps, builds lagged market features, validates dated HFR identities, and freezes
prediction targets and chronological evaluation rules before fitting.

[Live status and morning report](../runs/phase2-readiness/20260924-full-v1/index.html).

Phone: OneDrive → Project-Transfer → Activist-13D →
2026-09-24-Phase-2-Readiness → MORNING-REPORT.txt.
Reports are copied to the local sync folder; cloud delivery is unverified.

[Runner and resume guide](../../scripts/phase2_readiness/README.md).

Absolute output directory:
`/Users/jefflu/Projects/activist-13d/research/runs/phase2-readiness/20260924-full-v1`.
