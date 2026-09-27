"""Freeze and extract the supplied HFR database workbooks.

Reads the user-supplied HFR Excel files, copies each original byte-for-byte into
the dated raw evidence directory, and emits a manifest plus a JSONL extract of
the supplied HFR index constituent records. Fund-level workbooks are preserved
but are not turned into an index or aggregated series.

Identity: source values are copied; Excel serial dates in the constituent
extract are converted to ISO dates using the Excel 1900 date system. Blank
source cells remain JSON null. No return-unit, currency, fee, or index-return
assumption is introduced.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/ingest_hfr.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SOURCE = Path("/Users/jefflu/Downloads/HFR_HFRDB_EXCEL_New")
REPO = Path(__file__).resolve().parents[2]
AS_OF = "2026-09-13"
RAW = REPO / "data" / "raw" / "hfr" / AS_OF
INTERIM = REPO / "data" / "interim" / "hfr"
OUTPUT = REPO / "research/runs" / "data-collection"
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def serial_date(raw: str, date1904: bool = False) -> str | None:
    if date1904:
        raise ValueError("unsupported Excel 1904 date system")
    if not raw:
        return None
    try:
        serial = float(raw)
    except ValueError:
        return raw
    if serial < 1:
        return raw
    return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()


def text_value(cell: ET.Element, shared: list[str]) -> str:
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        return "".join(cell.itertext()).strip()
    node = cell.find("m:v", NS)
    if node is None:
        return ""
    raw = node.text or ""
    return shared[int(raw)] if typ == "s" else raw


def col_index(ref: str) -> int:
    out = 0
    for char in "".join(c for c in ref if c.isalpha()):
        out = out * 26 + ord(char.upper()) - 64
    return out - 1


def constituent_rows(path: Path, source_sha256: str) -> tuple[list[str], list[dict[str, object]], str, bool]:
    with ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(si.itertext()) for si in root.findall("m:si", NS)]
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        workbook_pr = workbook.find("m:workbookPr", NS)
        date1904 = workbook_pr is not None and workbook_pr.attrib.get("date1904", "0").lower() in {"1", "true"}
        if date1904:
            raise ValueError("unsupported Excel 1904 date system")
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet = workbook.find("m:sheets/m:sheet", NS)
        assert sheet is not None
        target = relmap[sheet.attrib[RID]]
        target = "xl/" + target.removeprefix("xl/")
        root = ET.fromstring(zf.read(target))
        rows = root.findall(".//m:sheetData/m:row", NS)
        header_cells = rows[0].findall("m:c", NS)
        headers = [text_value(cell, shared) for cell in header_cells]
        records: list[dict[str, object]] = []
        for row in rows[1:]:
            cells = {col_index(c.attrib.get("r", "A1")): text_value(c, shared) for c in row.findall("m:c", NS)}
            record: dict[str, object] = {}
            for i, header in enumerate(headers):
                raw = cells.get(i, "")
                if raw == "":
                    record[header] = None
                elif header == "Index_Month":
                    record[header] = serial_date(raw)
                elif header in {"Index_ID", "Fund_ID"}:
                    record[header] = int(float(raw))
                elif header == "Approx_Weight":
                    record[header] = float(raw)
                else:
                    record[header] = raw
            records.append(record)
        return headers, records, sheet.attrib["name"], date1904


def index_return_rows(path: Path, source_sha256: str, fund_id: str = "2703") -> tuple[list[dict[str, object]], str, bool]:
    """Extract the supplied Fund_ID's return rows with raw ROR text preserved."""
    with ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(si.itertext()) for si in shared_root.findall("m:si", NS)]
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        workbook_pr = workbook.find("m:workbookPr", NS)
        date1904 = workbook_pr is not None and workbook_pr.attrib.get("date1904", "0").lower() in {"1", "true"}
        if date1904:
            raise ValueError("unsupported Excel 1904 date system")
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet = workbook.find("m:sheets/m:sheet", NS)
        assert sheet is not None
        target = "xl/" + relmap[sheet.attrib[RID]].removeprefix("xl/")
        root = ET.fromstring(zf.read(target))
        rows = root.findall(".//m:sheetData/m:row", NS)
        matches: list[dict[str, object]] = []
        for row in rows[1:]:
            cells = {col_index(c.attrib.get("r", "A1")): (c, text_value(c, shared)) for c in row.findall("m:c", NS)}
            if cells.get(0, (None, ""))[1] != fund_id:
                continue
            raw_date = cells.get(2, (None, ""))[1]
            raw_ror = cells.get(3, (None, ""))[1]
            raw_nav = cells.get(4, (None, ""))[1]
            matches.append({
                "Fund_ID": int(fund_id),
                "Fund": cells.get(1, (None, ""))[1] or None,
                "Date": serial_date(raw_date),
                "Date_excel_serial": raw_date or None,
                "ROR": raw_ror or None,
                "NAV": raw_nav or None,
                "ROR_unit": "source field ROR; unit unspecified",
                "_source_sha256": source_sha256,
                "_sheet": sheet.attrib["name"],
                "_excel_row": int(row.attrib["r"]),
                "_ror_cell": f"D{row.attrib['r']}",
                "_ror_style_id": next((c.attrib.get("s") for c in row.findall("m:c", NS) if c.attrib.get("r") == f"D{row.attrib['r']}"), None),
            })
        return matches, sheet.attrib["name"], date1904


def fund_metadata_evidence(path: Path, source_sha256: str, fund_id: str = "2703") -> dict[str, object]:
    """Validate and return observed metadata cells for the matching Fund_ID."""
    with ZipFile(path) as zf:
        shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        shared = ["".join(si.itertext()) for si in shared_root.findall("m:si", NS)]
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet = workbook.find("m:sheets/m:sheet", NS)
        assert sheet is not None
        root = ET.fromstring(zf.read("xl/" + relmap[sheet.attrib[RID]].removeprefix("xl/")))
        for row in root.findall(".//m:sheetData/m:row", NS):
            cells = {col_index(c.attrib.get("r", "A1")): (c, text_value(c, shared)) for c in row.findall("m:c", NS)}
            if cells.get(0, (None, ""))[1] == fund_id:
                assert cells.get(1, (None, ""))[1] == "HFRI Event-Driven (Total) Index"
                assert cells.get(25, (None, ""))[1] == "USD"
                assert cells.get(18, (None, ""))[1] == "Net of All Fees"
                return {
                    "source_sha256": source_sha256,
                    "source_sheet": sheet.attrib["name"],
                    "excel_row": int(row.attrib["r"]),
                    "Fund": cells[1][1],
                    "currency": cells[25][1],
                    "fee_label": cells[18][1],
                }
    raise ValueError(f"Fund_ID {fund_id} not found in frozen Fund workbook")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in SOURCE.iterdir() if path.is_file())
    manifest: list[dict[str, object]] = []
    for source in files:
        frozen = RAW / source.name
        if frozen.exists() and sha256(frozen) != sha256(source):
            raise RuntimeError(f"refusing to overwrite changed frozen evidence: {frozen}")
        if not frozen.exists():
            shutil.copy2(source, frozen)
        stat = source.stat()
        manifest.append({
            "source_name": source.name,
            "source_path": str(source),
            "frozen_path": str(frozen),
            "bytes": stat.st_size,
            "sha256": sha256(source),
            "mtime_ns": stat.st_mtime_ns,
            "mode": oct(stat.st_mode & 0o777),
        })
    source = RAW / "HFR_HFRDB_EXCEL_HFR_Index_Constituents.xlsx"
    source_sha = next(item["sha256"] for item in manifest if item["source_name"] == source.name)
    headers, records, sheet_name, date1904 = constituent_rows(source, source_sha)
    extract = INTERIM / "hfr_index_constituents.jsonl"
    with extract.open("w", encoding="utf-8") as handle:
        for row_number, record in enumerate(records, 2):
            record = {**record, "_source_sha256": source_sha, "_sheet": sheet_name, "_excel_row": row_number}
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    dates = [r["Index_Month"] for r in records if r["Index_Month"] is not None]
    ids = sorted({r["Index_ID"] for r in records})
    returns_source = RAW / "HFR_HFRDB_EXCEL_Returns.xlsx"
    returns_sha = next(item["sha256"] for item in manifest if item["source_name"] == returns_source.name)
    return_records, return_sheet, return_date1904 = index_return_rows(returns_source, returns_sha)
    returns_extract = INTERIM / "hfri_event_driven_2703_monthly.jsonl"
    with returns_extract.open("w", encoding="utf-8") as handle:
        for record in return_records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    fund_source = RAW / "HFR_HFRDB_EXCEL_Fund.xlsx"
    fund_sha = next(item["sha256"] for item in manifest if item["source_name"] == fund_source.name)
    metadata = fund_metadata_evidence(fund_source, fund_sha)
    manifest_doc = {
        "as_of": AS_OF,
        "ingest_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "script_sha256": sha256(Path(__file__).resolve()),
        "source_datestamp": (SOURCE / "DATESTAMP.txt").read_text(encoding="ascii"),
        "source_directory": str(SOURCE),
        "raw_directory": str(RAW),
        "files": manifest,
        "workbook_classification": {
            "returns": "fund-level and HFRI index records with ROR and NAV; ROR unit/methodology documentation is absent",
            "assets": "fund-level assets; units undefined in supplied files",
            "fund": "fund and firm metadata",
            "instruments": "fund-level allocation by instrument and type",
            "regions": "fund-level allocation by region and type",
            "index_constituents": "index-to-fund membership/weight records by month; index returns are supplied separately in Returns",
        },
        "extract": {
            "path": str(extract),
            "headers": headers,
            "row_count": len(records),
            "index_count": len(ids),
            "index_month_min": min(dates) if dates else None,
            "index_month_max": max(dates) if dates else None,
            "missing_approx_weight": sum(r["Approx_Weight"] is None for r in records),
            "source_sha256": source_sha,
            "source_sheet": sheet_name,
            "excel_date1904": date1904,
            "extract_sha256": sha256(extract),
        },
        "hfri_event_driven_2703": {
            "user_supplied_mapping": "Fund_ID 2703 = HFRI Event-Driven (Total) Index",
            "source_sha256": returns_sha,
            "source_sheet": return_sheet,
            "excel_date1904": return_date1904,
            "row_count": len(return_records),
            "date_min": min((r["Date"] for r in return_records if r["Date"]), default=None),
            "date_max": max((r["Date"] for r in return_records if r["Date"]), default=None),
            "missing_ror": sum(r["ROR"] is None for r in return_records),
            "extract_path": str(returns_extract),
            "extract_sha256": sha256(returns_extract),
            "fund_metadata_evidence": {
                **metadata,
                "source_note": "Values observed in the matching Fund_ID 2703 row; column labels for these fields are not supplied in the visible header row.",
            },
        },
        "interpretation_limits": [
            "The Returns workbook contains the HFRI Event-Driven (Total) Index as Fund_ID 2703; the prior no-index-return statement is superseded by this revision.",
            "Matching Fund_ID 2703 metadata records currency USD and fee label Net of All Fees. ROR unit convention and return methodology documentation are absent.",
            "No artificial index construction or fund-level aggregation was performed.",
        ],
    }
    (INTERIM / "hfr_manifest.json").write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / f"hfr-{AS_OF}.md").write_text(
        "# HFR supplied data import\n\n"
        f"Frozen {len(manifest)} supplied files from `{SOURCE}` under `{RAW}`.\n\n"
        f"Extracted {len(records):,} index constituent rows across {len(ids):,} index IDs, "
        f"with Index_Month coverage {min(dates) if dates else 'unavailable'} to {max(dates) if dates else 'unavailable'}.\n\n"
        "The workbooks are a fund database extract. The Returns workbook contains Fund_ID 2703, "
        "HFRI Event-Driven (Total) Index, with monthly ROR/NAV observations. ROR values are preserved as source text. "
        "The source Fund workbook identifies USD and Net of All Fees; no conversion was applied.\n\n"
        f"Manifest: `{INTERIM / 'hfr_manifest.json'}`. Constituents JSONL: `{extract}`. "
        f"Index returns JSONL: `{returns_extract}`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
