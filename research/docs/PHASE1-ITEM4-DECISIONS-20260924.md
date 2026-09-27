# Phase 1 item 4 — agreed evaluation decisions

24 September 2026. **Historical rules and sample frozen. Performance evaluation has not yet run.**

We will test whether following initial 13D disclosures adds value in a later historical period ending in December 2025. This is a limited check of the investment hypothesis and the process. The sample is too small, and its prior exposure history too incomplete, to establish independent confirmation of an edge.

## Agreed investment test

| Decision | Frozen choice |
|---|---|
| Historical account period | 2 January 2024 through 31 December 2025 |
| Eligible events | Existing scheduled events whose planned exit is on or before 31 December 2025; no replacement based on returns or missing data |
| Primary signal | First observed manager–company pair under the existing conservative archive rules |
| Supporting signal | Standalone initial 13D forms, reported separately |
| Holding period | Six months primary; three and twelve months supporting |
| Stock comparison | Historical Russell segment ETF assignment, with SPY shown on the same sample; industry/year/size controls retain existing minimum coverage rules |
| Primary portfolio | $100,000 starting capital; existing 5% target positions, liquidity limits, costs, cash interest and delayed entry/exit rules |
| Capacity comparison | $100 million, with the same rules |
| Missing information | Document pre-purchase skips; unresolved held-position valuations prevent a complete portfolio claim; never silently remove failures |
| Investor and eligibility rules | Unchanged investor list and conservative history interpretation; Hill exclusion preserved and disclosed as retrospective |
| Interpretation | Later-period historical validation with incomplete exposure history; no claim of untouched confirmation |

The primary sample contains **503 scheduled events, including 6 focused activist candidates**. Historical Russell assignments exist for **138 of 503 events**, including **5 of the 6 focused events**. Assignment and scheduling counts do not establish that the returns are calculable. The focused subset is contained within the total and must not be added to it.

Supporting first-observed samples contain 612 events at three months (7 focused; 6 focused Russell assignments) and 312 at twelve months (4 focused; 3 focused assignments). Different holding periods have different calendar-eligible samples; the execution must also show a calendar-common comparison before interpreting differences as a holding-period effect.

A positive stock average alone will not establish success. We will report uncertainty, costs, cash deployment and complete portfolio accounting alongside benchmark-relative event results. Favorable performance in five matched focused observations would remain limited evidence. Six months stays primary even if twelve months performs better.

## What was completed

The approved date-only alternative has been activated in a new run. The earlier candidate sample and all development results remain preserved. Exact selected and date-excluded schedules, protocol hashes, inherited code snapshots, a decision timestamp and an exposure record are saved. Two runs reproduced the frozen outputs exactly, and the protected-asset check remained intact.

No new stock returns, numerical settlement values or portfolio performance were read or calculated by the decision-freeze script. The old fresh-confirmation gates have not been relabeled as passing. This historical branch explicitly accepts incomplete historical exposure provenance for a limited validation; it does not certify independence.

## Next execution step

Build the historical runner around the frozen sample and inherited accounting functions. Before numerical outcome access, snapshot its code and installed environment, verify the protocol/sample/source/protected-asset hashes, and append a timestamped access receipt. Then validate total-return chains, entry/exit prices and delisting settlement. Preserve every refusal and denominator; only complete held-position accounting may support a complete account result.

The user's acceptance already authorizes this historical validation. Routine implementation and verification do not require another permission request. The runner and numerical validation remain actual work to complete; this decision record does not claim they have run.

## Prospective test

Prepare a separate genuinely later test after the production implementation is ready. The [prospective plan](PHASE1-PROSPECTIVE-TEST-PLAN-20260924.md) proposes a fixed twelve-month collection window starting after its actual launch freeze, followed by the required holding-period observation. That duration is a planning recommendation; no collection dates or background automation have been activated. Do not backdate the prospective test to today.

## Continuation references

- [Frozen historical protocol](../protocol/phase1-historical-validation-v1.md)
- [Exact selected schedules](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/selection.json)
- [Date exclusions](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/calendar-exclusions.json)
- [Coverage counts](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/coverage-counts.json)
- [Exposure record](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/exposure-record.json)
- [Execution status](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/execution-status.json)
- [Source and output manifest](../runs/phase1-baseline/20260924-historical-decision-freeze-v1/manifest.json)
- [Item 3 input report](../runs/phase1-baseline/20260924-evaluation-inputs-report-v1/index.html)

Project: `/Users/jefflu/Projects/activist-13d`.
[Open project navigation](/Users/jefflu/Projects/activist-13d/START-HERE.html).

Run from the project root:

```sh
PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/freeze_phase1_historical_decisions.py
```

The script reads frozen metadata only, checks all 554 protected hashes, proves exact parity with the previously counted alternative, preserves both sides of each calendar partition and refuses changed frozen outputs. Do not edit this frozen protocol or decision run to introduce a later implementation change; write a new version and preserve its relationship to these decisions.
