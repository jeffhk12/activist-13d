"""Tier: 1. Activate the user-approved date-only historical evaluation scope.
Inputs: frozen requirements, earlier date-only counts, protocol, protected manifest.
Outputs: exact selected/excluded schedules, hashes, decision and exposure records.
Identity: selected = original scheduled events with planned exit <= 2025-12-31.
No numerical outcomes are read. Re-run verifies identical frozen outputs.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/freeze_phase1_historical_decisions.py
"""

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-historical-decision-freeze-v1"
PROTOCOL = ROOT / "research/protocol/phase1-historical-validation-v1.md"


def main():
    reqpath = BASE / "20260924-evaluation-inputs-v2/requirements.json"
    alternative = BASE / "20260924-evaluation-calendar-support-v1/candidate-metadata.json"
    countpath = BASE / "20260924-evaluation-calendar-support-v1/summary.json"
    guardpath = BASE / "20260924-completion-integration-v1/protected-assets.json"
    req = json.loads(reqpath.read_text())
    expected = json.loads(alternative.read_text())
    counts = json.loads(countpath.read_text())["counts"]
    for rel, sha in json.loads(guardpath.read_text()).items():
        assert digest(ROOT / rel) == sha, rel
    selected, excluded = {}, {}
    for branch, horizons in req["plans"].items():
        selected[branch], excluded[branch] = {}, {}
        for horizon, events in horizons.items():
            keep = [e for e in events if e["exit"] <= "2025-12-31"]
            drop = [e for e in events if e["exit"] > "2025-12-31"]
            assert [{k: v for k, v in e.items() if k != "days"} for e in keep] == expected[branch][
                horizon
            ]
            assert len(keep) + len(drop) == len(events)
            assert len(keep) == counts[branch][horizon]["calendar_supported"]
            assert all(e["entry"] >= "2024-01-01" for e in keep)
            selected[branch][horizon], excluded[branch][horizon] = keep, drop
    assert len(selected["first_observed"]["126"]) == 503
    assert sum(e["focused"] for e in selected["first_observed"]["126"]) == 6
    freeze(OUT / "selection.json", encode(selected))
    freeze(OUT / "calendar-exclusions.json", encode(excluded))
    freeze(OUT / "coverage-counts.json", encode(counts))
    stamp = OUT / "freeze-time.json"
    if not stamp.exists():
        freeze(
            stamp,
            encode(
                {
                    "actual_utc": datetime.now(timezone.utc).isoformat(),
                    "meaning": "Historical decision/sample freeze, not prospective launch",
                }
            ),
        )
    exposure = {
        "classification": "historical_temporal_validation_with_incomplete_exposure_provenance",
        "known_controls": "Inherited human-protected, development-issuer, preview-issuer/security and smoke-test quarantine in fixed requirements",
        "known_prior_work": "Outcome-aware development, prior screens/previews, metadata and pre-entry liquidity preparation",
        "unknown": "Complete prior outcome access across conversations, scratch output and other machines cannot be certified",
        "fresh_confirmation_eligible": False,
        "new_numeric_outcomes_read_by_this_run": False,
    }
    freeze(OUT / "exposure-record.json", encode(exposure))
    freeze(
        OUT / "execution-status.json",
        encode(
            {
                "decision_and_sample_frozen": True,
                "historical_validation_authorized_by_user": True,
                "original_fresh_gates_overridden": False,
                "production_runner_frozen": False,
                "numeric_return_and_settlement_validation": "pending",
                "complete_portfolio_claim_allowed_now": False,
                "next": "Snapshot and verify historical runner, check manifests, record first numerical access, then validate returns and settlement before reporting performance",
                "prospective_collection_started": False,
            }
        ),
    )
    paths = [
        reqpath,
        alternative,
        countpath,
        guardpath,
        PROTOCOL,
        ROOT / "research/protocol/phase1-evaluation-candidate-v1.md",
        ROOT / "research/protocol/phase1-rebuild-v1.md",
        ROOT / "research/docs/PHASE1-PROSPECTIVE-TEST-PLAN-20260924.md",
        BASE / "20260924-evaluation-inputs-v2/provenance.json",
        BASE / "20260924-evaluation-inputs-etf-v1/provenance.json",
        BASE / "20260924-evaluation-inputs-qa-v1/provenance.json",
    ]
    code = [
        Path(__file__),
        ROOT / "scripts/data_collection/run_phase1_development.py",
        ROOT / "scripts/data_collection/run_rebuilt_analysis.py",
        ROOT / "scripts/data_collection/run_phase1_skip_hill.py",
        ROOT / "src/activist13d/portfolio_accounting.py",
        ROOT / "src/activist13d/phase1_baseline.py",
        ROOT / "src/activist13d/matched_controls.py",
        ROOT / "src/activist13d/russell_benchmark.py",
    ]
    for path in code:
        freeze(OUT / "code" / path.relative_to(ROOT), path.read_bytes())
    freeze(
        OUT / "environment.json",
        encode(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "note": "Decision-run environment; production runner must snapshot installed dependencies before outcomes",
            }
        ),
    )
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest.json")
    freeze(
        OUT / "manifest.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in paths + code},
                "outputs": {str(p.relative_to(OUT)): digest(p) for p in files},
                "performance_calculated": False,
            }
        ),
    )
    print(
        "Historical sample frozen: 503 primary events, 6 focused; prior date-only selection reproduced exactly."
    )


if __name__ == "__main__":
    main()
