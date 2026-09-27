# Proposal V3: direction review

September 24, 2026. V3 is the current direction-review draft. V1 and V2 are preserved;
no professor submission or approval is implied.

## Agreed research sequence

1. Simple following: does buying after eligible initial 13Ds improve net returns
   relative to appropriate benchmarks? Compare all eligible events with identified
   manager subsets. No ML is needed for this first baseline.
2. Structured ML: does selection using investor, filing and company information
   improve on simple following? Include an identity ablation to measure its value.
3. NLP increment: does initial disclosed intent improve the same structured-data
   models and portfolio rules on comparable samples?

The conceptual comparison is: simple following → structured ML → structured ML
plus NLP. A manager-subset return comparison alone is not the ML contribution.
Neither stage must produce a positive result to justify reporting the next
pre-specified comparison. Sample feasibility and evaluation integrity remain gates.

## Preserved from V2

Long-only selection; corporate-equity focus; realistic delayed entry; capped equal
allocations; one position per issuer; interest-bearing cash; costs and two capacity
scenarios; chronological holdout; regularized and boosted baselines; a conditional
small neural extension; human-first NLP evaluation; no core causal claims.

## Changed or clarified

- Simple following and investor identification now precede NLP in the research
  sequence. Identity also becomes an explicit feature contribution to test.
- Historical HFR and the external supplement now define candidate universes, with
  explicit availability, selection and identity limitations.
- Current filing/event-candidate counts replace the original campaign estimate.
- Survival, causal disclosure analysis and investor participation are extensions.
- Phase 3 must control sample attrition as well as model/portfolio rules; otherwise
  apparent NLP gains might reflect easier-to-parse observations.
- The newer draft's next-session-open suggestion is superseded by V2's retained
  minimum-one-full-session entry baseline.

## Decisions still needed before a backtest specification is frozen

| Decision | Why it matters | Proposed approach for review |
|---|---|---|
| Primary sample and dates | HFR starts in 2018; the supplement is retrospective | Assess common 2018-onward coverage first; keep older/supplemental analyses explicit |
| Primary return horizon and target | Defines labels, maturity and trade duration | Choose after coverage checks, before comparative returns; select one primary target |
| Benchmark and controls | Raw returns alone do not establish improvement | Broad-equity benchmark plus comparable initial-disclosure controls; exact series pending |
| Investor identity eligibility | Known names are not verified historical relationships | Build a dated entity crosswalk; retain unresolved identities separately |
| Event and security eligibility | Repeated/joint filings and investment vehicles distort counts | Define initial/re-entry and issuer/security rules before joining outcomes |
| Neural model requirement | Must fit course expectations and effective sample size | Confirm with professor; do not force complexity based on raw filing count |

These are open design choices, not requests to restart data collection or run a
backtest. The immediate work after direction review is an event feasibility and
price-link audit. Exact allocation caps, participation limits, cash conventions,
split dates and optional filter thresholds belong in the later frozen specification.

## Review files

- [Proposal V3](PROFESSOR-PROPOSAL-v3.md)
- [Browser-readable V3](proposal_v3/index.html)
- [Historical scope comparison](PROPOSAL-SCOPE-REVIEW-20260924.md)
- [Preserved professor proposal V2](PROFESSOR-PROPOSAL-v2.md)
