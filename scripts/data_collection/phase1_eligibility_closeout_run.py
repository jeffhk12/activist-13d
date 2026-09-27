"""Independent source, history, identity and pre-event coverage closeout.

Inputs: frozen v3 universe, v1 canonical audit, fixed identity candidate lists,
and rebuilt development schedules/assignments. No outcome input is opened.
Outputs: separate immutable closeout JSON, evidence text and provenance.
Identity: history is strictly prior-only; all universe rows and unresolved cases
remain accounted for. Tier: 2; conventions/tests in closeout audit module.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_eligibility_closeout_run.py
"""

import gzip
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from lxml import html
from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.initial_eligibility import mark_history, normalized_form
from activist13d.initial_eligibility_v3 import classify
from activist13d.local_paths import resolve_project_path
from activist13d.phase1_eligibility_closeout_audit import CONVENTIONS, coverage

BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-eligibility-closeout-v1"
UNIVERSE = BASE / "20260924-universe-rebuild-v3/eligibility.jsonl"
AUDIT = BASE / "20260924-universe-rebuild-v1/audit.sqlite"
INPUT = BASE / "20260924-rebuilt-inputs-v2"
HFR = ROOT / "research/runs/hfr-all-managers/20260924-v1/candidates.json"
SUP = ROOT / "research/runs/investor-identity/20260924-supplemental-v1/candidates.json"


def raw_primary(raw):
    text = raw.decode("utf-8", errors="replace")
    blocks = []
    for block in re.findall(r"<DOCUMENT>\s*(.*?)</DOCUMENT>", text, re.S | re.I):
        typ = re.search(r"^<TYPE>([^\n]+)", block, re.M)
        name = re.search(r"^<FILENAME>([^\n]+)", block, re.M)
        if (
            typ
            and name
            and normalized_form(typ[1]) in {"13D", "13D/A"}
            and not name[1].lower().endswith((".pdf", ".jpg", ".png"))
        ):
            body = re.search(r"<TEXT>\s*(.*?)</TEXT>", block, re.S | re.I)
            if body:
                blocks.append((typ[1].strip(), name[1].strip(), body[1]))
    if len(blocks) != 1:
        return None
    typ, name, body = blocks[0]
    tree = html.fromstring(body)
    for node in tree.xpath("//script|//style"):
        node.drop_tree()
    canonical = re.sub(r"\s+", " ", " ".join(tree.itertext())).strip()
    return dict(document_form=typ, filename=name, text=canonical)


def main():
    rows = [json.loads(s) for s in UNIVERSE.read_text().splitlines()]
    db = sqlite3.connect(f"file:{AUDIT}?mode=ro", uri=True)
    lookup = {r["accession"]: r for r in rows}
    # Sample is frozen by status and accession hash, independent of returns.
    strata = defaultdict(list)
    for r in rows:
        if not r["status"].startswith("unresolved"):
            stratum = (
                "body_override"
                if r.get("body_overrides_initial")
                else r["status"] + "|" + r["campaign_status"]
            )
            strata[stratum].append(r)
    sample = []
    for key, rr in sorted(strata.items()):
        sample.extend(
            (key, r)
            for r in sorted(
                rr,
                key=lambda r: hashlib.sha256(
                    ("eligibility-closeout-v1|" + r["accession"]).encode()
                ).hexdigest(),
            )[:5]
        )
    selected = {r["accession"] for _, r in sample}
    dispositions = []
    sample_records = []
    replay = Counter()
    prior_checks = Counter()
    for r in rows:
        a = r["accession"]
        text = gzip.decompress(
            db.execute("select canonical_gzip from audit where accession=?", (a,)).fetchone()[0]
        ).decode()
        if text:
            assert hashlib.sha256(text.encode()).hexdigest() == r["canonical_sha256"]
            for span in r["amendment_evidence"] + r["prior_history"]:
                assert text[span["start"] : span["end"]] == span["quote"]
                replay["valid_spans"] += 1
            if not (r.get("body_overrides_initial") and not r["amendment_evidence"]):
                result = classify(text, [r["metadata_form"], r["header_form"], r["document_form"]])
                assert (
                    result["status"] == r["status"]
                    and result["prior_history"] == r["prior_history"]
                )
                replay["classification_replayed"] += 1
            else:
                replay["xml_amendment_requires_raw_replay"] += 1
        for previous in r["prior_accessions"]:
            p = lookup[previous]
            assert (p["accepted"] or p["filing_date"] + "T23:59:59") < (
                r["accepted"] or r["filing_date"] + "T23:59:59"
            )
            assert set(p["issuers"]) & set(r["issuers"]) and set(p["identity_keys"]) & set(
                r["identity_keys"]
            )
            keys = set(p["identity_keys"]) & set(r["identity_keys"])
            prior_checks["prior_edges"] += 1
            prior_checks[
                "manager_only_edges"
                if all(not k.startswith("CIK:") for k in keys)
                else "includes_reporter_cik"
            ] += 1
        if a in selected:
            freeze(OUT / "sample-text" / f"{a}.txt", text)
            sample_records.append(
                dict(
                    accession=a,
                    status=r["status"],
                    campaign_status=r["campaign_status"],
                    body_overrides_initial=r.get("body_overrides_initial", False),
                    source_sha256=r["source_sha256"],
                    canonical_sha256=r["canonical_sha256"],
                    source_path=r["source_path"],
                    amendment_evidence=r["amendment_evidence"],
                    prior_history=r["prior_history"],
                )
            )
        if r["status"].startswith("unresolved"):
            p = resolve_project_path(r["source_path"], ROOT)
            side = p.with_name(p.name + ".meta.json")
            d = dict(
                accession=a,
                status=r["status"],
                metadata_form=r["metadata_form"],
                filing_date=r["filing_date"],
                manager_keys=r["manager_keys"],
                source_path=r["source_path"],
                expected_sha256=r["source_sha256"],
                expected_bytes=r["source_bytes"],
                raw_exists=p.exists(),
                sidecar_exists=side.exists(),
                prior_accessions=r["prior_accessions"],
            )
            if text:
                d.update(
                    disposition="conversion_requires_reporting_history_adjudication",
                    canonical_sha256=r["canonical_sha256"],
                    cover_quote=text[:750],
                )
                freeze(OUT / "unresolved-text" / f"{a}.txt", text)
            elif p.exists():
                raw = p.read_bytes()
                valid = (
                    hashlib.sha256(raw).hexdigest() == r["source_sha256"]
                    and len(raw) == r["source_bytes"]
                )
                d.update(
                    raw_hash_size_verified=valid,
                    disposition="intact_raw_missing_retrieval_sidecar"
                    if valid
                    else "raw_integrity_failure",
                )
                if valid:
                    primary = raw_primary(raw)
                    if primary:
                        freeze(OUT / "unresolved-text" / f"{a}.txt", primary["text"])
                        d.update(
                            canonical_sha256=hashlib.sha256(primary["text"].encode()).hexdigest(),
                            cover_quote=primary["text"][:750],
                            diagnostic_only_form=classify(
                                primary["text"], [r["metadata_form"], primary["document_form"]]
                            )["status"],
                        )
            else:
                d["disposition"] = "missing_raw_submission"
                if side.exists():
                    meta = json.loads(side.read_text())
                    d["existing_receipt"] = meta
                    d["sidecar_sha256"] = digest(side)
            dispositions.append(d)
    replayed = mark_history(rows)
    assert {r["accession"]: (r["campaign_status"], r["prior_accessions"]) for r in replayed} == {
        r["accession"]: (r["campaign_status"], r["prior_accessions"]) for r in rows
    }
    replay["history_rows_replayed"] = len(rows)
    freeze(OUT / "unresolved-dispositions.json", encode(dispositions))
    freeze(
        OUT / "source-sample.json",
        encode(
            dict(
                rule="five lowest SHA256(eligibility-closeout-v1|accession) per status/history stratum; body overrides own stratum; diagnostic non-outcome sample, not precision/recall estimate",
                records=sample_records,
            )
        ),
    )
    # Independently reconstruct fixed manager keys, preserving candidate status.
    expected = defaultdict(set)
    identity = Counter()
    for path, prefix, field in [(HFR, "HFR:", "firm_id"), (SUP, "Supplement:", "manager")]:
        for r in json.loads(path.read_text()):
            for m in r["matches"]:
                expected[r["accession"]].add(prefix + m[field])
            identity[prefix + "candidate_records"] += 1
            identity[prefix + "not_strictly_prior_snapshot"] += bool(
                r.get("snapshot_not_strictly_before_acceptance_date")
            )
    for r in rows:
        assert set(r["manager_keys"]) == expected[r["accession"]]
    identity["universe_exact_key_joins"] = len(rows)
    for r in rows:
        if r["status"] == "standalone_initial_candidate":
            identity["initial_with_manager_keys"] += bool(r["manager_keys"])
            if r["campaign_status"] == "previously_observed_pair":
                previous = [lookup[a] for a in r["prior_accessions"]]
                cik_prior = any(set(r["reporter_ciks"]) & set(p["reporter_ciks"]) for p in previous)
                identity[
                    "initial_prior_pair_with_cik_overlap"
                    if cik_prior
                    else "initial_prior_pair_candidate_manager_only"
                ] += 1
    selection = json.loads((INPUT / "selection.json").read_text())
    assignments = json.loads((INPUT / "assignments.json").read_text())
    tables = {}
    detail = {}
    funnel = {}
    for branch, plans in selection["plans"].items():
        tables[branch] = {}
        detail[branch] = {}
        funnel[branch] = dict(
            selected_filings=len(selection["selected"][branch]),
            eligibility_exclusions=dict(
                Counter(r["reason"] for r in selection["exclusions"][branch]["eligibility"])
            ),
            schedules={},
        )
        for horizon, events in plans.items():
            detail[branch][horizon], tables[branch][horizon] = coverage(events, assignments)
            drops = selection["exclusions"][branch]["schedule"][horizon]
            funnel[branch]["schedules"][horizon] = dict(
                events=len(events),
                accessions_in_events=sum(len(e["accessions"]) for e in events),
                exclusions=dict(Counter(r["reason"] for r in drops)),
            )
            assert sum(len(e["accessions"]) for e in events) + len(drops) == len(
                selection["selected"][branch]
            )
    freeze(OUT / "pre-event-coverage.json", encode(dict(conventions=CONVENTIONS, tables=tables)))
    freeze(OUT / "pre-event-events.json", encode(detail))
    freeze(
        OUT / "development-funnel.json",
        encode(
            dict(
                base_exclusions=dict(Counter(r["reason"] for r in selection["base_exclusions"])),
                branches=funnel,
            )
        ),
    )
    summary = dict(
        universe_records=len(rows),
        unresolved_records=len(dispositions),
        dispositions=dict(Counter(d["disposition"] for d in dispositions)),
        sample_records=len(sample_records),
        replay=dict(replay),
        history_edges=dict(prior_checks),
        identity=dict(identity),
        six_month_coverage={
            b: tables[b]["126"][:1] + [x for x in tables[b]["126"] if x["dimension"] == "cohort"]
            for b in tables
        },
    )
    freeze(OUT / "summary.json", encode(summary))
    sources = [UNIVERSE, AUDIT, INPUT / "selection.json", INPUT / "assignments.json", HFR, SUP]
    for p in [
        Path(__file__),
        ROOT / "src/activist13d/phase1_eligibility_closeout_audit.py",
        ROOT / "tests/test_phase1_eligibility_closeout_audit.py",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in sources},
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    print(encode(summary))


if __name__ == "__main__":
    main()
