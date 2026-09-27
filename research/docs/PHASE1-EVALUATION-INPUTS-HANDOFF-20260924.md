# Phase 1 item 3 — evaluation-input handoff

24 September 2026. Status: input preparation completed; full evaluation NOT READY.

## Investment meaning

We are preparing a later-period test of simple following after an initial 13D. The extract ends on 31 December 2025, while the requested account ends on 23 September 2026. All 182 requested 2026 market sessions are empty. No new performance result exists. Six months remains primary; three and twelve months supporting. Investor membership and human labels are unchanged.

[Open the report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-evaluation-inputs-report-v1/index.html).
Absolute project: `/Users/jefflu/Projects/activist-13d`.

## Decisions to preserve

- Hill International (issuer 0001287808) stays excluded in the user-selected branch. Preserve original full-universe refusals and the retrospective exclusion history; do not resume the OTC search.
- User deferred nuanced cross-company history attribution to future NLP. A prior reference to Company B does not establish prior Company A involvement. Keep B as a research lead; do not assert a B position without sufficient evidence. Existing conservative history-reference exclusions remain until a separately specified, validated change. Do not promote assistant interpretations into human labels.
- First observed manager–issuer pairs are archive-relative mechanical candidates, not proven first-ever campaigns. Preserve standalone initial-form and first-observed branches separately.
- Do not tune the investor list to winners, drop missing-price events opportunistically, or call the later cohort untouched without an exposure audit. No ML/NLP training occurred.

## Completed work and limits

The immutable protocol is `research/protocol/phase1-evaluation-inputs-v1.md`. Fixed candidate requirements were saved before input checks. Unique entry specifications: 758; required daily sources: 705, including 684 account sessions and historical/pre-entry inputs. Two known 2025 holes (8 April and 17 December) were acquired; nonempty repair slices passed partition equality. Twenty-five month-end Russell snapshots were acquired. Refreshed cash data pass lag/staleness availability for 684/684 sessions. Each of SPY/IWB/IWM/IWR/IWV has dated identity coverage for 502/684 sessions, ending 2025-12-31.

Primary first-observed schedule: 700 events, including 8 focused. Russell assignments: 191/700 overall and 7/8 focused. All requested stock keys: 473/700; empty-market dates affect 187; post-delisting absences affect 40. No unexplained missing security keys remain under that status partition, but delisting settlement and numerical return validity remain unchecked. Prior 20-session liquidity inputs: 556/700. These are parallel coverage checks, not a sequential funnel.

All 705 daily requests and 25 membership requests retain vendor count discrepancies. Verified source bytes/date/unique keys do not certify vendor completeness. Monthly membership and revised cash histories do not prove contemporaneous publication timing. Future numeric prices, returns, signs, NAV and settlement amounts were not inspected or calculated. Only strictly pre-entry prices/volumes were used to prepare liquidity; automated later-window inspection used keys and delisting status.

## Unactivated calendar alternative

A planned-exit cutoff of 2025-12-31 gives 503 primary first-observed events, including 6 focused and 5 focused Russell assignments (138 overall). Twelve months gives 312 events, 4 focused, 3 focused assignments. Three months gives 612, 7 and 6 respectively. This is date-only feasibility; it does not change the original sample, guarantee valid returns or certify freshness. Five primary focused benchmark matches would support only a limited hypothesis check.

## Exact continuation order

1. Prepare the final rule/sample/exposure decision record (item 4). Reconcile the desired 2026 endpoint with demonstrated 2025 data coverage. Keep the original scope and calendar-only alternative separate until an explicit design decision is frozen; do not automatically activate the narrower sample.
2. For the full scope, obtain source coverage beyond 2025 with ETF identity support. For a narrower historical scope, freeze the endpoint and calendar eligibility before outcome access. Preserve all unmatched/uncalculable cases and denominators.
3. Complete the exposure audit and state what is known versus unprovable across prior chats/machines/previews. The later cohort is not certified untouched. A genuinely prospective cohort starts after the final freeze and must mature.
4. After final outcome-access gates, validate numerical total-return chains, marks, exit execution and delisting settlements under unchanged refusal rules. Row presence alone cannot authorize a portfolio result.
5. Then run the frozen later-period event/industry-time matched comparisons and portfolio accounting, with Russell ETF and SPY on the same common sample, costs, cash, capacity and uncertainty. Report excluded/unresolved observations separately. No winner-driven changes or human-label contamination.

## Run map

All names below are under `research/runs/phase1-baseline/`:

- `20260924-evaluation-inputs-v1/`: original acquisition history, requirements, source inventory, assignment and coverage files, frozen code/provenance.
- `20260924-evaluation-inputs-v2/`: current cache replay; all 10 analytical JSON files exactly match v1. Only receipt bookkeeping changed so original acquisition records survive warm-cache runs. Do not edit v1 to fix its rerun refusal.
- `20260924-evaluation-inputs-etf-v1/`: refreshed ETF identity source supplement. The base summary’s empty full-scope identity list means no 2026-wide coverage; this supplement establishes partial coverage through 2025.
- `20260924-evaluation-inputs-qa-v1/`: independent raw key/status replay, absence diagnostics, calendar cutoff.
- `20260924-evaluation-calendar-support-v1/`: unactivated date-only alternative and candidate metadata.
- `20260924-evaluation-inputs-replay-v1/`: v1/v2 parity, source hash checks and shared dependency snapshots.
- `20260924-evaluation-inputs-report-v1/`: this report, frozen generator and provenance.

New raw cache: `data/raw/wrds/evaluation-inputs-20260924-v1/`; official refreshed cash bytes: `data/raw/public-series/evaluation-inputs-20260924-v1/`. Old raw evidence remains unchanged. Existing raw pages may contain outcome fields; do not print/decode them into model-facing output when doing coverage work.

## Reproduction and verification

Use project `.venv/bin/python`, `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`, from the project root. Main scripts are under `scripts/data_collection/`:

- `prepare_phase1_evaluation_inputs_v2.py` — repeated preparation using the existing cache; v1 preserved original acquisition history.
- `verify_evaluation_etf_identities.py` — ETF supplement, cached responses.
- `verify_phase1_evaluation_inputs.py` — independent key/status/source checks.
- `describe_evaluation_calendar_support.py` — date-only counts, no activation.
- `verify_evaluation_input_replay.py` — source/output parity and dependency snapshot receipt.
- `report_phase1_evaluation_inputs.py` — report and handoff.
- `phase1_completion_guard.py` — verifies 554 protected assets unchanged.

Tests: `tests/test_evaluation_input_checks.py` pins pre-entry liquidity by hand, refuses missing/bad input, and proves key checks ignore changes to future numeric values. Full non-network suite: 180 passed, 1 deselected. QA independently replayed 705 daily sources and 184,522 requested keys; 30 membership/ETF raw hashes verified. Ten analytical JSONs reproduce byte-for-byte between v1/v2. Report generator asserts denominators/coverage contracts and supports identical reruns. All outcome-input limitations remain explicit rather than converted to assumed zero returns.

Earlier handoffs remain preserved: `PHASE1-SKIP-HILL-20260924.md`, `PHASE1-COMPLETION-STATUS-20260924.md`, and `PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md` in `research/docs/`.
