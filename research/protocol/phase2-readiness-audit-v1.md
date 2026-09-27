# Phase 2 feature-readiness audit v1

Frozen 24 September 2026. Offline analysis-stage audit of the completed 15,813
initial-candidate extraction. No outcome data, model calls, semantic classifications,
investor-list changes, human labels or held-out evaluation.

Validate original run code/input hashes, per-filing source/artifact hashes, schema
and exact evidence spans. Compare current header CIK sets with the source-audited
eligibility ledger. Recompute prior-disclosure counts independently using sorted
acceptance timestamps and first-appearance indices; strict earlier-than only.
Same-time disclosures cannot contribute to one another. History is cache-limited,
not proof of current positions or independent managers. Retain all discrepancies.

Report field opportunities and filings with any present field by year. Filings with
no ownership rows do not count as complete. Every-row presence does not certify
that all reporting persons were found. Do not aggregate shared ownership.
Report denominators and retain explicit missing/ambiguous/invalid statuses.
Results are diagnostics pending accuracy review, not model-ready certification.

Checkpoint per filing; 90-second per-file timeout, eight-hour budget, 20 GiB free-disk
floor. Separate output directory and source preservation. Summaries only to a new
OneDrive folder; cloud delivery not verified. Protected assets checked before/after.
