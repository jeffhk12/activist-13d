"""Tier: 1. Freeze delegation handoff and initial validation evidence.
Inputs: user-authorized handoff, baseline test log, protected-asset receipt.
Outputs: task manifest and initial check receipt. Identity: active is not completed.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_completion_receipt.py
"""

from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

OUT = ROOT / "research/runs/phase1-baseline/20260924-completion-integration-v1"


def main():
    handoff = ROOT / "research/docs/PHASE1-COMPLETION-TEAM-HANDOFF-20260924.md"
    receipt = dict(
        authorization="User requested a detailed handoff and fresh subagents to complete remaining Phase 1 work.",
        handoff=str(handoff.relative_to(ROOT)),
        handoff_sha256=digest(handoff),
        agents=[
            dict(
                name="/root/valuation_completion", assignment="Valuation and portfolio completion"
            ),
            dict(
                name="/root/eligibility_completion",
                assignment="Eligibility, identity and pre-event coverage",
            ),
            dict(
                name="/root/evaluation_readiness",
                assignment="Strategy and outcome-blind evaluation readiness",
            ),
        ],
        initial_status="agents_active; no new evaluation opened",
        protected_assets_sha256=digest(OUT / "protected-assets.json"),
        initial_validation="156 passed, 1 deselected; non-network suite",
        completion_rule="Do not claim fresh evaluation or Phase 1 completion until all required gates pass.",
    )
    freeze(OUT / "delegation.json", encode(receipt))
    freeze(OUT / "baseline-tests.txt", Path("/tmp/phase1-completion-suite.log").read_bytes())
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())


if __name__ == "__main__":
    main()
