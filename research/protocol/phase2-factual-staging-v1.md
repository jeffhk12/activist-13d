# Phase 2 factual staging v1 — 24 September 2026

Frozen preparation contract, not a model evaluation protocol. Offline only; no paid APIs.
Select all source-audited standalone initial candidates in universe-rebuild-v3 accepted
through 2025-12-31. Exclude protected human-review issuers/accessions and the user's
Hill International exclusion. Do not filter on realized returns or manager winners.
Do not call this a stock-eligible universe or untouched evaluation sample.

Rebuild canonical evidence from verified raw submissions and sidecars. Reuse the
unchanged deterministic extractor; validate schema and exact evidence citations.
Keep each reporting person's ownership separate. Preserve missing/ambiguous values.
These are parser candidates pending factual accuracy review, not human truth labels.
Mechanical section/reference extraction is allowed; no semantic interpretation.

Compute header-CIK history using strictly earlier SEC acceptance timestamps, handling
same-time filings as a batch. Count prior submissions and distinct issuers per CIK,
and prior reporter CIKs per issuer. Include earlier amendments as historical observed
filings only, never later amendments as initial features. Multiple CIKs can belong
to one investor; neither identity independence nor active positions are established.
History starts in 2013 and excludes protected issuers and Hill, so zero means no
observation in this restricted cache. Manager matching keys, HFR strategy labels,
prior-outcome track records and campaign audit labels are not model inputs here.

Output: gzip source bundles/facts, per-accession receipts, history JSONL, input/code
hashes, progress and a morning report. Resume only with unchanged source/code hashes;
verify checkpoint hashes. Single worker, 90 seconds per filing, 20 MiB raw source,
32 MiB per serialized artifact, 20 GiB free-disk floor, eight-hour processing budget.
Summaries only copied to OneDrive. Raw data, human worksheets and investor lists
are not edited or uploaded. Protected assets checked before and after.

Before fitting: freeze target/horizon/benchmark; complete point-in-time market and
HFR availability checks; define chronological folds with fully matured training
labels and grouped overlap controls. Existing examined data remain development.
No model training, hyperparameter search, outcome joins or return claims in this run.
