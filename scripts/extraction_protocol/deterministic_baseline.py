"""Tier 1: verify fixed 52 sources and measure unchanged parser availability.
Inputs: frozen human-first bundles and referenced submissions. Outputs: manifest/baseline.
Identity: source SHA256 equals bundle SHA256; coverage counts non-null parser fields.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/extraction_protocol/deterministic_baseline.py
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from activist13d.edgar.submission import parse_submission  # noqa: E402
from activist13d.local_paths import resolve_project_path  # noqa: E402

OUT = ROOT / "research/runs/deterministic-extraction/20260923-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect():
    paths = sorted((ROOT / "review/drafts/human-first-52/bundles").glob("*.json"))
    assert len(paths) == 52
    manifest, baseline = [], []
    for path in paths:
        bundle = json.loads(path.read_text())
        source = resolve_project_path(bundle["source_path"], ROOT)
        row = {
            "accession": bundle["accession"],
            "bundle_path": str(path.relative_to(ROOT)),
            "bundle_sha256": digest(path.read_bytes()),
            "source_path": str(source.relative_to(ROOT)),
            "expected_source_sha256": bundle["source_sha256"],
        }
        try:
            payload = source.read_bytes()
            if digest(payload) != bundle["source_sha256"]:
                raise ValueError("Raw source hash mismatch")
            for doc in bundle["documents"]:
                if (
                    doc.get("text") is not None
                    and digest(doc["text"].encode()) != doc["text_sha256"]
                ):
                    raise ValueError("Canonical hash mismatch: " + doc["document_id"])
            row["verification"] = "verified"
            row["source_bytes"] = len(payload)
            parsed = parse_submission(payload)
            if parsed["accession"] != bundle["accession"]:
                raise ValueError("Accession mismatch")
            baseline.append(
                {
                    "accession": bundle["accession"],
                    "format": parsed["parser_source"],
                    "cusip": bool(parsed["cusip"]),
                    "event_date": bool(parsed["event_date"]),
                    "item4": bool(parsed["item4_text"]),
                    "ownership": bool(parsed["reporting_persons_xml"]),
                    "status": "processed",
                }
            )
        except Exception as exc:
            row["verification"] = row.get("verification", "failed")
            row["error"] = str(exc)
            baseline.append(
                {"accession": bundle["accession"], "status": "failed", "error": str(exc)}
            )
        manifest.append(row)
    coverage = {
        "denominator": 52,
        "meaning": "Parser availability, not correctness or representative prevalence",
        "formats": dict(Counter(x.get("format", "failed") for x in baseline)),
        "present_counts": {
            k: sum(bool(x.get(k)) for x in baseline)
            for k in ["cusip", "event_date", "item4", "ownership"]
        },
        "failures": sum(x["status"] == "failed" for x in baseline),
    }
    return manifest, {"coverage": coverage, "records": baseline}


if __name__ == "__main__":
    manifest, baseline = inspect()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in [("input-manifest.json", manifest), ("baseline.json", baseline)]:
        target = OUT / name
        content = json.dumps(value, indent=2, sort_keys=True) + "\n"
        if target.exists() and target.read_text() != content:
            raise ValueError("Refusing changed baseline: " + str(target))
        target.write_text(content)
    print(json.dumps(baseline["coverage"], indent=2))
    first = json.loads((ROOT / manifest[0]["bundle_path"]).read_text())
    print(
        "Document shape:", [{k: v for k, v in d.items() if k != "text"} for d in first["documents"]]
    )
    print("Header preview:", first["documents"][0].get("text", "")[:1800])
