# HFR expansion: all strategies now matched to the filing archive

**Subsequent update:** [expanded development returns are now calculated](PHASE1-EXPANDED-HFR-RESULTS-20260924.md).
The original matching-stage status below is preserved as history.

24 September 2026. [Open the report](../runs/hfr-all-managers/20260924-v1/index.html)
or [search managers](../runs/hfr-all-managers/20260924-v1/managers.html).

## What this adds to the research

We can now distinguish the question “does following an HFR-listed manager help?”
from the narrower question “does following an activist candidate help?” The new
screen includes every strategy in the supplied snapshots, rather than restricting
the name universe to Event-Driven managers.

The 35 snapshots contain 3,372 distinct historical HFR Firm_IDs, with 1,601 in
the latest supplied snapshot. **180 HFR manager IDs have dated filing-name
candidates**, compared with 64 in the earlier HFR Event-Driven screen. These are
vendor manager units requiring identity review, not a certified count of unique
economic hedge fund managers.

| Universe | Unique filing records | Initial disclosures | Amendments |
|---|---:|---:|---:|
| Earlier HFR Event-Driven screen | 1,750 | 241 | 1,509 |
| Expanded HFR, all strategies | 3,161 | 525 | 2,636 |
| Additional HFR links | 1,411 | 284 | 1,127 |
| Expanded HFR plus seven external groups | 4,536 | 688 | 3,848 |

The combined universe previously had 3,125 filings and 404 initials. It now covers
about 6.0% of the 75,631-record archive. These rows overlap and are not additive.
The seven external groups remain Elliott, Starboard, Pershing Square, Sachem Head,
TCI, ValueAct and Icahn-related entities. There is no observed accession overlap
between their current candidate sets and this HFR screen; that does not prove
the underlying economic manager identities are distinct across databases.

Examples of newly linked HFR names include Cannell Capital, Perceptive Advisors,
GoldenTree, Cove Street, Wynnefield, Scopia and Nantahala. These are name candidates,
not verified fund-to-filing relationships. An HFR strategy label does not establish
the intent or investing vehicle of a particular filing.

## Comparison groups prepared for the next analysis

The following groups use explicit precedence and therefore do not overlap:

| Candidate group | Initial filings | Pass the existing basic data checks |
|---|---:|---:|
| Focused activist candidates, including the external supplement | 323 | 191 |
| Other Event-Driven candidates | 81 | 49 |
| Other HFR candidates newly included | 284 | 149 |
| Other or unresolved filers | 17,107 | 7,550 |

The expanded HFR/supplement universe has **389 preliminarily data-ready initials**,
up from 240. This is not a finalized event count, campaign count or new return
sample. The unchanged readiness rule checks source, stock matching, security type,
opening-price availability and basic dates/identity fields. It does not finish
company eligibility, manager identity, overlapping-event, or outcome review.

The focused cohort is unchanged. The next performance run should compare all HFR,
focused candidates and the other HFR groups over common periods using the proposed
Russell size benchmarks, retaining S&P 500 context. Existing performance reports
still use the earlier groups; **no returns have been recalculated by this expansion**.

## Matching method and limits

Use the latest complete supplied snapshot strictly before each filing date, as in
the previous screen. Do not carry a manager absent from that snapshot forward
from an older one, or backfill an earlier filing with later aliases/classifications.
Matching uses exact normalized firm names, firm names with trailing legal suffixes
removed, or exact normalized fund names. No fuzzy name expansion or inferred
CIK/adviser-registration conversion is used. A matched CIK is evidence on that
filing; it is not automatically propagated to all of the CIK's other filings.

All previous HFR candidate filings are retained. Of the archive, 46,185 records
have an earlier supplied snapshot and 29,446 do not. Expanded HFR candidates are
6.84% of the former and 4.18% of all archived records. Delivery dates remain
unverified availability proxies. Two candidate filings, including one initial,
have a snapshot/SEC-acceptance-date timing flag requiring review.

Ten filings match multiple HFR IDs; all are amendments. These remain ambiguous.
Managers can offer multiple strategies, so strategy coverage tables overlap.
There are 116 filings linked only to fund-of-funds-classified managers, including
24 initials. Those are flagged separately; diversified firms and risk-premia
categories remain visible rather than being silently called pure hedge funds.
HFR presence does not establish that a particular filing was made by a hedge fund
vehicle. Zero matches do not prove an institution lacks hedge fund activity.

This screen covers the existing 13D/13D-A archive only. It does not search 13G or
13F, and therefore cannot measure all investments or all filings by these managers.
No paid model calls, new SEC downloads, semantic intent labels, human-packet edits,
or protected evaluation outcome analysis occurred.

## Evidence and validation

- [Search matched filings and source documents](../runs/hfr-all-managers/20260924-v1/filings.html)
- [Exact counts](../runs/hfr-all-managers/20260924-v1/summary.json) and [deduplicated accession sets](../runs/hfr-all-managers/20260924-v1/accession-unions.json)
- [Dated match evidence](../runs/hfr-all-managers/20260924-v1/candidates.json)
- [Disjoint comparison groups](../runs/hfr-all-managers/20260924-verification-v1/disjoint-cohorts.json)
- [Initial-filing overlay](../runs/hfr-all-managers/20260924-verification-v1/initial-filings-overlay.json) and [readiness counts](../runs/hfr-all-managers/20260924-verification-v1/cohort-counts.json)
- [Verification receipt](../runs/hfr-all-managers/20260924-verification-v1/verification.json)

Six offline tests cover all-strategy grouping, share-class aggregation, missing
IDs, classification pairs, exact matching, ambiguity, date boundaries and replay.
The complete run reproduced byte-identical frozen outputs. Independent checks
verify hashes, prior-match retention, deduplicated counts, unchanged focused
membership, all local HTML links, and reproduction of the earlier readiness counts.
Tests are under tests/ and enter the existing offline CI suite; local lint passed.

Implementation: scripts/data_collection/screen_all_hfr.py,
src/activist13d/hfr_all_match.py and scripts/data_collection/verify_all_hfr.py.
Run with the project interpreter and PYTHONPATH=src, PYTHONNOUSERSITE=1,
PYTHONIOENCODING=utf-8. Preserve the old HFR, supplemental and return runs.
