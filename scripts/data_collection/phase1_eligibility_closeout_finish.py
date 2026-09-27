"""Tier: 2. Finish bounded eligibility closeout checks and interpretation record.
Inputs: frozen sources, closeout facts, independently reviewed source contexts.
Outputs: immutable supplemental checks and model-review notes, never human labels.
Identity: remove uncertain same-day manager keys, replay history, compare statuses;
XML counts must match original canonical classification. Run with project Python.
"""

import gzip
import json
import re
import sqlite3
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.initial_eligibility import mark_history
from activist13d.initial_eligibility_v3 import classify
from activist13d.local_paths import resolve_project_path

B = ROOT / "research/runs/phase1-baseline"
CLOSEOUT = B / "20260924-eligibility-closeout-v1"
rows = [
    json.loads(s)
    for s in (B / "20260924-universe-rebuild-v3/eligibility.jsonl").read_text().splitlines()
]
lookup = {r["accession"]: r for r in rows}
flags = json.loads((CLOSEOUT / "identity-timing-review.json").read_text())
flagged = {r["accession"]: set(r["eligibility"]["manager_keys"]) for r in flags}
modified = [
    dict(
        r,
        identity_keys=[
            k for k in r["identity_keys"] if k not in flagged.get(r["accession"], set())
        ],
    )
    for r in rows
]
replay = mark_history(modified)
changes = [
    dict(
        accession=r["accession"],
        old=lookup[r["accession"]]["campaign_status"],
        new=r["campaign_status"],
    )
    for r in replay
    if r["campaign_status"] != lookup[r["accession"]]["campaign_status"]
]
assert not changes
con = sqlite3.connect(f"file:{B / '20260924-universe-rebuild-v1/audit.sqlite'}?mode=ro", uri=True)
xml = []
for r in rows:
    if r.get("body_overrides_initial") and not r["amendment_evidence"]:
        p = resolve_project_path(r["source_path"], ROOT)
        assert digest(p) == r["source_sha256"]
        raw = p.read_text(errors="replace")
        m = re.search(r"<(?:\w+:)?(?:amendmentNo|amendmentNumber)>\s*(\d+)", raw, re.I)
        assert m
        t = gzip.decompress(
            con.execute(
                "select canonical_gzip from audit where accession=?", (r["accession"],)
            ).fetchone()[0]
        ).decode()
        assert (
            classify(t, [r["metadata_form"], r["header_form"], r["document_form"]], m[1])["status"]
            == r["status"]
        )
        xml.append(
            dict(accession=r["accession"], number=int(m[1]), source_sha256=r["source_sha256"])
        )
assert len(xml) == 9
freeze(
    CLOSEOUT / "supplemental-checks.json",
    encode(
        dict(
            xml_replay=xml,
            timing_key_removal_history_status_changes=changes,
            removed_keys={k: sorted(v) for k, v in flagged.items()},
        )
    ),
)
non_support = {
    "0001104659-18-072717": "Power-of-attorney/executive-order incorporation cites CGG and DBV Technologies; current issuer Millendo Therapeutics.",
    "0001104659-19-062731": "Regex crosses prior 13G filing date into the sentence saying current 13D is filed after board election.",
    "0001104659-20-058176": "Investor track-record narrative describes original 13Ds for other named issuers; current issuer Cincinnati Bancorp.",
    "0001104659-21-124586": "Investor track-record narrative describes original 13Ds for other named issuers; current issuer Generations Bancorp NY.",
    "0001213900-19-011253": "Regex crosses prior 13G history into current 13D filing sentence.",
    "0001213900-21-038712": "Conditional cover checkbox uses Schedule 13D in place of usual 13G; hypothetical is not affirmative history.",
    "0001437749-21-002940": "Prior 13G date followed by determination that current 13D reporting is more appropriate.",
    "0001575705-20-000024": "Was required to be originally filed describes initial ownership period, not evidence of an actual prior filing.",
}
ambiguous = {
    "0000899140-21-000415": "Detected span starts in a previously filed merger-agreement/Form 8-K reference and crosses into current Item 1; surrounding explanatory history needs same-issuer/person adjudication.",
    "0001531612-21-000035": "Generic Except as otherwise described in the original Schedule 13D may be self-history or reused boilerplate; source context alone does not settle it.",
}
contexts = json.loads((CLOSEOUT / "development-history-contexts.json").read_text())
notes = []
for r in contexts:
    a = r["accession"]
    status = (
        "detected_spans_do_not_establish_same_issuer_prior_13d"
        if a in non_support
        else "unresolved_attribution"
        if a in ambiguous
        else "context_supports_same_issuer_or_predecessor_reporting_history"
    )
    notes.append(
        dict(
            accession=a,
            interpretation_status=status,
            rationale=non_support.get(
                a,
                ambiguous.get(
                    a,
                    "Context identifies reporting persons, prior group, successor trust or issuer reorganization with prior Schedule 13D; this does not independently validate an economic campaign.",
                ),
            ),
            evidence_context_file="development-history-contexts.json",
            is_model_judgment=True,
            human_label=False,
            action="retain_existing_conservative_exclusion; no accession-specific promotion",
        )
    )
assert len(notes) == 24 and len(non_support) == 8 and len(ambiguous) == 2
freeze(
    CLOSEOUT / "history-attribution-review.json",
    encode(
        dict(
            review_kind="assistant source-attribution investigation, not human labels or validated reference set",
            notes=notes,
            conclusion="V3 history spans are lexical references, not validated same-issuer campaign history. No eligibility-changing rule is proposed; retain conservative exclusions pending general attribution validation.",
        )
    ),
)
paths = [
    Path(__file__),
    ROOT / "scripts/data_collection/phase1_eligibility_closeout_history_review.py",
    ROOT / "scripts/data_collection/phase1_eligibility_closeout_identity_review.py",
]
for p in paths:
    freeze(CLOSEOUT / "code" / p.name, p.read_bytes())
freeze(
    CLOSEOUT / "supplemental-provenance.json",
    encode(
        dict(
            original_provenance_sha256=digest(CLOSEOUT / "provenance.json"),
            outputs={
                str(p.relative_to(CLOSEOUT)): digest(p)
                for p in sorted(CLOSEOUT.rglob("*"))
                if p.is_file() and p.name not in {"provenance.json", "supplemental-provenance.json"}
            },
        )
    ),
)
print(
    "XML replay: 9. Same-day manager-key removal history changes: 0. Development history review: 14 supporting contexts, 8 nonsupporting, 2 ambiguous; classifications unchanged."
)
