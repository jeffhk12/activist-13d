"""Verify presentation structure, source links and text placement; no estimates.

Inputs: final PDF, speaking notes and evidence/verification JSON.
Output: verification.json updated with page/link checks after visual inspection.
Run: PDF-runtime Python verify_visual_brief.py (offline).
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
import json
import sys
from pypdf import PdfReader
import pdfplumber

root = Path(__file__).resolve().parent
pdf = root / "13D_Research_Brief_20261005_v3.pdf"
reader = PdfReader(pdf)
assert len(reader.pages) == 6
text = "\n".join(page.extract_text() for page in reader.pages)
assert "Questions for Professor" not in text and "?" not in text
assert "Jeff Lu, CFA |" not in text and "Professor Michael Sternberg" not in text
assert "Hill" not in text
assert "Yahoo" not in text and "yfinance" not in text
assert "Item 5(e)" in text and "full-exit date unknown" in text
assert "Proposed amendment buckets" in text and "not discarded" in text
assert "A funded account is a separate test" not in text and "-8.08" not in text and "Aratana" not in text
for expected in ("75,631", "15,813", "58,166", "53,070", "2013", "23/56", "17,795", "4,673", "4,440", "2,107", "+61.43", "WRDS", "HFR"):
    assert expected in text, expected
positions = []
with pdfplumber.open(pdf) as parsed:
    for i, page in enumerate(parsed.pages, 1):
        # Footer is independently positioned below the rule at y=30.
        body = [c for c in page.chars if c["top"] < 760 and c["text"].strip()]
        low = max(body, key=lambda c:c["bottom"])
        positions.append({"page":i,"lowest_body_glyph_bottom_from_top":round(low["bottom"],2),"footer_rule_from_top":762})
        assert low["bottom"] < 752, positions[-1]

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links += [v for k,v in attrs if k == "href"]

notes = (root / "discussion-notes.html").read_text()
assert "Hill" not in notes
assert "Yahoo" not in notes and "yfinance" not in notes
links = Links(); links.feed(notes)
local = [url for url in links.links if not urlparse(url).scheme]
for url in local:
    assert (root / unquote(urlparse(url).path)).resolve().exists(), url
verification = json.loads((root / "verification.json").read_text())
verification.update({"pdf_sha256": __import__("hashlib").sha256(pdf.read_bytes()).hexdigest(), "local_links_checked": len(local), "body_and_footer_positions": positions, "visual_review": "passed: all six final renders inspected" if "--visual-reviewed" in sys.argv else "pending"})
(root / "verification.json").write_text(json.dumps(verification, indent=2)+"\n")
print(json.dumps({"pages":6, "local_links_checked":len(local), "page_positions": positions}, indent=2))
