"""Tier: 2. Source-verify and reconcile the complete parsed filing universe.
Inputs: read-only SEC SQLite, immutable raw submissions, frozen HFR/supplement.
Outputs: resumable new SQLite canonical audit and chronological eligibility JSONL.
Identity: all 75,631 records retained with explicit status; history is prior-only.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/rebuild_initial_universe.py
"""

import gzip
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from lxml import html as lh
from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.initial_eligibility import classify, mark_history, normalized_form
from activist13d.local_paths import resolve_project_path

OUT = ROOT / "research/runs/phase1-baseline/20260924-universe-rebuild-v1"
DB = ROOT / "research/runs/phase1-overnight/full-20260915/sec.sqlite"
HFR = ROOT / "research/runs/hfr-all-managers/20260924-v1"
SUP = ROOT / "research/runs/investor-identity/20260924-supplemental-v1"


def audit(r):
    result = dict(
        accession=r["accession"],
        accepted=r.get("acceptance_datetime_et"),
        filing_date=r["filing_date"],
        metadata_form=r["form"],
        issuers=sorted({s["cik"] for s in r.get("subjects", []) if s.get("cik")}),
        reporter_ciks=sorted({s["cik"] for s in r.get("filers", []) if s.get("cik")}),
        source_sha256=r["source_sha256"],
        source_path=r["source_path"],
        source_bytes=r["source_bytes"],
    )
    text = ""
    try:
        p = resolve_project_path(r["source_path"], ROOT)
        raw = p.read_bytes()
        meta = json.loads(p.with_name(p.name + ".meta.json").read_text())
        if (
            len(raw) != r["source_bytes"]
            or hashlib.sha256(raw).hexdigest() != r["source_sha256"]
            or meta["sha256"] != r["source_sha256"]
            or not meta["url"].endswith(r["accession"] + ".txt")
        ):
            raise ValueError("raw_source_integrity")
        if len(raw) > 20 * 1024**2:
            raise ValueError("source_over_20MiB")
        source = raw.decode("utf-8", errors="replace")
        header = source.split("<DOCUMENT>", 1)[0]
        accession = re.search(r"ACCESSION NUMBER:\s*([\d-]+)", header)
        form = re.search(r"CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)", header)
        filed = re.search(r"FILED AS OF DATE:\s*(\d{8})", header)
        if (
            not accession
            or accession[1] != r["accession"]
            or not filed
            or filed[1] != r["filing_date"].replace("-", "")
        ):
            raise ValueError("header_identity_or_date")
        blocks = []
        for block in re.findall(r"<DOCUMENT>\s*(.*?)</DOCUMENT>", source, re.S | re.I):
            typ = re.search(r"^<TYPE>([^\n]+)", block, re.M)
            name = re.search(r"^<FILENAME>([^\n]+)", block, re.M)
            if (
                typ
                and normalized_form(typ[1]) in {"13D", "13D/A"}
                and name
                and not name[1].lower().endswith((".pdf", ".jpg", ".png"))
            ):
                body = re.search(r"<TEXT>\s*(.*?)</TEXT>", block, re.S | re.I)
                if body:
                    blocks.append((typ[1].strip(), name[1].strip(), body[1]))
        if len(blocks) != 1:
            raise ValueError("ambiguous_primary_document")
        typ, name, body = blocks[0]
        tree = lh.fromstring(body)
        for node in tree.xpath("//script|//style"):
            node.drop_tree()
        text = re.sub(r"\s+", " ", " ".join(tree.itertext())).strip()
        xml = re.search(r"<(?:\w+:)?(?:amendmentNo|amendmentNumber)>\s*(\d+)", body, re.I)
        result.update(
            classify(
                text, [r["form"], form[1].strip() if form else "", typ], xml[1] if xml else None
            ),
            header_form=form[1].strip() if form else None,
            document_form=typ,
            filename=name,
            canonical_sha256=hashlib.sha256(text.encode()).hexdigest(),
            source_url=meta["url"],
            sidecar_sha256=digest(p.with_name(p.name + ".meta.json")),
        )
    except Exception as error:
        result.update(
            status="unresolved_source_or_primary",
            reason=type(error).__name__ + ":" + str(error)[:150],
            amendment_evidence=[],
            prior_history=[],
        )
    return result, gzip.compress(text.encode(), mtime=0)


def main():
    for p in [
        Path(__file__),
        ROOT / "src/activist13d/initial_eligibility.py",
        ROOT / "research/protocol/phase1-rebuild-v1.md",
    ]:
        freeze(OUT / "code" / p.name, p.read_bytes())
    inputs = {}
    evidence = defaultdict(set)
    for r in json.loads((HFR / "candidates.json").read_text()):
        for m in r["matches"]:
            evidence[r["accession"]].add("HFR:" + m["firm_id"])
    for r in json.loads((SUP / "candidates.json").read_text()):
        for m in r["matches"]:
            evidence[r["accession"]].add("Supplement:" + m["manager"])
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as old:
        records = []
        for (raw,) in old.execute("select record_json from records order by accession"):
            r = json.loads(raw)
            records.append(
                {
                    k: r.get(k)
                    for k in [
                        "accession",
                        "acceptance_datetime_et",
                        "filing_date",
                        "form",
                        "subjects",
                        "filers",
                        "source_sha256",
                        "source_path",
                        "source_bytes",
                    ]
                }
            )
    with sqlite3.connect(OUT / "audit.sqlite") as db:
        db.execute(
            "create table if not exists audit(accession text primary key, record text, canonical_gzip blob)"
        )
        done = {r[0] for r in db.execute("select accession from audit")}
        pending = [r for r in records if r["accession"] not in done]
        with ProcessPoolExecutor(max_workers=4) as pool:
            for i, (r, text) in enumerate(pool.map(audit, pending, chunksize=20)):
                db.execute(
                    "insert into audit values(?,?,?)",
                    (r["accession"], json.dumps(r, sort_keys=True), text),
                )
                if i % 500 == 0:
                    db.commit()
                    print("Audited", len(done) + i + 1, "/", len(records), flush=True)
        db.commit()
        audited = [
            json.loads(r[0]) for r in db.execute("select record from audit order by accession")
        ]
    assert len(audited) == len(records) == 75631
    for r in audited:
        r["manager_keys"] = sorted(evidence[r["accession"]])
        r["identity_keys"] = sorted(
            evidence[r["accession"]] | {"CIK:" + c for c in r["reporter_ciks"]}
        )
    marked = mark_history(audited)
    freeze(OUT / "eligibility.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in marked))
    summary = dict(
        records=len(marked),
        forms=dict(Counter(r["status"] for r in marked)),
        campaigns=dict(Counter(r["campaign_status"] for r in marked)),
        initial_body_overrides=sum(r.get("body_overrides_initial", False) for r in marked),
    )
    freeze(OUT / "summary.json", encode(summary))
    for p in [DB, HFR / "candidates.json", SUP / "candidates.json"]:
        inputs[str(p.relative_to(ROOT))] = digest(p)
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs=inputs,
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name not in {"provenance.json", "audit.sqlite"}
                },
            )
        ),
    )
    print(encode(summary))


if __name__ == "__main__":
    main()
