# Focused activist concentration diagnostic v1

24 September 2026. Exploratory checks after viewing development results, not
confirmatory tests. Six months remains primary; twelve months is the motivating
supporting result. Use only the frozen Russell-return development ledger, keeping
all original assignments, prices, eligibility, missingness and protected issuers.

For 63/126/252 sessions, select focused events with calculable common-sample
Russell excess. Report mean, median, win fraction and original company-bootstrap
interval. Examine entry year, company CIK and candidate manager. Attribute only
the matches qualifying an event as focused: HFR hits with manager_has_activist,
or supplemental manager groups, across every merged accession. Deduplicate HFR
Firm_ID and supplemental group separately; do not assert economic entity mergers.
Refuse events without qualifying manager evidence. Multiple-manager events appear
in each manager's descriptive mean; allocate each event's excess equally among
its m candidate managers for additive contribution (excess / m / total events).
These descriptive manager rows overlap and are not independent observations.

Report all company/manager/year results, leave-one-company/manager/year-out means,
and equal-company-weight mean of company event averages. Removing a manager
removes every event linked to it; do not assign co-managed events to another
manager after removal. Rank largest positive event excess returns and remove
1/3/5 events; also remove the 1/3/5 companies with largest aggregate positive
excess contribution, including all events for each. Ties: accession/entry for
events, CIK for companies. Contribution means arithmetic percentage points of
an equal-weight event mean, not funded portfolio P&L. Do not report net-profit
shares when the denominator is small; show top-k share of gross positive excess.

Rankings and removals use realized outcomes deliberately for stress diagnostics,
never as a tradable selection rule. Display sample sizes after every removal.
Report HFR-only qualifying evidence, supplemental-only and mixed sources.

Compare 63/126/252 on the intersection of exact event keys (accession, entry,
PERMNO), so changes in sample do not masquerade as horizon effects. Summarize
benchmark/stock/excess for each horizon on that intersection. Different holding
periods still have different market exposure and are correlated; do not infer
causation or optimize the holding period. No new outcomes, model labels, ML or
paid APIs. No new p-value or significance claim from this multiple-check exercise.

Preserve provenance, pure-function hand pins/refusals, arithmetic reconciliation,
original-sample parity, protected boundaries, test logs and exact offline replay.
