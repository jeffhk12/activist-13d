"""Verify the expanded report's hashes, links and invented toy derivatives.

Inputs: expanded evidence/verification receipts, preserved PDFs and sources.
Outputs: post-render QA status; calculation research artifacts remain unchanged.
Identity: central difference approximates a toy loss derivative away from ReLU's
kink; numerical text and source fingerprints must agree with preserved evidence.
Tier: 0, presentation QA. Use --visual-reviewed only after inspecting all final PNGs.
Run: bundled PDF-runtime Python verify_expanded_update.py --visual-reviewed
"""

import argparse
import hashlib
import json
import math
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class Links(HTMLParser):
    def __init__(self, parent):
        super().__init__()
        self.parent, self.count = parent, 0

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href and not href.startswith(("https:", "http:", "#")):
            assert (self.parent / href).resolve().exists(), href
            self.count += 1


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--visual-reviewed", action="store_true")
    args = parser.parse_args()
    evidence = json.loads((HERE / "evidence-v2.json").read_text())
    for relative, sha in evidence["source_sha256"].items():
        assert digest(ROOT / relative) == sha, relative
    for relative, sha in evidence["code_sha256"].items():
        assert digest(ROOT / relative) == sha, relative
    for name, sha in evidence["preserved_pdf_sha256"].items():
        path = HERE / name
        if not path.exists():
            path = HERE.parent / "professor-discussion-20261013" / name
        assert digest(path) == sha, name
    pdf_path = HERE / evidence["pdf"]
    assert digest(pdf_path) == evidence["pdf_sha256"]
    reader = PdfReader(pdf_path)
    assert len(reader.pages) == evidence["pages"]
    text = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    for phrase in ("17,795", "93.68", "285", "0.0126", "0.1407584", "not frozen, implemented or trained", "Invented one-hidden-neuron calculation"):
        assert phrase in text, phrase
    assert evidence["fixed_page_cap"] is None
    local_links = {}
    for path in (HERE / "index-v2.html", ROOT / "START-HERE.html", ROOT / "research/docs/ml-checkpoints.html"):
        links = Links(path.parent)
        content = path.read_text()
        links.feed(content.split("</section>", 1)[0] if path.name == "START-HERE.html" else content)
        local_links[path.name] = links.count
    toy = json.loads((HERE / "toy-calculation-v2.json").read_text())

    def loss(values):
        pred = values["v"] * max(0, values["w"] * values["x"] + values["b"]) + values["c"]
        return (pred - values["y"]) ** 2 + values["lambda"] * (values["w"] ** 2 + values["v"] ** 2)

    assert math.isclose(loss(toy), 0.0126, abs_tol=1e-12)
    differences = {}
    for key, expected in toy["gradients"].items():
        upper, lower = dict(toy), dict(toy)
        upper[key] += 1e-6
        lower[key] -= 1e-6
        finite = (loss(upper) - loss(lower)) / 2e-6
        assert math.isclose(finite, expected, abs_tol=1e-8), (key, finite, expected)
        differences[key] = abs(finite - expected)
    renders = [f"qa/expanded-final-{n}.png" for n in range(1, len(reader.pages) + 1)]
    assert all((HERE / name).exists() for name in renders)
    status = f"passed: all {len(reader.pages)} final page renders inspected" if args.visual_reviewed else "pending"
    verification = json.loads((HERE / "verification-v2.json").read_text())
    verification.update({"source_and_code_hashes": "passed", "earlier_pdfs": "byte-for-byte preserved",
                         "local_links_checked": local_links, "toy_derivative_absolute_errors": differences,
                         "toy_check_scope": "Invented report arithmetic only; not a neural implementation or training suite",
                         "final_renders": renders, "visual_review": status})
    (HERE / "verification-v2.json").write_text(json.dumps(verification, indent=2) + "\n")
    evidence["visual_review"] = status
    (HERE / "evidence-v2.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"pages": len(reader.pages), "source_hashes": "passed", "prior_pdfs": "preserved",
                      "toy_arithmetic": "passed", "local_links": local_links, "visual_review": status}))


if __name__ == "__main__":
    main()
