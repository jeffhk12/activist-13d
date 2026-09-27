"""Tier: 0. Prepare portable review copies for the user's personal OneDrive.
Inputs: three published HTML reports. Outputs: portable HTML/PDF package and hashes.
Identity: presentation-only copies; source research outputs remain unchanged.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/package_phase1_phone_review.py
"""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/runs/phase1-baseline"
OUT = BASE / "20260924-phone-review-v1"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPORTS = [
    ("20260924-phase1-final-conclusion-v1", "01-Phase-1-Final-Conclusion", "portrait"),
    ("20260924-long-horizon-report-v1", "02-Long-Horizon-Results", "landscape"),
    ("20260924-historical-validation-report-v1", "03-Later-Historical-Test", "landscape"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = {
        (BASE / folder / "index.html").resolve(): name + ".html" for folder, name, _ in REPORTS
    }
    sources = {}
    for folder, name, orientation in REPORTS:
        source = BASE / folder / "index.html"
        sources[str(source.relative_to(ROOT))] = sha(source)
        tree = html.fromstring(source.read_bytes())
        for element in tree.xpath("//details"):
            element.set("open", "open")
        for link in tree.xpath("//a[@href]"):
            raw = link.get("href")
            u = urlsplit(raw)
            if u.scheme in {"http", "https", "mailto"} or not u.path:
                continue
            target = (source.parent / unquote(u.path)).resolve()
            if target in mapping:
                link.set("href", mapping[target])
            elif target == ROOT / "START-HERE.html":
                link.set("href", "index.html")
            else:
                link.attrib.pop("href")
                link.set("title", "Detailed evidence retained in the full project archive")
        style = html.Element("style")
        style.text = f"""@media print {{ @page {{size: A4 {orientation}; margin: 15mm 13mm;}} body{{background:white;font-size:10.5pt;line-height:1.45}} main{{max-width:none;margin:0;padding:0}} h1{{font-size:25pt;line-height:1.15}} h2{{font-size:16pt;break-after:avoid}} .lead{{font-size:13pt;padding:14px;break-inside:avoid}} table{{font-size:8.5pt;table-layout:auto}} td,th{{padding:6px}} tr{{break-inside:avoid}} thead{{display:table-header-group}} .scroll{{overflow:visible}} details{{border:0;padding:0}} a{{color:#155c99;text-decoration:none}} }}"""
        tree.find("head").append(style)
        foot = html.Element("p")
        foot.text = "Portable review copy. Full calculation ledgers and provenance remain in the project archive. Public source links remain available. No research results were changed for this copy."
        tree.xpath("//main")[0].append(foot)
        target = OUT / (name + ".html")
        target.write_bytes(html.tostring(tree, encoding="utf-8", doctype="<!doctype html>"))
        pdf = OUT / (name + ".pdf")
        subprocess.run(
            [
                CHROME,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}",
                target.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert pdf.read_bytes().startswith(b"%PDF-")
        print(pdf.name, pdf.stat().st_size, flush=True)
    index = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D research - phone review</title><style>body{font:18px/1.6 system-ui;max-width:760px;margin:30px auto;padding:0 20px;color:#203448}a{color:#155c99}li{margin:18px 0}</style><h1>Phase 1 - review on your phone</h1><p>Snapshot: 24 September 2026.</p><p><strong>The historical baseline is established; a reliable investable edge is not.</strong> Longer-horizon averages improve, but typical outcomes and matched comparisons remain mixed. Aratana's merger settlement remains an open accounting exception.</p><ol><li><a href="01-Phase-1-Final-Conclusion.pdf">Start here: final Phase 1 conclusion (PDF)</a></li><li><a href="02-Long-Horizon-Results.pdf">Longer-horizon results (PDF)</a></li><li><a href="03-Later-Historical-Test.pdf">Earlier 2024-2025 test (PDF)</a></li></ol><p>Matching HTML files are included for browser reading. In OneDrive on your phone, open the PDFs directly if HTML preview is unavailable. Choose “Make available offline” in OneDrive if you want access without a connection.</p><p>This package contains reports, not the raw data, source code or a full project backup. Research outputs and investor lists are unchanged.</p></html>"""
    (OUT / "index.html").write_text(index)
    (OUT / "00-START-HERE.txt").write_text(
        "PHASE 1 - PHONE REVIEW\n24 September 2026\n\nOPEN FIRST: 01-Phase-1-Final-Conclusion.pdf\n\nHistorical baseline established; reliable investable edge not established.\nLonger-horizon means improve but medians/matched comparisons are mixed.\nAratana settlement remains an open accounting exception; primary long-horizon portfolios are incomplete.\n\n02-Long-Horizon-Results.pdf: expanded 2018-2025 research.\n03-Later-Historical-Test.pdf: separate 2024-2025 historical test.\n\nHTML versions are also included. Open PDFs directly in OneDrive on your phone.\nThis is a dated review snapshot, not a full project backup or ongoing automatic mirror.\nRaw datasets, credentials, environments and human-review worksheets are not included.\n"
    )
    files = [p for p in OUT.iterdir() if p.is_file() and p.suffix in {".html", ".pdf", ".txt"}]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_reports": sources,
        "files": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(files)},
        "research_results_changed": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
