# Expanded HFR return comparison — v1

24 September 2026. User requested recalculation after expanding HFR to all
strategies. This is a development comparison after observing earlier results.

Use exactly the schedules, price panel, return engine and protected-issuer list
from development-v4, governed by phase1-development-v1.md. Recompute each stock
and SPY return from that panel and require exact parity with the preserved event
ledger. Do not reschedule entries separately for each manager group, replace
unusable trades, change horizons or expose later evaluation outcomes.

The full filing sample already contains the newly identified HFR events; this
changes group membership and group averages, not the all-event return sample.
Use every accession of merged same-issuer/same-security/same-entry events when
assigning group membership, and count the event once in each applicable group.

Expanded manager membership = any event accession in all_hfr_plus_supplement
from hfr-all-managers/20260924-v1/accession-unions.json. HFR-only membership uses
all_hfr, excluding the external supplement unless the same event also has an HFR
accession. Preserve the old broad and focused flags and require exact equality
between those flags and their corresponding accession unions.

The mutually exclusive groups, in order of precedence, are: focused activist
candidates (HFR activist offering or external supplement); other Event-Driven
candidates (old broad minus focused); newly recognized other HFR candidates
(expanded minus old broad); and other/unresolved (expanded complement). These
are candidate manager classifications, not investor intent or verified campaigns.
Also report HFR-only and the combined expanded universe, clearly labelled as
overlapping aggregates. Strategy offering groups are overlapping secondary views.

Flag events linked solely to fund-of-funds-classified HFR managers and show their
counts; do not silently remove them. For merged events, this flag requires some
HFR match, all matched HFR accessions to be fund-of-funds-only, and no external
supplement accession. No name matching, classification or timing rule is changed.

Six months (126 sessions including entry) remains primary; 63 and 252 sessions
remain supporting comparisons. Preserve the March 2018–December 2022 entry bounds,
follow-up through 2023, delayed opening entry, closing-trade exit requirement,
usable delisting-return treatment and zero-return cash after delisting. Missing
or invalid returns and unavailable scheduled exit trades remain explicit refusals.

Results are equally weighted gross event averages against same-window SPY, with
mean/median excess returns, win fraction and issuer-cluster bootstrap intervals
(2,000 resamples, seed 20260924). This is not funded portfolio performance; costs,
capacity, cash drag and complete identity/eligibility validation remain open.
Issuer intervals do not account for market-time or manager dependence.

Russell size-segment benchmarking remains the requested primary research direction.
Historical membership/assignment is not yet verified. This recalculation explicitly
retains SPY as the available high-level reference and must not be labelled as
Russell-relative, size-adjusted or risk-adjusted alpha. Preserve this result for
the eventual common-sample Russell comparison. No paid APIs, NLP labels or ML fitting.
