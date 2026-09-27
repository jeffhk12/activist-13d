"""
Render DESIGN-RECORD.md to a professionally styled .docx.

DESIGN-RECORD.md is the single source of truth. Edit the markdown, re-run this,
never edit the .docx by hand.

Supported markdown:
    ---            YAML-ish front matter (title, subtitle, kicker, course, author, date)
    # / ## / ###   headings (H1 starts a new page after the first)
    | a | b |      tables with a --- separator row
    - item         bullets
    1. item        numbered list
    > [!NOTE] LBL  callout (also [!WARN]); continuation lines prefixed with >
    **bold**  *italic*  `mono`

Tier: 1 (analysis support)
Run:  $py build_docx.py
Out:  Activist-13D-Design-Record.docx
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor, Emu

HERE = Path(__file__).resolve().parent

# Default target is the design record; pass a markdown path to render any other.
STEMS = {"DESIGN-RECORD": "Activist-13D-Design-Record",
         "PROPOSAL": "Activist-13D-Proposal",
         "DATA-SOURCING": "Activist-13D-Data-Sourcing"}

SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "DESIGN-RECORD.md"
OUT = SRC.with_name(STEMS.get(SRC.stem, SRC.stem) + ".docx")

# ---------------------------------------------------------------- palette ---

INK, NAVY, SLATE, GREY = (
    RGBColor(0x1A, 0x1A, 0x1A),
    RGBColor(0x12, 0x3A, 0x5E),
    RGBColor(0x3D, 0x52, 0x66),
    RGBColor(0x6B, 0x72, 0x80),
)
RULE, TH_FILL = "D4D9DE", "F2F5F7"
NOTE_FILL, NOTE_EDGE = "F0F5F9", "123A5E"
WARN_FILL, WARN_EDGE = "FDF6E8", "B8860B"
NOTE_LBL, WARN_LBL = RGBColor(0x12, 0x3A, 0x5E), RGBColor(0x8A, 0x64, 0x00)
BODY, MONO = "Calibri", "Consolas"

# Column widths per table, keyed by the joined header row. Anything not listed
# is left to Word's autofit.
WIDTHS = {
    "|Question|Method": [0.07, 0.55, 0.38],
    "Method|What it does|Why it is advanced": [0.24, 0.38, 0.38],
    "Step|Candidate|Why it moved on": [0.06, 0.40, 0.54],
    "Filing|Deadline|What it tells you": [0.14, 0.26, 0.60],
    "Established finding|Source": [0.62, 0.38],
    "Field|Type|Source": [0.28, 0.38, 0.34],
    "Dropped|Why": [0.34, 0.66],
    "Step|Model tier|Purpose": [0.22, 0.34, 0.44],
    "Check|What it buys": [0.34, 0.66],
    "Source|Role|Access": [0.28, 0.44, 0.28],
    "Decision|Chosen|Rejected, and why": [0.16, 0.31, 0.53],
    "Weeks|Dates|Work": [0.10, 0.20, 0.70],
    "Risk|Mitigation": [0.34, 0.66],
    "Ref|Why": [0.42, 0.58],
}


# ------------------------------------------------------------- xml helpers --

def _apply_font(el, name):
    rPr = el.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rPr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def font(run, name=BODY, size=10.5, bold=False, italic=False, color=INK):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    _apply_font(run._element, name)
    return run


def shade(cell, fill):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(el)


def cell_borders(cell, **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    old = tcPr.find(qn("w:tcBorders"))
    if old is not None:
        tcPr.remove(old)
    bs = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        spec = edges.get(edge, "keep")
        if spec == "keep":
            continue
        el = OxmlElement(f"w:{edge}")
        if spec is None:
            el.set(qn("w:val"), "nil")
        else:
            sz, col = spec
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), col)
        bs.append(el)
    tcPr.append(bs)


def strip_table_borders(table):
    tblPr = table._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    bs = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        bs.append(el)
    tblPr.append(bs)


def cell_margins(table, top=60, bottom=60, left=90, right=90):
    mar = OxmlElement("w:tblCellMar")
    for edge, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    table._tbl.tblPr.append(mar)


def repeat_header(row):
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    row._tr.get_or_add_trPr().append(el)


def rule_below(par, color=RULE, sz=6):
    bd = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "4")
    b.set(qn("w:color"), color)
    bd.append(b)
    par._p.get_or_add_pPr().append(bd)


def field(par, instr, placeholder="1"):
    for kind in ("begin",):
        r = par.add_run()
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), kind)
        r._r.append(fc)
    r = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r._r.append(it)
    r = par.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "separate")
    r._r.append(fc)
    out = par.add_run(placeholder)
    r = par.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    r._r.append(fc)
    return out


# ------------------------------------------------------------ inline markup --

TOKEN = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+?`)")


def rich(par, text, size=10.5, bold=False, italic=False, color=INK):
    for tok in TOKEN.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            font(par.add_run(tok[2:-2]), BODY, size, True, italic, color)
        elif tok.startswith("`") and tok.endswith("`"):
            font(par.add_run(tok[1:-1]), MONO, size - 0.5, bold, italic, SLATE)
        elif tok.startswith("*") and tok.endswith("*"):
            font(par.add_run(tok[1:-1]), BODY, size, bold, True, color)
        else:
            font(par.add_run(tok), BODY, size, bold, italic, color)
    return par


# ------------------------------------------------------------- doc scaffold --

doc = Document()
sec = doc.sections[0]
sec.top_margin = sec.bottom_margin = Inches(0.9)
sec.left_margin = sec.right_margin = Inches(1.0)

normal = doc.styles["Normal"]
normal.font.name = BODY
normal.font.size = Pt(10.5)
normal.font.color.rgb = INK
normal.paragraph_format.space_after = Pt(7)
normal.paragraph_format.line_spacing = 1.14
_apply_font(normal.element, BODY)

for name, size, color, before, after in (
    ("Heading 1", 17, NAVY, 22, 8),
    ("Heading 2", 12.5, NAVY, 16, 5),
    ("Heading 3", 10.5, SLATE, 12, 3),
):
    st = doc.styles[name]
    st.font.name = BODY
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.italic = False
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True
    _apply_font(st.element, BODY)


def para(text="", size=10.5, bold=False, italic=False, color=INK,
         after=7, before=0, indent=0.0, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    if align is not None:
        p.alignment = align
    if text:
        rich(p, text, size=size, bold=bold, italic=italic, color=color)
    return p


def emit_table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    strip_table_borders(t)
    cell_margins(t)

    hdr = t.rows[0]
    repeat_header(hdr)
    for i, h in enumerate(headers):
        c = hdr.cells[i]
        c.text = ""
        p = c.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        rich(p, h, size=9.5, bold=True, color=NAVY)
        shade(c, TH_FILL)
        cell_borders(c, top=(6, RULE), bottom=(8, RULE), left=None, right=None)

    for r in rows:
        cells = t.add_row().cells
        for i, val in enumerate(r):
            c = cells[i]
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.08
            rich(p, val, size=9.5)
            cell_borders(c, bottom=(4, RULE), top=None, left=None, right=None)

    key = "|".join(headers)
    fracs = WIDTHS.get(key)
    if fracs:
        total = Inches(6.5)
        for row in t.rows:
            for i, f in enumerate(fracs):
                row.cells[i].width = Emu(int(total * f))
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def emit_callout(kind, label, text):
    warn = kind == "WARN"
    t = doc.add_table(rows=1, cols=1)
    t.autofit = False
    strip_table_borders(t)
    cell_margins(t, top=110, bottom=110, left=150, right=150)
    c = t.rows[0].cells[0]
    c.width = Inches(6.5)
    c.text = ""
    shade(c, WARN_FILL if warn else NOTE_FILL)
    cell_borders(c, left=(24, WARN_EDGE if warn else NOTE_EDGE),
                 top=None, bottom=None, right=None)
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.12
    if label:
        font(p.add_run(label + "  "), BODY, 9.5, True, False, WARN_LBL if warn else NOTE_LBL)
    rich(p, text, size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# ------------------------------------------------------------------ parser --

raw = SRC.read_text(encoding="utf-8")

meta: dict[str, str] = {}
if raw.startswith("---"):
    fm, raw = raw[3:].split("---", 1)
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()

lines = raw.splitlines()

# ---- title page

for _ in range(4):
    doc.add_paragraph().paragraph_format.space_after = Pt(0)

if meta.get("kicker"):
    font(para(after=14).add_run(meta["kicker"]), BODY, 9, True, False, GREY)

tp = doc.add_paragraph()
tp.paragraph_format.space_after = Pt(4)
font(tp.add_run(meta.get("title", "Untitled")), BODY, 27, True, False, NAVY)

sp = doc.add_paragraph()
sp.paragraph_format.space_after = Pt(20)
font(sp.add_run(meta.get("subtitle", "")), BODY, 13, False, False, SLATE)
rule_below(sp)

for key, color in (("course", SLATE), ("author", SLATE), ("date", GREY)):
    if meta.get(key):
        para(meta[key], size=10.5, color=color, after=2)
doc.paragraphs[-1].paragraph_format.space_after = Pt(24)


def flush_list(buf, numbered):
    for item in buf:
        p = doc.add_paragraph(style="List Number" if numbered else "List Bullet")
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.12
        rich(p, item)
    buf.clear()


def flush_para(buf):
    if buf:
        para(" ".join(buf))
        buf.clear()


i = 0
first_h1 = True
toc_done = False
list_buf: list[str] = []
list_numbered = False
text_buf: list[str] = []

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # --- blank
    if not stripped:
        flush_para(text_buf)
        flush_list(list_buf, list_numbered)
        i += 1
        continue

    # --- headings
    m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
    if m:
        flush_para(text_buf)
        flush_list(list_buf, list_numbered)
        level, txt = len(m.group(1)), m.group(2)
        if level == 1:
            if first_h1:
                # contents page ahead of the first section
                doc.add_page_break()
                hp = doc.add_heading("Contents", level=1)
                rule_below(hp)
                tocp = doc.add_paragraph()
                tocp.paragraph_format.space_before = Pt(6)
                field(tocp, r'TOC \o "1-2" \h \z \u', "…")
                emit_callout("NOTE", "NOTE",
                             "Right-click the field above in Word and choose "
                             "**Update Field** to populate the contents.")
                toc_done = True
                first_h1 = False
            doc.add_page_break()
            h = doc.add_heading(txt, level=1)
            rule_below(h)
        else:
            doc.add_heading(txt, level=level)
        i += 1
        continue

    # --- callout
    m = re.match(r"^>\s*\[!(NOTE|WARN)\]\s*(.*)$", stripped)
    if m:
        flush_para(text_buf)
        flush_list(list_buf, list_numbered)
        kind, label = m.group(1), m.group(2).strip()
        body: list[str] = []
        i += 1
        while i < len(lines) and lines[i].strip().startswith(">"):
            body.append(lines[i].strip().lstrip(">").strip())
            i += 1
        emit_callout(kind, label, " ".join(body))
        continue

    # --- table
    if stripped.startswith("|"):
        flush_para(text_buf)
        flush_list(list_buf, list_numbered)

        def cells(row: str) -> list[str]:
            return [c.strip() for c in row.strip().strip("|").split("|")]

        headers = cells(stripped)
        i += 1  # separator row
        if i < len(lines) and set(lines[i].strip()) <= set("|-: "):
            i += 1
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(cells(lines[i]))
            i += 1
        emit_table(headers, rows)
        continue

    # --- lists
    m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
    if m:
        flush_para(text_buf)
        if list_buf and not list_numbered:
            flush_list(list_buf, list_numbered)
        list_numbered = True
        item = [m.group(2)]
        i += 1
        while i < len(lines) and lines[i].startswith("   ") and lines[i].strip():
            item.append(lines[i].strip())
            i += 1
        list_buf.append(" ".join(item))
        continue

    m = re.match(r"^[-*]\s+(.*)$", stripped)
    if m:
        flush_para(text_buf)
        if list_buf and list_numbered:
            flush_list(list_buf, list_numbered)
        list_numbered = False
        item = [m.group(1)]
        i += 1
        while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() \
                and not re.match(r"^\s*[-*\d]", lines[i]):
            item.append(lines[i].strip())
            i += 1
        list_buf.append(" ".join(item))
        continue

    # --- body text
    flush_list(list_buf, list_numbered)
    text_buf.append(stripped)
    i += 1

flush_para(text_buf)
flush_list(list_buf, list_numbered)

# ------------------------------------------------------------------ footer --

fp = doc.sections[0].footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
font(fp.add_run("Activist 13D — Design Record  ·  "), BODY, 8.5, False, False, GREY)
font(field(fp, "PAGE"), BODY, 8.5, False, False, GREY)

doc.save(OUT)
print(f"WROTE {OUT}")
print(f"  source: {SRC.name}  ({len(lines)} lines)")
