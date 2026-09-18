"""Probe frozen HFR Returns and Fund rows for user-specified Fund_ID 2703.

Reads frozen source XML without modifying it and prints matching records and
cell style identifiers for unit/format inspection.

Identity: source values are reported verbatim; no percentage conversion.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/probe_hfr_2703.py
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/hfr/2026-09-13"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def col(ref: str) -> int:
    n = 0
    for c in "".join(x for x in ref if x.isalpha()):
        n = n * 26 + ord(c.upper()) - 64
    return n - 1


def main() -> None:
    for filename in ["HFR_HFRDB_EXCEL_Returns.xlsx", "HFR_HFRDB_EXCEL_Fund.xlsx"]:
        path = RAW / filename
        with ZipFile(path) as zf:
            shared = []
            if "xl/sharedStrings.xml" in zf.namelist():
                shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                shared = ["".join(si.itertext()) for si in shared_root.findall("m:si", NS)]
            styles = ET.fromstring(zf.read("xl/styles.xml")) if "xl/styles.xml" in zf.namelist() else None
            numfmts = {}
            if styles is not None:
                for node in styles.findall("m:numFmts/m:numFmt", NS):
                    numfmts[int(node.attrib["numFmtId"])] = node.attrib.get("formatCode", "")
            wb = ET.fromstring(zf.read("xl/workbook.xml"))
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            sheet = wb.find("m:sheets/m:sheet", NS)
            assert sheet is not None
            target = "xl/" + relmap[sheet.attrib[RID]].removeprefix("xl/")
            root = ET.fromstring(zf.read(target))
            rows = root.findall(".//m:sheetData/m:row", NS)
            print(f"FILE {filename} sheet={sheet.attrib['name']} rows={len(rows)}")
            if filename.endswith("Returns.xlsx"):
                for row in rows:
                    cells = row.findall("m:c", NS)
                    vals = {col(c.attrib["r"]): c.findtext("m:v", default="", namespaces=NS) for c in cells}
                    if vals.get(0) and ((shared[int(vals[0])] if cells[0].attrib.get("t") == "s" else vals[0]) == "2703"):
                        print("MATCH", row.attrib.get("r"), [(c.attrib.get("r"), c.attrib.get("s"), c.attrib.get("t"), shared[int(c.findtext("m:v", default="0", namespaces=NS))] if c.attrib.get("t") == "s" else c.findtext("m:v", default="", namespaces=NS)) for c in cells])
            else:
                for row in rows:
                    cells = row.findall("m:c", NS)
                    vals = {col(c.attrib["r"]): c.findtext("m:v", default="", namespaces=NS) for c in cells}
                    if vals.get(0) and ((shared[int(vals[0])] if cells[0].attrib.get("t") == "s" else vals[0]) == "2703"):
                        print("MATCH", row.attrib.get("r"), [(c.attrib.get("r"), c.attrib.get("s"), c.attrib.get("t"), shared[int(c.findtext("m:v", default="0", namespaces=NS))] if c.attrib.get("t") == "s" else c.findtext("m:v", default="", namespaces=NS)) for c in cells])
            print("CUSTOM_NUMFMTS", numfmts)


if __name__ == "__main__":
    main()
