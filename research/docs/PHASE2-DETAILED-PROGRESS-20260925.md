# Phase 2 detailed progress review — 25 September 2026

The investment question is whether information available when an initial 13D becomes
public can help select better investments than the Phase 1 simple-following baseline.
The background work built and checked a factual foundation. It has not trained a
model, predicted returns, or demonstrated incremental investment performance.

## What was completed

The extraction pass processed 15,813 initial-filing candidates from 2013–2025.
It saved original-source references, canonical document text, separate reporting-person
ownership records, identifiers, timestamps, missing-value statuses and exact citations.
A second pass audited every candidate, with zero processing failures. It checked source
and artifact hashes, schema and citations, header identities against the eligibility
ledger, and an independent calculation of strictly prior disclosure history.

The selection reconciles to 75,631 universe records: 15,813 selected; 3,107 excluded
for protected review records/issuers or Hill International; 3,613 after 2025; 28 with
unresolved source/primary documents; and 53,070 remaining records not classified as
standalone initial candidates. These are mutually exclusive selection categories,
not counts of all amendments or all later filings in the original universe.

The sample is broader than hedge funds and does not require price coverage or
successful past returns. Of the selected filings, 14,838 are classified as first
observed party–issuer pairs, 809 as previously observed pairs, and 166 have prior
history references in the document. Standalone initial forms therefore do not all
establish new investment campaigns. These classifications remain audit metadata.

## What the data contains

All coverage below uses 15,813 selected filings as the denominator. “At least one”
does not imply all reporting persons were identified or all their fields recovered.

| Prepared field | Filings with a present value | Meaning and limitation |
|---|---:|---|
| SEC header filer name/CIK, issuer name/CIK and acceptance time | 15,813 | Reliable linkage starting point; not validated hedge-fund identities |
| Security CUSIP | 14,515 | Extracted identifier, not a verified historical stock match |
| Cover-page event date | 14,511 | Separate from public disclosure/entry time |
| At least one cover-page reporting-person name | 15,329 | Can include funds, controllers and other related parties |
| At least one ownership percentage | 12,673 | Partial reporting-person coverage is possible |
| Percentage present for every extracted ownership row | 11,961 | Still does not prove all people/rows were extracted |
| Share count present for every extracted ownership row | 12,228 | Holdings remain separate; overlapping shares are not summed |
| At least one cover-page reporting-person CIK | 1,132 | Major gap in linking each disclosed holder to a stable identity |

There are 316 filings with no extracted reporting-person rows. Do not interpret
missing fields as zero ownership or a non-activist investor.

## What the checks do—and do not—establish

Zero header-identity disagreements means the new header extraction agrees with the
existing eligibility ledger. It is an internal consistency check, not independent
confirmation that the filer is Elliott or another HFR manager, or that the correct
historical security has been selected.

The extraction also flags 5,867 header-versus-body issuer-name differences and 86
CUSIP check-digit failures. Name differences may reflect formatting or abbreviations,
but their causes have not been reviewed. They were retained, not automatically fixed.
The large missing/invalid-format totals count field occurrences across multiple rows;
they are not counts of failed filings. Citation validation shows where a value came
from; it does not prove that the parser understood it correctly or found every row.

Ownership coverage is time-dependent. At least one percentage was recovered in
1,032/1,417 filings in 2015, 853/1,010 in 2024, and 1,079/1,080 in 2025. The cause of
this difference needs investigation. A model could learn filing-era or document-format
effects rather than investment quality. Dropping incomplete filings could also change
the investment universe and bias comparisons.

## Investor history that is now prepared

The data separates previous submissions by the current header reporter, previous
companies associated with that reporter, and previous reporting-party CIKs associated
with the current issuer. Only strictly earlier acceptance timestamps count; simultaneous
filings cannot contribute to one another.

Among 15,813 selected filings, 5,829 have a header reporter with earlier submissions,
and 9,275 have prior issuer reporters outside the current header reporter group.
These overlapping counts describe potential features, not investment findings.
The selected records contain 10,509 distinct header reporter CIKs and 7,234 issuer
CIKs. The first number is not a count of unique hedge-fund managers.

Earlier investment in company B does not establish a position in company A.
Earlier disclosure in A does not establish that the position remains open.
Related funds/controllers may have different CIKs. History begins in 2013 and excludes
protected issuers and Hill, so zero means no observation in this restricted cache.

## What remains before a useful Phase 2 model

1. Review factual extraction gaps by year/format, especially ownership fields and
   cover-person identity. Distinguish recoverable parsing problems from genuinely
   unavailable information; retain original outputs and uncertainty.
2. Link reporting persons to manager families and dated HFR records. Confirm the
   information was available at the historical disclosure. Existing HFR work is not
   yet a validated disclosure-time feature panel in these runs.
3. Build lagged market features: historical company size, industry, liquidity,
   volatility and prior returns, with verified security links and availability dates.
4. Freeze the prediction target, holding period, benchmark and training/evaluation
   rules. The longer activism horizon remains relevant, but the exact model target
   has not been implemented here. Training returns must finish before the training
   cutoff; examined history is development data, not a fresh holdout.
5. Fit a simple structured-data baseline, compare inputs with and without investor
   information, and compare economic results with Phase 1 under consistent portfolio
   and cost rules. Existing settlement/accounting exceptions still need treatment.

Intent NLP remains Phase 3's incremental contribution. No human labels, investor lists
or historical performance conclusions were changed by these background jobs.
The next priority is a focused ownership/identity gap review before broad model fitting.

## Evidence

- [Extraction completion](../runs/phase2-overnight/20260924-full-v1/progress.json)
- [Audit completion](../runs/phase2-readiness/20260924-full-v1/progress.json)
- [Field coverage by year](../runs/phase2-readiness/20260924-full-v1/field-coverage.json)
- [Selection and campaign audit metadata](../runs/phase2-overnight/20260924-full-v1/selection.json)
- [Prior-header-CIK history](../runs/phase2-overnight/20260924-full-v1/prior-header-cik-history.jsonl)
- [Read-only inspection script](../../scripts/phase2_readiness/inspect_completed.py)

All findings are preparation diagnostics, not validated predictions or alpha estimates.
