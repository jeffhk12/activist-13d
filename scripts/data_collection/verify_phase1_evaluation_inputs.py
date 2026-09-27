"""Tier: 2. Replay candidate input keys and distinguish missing-row causes.
Inputs: frozen requirements, raw daily hashes, source status and pre-event joins.
Outputs: input QA, calendar coverage and per-event missing-row diagnostics.
Identity: missing keys partition into empty-source, after delisting flag, unexplained.
Future numeric prices/returns remain unread; delisting settlement values unchecked.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_phase1_evaluation_inputs.py
"""

import bisect
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze, read_page

from activist13d.evaluation_input_checks import daily_keys
from activist13d.russell_benchmark import assign

BASE = ROOT / "research/runs/phase1-baseline"
RUN = BASE / "20260924-evaluation-inputs-v1"
OUT = BASE / "20260924-evaluation-inputs-qa-v1"


def main():
    prov = json.loads((RUN / "provenance.json").read_text())
    for rel, sha in prov["inputs"].items():
        assert digest(ROOT / rel) == sha, rel
    for rel, sha in prov["outputs"].items():
        assert digest(RUN / rel) == sha, rel
    req = json.loads((RUN / "requirements.json").read_text())
    daily = json.loads((RUN / "daily-source-coverage.json").read_text())
    stored = json.loads((RUN / "event-input-coverage.json").read_text())
    assignments = json.loads((RUN / "assignments.json").read_text())
    originals = json.loads(
        (BASE / "20260924-evaluation-readiness-v1/candidate-selection.json").read_text()
    )
    for b, pp in req["plans"].items():
        for h, events in pp.items():
            clean = [{k: v for k, v in e.items() if k != "input_key"} for e in events]
            assert clean == [
                e for e in originals["plans"][b][h]["events"] if e["issuer"] != "0001287808"
            ]
    observed = defaultdict(set)
    delist = defaultdict(set)
    empty = set()
    inventory = {}
    dates = []
    checked = 0
    for i, rec in enumerate(daily):
        d = rec["day"]
        needed = set(req["wanted"][d])
        assert rec["present"] + len(rec["missing"]) == len(needed)
        if rec["status"] != "source_verified":
            continue
        payload, _ = read_page(ROOT / rec["source"], inventory)
        keyed = daily_keys(payload, d)
        assert len(keyed) == rec["page_rows"]
        assert sorted(needed - set(keyed)) == rec["missing"]
        assert len(needed & set(keyed)) == rec["present"]
        if not keyed:
            empty.add(d)
        for n in needed & set(keyed):
            observed[n].add(d)
            if keyed[n].get("dlydelflg") == "Y":
                delist[n].add(d)
        dates.append(
            dict(
                day=d,
                market_rows=len(keyed),
                requested_key_count=len(needed),
                present_requested_keys=rec["present"],
            )
        )
        checked += len(needed)
        if i % 100 == 0:
            print("Replayed daily key coverage", i + 1, len(daily), flush=True)
    diagnostics = {}
    counts = {}
    for b, pp in req["plans"].items():
        diagnostics[b] = {}
        counts[b] = {}
        for h, events in pp.items():
            rows = []
            for e, saved in zip(events, stored[b][h], strict=True):
                assert e["accession"] == saved["accession"]
                missing = [d for d in e["days"] if d not in observed[e["permno"]]]
                assert missing == saved["absent_dates"]
                flagged = sorted(d for d in delist[e["permno"]] if e["entry"] <= d <= e["exit"])
                first_flag = flagged[0] if flagged else None
                causes = Counter()
                for d in missing:
                    if first_flag and d > first_flag:
                        causes["after_delisting_flag_settlement_unchecked"] += 1
                    elif d in empty:
                        causes["empty_market_source_date"] += 1
                    else:
                        causes["unexplained_missing_security_key"] += 1
                assert sum(causes.values()) == len(missing)
                a = assignments[e["input_key"]]
                assert (
                    a["snapshot"] < a["public"]
                    and a["pre"] < a["public"]
                    and max(a["advdays"]) < a["entry"]
                )
                if a["status"] == "matched":
                    assert assign(a["matched_rows"]) == (a["etf"], "matched")
                rows.append(
                    dict(
                        accession=e["accession"],
                        issuer=e["issuer"],
                        focused=e["focused"],
                        missing_key_sessions=len(missing),
                        first_delisting_flag=first_flag,
                        causes=dict(causes),
                        all_keys_present=not missing,
                    )
                )
            diagnostics[b][h] = rows
            counts[b][h] = dict(
                scheduled=len(rows),
                all_keys_present=sum(r["all_keys_present"] for r in rows),
                with_empty_market_dates=sum(
                    bool(r["causes"].get("empty_market_source_date")) for r in rows
                ),
                with_unexplained_missing_keys=sum(
                    bool(r["causes"].get("unexplained_missing_security_key")) for r in rows
                ),
                with_post_delisting_absences=sum(
                    bool(r["causes"].get("after_delisting_flag_settlement_unchecked")) for r in rows
                ),
                focused_all_keys_present=sum(r["focused"] and r["all_keys_present"] for r in rows),
                focused_with_empty_market_dates=sum(
                    r["focused"] and bool(r["causes"].get("empty_market_source_date")) for r in rows
                ),
                focused_with_unexplained_missing_keys=sum(
                    r["focused"] and bool(r["causes"].get("unexplained_missing_security_key"))
                    for r in rows
                ),
                focused_with_post_delisting_absences=sum(
                    r["focused"]
                    and bool(r["causes"].get("after_delisting_flag_settlement_unchecked"))
                    for r in rows
                ),
            )
    calendar = json.loads(
        (
            ROOT / "research/runs/phase1-baseline/20260924-feasibility-v2/entry-calendar.json"
        ).read_text()
    )
    cash = json.loads((RUN / "cash-readiness.json").read_text())
    for r in cash["days"]:
        i = bisect.bisect_left(calendar, r["day"])
        cutoff = (date.fromisoformat(calendar[i - 1]) - timedelta(days=2)).isoformat()
        assert r["observation"] is None or r["observation"] <= cutoff
        if r["status"] == "available":
            assert r["age_days"] <= 10
    summary = dict(
        status="passed_key_and_input_replay",
        future_numeric_prices_returns_inspected=False,
        performance_calculated=False,
        selection_equal_to_frozen_candidate_excluding_hill=True,
        required_daily_key_checks=checked,
        daily_sources_replayed=len(dates),
        empty_source_dates=len(empty),
        first_empty_date=min(empty) if empty else None,
        last_nonempty_date=max(r["day"] for r in dates if r["market_rows"]),
        branches=counts,
        cash_days_checked=len(cash["days"]),
        limitations="A present row is not a valid total return or executable price. A delisting flag is not a validated settlement. Date-coverage and exposure/selection gates remain distinct.",
    )
    freeze(OUT / "summary.json", encode(summary))
    freeze(OUT / "missing-key-diagnostics.json", encode(diagnostics))
    freeze(OUT / "calendar-coverage.json", encode(dates))
    freeze(OUT / Path(__file__).name, Path(__file__).read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={
                    str(RUN.relative_to(ROOT)) + "/provenance.json": digest(RUN / "provenance.json")
                },
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
