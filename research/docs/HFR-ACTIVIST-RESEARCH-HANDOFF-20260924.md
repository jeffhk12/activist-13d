# HFR / activist 13D research handoff — 24 September 2026

## Resume here

The user wants to center the research on identifiable activist/event-driven managers, using HFR to construct the manager universe, SEC filings to trace their investments and stated intentions, and later other investors' disclosures to study participation around those events. This is a research pipeline, not an investment recommendation or operational trading system.

Read this handoff, `AGENTS.md`, `STANDARDS.md`, `research/WORKSPACE-STANDARD.md` and `research/protocol/extraction-workflow-v1.md` before continuing. Preserve existing raw data, frozen runs and human answers. The earlier deterministic-extraction handoff remains relevant to parser work; this document records the newer investor-universe direction and completed screens.

## Exact workspace and navigation

- Active project, Mac internal drive: `/Users/jefflu/Projects/activist-13d`
- Navigation: `/Users/jefflu/Projects/activist-13d/START-HERE.html`
- HFR manager review: `/Users/jefflu/Projects/activist-13d/review/drafts/hfr-event-driven-20260923/index.html`
- Elliott identity review: `/Users/jefflu/Projects/activist-13d/review/drafts/investor-identity-elliott-20260923/index.html`
- Elliott full filing readers / timelines: `/Users/jefflu/Projects/activist-13d/review/drafts/investor-identity-elliott-20260923/filings.html`
- Example initial E2open filing: `/Users/jefflu/Projects/activist-13d/review/drafts/investor-identity-elliott-20260923/0000902664-23-005125.html`

This checkout is outside iCloud and OneDrive. Windows has a separate checkout; these changes have not been verified there. Do not assume local code, environments or processes synchronize. Historical path strings in frozen artifacts are provenance; use the project's path resolver where applicable rather than rewriting evidence. There are substantial pre-existing uncommitted migration/research changes; do not reset them or commit unrelated work.

Use `/Users/jefflu/Projects/activist-13d/.venv/bin/python`, with `PYTHONNOUSERSITE=1` and `PYTHONIOENCODING=utf-8`; scripts importing `activist13d` also need `PYTHONPATH=src` when run from this checkout. No dependencies were installed for the latest screens.

## Decisions and working research direction

1. Focus first on **who filed**: separate investment manager, fund vehicle, adviser, general partner, controller and issuer-specific portfolio manager. A signer, principal or CIO is not automatically the PM responsible for a stock.
2. Use **HFR Event-Driven** as a broad screening universe and **HFR Activist** as a focused subset. Event-driven membership does not establish activist intent or investment quality.
3. Preserve exact legal entities and identifiers. Name matches are candidates, not verified links. HFR Firm_ID, Fund_ID, CRD, SEC adviser file number and EDGAR CIK are different identifiers.
4. User selected Elliott as a known-activist example. Its manager reputation does not mean every filing discloses an activist demand. Elliott is retained as a separately sourced example because no Elliot/Elliott name match was found in the supplied HFR Fund/Firm columns.
5. Keep deterministic facts and source passages ahead of semantic judgments. Existing human-first packets remain unmodified by this work. The first-five identity pilot was paused when the user prioritized Elliott.
6. Historical annual HFR snapshots would improve the universe: recover managers absent today, preserve dated classifications and names, and reduce survivorship/look-ahead bias. **Historical snapshots have not yet been supplied or ingested.** A current export containing historical returns is not an as-of historical manager list.
7. The user supports adding other investors around activist events. Separate previously disclosed holders, subsequent disclosures, and explicitly disclosed coordination. Similar holdings do not establish copying, herding or coordination; a newly reported position need not be newly purchased.

The proposed thesis framing is: **Do disclosures by identifiable activist managers predict subsequent stock performance, and do stated intentions and other investors' participation add information?** This is a working direction, not a frozen hypothesis or approved statistical protocol.

Proposed sequence: manager/event baseline → incremental filing-content information → incremental other-investor participation. The manager–company event timeline is the proposed observation structure. Exact event boundaries, return windows, eligibility filters and estimators are not decided. Later amendments/participation cannot enter an initial-disclosure signal; every feature must respect public availability time. An investment holding-period rule is still unresolved.

## Completed: HFR universe and SEC name screen

Frozen source:

`/Users/jefflu/Projects/activist-13d/data/raw/hfr/2026-09-13/HFR_HFRDB_EXCEL_Fund.xlsx`

- Source datestamp: **2026-09-08**; frozen ingest directory: 2026-09-13.
- SHA-256: `aa3cc17cd1662b5c5e984aab52e94d03a6010cab0739d6890c681cc6a8846062`
- Worksheet: `HFR_HFRDB_EXCEL_Fund`.
- Filter: `Main_Strategy == "Event-Driven"` exactly; managers grouped by supplied `Firm_ID`.
- 387 fund rows, **173 manager Firm_IDs**. Rows can include share classes and multiple funds, not unique portfolios.

| HFR substrategy | Fund rows |
|---|---:|
| Multi-Strategy | 124 |
| Special Situations | 91 |
| Merger Arbitrage | 80 |
| Distressed/Restructuring | 39 |
| Activist | 34 |
| Credit Arbitrage | 19 |

The 34 Activist rows map to **24 managers**. A manager can span multiple substrategies.

SEC input:

`/Users/jefflu/Projects/activist-13d/research/runs/phase1-overnight/full-20260915/sec.sqlite`

Screened **75,631 local records** whose parsed form is 13D or 13D/A. Compared HFR firm names with SEC reporting-party names, first using punctuation/case normalization, then removing trailing legal suffixes; also checked normalized HFR fund names. No fuzzy/substring matching, issuer-name matching or body-mention matching was used. All hits remain `name_candidate_not_identity_verified`. **Zero cross-database identifier links have been verified in this screen.** CRD and SEC adviser numbers require a separate bridge to CIK.

| Universe | Managers with name candidates | Initial 13Ds | Amendments | Unique accessions | Share of local records |
|---|---:|---:|---:|---:|---:|
| All Event-Driven | 45 / 173 | 353 | 1,658 | **2,011** | 2.66% |
| Activist subset | 9 / 24 | 217 | 1,265 | **1,482** | 1.96% |

Counts are unions of accession IDs across matching names/managers; they are not campaign counts. There was no cross-manager accession overlap in this output. These are metadata matches, not a certification that every linked raw file exists or that every source has been reverified.

| HFR activist manager name | Initial | Amendments | Total |
|---|---:|---:|---:|
| Ancora Alternatives, LLC | 0 | 7 | 7 |
| Barington Capital Group, L.P. | 1 | 3 | 4 |
| EJF Capital LP | 3 | 8 | 11 |
| Engaged Capital, LLC | 25 | 129 | 154 |
| Engine Capital Management, LP | 15 | 42 | 57 |
| Headlands Capital Management LLC | 1 | 2 | 3 |
| P2 Capital Partners, LLC | 13 | 29 | 42 |
| Saba Capital Management, L.P. | 158 | 1,042 | 1,200 |
| Tensile Capital Management LP | 1 | 3 | 4 |

Saba represents about 81% of the activist-subset filings. Issuer/security-type eligibility and concentration need review before pooling outcomes; no issuer-type filter has been implemented here. The 217 initial records are a potential review starting point, not 217 validated independent campaigns.

Artifacts:

- Full fund rows, source cells, manager IDs, candidate CIKs/accessions, rules and provenance: `/Users/jefflu/Projects/activist-13d/research/runs/investor-identity/20260923-hfr-event-driven-v1/matches.json`
- Reproducible screen: `scripts/extraction_protocol/match_hfr_event_driven.py`
- Deduplicated counts: `scripts/extraction_protocol/count_hfr_matched_filings.py` (stdout only).

Validation: frozen HFR hash checked; synthetic normalization/refusal/deduplication assertions; manager/fund counts reconciled; full screen replay produced identical output; accession counts checked by form and subset inclusion. No external identity validation was completed. Some matched metadata points to raw files absent at the recorded path; the HTML explicitly marks those entries rather than linking to missing files. Missing sources and archive completeness remain unresolved.

## Completed: Elliott identity and filing readers

Official-source notes, cached ADV and discovery inventories:

`/Users/jefflu/Projects/activist-13d/research/runs/investor-identity/20260923-elliott/`

- Current adviser: **Elliott Investment Management L.P.**, CIK 1791786, CRD 307151, SEC file 801-119969.
- Official ADV dated **2026-07-24** identifies Elliott Investment Management GP LLC as direct GP; Paul E. Singer appears as managing member/president of that GP. Adviser-chain control is not portfolio-company control.
- Elliott Management Corporation is a separate relying adviser (CRD 156601).
- Official leadership information does not establish an issuer-specific PM or historical filing-date roles.
- Source notes: `EXTERNAL-SOURCES.md`; metadata: `external-sources.json`; cached PDF SHA-256: `479b650834d86b42b37ef9f1e7d4636f27297b2e7f79c9f987607f62f37fbc9c`.
- Broad local name discovery contained unrelated Elliott names. The review deliberately selected **56 filings** with verified adviser CIK 0001791786. Historical Elliott Associates records are outside this subset pending entity mapping.
- All 56 selected raw-source hashes checked; full canonical document bundles and exact Item 4 citations saved under `filing-readers-v1/`. Readers have company timelines, purpose passages, expandable full text and exhibit inventories. Repeat output and local links validated.
- HTML formatting is flattened in canonical text; binary attachments are listed but not converted. Externally incorporated evidence was not fetched. Local timelines are not certified complete.

E2open example: initial filing **0000902664-23-005125**, 16 October 2023. Item 4 states an undervaluation rationale, intended strategic discussions, and possible participation as acquirer/investor/financing source. Conditional possibilities must not be converted into firm demands. Later cached amendments (12 April 2024 and 28 May 2025) disclose subsequent engagement and merger-related actions; they were shown separately, not incorporated into initial-entry features. This was a source-reading example, not a frozen semantic label or return study.

## Earlier work preserved

- Ready 200-filing review pack: `/Users/jefflu/Projects/activist-13d/review/current/`.
- Original 52-candidate human-first draft: `/Users/jefflu/Projects/activist-13d/review/drafts/human-first-52/`; Excel workbook still pending as previously documented.
- Deterministic 52-filing facts: `/Users/jefflu/Projects/activist-13d/review/drafts/deterministic-52-20260923/`.
- Frozen deterministic run and its own technical handoff: `/Users/jefflu/Projects/activist-13d/research/runs/deterministic-extraction/20260923-v1/`. Do not overwrite finalized artifacts.
- First-five identity discovery: `research/runs/investor-identity/20260923-five/`; paused, not a completed identity pack.
- Broader 13G/13F/other-filing expansion remains planned; this session did not implement those collectors or joins. 13D remains first priority.

## Next-session sequence

1. Open the HFR review and verify the **nine activist-manager candidates** using dated regulatory/official sources. Preserve fund/adviser/GP distinctions and unresolved aliases. Match CRD/SEC adviser identity to CIK with explicit evidence; do not promote normalized names automatically.
2. Obtain historical annual HFR snapshots if the user has them. Inventory and hash originals, retain original IDs/classifications and actual availability dates, then build dated manager records. Use the latest snapshot available before each filing; do not backfill 2026 classifications into earlier years.
3. Inspect issuer/security type and manager concentration. Decide treatment of operating companies, closed-end funds and other vehicles before a pooled price study. Reconcile missing raw sources and initial/amendment chains.
4. Define and review initial manager–issuer events from the candidate initial filings. Retain all amendments as subsequent disclosures; decide re-entry and joint-filing rules explicitly.
5. Freeze the baseline event protocol before testing NLP improvements: public timestamp, eligibility, duplicate/grouping rules, price identifiers, return windows/benchmarks and chronological evaluation splits.
6. Add other-investor disclosures in stages (13D/13G first, then 13F as appropriate). Distinguish holdings dates, transaction dates and disclosure dates; quarter-end 13F positions cannot be treated as purchase dates. Explicit coordination requires supporting evidence.

These are proposed next steps, not completed features or a frozen protocol. No new overnight job, scheduled collection, paid model call or return backtest was launched during this work. Do not infer authorization to restart unrelated BTC/Kalshi processes. Do not claim an empirically validated strategy, historical HFR universe or verified manager crosswalk exists yet.

## Suggested restart instruction

“Read `/Users/jefflu/Projects/activist-13d/research/docs/HFR-ACTIVIST-RESEARCH-HANDOFF-20260924.md`. Resume the HFR activist-manager identity verification, starting with the nine name-match candidates. Preserve current review packs and frozen evidence. Historical HFR snapshots are not yet ingested; do not use current classifications as historical facts.”
