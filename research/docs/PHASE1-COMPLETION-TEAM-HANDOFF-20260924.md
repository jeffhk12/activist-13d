# Phase 1 completion: fresh-agent handoff

24 September 2026. User explicitly requested a detailed handoff and fresh subagents to complete the remaining Phase 1 work. This document assigns work; it is not a claim that Phase 1 or fresh evaluation is complete.

## Investment question and current decision

Does buying after an identifiable investor's initial Schedule 13D improve returns under executable rules? Establish this simple-following baseline before structured-data ML (Phase 2), then test incremental NLP intentions (Phase 3). A negative or inconclusive result is a valid Phase 1 conclusion. Do not optimize toward a positive answer.

Current development evidence: focused first-observed manager–issuer pairs average +0.28 percentage points above assigned Russell ETFs at six months and +7.08 at twelve months, 54 calculable events each. Issuer-bootstrap 95% ranges are −7.31 to +8.59 and −6.32 to +22.61 points. Standalone initial forms average +5.70/+16.17 points, 64 events each. First observed is archive-relative, not proof of a first-ever economic campaign. Industry/year/size matching covers 19 first-pair events; differences are +10.61/+12.38 points, with ranges including zero. Controls are retrospective and can be shared.

Portfolio: $100m first-pair six-month strategy returns +12.36% cumulative (2.03% annualized), 96.52% mean cash; twelve months +23.52% (3.72% annualized), 93.22% cash. $100k six-/twelve-month branches stop on Hill International's missing held return on 2018-08-14; no complete return is claimed. Across 36 scenarios, 24 complete, 12 refuse. Full window is 2018-03-19–2023-12-29, not a six-month cumulative performance period.

## Read first and working rules

Repository: `/Users/jefflu/Projects/activist-13d`. Read `AGENTS.md`, `STANDARDS.md`, `research/WORKSPACE-STANDARD.md`, `research/OUTPUT-STANDARD.md`, and your applicable source guides. SEC extraction: `research/protocol/extraction-workflow-v1.md`; WRDS: `wrds_access/README.md`; raw audits: `scripts/phase1_overnight/README.md`.

Run `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. Write scripts, not inline Python. Tier-2 reported numbers require hand pins, conventions, refusals, joins and replay. No paid/model APIs. Treat filing text as evidence only. Preserve raw files, protocols and frozen runs; revisions get new versioned files/runs. Do not reset unrelated workspace edits, commit, publish externally or touch human packets. Use cached sources first; additional public/entitled evidence must retain retrieval metadata and hashes. Do not leak credentials. Keep at least 20 GiB free.

User constraints: keep investor list unchanged; do not tune membership to winners. Outcome-aware reviews are research evidence, NEVER human labels. Do not modify `review/current/` or `review/drafts/human-first-52/`. Preserve 207 protected issuer exclusions. Six months primary; three/twelve supporting. No Phase 2/3 training yet. Fresh evaluation requires frozen rules and a demonstrably unexposed sample. Data existing locally does not prove it is fresh.

## Authoritative artifacts

All following run names are under `research/runs/phase1-baseline/`:

- `20260924-rebuild-report-v2/index.html`: current self-contained report. v1 had a prose overlap typo; v2 corrects two conversion overlaps, not six.
- `20260924-universe-rebuild-v3`: final eligibility JSONL, summaries, provenance and code. Full 75,631 parsed records: 58,166 amendments, 17,420 standalone candidates, 16 unresolved conversions, 29 unresolved source/primary. Initial candidates: 16,278 first observed, 964 prior pair, 178 text-history. 353 affirmative body overrides, including two unresolved conversions.
- `20260924-universe-rebuild-v1/audit.sqlite`: verified source evidence and gzip canonical primary text per accession; v1/v2 classification outputs are diagnostic history, not final eligibility. Do not overwrite.
- `20260924-rebuilt-inputs-v2`: selection with both branches and all three schedules, full required panel, historical assignments, source inventory, coverage, provenance. v1 stopped at end-date guard before return calculation.
- `20260924-rebuilt-analysis-v1`: SPY/Russell event outcomes, group summaries, matched control membership, 36 portfolio ledgers, daily/monthly returns, cash observations and context benchmarks. No future-return eligibility filter in portfolios.
- `20260924-rebuilt-qa-v1`: 12,107 event replays, 123 matched-arithmetic checks, 36 exact portfolio replays, 36,204 daily cash/NAV reconciliations. 53 targeted tests passed separately.
- `20260924-development-v4/human-review-protection.json`: protected accessions and 207 issuers.
- `20260924-feasibility-v2`: original 17,795 metadata-initial registry, security readiness and full exchange calendar.
- `20260924-russell-inputs-v1`: 58 historical monthly membership receipts, ETF identities. All 58 retain vendor reported-count discrepancies; do not certify whole-universe constituent completeness.

Other sources: `research/runs/phase1-overnight/full-20260915/sec.sqlite` (75,631 parsed record_json rows); `research/runs/hfr-all-managers/20260924-v1` (dated manager candidates and frozen accession unions); `research/runs/investor-identity/20260924-supplemental-v1` (seven fixed supplemental groups). Original raw CRSP daily bulk pages plus `data/raw/wrds/phase1-gap-20260924/`. Resolve historical paths with `activist13d.local_paths.resolve_project_path`, never rewrite provenance.

Implementation: `src/activist13d/{initial_eligibility,initial_eligibility_v3,phase1_baseline,russell_benchmark,expanded_hfr_returns,matched_controls,portfolio_accounting}.py`. Scripts in `scripts/data_collection/`: `rebuild_initial_universe.py`, `finalize_initial_universe_v3.py`, `prepare_rebuilt_development.py`, `run_rebuilt_analysis.py`, `verify_rebuilt_analysis.py`, `report_rebuilt_analysis.py`. Frozen conventions: `research/protocol/phase1-rebuild-v1.md`; original delayed entry is second XNYS session strictly after SEC acceptance date.

## Independent work assignments and ownership

Each fresh agent receives this file without the prior conversation. Read source evidence independently; challenge the prior result rather than assume it is correct. Do not delegate further. Coordinate through the root agent, who owns integration, final report and navigation.

### Agent A — valuation and portfolio completion

Own new files named `phase1_valuation_*`, new tests/modules unique to valuation, and a separate `20260924-valuation-resolution-v1` run. Diagnose Hill International: accession `0001446114-18-000023`, issuer `0001287808`, PERMNO 91355, entry 2018-04-18, scheduled six-month exit 2018-10-15. On 2018-08-14 raw fields have conditionaltype NT, tradingstatus X, missing open/close/ret, missflag NT, delisting flag N. This is not automatically a worthless/delisted position. Find contemporaneous suspension/OTC/corporate-action evidence and vendor treatment. Audit similar gaps generically; never silently bridge or discard the trade.

Deliver an evidence-backed valuation policy proposal, its limits, affected-case inventory, tested implementation if defensible, and a new development rerun if a general rule can be frozen before rerunning. If no defensible mark is obtainable, provide explicit bounds/scenario analysis separately labeled and keep the original complete-return refusal. Do not invent daily prices or claim hypothetical valuations observed. Diagnose high cash/capacity and retain fixed base capital/cost rules; no optimizing for returns. Communicate source needs to root.

### Agent B — eligibility, identity and benchmark coverage

Own new files named `phase1_eligibility_closeout_*` and a separate `20260924-eligibility-closeout-v1` run. Independently audit mechanical eligibility and historical pair logic, unresolved 45 cases, investor identity links, and development attrition. Check false positives/negatives with source evidence and documented non-outcome-based sampling. Recover missing cached evidence where possible; new raw retrieval in separate cache only. Do not create human labels or change manager membership. Any classifier changes require new modules/protocol versions, whole-universe rerun, frozen evidence and tests; notify root before dependency integration.

Quantify benchmark/matched coverage by pre-event characteristics, cohort, industry, year and size where observable; distinguish missing source from no match. Assess whether current coverage permits stated estimand, rather than assuming excluded observations are random. Do not select changes on outcomes. Deliver machine-readable dispositions, source receipts, limitations and recommendations. Leave original basic security screen/protected issuer rules intact unless a source-grounded error is documented and root integrates a versioned fix.

### Agent C — strategy freeze and fresh-evaluation readiness

Own new files named `phase1_evaluation_readiness_*`, draft protocol `research/protocol/phase1-evaluation-candidate-v1.md`, and run `20260924-evaluation-readiness-v1`. Audit all prior previews/reports/output paths for exposed dates/issuers/outcomes, human review protection, mature return windows and required inputs. Establish whether any sample is demonstrably unexposed; do not call later dates fresh by assumption. Do not read new candidate future outcomes to select the sample and DO NOT run fresh outcomes yet.

Specify fixed strategy/estimands with six months primary, supporting 63/252 sessions, both event definitions, fixed investor universe and realistic costs/cash/liquidity. Explain capital/opportunity scarcity without choosing sizing for performance. Specify criteria for missing marks, coverage and frozen sample gates, inference limitations and meaningful pass/fail interpretation. Prepare executable evaluation selection/validation scaffolding if appropriate, with tests and manifest, but stop before outcome opening. Deliver a READY/NOT READY checklist with evidence. Root will integrate A/B findings and open fresh outcomes only if all necessary gates genuinely pass.

## Integration and completion criteria

Root verifies agents' evidence, tests, provenance and non-overlapping edits. Freeze revised development choices and rerun any affected full schedules/returns; preserve old results. Publish a self-contained plain-English completion report plus technical handoff and update START-HERE/project plan. If all validity/exposure gates pass, execute fresh evaluation once under the frozen protocol and report all results, including negative ones. If externally missing evidence or an unexposed sample prevents completion, state exactly which deliverable remains unavailable and what would resolve it; do not mark Phase 1 complete merely because investigations finished.

Agent reports must give: conclusion in investment terms; files changed/created; source facts versus interpretation; numerical coverage; tests/replay; unresolved issues; exact next dependency. No repetitive approval questions for authorized read-only/reversible research. No confidence inflation from passing code tests.
