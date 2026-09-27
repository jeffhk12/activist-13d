# Phase 1 eligibility and comparison coverage closeout

24 September 2026 — development data audit; no fresh investment outcomes evaluated.

Does following an identifiable investor's initial 13D offer a useful investment baseline? Existing estimates remain usable as development diagnostics for the explicitly selected sample. This audit does **not** establish that every retained observation begins a new economic campaign, or that benchmark coverage represents all initial filings. No manager membership, eligibility decision, human label or return estimate was changed.

The consequential finding is a source-attribution limitation in the first-observed branch. Its 24 development exclusions called `prior_history_in_document` include eight cases where detected passages do not establish prior same-issuer 13D reporting and two requiring further attribution review. Fourteen contain supporting same-issuer, previous-group or predecessor reporting context. These are assistant interpretations of source passages, not human labels or validated campaign classifications. Keep all 24 conservative exclusions, but describe them as **unvalidated history-reference exclusions**, rather than verified prior campaigns. There is no tested general attribution correction sufficient to promote individual accessions.

## What the comparison sample covers

The following counts use only frozen schedules and information dated before disclosure. They require no future returns. The six-month schedule is primary; 63- and 252-session tables are also saved.

| Six-month branch/cohort | Scheduled events | Historical Russell ETF assigned | Potential five-other-issuer controls |
|---|---:|---:|---:|
| First observed, all | 1,981 | 709 | Not an all-event estimand |
| First observed, focused | 62 | 55 | 19 |
| First observed, broad managers outside focused | 27 | 15 | Not focal |
| First observed, other | 1,892 | 639 | Not focal |
| Standalone, all | 2,069 | 750 | Not an all-event estimand |
| Standalone, focused | 73 | 65 | 22 |

Focused is a subset of broad managers. The disjoint first-observed cohort rows reconcile to 1,981; do not add focused to a separately reported inclusive broad cohort. Assignment is not a calculable-return count. Potential controls use the same entry year, two-digit SIC and assigned Russell segment, excluding the focal issuer; actual retrospective return comparisons can lose controls when returns are unavailable.

For the 1,981 first-observed events, 197 lack required historical security evidence and 1,075 have no constituent row in the supplied snapshot. These are different failure modes. An absent constituent row is not proof that the stock was outside Russell: all 58 membership receipts retain unresolved vendor count discrepancies. No cap-based benchmark substitution was introduced.

| Entry year | Assigned / scheduled first-observed events | Focused events with potential five-control match / focused events |
|---|---:|---:|
| 2018 | 125 / 277 | 6 / 16 |
| 2019 | 160 / 345 | 4 / 13 |
| 2020 | 152 / 375 | 4 / 16 |
| 2021 | 124 / 543 | 1 / 6 |
| 2022 | 148 / 441 | 4 / 11 |

Size coverage is reported using observable historical segment assignments, not guessed market-cap categories. First-observed events comprise 585 IWM, 117 IWR, seven IWB and 1,272 unassigned. Focused observations comprise 38 IWM, 16 IWR, one IWB and seven unassigned; the potential control matches are 17 IWM and two IWR. Of 19 potential focused matches, 13 fall in SIC 73, four in SIC 28, one in SIC 67 and one in SIC 87. Full industry tables retain zero-match industries. These concentrations and the cohort/year differences rule out assuming coverage exclusions are random. The matched comparison describes a narrow retrospective subset, not the average effect of all manager initial disclosures.

## Why the sample gets smaller

Starting from the 17,795 metadata-initial registry, 11,868 filings are outside development entry dates, 302 are protected human-review issuer filings and 2,710 fail prior basic readiness: 2,915 remain. The standalone branch then excludes 40 amendments, three unresolved conversions and three source failures, leaving 2,869 filings. The first-observed branch additionally excludes 111 prior-pair filings and the 24 history-reference filings, leaving 2,734.

For six months, first-observed scheduling excludes 445 overlapping-issuer filings. The remaining 2,289 filings consolidate into 1,981 events. Standalone scheduling excludes 484 overlapping filings; 2,385 remaining filings consolidate into 2,069 events. Different schedule horizons have different overlap exclusions; they are not independent samples. The original basic security screen and 207 protected issuers are unchanged.

## Source and identity findings

All 45 unresolved universe records have machine-readable dispositions: 16 conversion/history questions, 18 intact raw submissions missing retrieval sidecars, and 11 missing raw submissions. All 18 intact submissions match the original stored byte counts and SHA-256 hashes. Their recovered canonical text permits content diagnosis but cannot recreate absent retrieval receipts. The 11 missing raw files retain available receipt metadata separately. No new retrieval was performed, no fabricated sidecars were written, and no unresolved case was restored to eligibility. Archive spot checks contained the same missing counterparts; this was bounded recovery work, not an exhaustive search of every historical storage system.

A fixed, non-outcome sample selected the five smallest SHA-256 values per status/history stratum, treating body overrides as a separate stratum: 35 filings in seven strata. Canonical texts and exact evidence spans are saved. Source reading identified other-issuer track records and incorporated powers of attorney incorrectly treated as self-history; checking all 24 development history-reference exclusions also found prior-13G sentence crossings, a hypothetical cover checkbox and a late-filing time description. Absence of these lexical matches would not prove absence of prior history, so broad regex removal is not a defensible restoration rule. The sample is a diagnostic challenge set, not a precision/recall estimate or an independent human reference set.

Fixed investor-key joins reconcile for all 75,631 records. There are 55,019 prior-history edges: 54,981 include a shared reporting-person CIK and 38 rely only on a shared candidate manager key. Of 964 standalone prior-pair filings, 963 have some prior reporting-person CIK overlap; one relies only on the fixed Elliott candidate key (`0000902664-20-002925`, prior `0001013594-15-000148`). Neither a CIK overlap nor a name candidate validates an economic campaign. Investor-list membership was not adjusted.

Two HFR candidates have a delivery-date proxy equal to their SEC acceptance date, although the official filing date is the next day: JW Asset Management (`0001019056-22-000279`, 16 March 2022 acceptance) and First Pacific Advisors (`0001193125-18-276704`, 18 September 2018 acceptance). Same-day receipt time is unverified, so strictly prior availability is not established. Neither enters either selected development branch. Removing their HFR keys and replaying all history changes zero campaign-status classifications. This does not validate the historical availability of HFR delivery-folder proxies generally, or the retrospective supplemental investor universe.

## Verification, limits and next dependency

Mechanical replay verifies 75,602 available canonical classifications: 75,593 direct text/form replays plus nine raw XML amendment-number replays. All 242,988 stored evidence spans match their canonical character offsets. History replays for all 75,631 rows; every one of 55,019 prior edges is strictly earlier and shares issuer/identity keys. Six new coverage tests pass, covering hand-calculated distinct-issuer counts, unavailable assignments, deterministic replay, date conventions, duplicate events and failed identifier joins. These checks establish arithmetic and faithful implementation, not semantic classifier accuracy.

Root integration should keep existing return estimates unchanged, narrow the first-observed wording as above, and retain same-day HFR timing flags and candidate-identity limitations in the freeze gate. A later eligibility correction requires a source-grounded general attribution rule, versioned protocol/module, whole-universe reclassification, and all affected development schedules and returns rerun before any fresh evaluation. The 45 unresolved records require original receipts/raw evidence or specific reporting-history adjudication; no statistically representative classifier validation has been established.

Evidence directory: [20260924-eligibility-closeout-v1](../runs/phase1-baseline/20260924-eligibility-closeout-v1/).

- [Summary and replay counts](../runs/phase1-baseline/20260924-eligibility-closeout-v1/summary.json), [supplemental XML/timing checks](../runs/phase1-baseline/20260924-eligibility-closeout-v1/supplemental-checks.json).
- [All 45 dispositions](../runs/phase1-baseline/20260924-eligibility-closeout-v1/unresolved-dispositions.json), [deterministic source sample](../runs/phase1-baseline/20260924-eligibility-closeout-v1/source-sample.json).
- [All 24 development source contexts](../runs/phase1-baseline/20260924-eligibility-closeout-v1/development-history-contexts.json), [separate assistant interpretation record](../runs/phase1-baseline/20260924-eligibility-closeout-v1/history-attribution-review.json).
- [Coverage tables](../runs/phase1-baseline/20260924-eligibility-closeout-v1/pre-event-coverage.json), [per-event coverage](../runs/phase1-baseline/20260924-eligibility-closeout-v1/pre-event-events.json), [reconciling filing/event counts](../runs/phase1-baseline/20260924-eligibility-closeout-v1/development-funnel.json).
- [Timing evidence](../runs/phase1-baseline/20260924-eligibility-closeout-v1/identity-timing-review.json), [initial provenance](../runs/phase1-baseline/20260924-eligibility-closeout-v1/provenance.json), [supplemental provenance](../runs/phase1-baseline/20260924-eligibility-closeout-v1/supplemental-provenance.json).
