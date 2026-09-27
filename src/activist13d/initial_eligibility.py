"""Tier: 2. Mechanical body/header reconciliation and historical pair tracking.
Inputs: primary canonical text, form fields and contemporaneous identity keys.
Outputs: form eligibility/evidence and first-observed flags, never intent labels.
Identity: affirmative amendment evidence overrides initial-form metadata.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_initial_eligibility.py
"""

import re


def normalized_form(value):
    return re.sub(r"^(SC|SCHEDULE)\s+", "", (value or "").upper().strip())


def classify(text, forms, xml_number=None):
    if not text or any(normalized_form(f) not in {"13D", "13D/A"} for f in forms):
        return dict(status="unresolved_primary_or_form", amendment_evidence=[], prior_history=[])
    spans = []
    for m in re.finditer(
        r"Amendment\s+(?:No\.?|Number)\s*[:#]?\s*(\d+)\s*(?:\)|\*|\s|$)", text[:4000], re.I
    ):
        if int(m[1]) > 0:
            spans.append(dict(start=m.start(), end=m.end(), quote=m[0], number=int(m[1])))
    for m in re.finditer(
        r"This\s+Amendment\s+(?:No\.?|Number)\s*(\d+).{0,160}?Schedule\s+13D", text, re.I
    ):
        if int(m[1]) > 0:
            spans.append(dict(start=m.start(), end=m.end(), quote=m[0], number=int(m[1])))
    history = []
    # Skip the cover's standard hypothetical 13G checkbox; target affirmative 13D history.
    for m in re.finditer(
        r"(?:originally|initially|previously)\s+filed.{0,150}?Schedule\s+13D|original\s+Schedule\s+13D|ceased\s+filing\s+as\s+a\s+group|Investor\s+Group\s+disbanded",
        text,
        re.I,
    ):
        history.append(dict(start=m.start(), end=m.end(), quote=m[0]))
    amended = bool(
        spans
        or any(normalized_form(f) == "13D/A" for f in forms)
        or (xml_number and str(xml_number).strip().isdigit() and int(xml_number) > 0)
    )
    return dict(
        status="amendment" if amended else "standalone_initial_candidate",
        amendment_evidence=spans,
        prior_history=history,
        body_overrides_initial=bool(amended and all(normalized_form(f) == "13D" for f in forms)),
    )


def mark_history(records):
    """No later filing can change an earlier status; equal timestamps share history."""
    seen = {}
    output = []
    ordered = sorted(
        records, key=lambda r: (r["accepted"] or r["filing_date"] + "T23:59:59", r["accession"])
    )
    i = 0
    while i < len(ordered):
        timestamp = ordered[i]["accepted"] or ordered[i]["filing_date"] + "T23:59:59"
        j = i + 1
        while (
            j < len(ordered)
            and (ordered[j]["accepted"] or ordered[j]["filing_date"] + "T23:59:59") == timestamp
        ):
            j += 1
        for r in ordered[i:j]:
            pairs = [(issuer, k) for issuer in r["issuers"] for k in r["identity_keys"]]
            prior = sorted({seen[p] for p in pairs if p in seen})
            status = (
                "unresolved_identity"
                if len(r["issuers"]) != 1 or not r["identity_keys"]
                else "previously_observed_pair"
                if prior
                else "prior_history_in_document"
                if r["prior_history"]
                else "first_observed_pair"
            )
            output.append(dict(r, campaign_status=status, prior_accessions=prior))
        for r in ordered[i:j]:
            for issuer in r["issuers"]:
                for key in r["identity_keys"]:
                    seen.setdefault((issuer, key), r["accession"])
        i = j
    return output
