# Project output standard

Effective 24 September 2026. Applies to project chat explanations, progress updates,
reports, proposals, dashboards and handoffs. This is the single source of truth
for communication; STANDARDS.md continues to govern research evidence and code.

## Audience and level

Write for Jeff as an institutional investment professional with CFA training,
hedge fund manager research, portfolio analytics, performance measurement and risk
experience, plus quantitative finance and applied AI experience. This calibration
is based on the supplied V6 institutional AI résumé. Do not reproduce personal
contact information or import employer materials into the project.

Use the language of manager due diligence and performance analysis. Do not explain
basic investment concepts unnecessarily. Explain project-specific data decisions,
statistical methods and software terminology when they affect interpretation.
Plain English should preserve precision, not remove the reasoning.

## Required order of explanation

1. **Investment question:** What are we trying to learn or decide?
2. **Direct answer and status:** What do we know today? State whether this is
   data preparation, exploratory evidence, or an evaluated investment result.
3. **Evidence and meaning:** Give the important numbers alongside what they mean.
4. **Limits on the conclusion:** Explain the specific unresolved issue and how it
   could affect the answer. Distinguish facts, interpretations and proposed choices.
5. **Next decision or action:** Say what comes next and what it will establish.
6. **Supporting methods and sources:** Provide reproducible evidence after the
   explanation, using links or an expandable technical appendix in HTML.

Short chat updates may combine these into two or three paragraphs. Reports should
be self-contained: a reader should not need earlier chat messages to understand
their purpose or findings. Do not lead with filenames, test counts or code changes.

## Numbers must explain themselves

- Label the unit: filing, initial filing, amendment, security, manager candidate,
  validated manager, or campaign. Never substitute one for another.
- Give the denominator for percentages, the relevant dates or coverage limits,
  and the comparison group. A report date is not the sample period.
- Explain why a sample gets smaller with sequential, reconciling counts. Do not
  combine parallel coverage counts into a sequential funnel.
- State when groups overlap. The focused activist subset is inside the broader
  manager subset; their counts must not be added together.
- Translate missing or excluded data into its research consequence. A record that
  is not ready for analysis is not a bad investment or evidence of no activism.
- Link numerical claims to the dated calculation/evidence. Preserve frozen runs;
  publish a new explanatory companion when improving an old report's language.

## How to explain this project's stages

**Phase 1 — simple following:** Test whether buying after an initial 13D disclosure
improves returns under realistic trading rules. Compare the identified-manager
subset with other filings and the agreed benchmark. No predictive ML is needed
for this baseline. Manager names that are not matched are not automatically
non-activists or passive investors.

**Phase 2 — structured-data ML:** Test whether information such as investor identity,
company characteristics and filing facts helps choose better opportunities than
simple following. Explain the model's inputs, target and evaluation in investment
terms before naming the algorithm.

**Phase 3 — incremental NLP:** Test whether extracting what the investor says it
intends to do adds value beyond Phase 2, using comparable samples, trading rules
and evaluation periods. NLP is the additional contribution, not assumed alpha.

When reporting returns, specify entry timing, holding period, benchmark, weighting,
costs, sample size and dates, treatment of overlapping positions and delistings,
and whether results are from development or untouched evaluation data. Separate
absolute return, benchmark-relative return and risk-adjusted evidence. Report
uncertainty and economic magnitude before claiming an edge. Never call a price
availability check a return result or an observed opening price guaranteed execution.

For Phase 1, stock-appropriate Russell size-segment benchmarking is the primary
research direction; S&P 500/SPY remains the high-level market reference. Industry
matching is a subsequent robustness check. Distinguish index returns from ETF
proxy returns and verified historical membership from size approximations.
Russell 3000 is a broad-market index, not a microcap category. Until the revised comparison is
computed, label the existing figures explicitly as SPY-relative. When benchmarks
change, show both on the same matched sample and report excluded events separately.
Positive in-sample excess return is an observed pattern, not automatically alpha
or a repeatable edge. Disclose revisions made after inspecting development results.

## Preferred wording

| Technical term | Explain it this way first |
|---|---|
| Attrition | Why the sample gets smaller at each check |
| Historical identifier match | Matching the filing to the correct stock at that time |
| PERMNO | The stock database's persistent security ID; keep the code in supporting detail |
| Candidate manager link | A possible manager match that still needs confirmation |
| Positive entry open observed | We found an opening price on the proposed purchase date |
| Basic readiness | Enough information to continue review, not final approval for a backtest |
| Look-ahead bias / leakage | Using information an investor could not have known at the time |
| Holdout | Later or otherwise reserved observations the model has not used to learn or tune |
| Incremental NLP contribution | Whether reading the stated intentions improves the decision beyond the other data |

Introduce necessary technical terms in parentheses after their meaning. Avoid
unexplained abbreviations and claims such as “verified” without specifying what
was verified. Use practical examples where a method's investment meaning is unclear.

## Report template and release check

Use a descriptive title, report date and research status. Start with a short
investment takeaway. Include a compact table with “What we found” and “What it
means” when several findings need comparison, then limitations, next steps and
linked supporting evidence. HTML should offer clear navigation and readable tables.
Technical handoffs can be detailed but must start with the same plain-English summary.

Before publishing, check that a reader can answer: What question does this address?
What did we actually find? Does this establish an investment edge? What remains
uncertain? What happens next? Verify that counts reconcile, links work, overlapping
groups are labelled, and no proposed research choice is presented as settled.
