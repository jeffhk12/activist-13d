"""Tier: 2. Verify frozen scope and construct an outcome panel from cached sources.
Inputs: approved historical sample, raw-date receipts, frozen accounting code.
Outputs: access registration, code/environment snapshot, selected panel/receipts.
Identity: source SHA and selected date/security keys precede numeric outcome use.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/prepare_phase1_historical_execution.py
"""

import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from run_phase1_development import FIELDS, INPUT, ROOT, digest, encode, freeze, read_page

from activist13d.evaluation_input_checks import daily_keys

BASE = ROOT / "research/runs/phase1-baseline"
DECISION = BASE / "20260924-historical-decision-freeze-v1"
PREP = BASE / "20260924-evaluation-inputs-v2"
OUT = BASE / "20260924-historical-execution-inputs-v1"


def main():
    manifest = json.loads((DECISION / "manifest.json").read_text())
    for kind, base in [("inputs", ROOT), ("outputs", DECISION)]:
        for rel, sha in manifest[kind].items():
            assert digest(base / rel) == sha, rel
    guard = BASE / "20260924-completion-integration-v1/protected-assets.json"
    for rel, sha in json.loads(guard.read_text()).items():
        assert digest(ROOT / rel) == sha, rel
    for folder in [
        PREP,
        BASE / "20260924-evaluation-inputs-etf-v1",
        BASE / "20260924-evaluation-inputs-qa-v1",
    ]:
        prov = json.loads((folder / "provenance.json").read_text())
        for rel, sha in prov["outputs"].items():
            assert digest(folder / rel) == sha, rel
        for rel, sha in prov["inputs"].items():
            assert digest(ROOT / rel) == sha, rel
    plans = json.loads((DECISION / "selection.json").read_text())
    original_assign = json.loads((PREP / "assignments.json").read_text())
    sessions = json.loads((INPUT / "entry-calendar.json").read_text())
    assignments, needed = {}, defaultdict(set)
    focused = set()
    for pp in plans.values():
        for events in pp.values():
            for e in events:
                a = original_assign[e["input_key"]]
                sic = a["siccd"]
                industry = str(int(sic)).zfill(4)[:2] if sic is not None else None
                assignments[e["input_key"]] = dict(a, industry=industry)
                for d in e["days"] + a["advdays"]:
                    needed[d].add(e["permno"])
                if e["focused"]:
                    focused.add(e["permno"])
    begin = sessions.index("2024-01-02") - 20
    for day in sessions[begin:]:
        if day > "2025-12-31":
            break
        needed[day].update(focused | {84398, 88221, 88222, 89059, 88223})
    sources = {r["day"]: r for r in json.loads((PREP / "daily-source-coverage.json").read_text())}
    assert all(d in sources and sources[d]["status"] == "source_verified" for d in needed)
    identities = json.loads(
        (BASE / "20260924-evaluation-inputs-etf-v1/identity-coverage.json").read_text()
    )
    assert len(identities) == 5 and all(
        r["covered_sessions"] == 502 and r["last_verified_date"] == "2025-12-31" for r in identities
    )
    code = [Path(__file__), ROOT / "scripts/data_collection/run_phase1_historical_validation.py"]
    code += sorted((ROOT / "src/activist13d").glob("*.py"))
    code += [ROOT / "scripts/data_collection/run_phase1_development.py"]
    for path in code:
        freeze(OUT / "code" / path.relative_to(ROOT), path.read_bytes())
    freeze(
        OUT / "environment.json",
        encode(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": json.loads(
                    subprocess.check_output(
                        [sys.executable, "-m", "pip", "list", "--format=json"], text=True
                    )
                ),
            }
        ),
    )
    freeze(OUT / "selection.json", encode({"plans": plans}))
    freeze(OUT / "assignments.json", encode(assignments))
    freeze(OUT / "required-keys.json", encode({d: sorted(v) for d, v in sorted(needed.items())}))
    access = OUT / "outcome-access-0001.json"
    if not access.exists():
        freeze(
            access,
            encode(
                {
                    "actual_utc": datetime.now(timezone.utc).isoformat(),
                    "purpose": "First numerical access for authorized limited historical validation; validate return chains and accounting",
                    "window": ["2024-01-02", "2025-12-31"],
                    "historical_liquidity_before_entry_included": True,
                    "sample_sha256": digest(DECISION / "selection.json"),
                    "protocol_sha256": digest(
                        ROOT / "research/protocol/phase1-historical-validation-v1.md"
                    ),
                    "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in code},
                    "fresh_confirmation": False,
                }
            ),
        )
    else:
        for rel, sha in json.loads(access.read_text())["code_hashes"].items():
            assert digest(ROOT / rel) == sha, rel
    # Access receipt and source snapshot exist before numerical fields are selected.
    panel, inventory, missing = defaultdict(dict), {}, []
    for i, (day, nums) in enumerate(sorted(needed.items())):
        payload, _ = read_page(ROOT / sources[day]["source"], inventory)
        keyed = daily_keys(payload, day)
        for n in nums:
            if n in keyed:
                panel[n][day] = {k: keyed[n].get(k) for k in FIELDS}
            else:
                missing.append({"day": day, "permno": n})
        if i % 100 == 0:
            print("Verified historical source dates", i + 1, "/", len(needed), flush=True)
    freeze(OUT / "panel.json", encode(panel))
    freeze(OUT / "missing-keys.json", encode(missing))
    freeze(OUT / "source-inventory.json", encode(inventory))
    inputs = [
        DECISION / "manifest.json",
        DECISION / "selection.json",
        PREP / "provenance.json",
        PREP / "daily-source-coverage.json",
        PREP / "assignments.json",
        INPUT / "entry-calendar.json",
        guard,
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            {
                "inputs": {str(p.relative_to(ROOT)): digest(p) for p in inputs},
                "outputs": {
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            }
        ),
    )
    print(
        "Panel prepared with explicit missing-key receipts; no event exclusions added.", flush=True
    )


if __name__ == "__main__":
    main()
