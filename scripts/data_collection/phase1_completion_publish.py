"""Tier: 0. Publish reviewed closeout navigation and a precise continuation handoff.
Inputs: integrated closeout report. Outputs: home/plan links and dated status note.
Identity: preserve prior reports and distinguish research closeout from confirmation.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_completion_publish.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    note = """# Phase 1 completion status and continuation handoff

24 September 2026. Three fresh agents completed independent work from the detailed written handoff, without inheriting the earlier conversation. Root reviewed their source evidence and integrated the results. **The investigations are complete; Phase 1 confirmation is not complete.** No new candidate future outcomes were opened.

[Open the combined report](/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-completion-integration-v1/index.html).

## Investment meaning

The unchanged development baseline averages +0.28 percentage points versus Russell ETFs at six months and +7.08 at twelve months across 54 focused mechanically first-observed events each. Both uncertainty ranges include zero. The stricter branch must now be described as archive-relative pairs with conservative, unvalidated history-reference exclusions, not a fully validated first-campaign census.

The $100m six-month portfolio's $12.361m total gain over 2018–2023 includes $11.731m cash interest. This is not evidence of a large deployable equity-selection edge. The $100k six-/twelve-month portfolios still lack a complete daily valuation series.

## Completed and verified

1. Valuation: diagnosed Hill's exchange suspension/OTC interval using contemporaneous issuer/NYSE evidence and CRSP definitions. NT means Not Tracked and X Unknown or Unavailable, correcting the earlier report's no-trading implication. Checked 12,107 overlapping schedules; 121 potential gap schedules represent 29 accessions/26 securities. Hill is the only focused affected security. All 36 portfolios replay exactly; 24 complete, 12 retain refusal. Hypothetical mark scenarios are isolated exposure illustrations, not terminal-return bounds.
2. Eligibility: complete disposition of 45 unresolved filings (18 intact raw files missing retrieval sidecars, 11 missing submissions, 16 conversion questions); deterministic 35-case source sample; all 24 development text-history cases reviewed. Assistant interpretations judge 14 supportive contexts, eight non-supporting lexical matches and two ambiguous. All exclusions retained; no accession-specific restoration, human labels, or return-informed investor change. Removing two same-day HFR proxy keys changes no history statuses and affects neither selected development branch.
3. Coverage: 709/1,981 six-month first-pair schedules have benchmark assignments, including 55/62 focused versus 639/1,892 other/unresolved events. Potential five-company control matches cover 19/62 focused, 13 of those in SIC 73. These pre-outcome counts differ from 54 calculable focused outcomes because of one missing stock return.
4. Evaluation: outcome-blind candidate protocol, selection code, exposure inventory and explicit gates. Conservative six-month candidate pool has 700 first-pair events, 653 companies, eight focused events. Date-only plus protected comparator has 925/12. The conservative issuer quarantine changes the estimand toward companies absent from prior development selection. Ten previously previewed companies were not already among the 207 human-protected issuers. No sample is certified untouched.
5. Input inventory: 172/174 primary dates missing from the older feasibility inventory actually have cached full-date CRSP requests/payload files. Only 2025-04-08 and 2025-12-17 lack matching requests in 4,928 scanned sidecars. This is metadata presence, not usable rows or integrity. No future-return rows were opened.
6. Root validation: 176 non-network tests passed, one deselected; new core modules/tests pass lint. All 554 protected investor/human assets match initial hashes. Passing code checks does not establish semantic correctness, complete market data or an investment edge.

## Artifacts and exact replay paths

- [Original detailed team handoff](PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md): sources, fixed definitions, ownership, user constraints and acceptance criteria.
- `research/runs/phase1-baseline/20260924-completion-integration-v1`: combined HTML, final-status.json, protected-asset manifest and test receipts.
- `20260924-valuation-resolution-v1`: source-rich phase1_valuation_report.md, gap inventory, capacity attribution, isolated scenarios. `20260924-valuation-resolution-v2`: source-only CI cleanup, analytical equality proof, repeatable verifier and preserved v1 source replay instructions. Read phase1_valuation_ci_closeout.md before replaying older code; v1 original files remain intact.
- `20260924-eligibility-closeout-v1`: source sample, 45 dispositions, all 24 history contexts, explicitly marked assistant interpretations, pre-event coverage, identity timing and verification. Read `research/docs/phase1_eligibility_closeout_report_20260924.md`. Original and formatted source snapshots plus formatting-receipt-v1.json preserve replay provenance.
- `20260924-evaluation-readiness-v1`: HANDOFF.md, candidate-selection.json, gates.json, manifest.json, metadata exposure audit. `receipts/SUPPLEMENT.md` and `receipts/source-cleanup-v1/provenance.json` document cache follow-up and source-only cleanup. Original source bytes are in receipts/source-cleanup-v1/preformat/. Use phase1_evaluation_readiness_cleanup_receipt.py for the current replay; the original verifier intentionally refuses changed live source hashes.
- `research/protocol/phase1-evaluation-candidate-v1.md` is a preserved DRAFT. It is not the final rule/sample freeze or authorization to open outcomes.

Run identifiers above are under `research/runs/phase1-baseline/`. Active scripts are in `scripts/data_collection/`; pure modules/tests use phase1_valuation, phase1_eligibility_closeout and phase1_evaluation_readiness prefixes. Run from `/Users/jefflu/Projects/activist-13d` using `.venv/bin/python` with `PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8`. Read agent replay instructions before rerunning a version whose source was reformatted; never overwrite frozen outputs to make hashes agree.

## What still must happen before confirmation

- Obtain auditable HILI/HIL OTC daily prices/quotes, corporate actions and execution liquidity for 2018-08-14 through 2018-10-17, with boundary identity. A single endpoint quote does not complete daily accounting. Any general policy change must be frozen and replayed across affected holdings.
- Validate current-issuer/current-reporter attribution for history references, or explicitly choose a conservative exclusion-based estimand. The present semantic review is not a human training/reference label set. Do not restore named cases based on returns.
- Prepare benchmark, price, cash and liquidity sources for the final candidate cohort. Historical Russell receipts currently end 2022-11-30. Request-file presence cannot certify individual stock data, constituent completeness or contemporaneous availability.
- Freeze rules, sample, terminal dates, inference and source inventories. A limited historical temporal-validation exercise must state incomplete exposure provenance. A truly prospective cohort begins after the actual final freeze and needs future holding-period observations to mature.

Continue these source/definition tasks before opening new outcomes. No Phase 2/3 training yet. Investor membership, human worksheets and 207 protected issuers remain unchanged. Preserve all previous analyses as development history. Report a negative or inconclusive finding honestly; do not tune toward positive returns.
"""
    path = ROOT / "research/docs/PHASE1-COMPLETION-STATUS-20260924.md"
    if path.exists():
        assert path.read_text() == note
    else:
        path.write_text(note)
    home = ROOT / "START-HERE.html"
    text = home.read_text()
    section = """<section><h2>Current: independent Phase 1 closeout</h2><p>Three fresh agents completed valuation, eligibility/coverage, and evaluation-readiness reviews. The development estimates are unchanged, but campaign-history interpretation is narrower. Missing OTC valuations, selective coverage and an uncertified later sample prevent fresh confirmation.</p><p>The later conservative candidate pool contains only eight focused six-month events. No fresh returns were opened. All 554 protected investor/human assets remain unchanged; 176 non-network tests pass.</p><a class="button" href="research/runs/phase1-baseline/20260924-completion-integration-v1/index.html">Read the combined findings</a><a href="research/docs/PHASE1-COMPLETION-STATUS-20260924.md">Detailed continuation handoff</a><p><a href="research/docs/PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md">Original team assignments and source map</a></p></section>\n"""
    if "20260924-completion-integration-v1/index.html" not in text:
        text = text.replace("<section>", section + "<section>", 1)
    text = text.replace(
        "Current: rebuilt initial events, matched peers and portfolio accounting",
        "Development baseline: rebuilt events and portfolio accounting",
    )
    home.write_text(text)
    plan = ROOT / "research/docs/PROJECT-PLAN.md"
    text = plan.read_text()
    addition = """**Independent closeout completed; confirmation remains not ready.** [Combined status and continuation handoff](PHASE1-COMPLETION-STATUS-20260924.md) integrates three fresh agents. Hill's missing interval is OTC trading not tracked by CRSP; daily valuation/execution data remain unavailable. Of 24 development history-reference exclusions, eight are non-supporting lexical matches and two ambiguous, so retain exclusions but narrow the campaign interpretation. Later conservative candidates include only eight focused six-month events and are not certified untouched. Existing returns, investor membership and human labels are unchanged. No fresh outcomes opened. Complete the precise source/attribution/input/freeze dependencies in the handoff before confirmation.\n\n"""
    if "Independent closeout completed" not in text:
        text = text.replace(
            "## Current direction — September 24, 2026\n\n",
            "## Current direction — September 24, 2026\n\n" + addition,
        )
    plan.write_text(text)


if __name__ == "__main__":
    main()
