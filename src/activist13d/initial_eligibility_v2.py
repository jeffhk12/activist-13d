"""Tier: 2. Reconcile amendment evidence while excluding cover boilerplate.
Inputs: canonical primary text and index/header/document forms.
Outputs: conservative form status and exact self-history spans.
Identity: cover 13G checkbox and amendments to other agreements are not own history.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_initial_eligibility_v2.py
"""

import re

from activist13d.initial_eligibility import mark_history, normalized_form  # noqa: F401


def classify(text, forms, xml_number=None):
    if not text or any(normalized_form(f) not in {"13D", "13D/A"} for f in forms):
        return dict(status="unresolved_primary_or_form", amendment_evidence=[], prior_history=[])
    spans = []
    patterns = [
        (r"\(\s*Amendment\s+(?:No\.?|Number)\s*[:#]?\s*(\d+)\s*\)", text[:2000]),
        (r"Amendment\s+(?:No\.?|Number)\s*[:#]?\s*(\d+)\s*(?:\*|$)", text[:500]),
        (
            r"This\s+Amendment\s+(?:No\.?|Number)\s*(\d+)(?:(?!agreement|exhibit|contract).){0,160}?Schedule\s+13D",
            text,
        ),
    ]
    for pattern, body in patterns:
        for m in re.finditer(pattern, body, re.I):
            if int(m[1]) > 0:
                spans.append(dict(start=m.start(), end=m.end(), quote=m[0], number=int(m[1])))
    history = []
    pattern = r"(?:originally|initially|previously)\s+filed(?:(?!Schedule|13G|l3G).){0,150}?Schedule\s+13D|original\s+Schedule\s+13D|ceased\s+filing\s+as\s+a\s+group|Investor\s+Group\s+disbanded"
    for m in re.finditer(pattern, text, re.I):
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
