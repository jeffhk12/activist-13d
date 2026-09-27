# Original proposal versus current work — 24 September 2026

This is a comparison and recommendation, not a replacement proposal or frozen
research protocol. The original documents remain preserved. No new backtest,
labeling job, collection or modeling commitment follows from this review.

## Which proposal is the baseline?

There are two materially different proposals:

- [September 8 original](PROPOSAL.md): stated intent predicts campaign duration
  and terminal outcome; the 2024 disclosure change supplies a causal question;
  duration-informed sizing and holding periods are the final deliverable.
- [September 13 professor V2](PROFESSOR-PROPOSAL-v2.md), designated canonical in
  [the project plan](PROJECT-PLAN.md): a long-only investment-selection backtest,
  comparing simple following, structured-feature selection and selection with
  validated NLP intent features. Duration/DeepHit became conditional extensions;
  disclosure-period comparisons became robustness without core causal claims.

The current direction should be assessed primarily against V2. No professor
approval/submission status is inferred from the existence of that document.

## Comparison

| Dimension | September 8 | September 13 V2 | September 24 direction/status |
|---|---|---|---|
| Main question | Predict campaign duration/outcome from intent | Does NLP improve investment selection? | Does manager identity help first, then does intent add value? |
| Deliverable | Duration-conditioned sizing and exit rule | Cost-aware long-only selection backtest | Manager-based return comparison proposed as baseline; no strategy result yet |
| Universe | Curated activist managers, estimated 3,000–4,000 campaigns | Eligible corporate campaigns; feasibility count required | Dated HFR ED/Activist candidates plus seven externally selected groups |
| HFR role | Not a core source in original proposal; historical sourcing note excluded it | Monthly event-driven index benchmark | Fund/manager snapshots now also construct the universe; benchmark-return task remains distinct |
| Models | DeepHit, survival baselines, causal forests, sizing layer | Regularized baseline, boosting, small feedforward neural extension | No fitted investment models; original V2 modeling comparison remains relevant |
| Text | LLM extraction central from the outset | Human-first development, held-out extraction evaluation | Deterministic facts and identity evidence prioritized; validated semantic dataset still pending |
| Other investors | Not a core branch | Not a core prerequisite | Participation and 13G/proxy/8-K/13F/insider context added as staged scope; not operational or required for first baseline |
| Time coverage | 2013–2026 | 2013–2026 subject to coverage/follow-up | HFR snapshots begin 2018 Q1; combined discovery counts mix temporal coverage |
| Causal claims | 2024 rule-change DiD and heterogeneous effects | No causal claims in core period comparisons | Current comparison remains predictive/observational |

## What we have actually built

- Local SEC screen denominator: 75,631 parsed 13D/13D-A metadata records, not
  75,631 campaigns or certified complete source coverage.
- Ready 200-filing review pack. The separate human-first 52-candidate draft is
  still paused with its workbook pending; prepared packets are not completed labels.
- Deterministic extraction over 52 legacy filings, source/citation checks and
  reproducible factual tables. This is development evidence, not full-archive
  extraction accuracy or an independently validated intent dataset.
- Elliott identity example and 56 source-verified filing readers. The newer
  broader Elliott 230-filing candidate set does not inherit that verification.
- 35 HFR snapshots, 2018 Q1–2026 Q3, preserved and inventoried. Historical ED union:
  393 Firm_IDs; historical Activist union: 44. Dates remain availability proxies.
- Dated HFR matches plus supplement: 71 candidate manager units, 3,125 filings,
  including 404 initials. Focused activist version: 22 units, 2,636 filings,
  including 323 initials. Economic-manager deduplication is not certified.
- WRDS access and raw-data acquisition work exist, with documented vendor-count,
  coverage and convention limitations. A validated linked event/return panel is
  not established by access or raw collection.

Not yet established: eligible independent campaign count, complete manager identity
crosswalk, price-linked event panel, accepted intent labels, validated campaign-end
labels, trained investment models, or a tested investment edge. The original
3,000–4,000 campaign estimate is unvalidated. Our 3,125 count is filings, mostly
amendments; it cannot be offered as confirmation of the original sample estimate.

## Agreed additions versus unresolved ideas

Agreed work includes deterministic extraction first, the historical HFR manager
screen, the external supplement, and staged complementary filings with 13D first.
The user has proposed comparing this subset's post-disclosure stock performance
with other filings. The comparison's event definitions, controls, horizons,
eligibility and evaluation design are not frozen. Latest proposed horizons and
model choices are not approved replacements for V2.

The original V2 economic rules remain on record: capped equal allocations, one
position per issuer, interest-bearing cash, trading costs, $100,000/$100 million
capacity scenarios, and comparison of announcement filters/stops with unfiltered
and no-stop baselines. Recent conversation did not cancel these. Exact benchmarks
and target still need specification; HFR fund snapshots do not supply an agreed
benchmark-return definition by themselves.

Operationally, paid model APIs remain off under current project instructions,
even though V2 discussed a $50 candidate-provider budget.

## Scope drift and corrections

1. V2 requires the first regular-session opening at least one full trading session
   after publication. The newer return-comparison draft's next-session-open example
   is inconsistent and was not authorized as a replacement. Retain V2's baseline
   pending an explicit revised specification.
2. A famous-manager supplement selected today creates retrospective selection
   concerns. Dated HFR membership and external-manager selection must remain
   separately flagged; harmonize dates before comparison.
3. Other filings are not automatically non-activist controls. Unresolved identities,
   issuer types and coverage can drive group differences.
4. An event-return comparison alone would not fulfill V2's incremental NLP and
   supervised-ML contribution. Use it as a baseline/feasibility stage.
5. The multi-source participation branch risks expanding a solo 5–10-hour/week
   project before the core event panel exists. Keep it optional after the baseline.
6. The September 8 schedule expected a campaign event list by September 21.
   Raw collection has grown substantially, but that validated event-list gate has
   not yet been met. Replan based on usable events rather than raw filing totals.

## Recommended reconciliation

Preserve V2's strategy-first objective. Treat manager identity as an additional
baseline and feature family, then test the incremental value of validated intent:

1. Establish eligible, time-consistent initial manager–issuer events and price links.
2. Measure naive following and identified-manager following against comparable
   initial 13Ds and investment benchmarks, after feasible entry and costs.
3. Compare matched model families using company/filing features, then manager
   information, then validated NLP features. This separates each source's contribution.
4. Evaluate a frozen long-only strategy under V2's portfolio rules and protected
   chronological testing. Keep survival, causal analysis and investor participation
   as extensions unless a revised proposal deliberately makes them core.

Possible reconciled question: **Does identifying the investor improve a long-only
strategy following initial Schedule 13D disclosures, and does disclosed intent
provide additional out-of-sample value?** This is a recommendation, not a claim
that a new proposal has already been agreed or that returns demonstrate an edge.

## Evidence

- [Completed deterministic run](../runs/deterministic-extraction/20260923-v1/HANDOFF.md)
- [HFR/identity direction handoff](HFR-ACTIVIST-RESEARCH-HANDOFF-20260924.md)
- [Quarterly HFR handoff](HFR-QUARTERLY-HANDOFF-20260924.md)
- [Supplemental universe handoff](HFR-SUPPLEMENTAL-HANDOFF-20260924.md)
- [Latest return-comparison draft](MANAGER-IDENTITY-RETURN-COMPARISON-DRAFT-20260924.md)
- [Collection limitations](../runs/data-collection/README.md)
