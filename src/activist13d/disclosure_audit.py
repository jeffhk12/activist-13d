"""Tier: 2. Detect explicit cover amendment numbers and summarize exposure groups.
Inputs: canonical disclosure text, dated event rows with industry/entry fields.
Outputs: exact cover spans and descriptive contributions; no intent labels.
Identity: mean contribution=sum(group excess)/total n. No causal estimator.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_disclosure_audit.py
"""

import re
from collections import defaultdict

from activist13d.concentration import simple


def cover_amendments(text):
    if not isinstance(text, str) or not text:
        raise ValueError("Canonical text required")
    return [
        dict(start=m.start(), end=m.end(), quote=m.group(), number=int(m.group(1)))
        for m in re.finditer(r"\(\s*Amendment\s+No\.?\s*(\d+)\s*\)", text[:2000], re.I)
        if int(m.group(1)) > 0
    ]


def exposure(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return {
        k: dict(
            simple(v),
            contribution=sum(r["excess"] for r in v) / len(rows),
            leave_out=simple([r for r in rows if r[key] != k]),
        )
        for k, v in sorted(groups.items())
    }
