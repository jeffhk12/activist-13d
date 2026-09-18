"""Inspect supplied HFR workbooks without changing them.

Reads Excel workbook metadata and bounded representative rows; prints sheet names,
dimensions, headers, date-like coverage, and value examples.

Identity: inspection only; no source values are transformed or written.
Tier: 0
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/inspect_hfr.py
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SOURCE = Path("/Users/jefflu/Downloads/HFR_HFRDB_EXCEL_New")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def col_index(ref: str) -> int:
    letters = "".join(c for c in ref if c.isalpha())
    out = 0
    for c in letters:
        out = out * 26 + ord(c.upper()) - 64
    return out - 1


def value(cell: ET.Element, shared: list[str]) -> str:
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        return "".join(cell.itertext()).strip()
    node = cell.find("m:v", NS)
    if node is None:
        return ""
    raw = node.text or ""
    if typ == "s":
        return shared[int(raw)]
    return raw


def inspect(path: Path) -> None:
    with ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(si.itertext()) for si in root.findall("m:si", NS)]
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        for sheet in workbook.find("m:sheets", NS):
            target = relmap[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            if not target.startswith("/"):
                target = "xl/" + target.removeprefix("xl/")
            root = ET.fromstring(zf.read(target))
            rows = root.findall(".//m:sheetData/m:row", NS)
            print(f"SHEET\t{sheet.attrib['name']!r}\trows={len(rows)}")
            for row in rows[:5]:
                cells = {col_index(c.attrib.get("r", "A1")): value(c, shared) for c in row.findall("m:c", NS)}
                vals = [cells.get(i, "") for i in range(min(max(cells, default=-1) + 1, 12))]
                print("ROW" + row.attrib.get("r", "?") + "\t" + "\t".join(repr(v) for v in vals))
            dates = []
            for row in rows:
                for cell in row.findall("m:c", NS):
                    v = value(cell, shared)
                    if len(v) in (7, 10) and v[:4].isdigit() and v[4:5] in ("-", "/"):
                        dates.append(v)
            if dates:
                print(f"DATES\tmin={min(dates)}\tmax={max(dates)}\tcount={len(dates)}")


def main() -> None:
    for path in sorted(SOURCE.glob("*.xlsx")):
        print(f"FILE\t{path.name}\tbytes={path.stat().st_size}")
        inspect(path)


if __name__ == "__main__":
    main()
