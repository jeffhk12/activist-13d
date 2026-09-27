"""Tier: 2. Verify frozen evidence and replay pre-event coverage after formatting.

Inputs: original provenance, supplemental provenance, schedules and assignments.
Outputs: immutable formatting receipt and current source snapshots.
Identity: each preserved SHA equals receipt; replayed coverage equals frozen JSON.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_eligibility_closeout_verify.py
"""

import json

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.phase1_eligibility_closeout_audit import coverage

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-eligibility-closeout-v1"
checks = 0
for name in ["provenance.json", "supplemental-provenance.json"]:
    receipt = json.loads((OUT / name).read_text())
    for path, expected in receipt["outputs"].items():
        assert digest(OUT / path) == expected
        checks += 1
selection = json.loads((BASE / "20260924-rebuilt-inputs-v2/selection.json").read_text())
assignments = json.loads((BASE / "20260924-rebuilt-inputs-v2/assignments.json").read_text())
expected_events = json.loads((OUT / "pre-event-events.json").read_text())
expected_tables = json.loads((OUT / "pre-event-coverage.json").read_text())["tables"]
replayed = 0
for branch, plans in selection["plans"].items():
    for horizon, events in plans.items():
        detail, table = coverage(events, assignments)
        assert detail == expected_events[branch][horizon]
        assert table == expected_tables[branch][horizon]
        replayed += len(events)
sources = [
    ROOT / "src/activist13d/phase1_eligibility_closeout_audit.py",
    ROOT / "tests/test_phase1_eligibility_closeout_audit.py",
    *sorted((ROOT / "scripts/data_collection").glob("phase1_eligibility_closeout_*.py")),
]
for path in sources:
    freeze(OUT / "code-formatted-v1" / path.name, path.read_bytes())
freeze(
    OUT / "formatting-receipt-v1.json",
    encode(
        dict(
            change="ruff formatting/import sorting and ambiguous scratch variable rename only; original source snapshots retained",
            frozen_hash_checks=checks,
            pre_event_rows_replayed=replayed,
            source_sha256={str(p.relative_to(ROOT)): digest(p) for p in sources},
            report_sha256=digest(
                ROOT / "research/docs/phase1_eligibility_closeout_report_20260924.md"
            ),
        )
    ),
)
print(f"{checks} frozen hashes verified; {replayed} event rows replayed exactly.")
