"""Verify two professor-facing PDFs and portable local speaking-note links.

Inputs: new PDFs, evidence and QA records; no research source modifications.
Outputs: page/text/link/source checks added to verification.json.
Tier: 0. Presentation QA, not a financial calculation or investment result.
Run: PDF-runtime Python verify_briefs.py [--visual-reviewed].
The visual flag is used only after final rendered pages have been inspected.
"""

import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pdfplumber
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
PDFS = [HERE / "13D_Machine_Learning_Brief_20261013.pdf", HERE / "13D_Private_Markets_Modeling_Brief_20261013.pdf"]
evidence = json.loads((HERE / "evidence.json").read_text())
for key, relative in evidence["source_paths"].items():
    assert hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest() == evidence["source_sha256"][key]
positions = {}
for path in PDFS:
    reader = PdfReader(path)
    assert len(reader.pages) == 4
    text = " ".join("\n".join(page.extract_text() for page in reader.pages).split())
    for expected in ("667", "556", "557", "365", "86", "69", "15,813", "13 October 2026"):
        assert expected in text, (path.name, expected)
    assert "No predictive model" in text
    assert "No validated intent accuracy" in text or "No issuer-specific" in text
    assert "Questions for" not in text
    assert "Jeff Lu, CFA" not in text
    if "Machine_Learning" in path.name:
        for expected in ("8.65%", "504-session", "Human development references", "M1:"):
            assert expected in text, expected
    else:
        for expected in ("117.50", "97.11", "teaching assumptions", "calibrated scenario", "D1:"):
            assert expected in text, expected
    bounds = []
    with pdfplumber.open(path) as parsed:
        for index, page in enumerate(parsed.pages, 1):
            body = [c for c in page.chars if c["text"].strip() and c["top"] < 752]
            assert body
            minimum_x = min(c["x0"] for c in body)
            maximum_x = max(c["x1"] for c in body)
            maximum_bottom = max(c["bottom"] for c in body)
            assert minimum_x >= 38 and maximum_x <= 575, (path.name, index, minimum_x, maximum_x)
            assert maximum_bottom < 750
            bounds.append({"page": index, "min_x": round(minimum_x, 2), "max_x": round(maximum_x, 2),
                           "lowest_body_from_top": round(maximum_bottom, 2)})
    positions[path.name] = bounds


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.local_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = urlsplit(dict(attrs).get("href", ""))
            if not href.scheme and href.path:
                assert (HERE / unquote(href.path)).resolve().exists(), href.path
                self.local_count += 1


links = Links()
links.feed((HERE / "discussion-notes.html").read_text())
verification = json.loads((HERE / "verification.json").read_text())
verification.update({"source_hashes_checked": True, "local_links_checked": links.local_count,
                     "body_bounds": positions,
                     "visual_review": "passed: all eight final page renders inspected" if "--visual-reviewed" in sys.argv else "pending"})
(HERE / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print(json.dumps({"pdfs": len(PDFS), "pages_each": 4, "local_links_checked": links.local_count,
                  "visual_review": verification["visual_review"]}, indent=2))
