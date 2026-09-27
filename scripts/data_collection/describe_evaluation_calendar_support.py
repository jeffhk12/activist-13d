"""Tier: 1. Count a calendar-only subset supported by observed market-date coverage.
Inputs: frozen candidate requirements and input QA date cutoff. Outputs: counts.
Identity: subset uses planned exit <= common observed date, never return values.
This is a scope alternative, not an activated evaluation or sample replacement.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/describe_evaluation_calendar_support.py
"""

import json
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-evaluation-calendar-support-v1"


def main():
    reqpath = BASE / "20260924-evaluation-inputs-v1/requirements.json"
    qapath = BASE / "20260924-evaluation-inputs-qa-v1/summary.json"
    assignpath = BASE / "20260924-evaluation-inputs-v1/assignments.json"
    req = json.loads(reqpath.read_text())
    qa = json.loads(qapath.read_text())
    assignments = json.loads(assignpath.read_text())
    cutoff = qa["last_nonempty_date"]
    counts = {}
    candidates = {}
    for b, pp in req["plans"].items():
        counts[b] = {}
        candidates[b] = {}
        for h, events in pp.items():
            eligible = [e for e in events if e["exit"] <= cutoff]
            candidates[b][h] = [{k: v for k, v in e.items() if k != "days"} for e in eligible]
            counts[b][h] = dict(
                original_scheduled=len(events),
                calendar_supported=len(eligible),
                focused=sum(e["focused"] for e in eligible),
                benchmark_assigned=sum(
                    assignments[e["input_key"]]["status"] == "matched" for e in eligible
                ),
                focused_benchmark_assigned=sum(
                    e["focused"] and assignments[e["input_key"]]["status"] == "matched"
                    for e in eligible
                ),
            )
            assert len(eligible) + sum(e["exit"] > cutoff for e in events) == len(events)
    summary = dict(
        status="unactivated_calendar_scope_alternative",
        terminal_date=cutoff,
        performance_calculated=False,
        changes_original_sample=False,
        counts=counts,
        limitation="Scope determined by planned dates and common source coverage, not future returns. Present records and matched benchmarks do not prove usable returns; portfolio still needs an explicit final freeze.",
    )
    freeze(OUT / "summary.json", encode(summary))
    freeze(OUT / "candidate-metadata.json", encode(candidates))
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in [reqpath, qapath, assignpath]},
                outputs={
                    p.name: digest(p)
                    for p in OUT.iterdir()
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    print(encode(summary))


if __name__ == "__main__":
    main()
