"""
MIT 8339 - Stage 7: editable Word version of the analytical report

Inputs : report/report_body.html (narrative), src/report_tables.py (tables, references),
         figures/*.png, outputs/*.csv, outputs/log_*.txt, src/* (code appendix)
Output : submission/MIT8339_StudentName_StudentID_BI_Virtual_Lab.docx
Run    : python src/07_build_word_report.py
"""
from pathlib import Path
from html.parser import HTMLParser
import html as htmllib
import re
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_tables import TABLES, FIGURES, REFERENCES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission" / "MIT8339_StudentName_StudentID_BI_Virtual_Lab.docx"
OUT.parent.mkdir(exist_ok=True)
GITHUB_URL = "https://github.com/<your-username>/mit8339-retention-bi"   # update after pushing

NAVY = RGBColor(0x0D, 0x36, 0x6B)
GREY = RGBColor(0x52, 0x51, 0x4E)
BODY_FONT, HEAD_FONT, MONO = "Calibri", "Cambria", "Consolas"
TEXT_WIDTH_CM = 16.0


# ---------------------------------------------------------------------------- helpers
def set_cell_shading(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader"); el.set(qn("w:val"), "true"); trPr.append(el)


def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit"); el.set(qn("w:val"), "true"); trPr.append(el)


def add_field(paragraph, instr):
    """Insert a Word field (PAGE, NUMPAGES, TOC ...). Word fills it when opened / on F9."""
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    r2 = paragraph.add_run()
    t = OxmlElement("w:instrText"); t.set(qn("xml:space"), "preserve"); t.text = instr; r2._r.append(t)
    r3 = paragraph.add_run()
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); r3._r.append(s)
    r4 = paragraph.add_run("Right-click and choose Update Field to build the table of contents." if "TOC" in instr else "1")
    r5 = paragraph.add_run()
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r5._r.append(e)


def fix_widths(t, widths):
    """Fixed layout + explicit grid so Word, LibreOffice and Google Docs all honour the column widths."""
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    tw = tblPr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW"); tblPr.append(tw)
    tw.set(qn("w:type"), "dxa"); tw.set(qn("w:w"), str(int(sum(w.twips for w in widths))))
    for col, w in zip(t.columns, widths):
        col.width = w


def caption(doc, text):
    p = doc.add_paragraph(style="Caption")
    p.add_run(text)
    return p


def add_table(doc, spec, font_size=9):
    cap, header, rows, rel = spec
    p = caption(doc, cap); p.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    widths = [Cm(TEXT_WIDTH_CM * w / sum(rel)) for w in rel]
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.width = widths[i]
        c.paragraphs[0].text = ""
        run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(font_size); run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_shading(c, "0D366B")
    set_repeat_header(t.rows[0])
    fix_widths(t, widths)
    for ri, r in enumerate(rows):
        cells = t.add_row().cells
        no_split(t.rows[-1])
        for i, v in enumerate(r):
            cells[i].width = widths[i]
            par = cells[i].paragraphs[0]
            if isinstance(v, tuple):              # (bold lead, rest)
                a = par.add_run(v[0]); a.bold = True; a.font.size = Pt(font_size)
                b = par.add_run(v[1]); b.font.size = Pt(font_size)
            else:
                run = par.add_run(str(v)); run.font.size = Pt(font_size)
            if ri % 2:
                set_cell_shading(cells[i], "F3F2EF")
    for row in t.rows:
        for c in row.cells:
            for par in c.paragraphs:
                par.paragraph_format.space_after = Pt(1); par.paragraph_format.space_before = Pt(1)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_figure(doc, path, frac, cap):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(ROOT / path), width=Cm(TEXT_WIDTH_CM * frac))
    c = caption(doc, cap); c.alignment = WD_ALIGN_PARAGRAPH.CENTER


def mono_block(doc, text, size=7):
    for line in text.rstrip("\n").split("\n"):
        p = doc.add_paragraph(style="Code")
        p.add_run(line if line else " ")


# ---------------------------------------------------------------------------- HTML narrative -> Word
class Narrative(HTMLParser):
    """Walks report_body.html: h1/h2 -> headings, p/li -> paragraphs with b/i/code runs, __X__ -> tables/figures."""

    def __init__(self, doc):
        super().__init__(convert_charrefs=True)
        self.doc, self.par, self.fmt, self.in_li = doc, None, [], False
        self.words = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2"):
            self.par = self.doc.add_heading(level=1 if tag == "h1" else 2)
        elif tag == "p":
            self.par = self.doc.add_paragraph(style="Body Text")
        elif tag == "li":
            self.par = self.doc.add_paragraph(style="List Bullet")
        elif tag in ("b", "i", "code"):
            self.fmt.append(tag)

    def handle_endtag(self, tag):
        if tag in ("b", "i", "code") and tag in self.fmt:
            self.fmt.remove(tag)
        elif tag in ("h1", "h2", "p", "li"):
            self.par = None

    def handle_data(self, data):
        token = data.strip()
        if token in TABLES:
            add_table(self.doc, TABLES[token], 8.5 if token in ("__DQ_TABLE__", "__COMP_TABLE__", "__REC_TABLE__") else 9)
            return
        if token in FIGURES:
            for f in FIGURES[token]:
                add_figure(self.doc, *f)
            return
        if self.par is None:
            return
        text = re.sub(r"\s+", " ", data)
        if not self.par.runs:
            text = text.lstrip()
        if not text:
            return
        run = self.par.add_run(text)
        run.bold = "b" in self.fmt or None
        run.italic = "i" in self.fmt or None
        if "code" in self.fmt:
            run.font.name = MONO; run.font.size = Pt(9.5)
        if self.par.style.name != "Heading 1" and self.par.style.name != "Heading 2":
            self.words += len(re.findall(r"[A-Za-z0-9][\w'’.,%$/–-]*", text))


# ---------------------------------------------------------------------------- document setup
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.3)

st = doc.styles
st["Normal"].font.name = BODY_FONT; st["Normal"].font.size = Pt(11)
st["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
st["Normal"].paragraph_format.space_after = Pt(6)
bt = st["Body Text"]; bt.font.name = BODY_FONT; bt.font.size = Pt(11)
bt.paragraph_format.space_after = Pt(8); bt.paragraph_format.line_spacing = 1.15; bt.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
for name, size, before, after in (("Heading 1", 16, 18, 6), ("Heading 2", 13, 12, 4), ("Heading 3", 11.5, 10, 4)):
    h = st[name]; h.font.name = HEAD_FONT; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = NAVY
    rf = h.element.rPr.rFonts; rf.set(qn("w:ascii"), HEAD_FONT); rf.set(qn("w:hAnsi"), HEAD_FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after); h.paragraph_format.keep_with_next = True
cap = st["Caption"]; cap.font.name = BODY_FONT; cap.font.size = Pt(9); cap.font.bold = True; cap.font.italic = False; cap.font.color.rgb = GREY
cap.paragraph_format.space_after = Pt(4)
lb = st["List Bullet"]; lb.font.size = Pt(11); lb.paragraph_format.space_after = Pt(4)
code = st.add_style("Code", 1); code.base_style = st["Normal"]
code.font.name = MONO; code.font.size = Pt(7)
code.element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
code.paragraph_format.space_after = Pt(0); code.paragraph_format.space_before = Pt(0); code.paragraph_format.line_spacing = 1.0
ref = st.add_style("Reference", 1); ref.base_style = st["Normal"]
ref.paragraph_format.left_indent = Cm(1.27); ref.paragraph_format.first_line_indent = Cm(-1.27); ref.paragraph_format.space_after = Pt(6)

# footer: course + page x of y
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = fp.add_run("MIT 8339 – BI & DSS Virtual Lab   |   Page "); r.font.size = Pt(8); r.font.color.rgb = GREY
add_field(fp, "PAGE"); r = fp.add_run(" of "); r.font.size = Pt(8); r.font.color.rgb = GREY; add_field(fp, "NUMPAGES")
sec.different_first_page_header_footer = True

# ---------------------------------------------------------------------------- cover
for _ in range(4):
    doc.add_paragraph()
p = doc.add_paragraph(); r = p.add_run("Miva Open University · School of Postgraduate Studies · Master of Information Technology"); r.font.size = Pt(11); r.font.color.rgb = GREY
p = doc.add_paragraph(); r = p.add_run("Customer Retention and Performance Intelligence for a Nigerian Commercial Bank")
r.font.name = HEAD_FONT; r.font.size = Pt(24); r.bold = True; r.font.color.rgb = NAVY
p = doc.add_paragraph(); r = p.add_run("MIT 8339 – Business Intelligence and Decision Support Systems (Virtual Lab) · Continuous Assessment, 2026/2027")
r.font.size = Pt(13); r.font.color.rgb = NAVY
doc.add_paragraph()
cover_rows = [("Student name", "[Student Name]"), ("Student ID", "[Student ID]"), ("Student email", "[Student Email]"),
              ("Course", "MIT 8339 – Business Intelligence and Decision Support Systems"),
              ("Dataset", "Credit Card Customers / BankChurners (Goyal, 2020)"),
              ("Tools", "Python 3 (Pandas, SciPy, scikit-learn, Matplotlib), Plotly.js dashboard"),
              ("Code repository", GITHUB_URL),
              ("Report length", "__WORDS__ words (Sections 1–8, excluding tables, figures, appendices and references)"),
              ("Date", "November 2026")]
ct = doc.add_table(rows=0, cols=2); ct.autofit = False
fix_widths(ct, [Cm(4.5), Cm(11.5)])
for k, v in cover_rows:
    cells = ct.add_row().cells
    cells[0].width, cells[1].width = Cm(4.5), Cm(11.5)
    a = cells[0].paragraphs[0].add_run(k); a.font.color.rgb = GREY
    cells[1].paragraphs[0].add_run(v)
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

p = doc.add_paragraph(); r = p.add_run("Contents"); r.font.name = HEAD_FONT; r.font.size = Pt(16); r.bold = True; r.font.color.rgb = NAVY
add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ---------------------------------------------------------------------------- narrative sections 1-8
nar = Narrative(doc)
nar.feed((ROOT / "report" / "report_body.html").read_text(encoding="utf-8"))
words = nar.words

# ---------------------------------------------------------------------------- references
doc.add_heading("References", level=1)
for segs in REFERENCES:
    p = doc.add_paragraph(style="Reference")
    for text, ital in segs:
        p.add_run(text).italic = bool(ital) or None

# ---------------------------------------------------------------------------- Appendix A
doc.add_page_break()
doc.add_heading("Appendix A – Data Preparation and KPI Evidence", level=1)
p = doc.add_paragraph(style="Body Text")
p.add_run("Reproduce: ").bold = True
p.add_run("install the packages in requirements.txt, run python -m playwright install chromium, place BankChurners.csv in data/, then run scripts 01 to 07 in order from the project root. "
          f"The hold-out split uses a fixed random seed (42). Full code: {GITHUB_URL}.")
add_table(doc, ("Table A1. Before-and-after data-quality summary", ["Quality dimension", "Before", "After"], [
    ["Rows", "10,127", "10,127"], ["Columns", "21", "36 (12 derived + target encoding + flags)"],
    ["System missing (NaN)", "0", "0"], ["'Unknown' placeholders", "3,380 cells in 3 columns", "Retained as category; 3,046 rows flagged"],
    ["Duplicate customers", "0", "0"], ["Label format", "F/M codes; text target", "Female/Male; Churned 1/0"],
    ["Business-rule violations", "0", "0"]], [3, 3, 4]))
before = pd.read_csv(ROOT / "outputs" / "dq_before.csv")[["column", "dtype", "missing_nan", "unknown_placeholder", "distinct"]]
add_table(doc, ("Table A2. Raw data profile before cleaning (21 columns)", ["Column", "Type", "NaN", "'Unknown'", "Distinct"],
                [[str(x) for x in r] for r in before.values.tolist()], [4, 1.5, 1, 1.3, 1.3]), 8)
doc.add_heading("A.1 Console output – data preparation", level=2)
mono_block(doc, (ROOT / "outputs" / "log_01.txt").read_text(encoding="utf-8"))
clean = pd.read_csv(ROOT / "data" / "BankChurners_cleaned.csv")
cols = ["CLIENTNUM", "Customer_Status", "Gender", "Age_Band", "Total_Trans_Ct", "Total_Revolving_Bal", "Product_Depth", "Risk_Score", "Risk_Band"]
doc.add_paragraph()
add_table(doc, ("Table A3. Cleaned dataset – first 8 rows, selected columns (10,127 rows × 36 columns in full)", cols,
                [[str(x) for x in r] for r in clean[cols].head(8).values.tolist()], [1.6, 1.3, 1, 1, 1, 1.2, 1.3, 0.9, 0.9]), 7)
doc.add_heading("A.2 Console output – KPIs, comparisons, risk validation", level=2)
mono_block(doc, (ROOT / "outputs" / "log_02.txt").read_text(encoding="utf-8"), 6.5)

# ---------------------------------------------------------------------------- Appendix B
doc.add_page_break()
doc.add_heading("Appendix B – Dashboard Screenshots", level=1)
add_figure(doc, "figures/dash_p1_overview.png", 1.0, "Figure B1. Page 1 – Executive overview (no filters).")
doc.add_page_break()
add_figure(doc, "figures/dash_p2_retention.png", 0.92, "Figure B2. Page 2 – Customer retention analysis.")
doc.add_page_break()
add_figure(doc, "figures/dash_p1_filtered.png", 1.0, "Figure B3. Slicers applied (Female, income < $40K, Blue card): all KPIs and visuals recalculate for 3,146 customers.")

# ---------------------------------------------------------------------------- Appendix C
doc.add_page_break()
doc.add_heading("Appendix C – Complete Code Base", level=1)
p = doc.add_paragraph(style="Body Text")
p.add_run(f"The full repository, including the README, requirements and run outputs, is at {GITHUB_URL}. "
          "The dashboard script embeds the Plotly.js library at build time; the listing below is the full source that generates it.")
code_files = ["src/01_data_preparation.py", "src/02_analysis_kpis.py", "src/03_build_dashboard.py", "src/04_capture_screenshots.py",
              "src/report_tables.py", "src/05_build_report.py", "src/06_build_deck.js", "src/07_build_word_report.py", "requirements.txt"]
for i, f in enumerate(code_files, 1):
    doc.add_heading(f"C.{i} {f}", level=2)
    mono_block(doc, (ROOT / f).read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------- Appendix D
doc.add_page_break()
doc.add_heading("Appendix D – Submission Files", level=1)
add_table(doc, ("Table D1. Submission contents", ["Deliverable", "File / location"], [
    ["Cleaned dataset", "BankChurners_cleaned.csv; BankChurners_cleaned.xlsx (data, field dictionary, quality log, before/after profiles)"],
    ["Technical evidence", f"GitHub repository ({GITHUB_URL}); Appendix A console output; outputs/*.csv"],
    ["Dashboard file", "MIT8339_Retention_Dashboard.html (opens offline in any browser)"],
    ["Screenshots", "Appendix A (data preparation, KPI output) and Appendix B (dashboard pages, filtered view)"],
    ["Analytical report", "This document, Sections 1–8"],
    ["Presentation", "8-slide PowerPoint deck with speaker notes"],
    ["References", "APA 7th edition"]], [3, 7]))

# fill the word count on the cover
for row in ct.rows:
    for par in row.cells[1].paragraphs:
        for run in par.runs:
            run.text = run.text.replace("__WORDS__", f"{words:,}")

doc.core_properties.title = "Customer Retention and Performance Intelligence"
doc.core_properties.author = "[Student Name]"
doc.save(OUT)
print(f"Report narrative word count: {words}")
print(f"Saved {OUT.relative_to(ROOT)}")
