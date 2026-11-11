"""
MIT 8339 - Stage 5: assemble the analytical report and submission PDF (HTML -> PDF via headless Chromium)

Inputs : report/report_body.html (narrative), outputs/*.csv, figures/*.png, src/*.py, outputs/log_*.txt
Output : submission/<file name>.pdf
Run    : python src/05_build_report.py
"""
from pathlib import Path
import base64, html, json, re
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"; SUB.mkdir(exist_ok=True)

# ---- Student details: replace before submission -----------------------------------------
STUDENT = {"name": "[Student Name]", "id": "[Student ID]", "email": "[Student Email]"}
FILE_STEM = "MIT8339_StudentName_StudentID_BI_Virtual_Lab"
# ------------------------------------------------------------------------------------------

S = json.loads((ROOT / "outputs" / "summary.json").read_text(encoding="utf-8"))
K = S["kpis"]


def img(path, width="100%"):
    b = base64.b64encode((ROOT / path).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" style="width:{width}">'


def table(rows, header, caption, cls=""):
    h = "".join(f"<th>{c}</th>" for c in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><caption>{caption}</caption><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_tables import TABLES, FIGURES, REFERENCES  # shared with the Word report


def spec_to_html(spec):
    cap, header, rows, _ = spec
    cls = "small" if len(header) >= 4 or cap.startswith("Table 3") else ""
    def cell(v):
        return f"<b>{html.escape(v[0])}</b>{html.escape(v[1])}" if isinstance(v, tuple) else html.escape(str(v))
    return table([[cell(v) for v in r] for r in rows], header, cap, cls)


def figs_to_html(items):
    return "".join(f'<figure>{img(p, f"{int(w * 100)}%")}<figcaption>{html.escape(c)}</figcaption></figure>' for p, w, c in items)


body = (ROOT / "report" / "report_body.html").read_text(encoding="utf-8")
for k, v in TABLES.items():
    body = body.replace(k, spec_to_html(v))
for k, v in FIGURES.items():
    body = body.replace(k, figs_to_html(v))

# Word count: narrative prose only (excludes tables, figures, code, appendices and references)
prose = re.sub(r"<table.*?</table>|<figure.*?</figure>|<h[12]>.*?</h[12]>", " ", body, flags=re.S)
prose = re.sub(r"<[^>]+>", " ", prose)
words = len(re.findall(r"[A-Za-z0-9][\w'’.,%$/–-]*", html.unescape(prose)))
print(f"Report narrative word count: {words}")

refs = "".join("<p>" + "".join(f"<i>{html.escape(t)}</i>" if it else html.escape(t) for t, it in segs) + "</p>" for segs in REFERENCES)

def term(path, title):
    return f'<div class="term"><div class="tt">{title}</div><pre>{html.escape((ROOT / path).read_text(encoding="utf-8"))}</pre></div>'

clean = pd.read_csv(ROOT / "data" / "BankChurners_cleaned.csv")
cols = ["CLIENTNUM", "Customer_Status", "Gender", "Age_Band", "Income_Category", "Total_Trans_Ct", "Total_Revolving_Bal",
        "Utilisation_Category", "Product_Depth", "Customer_Value_Class", "Risk_Score", "Risk_Band"]
sample = table(clean[cols].head(8).values.tolist(), cols, "Cleaned dataset - first 8 rows, selected columns (10,127 rows × 36 columns in full)", "tiny")
before = pd.read_csv(ROOT / "outputs" / "dq_before.csv")[["column", "dtype", "missing_nan", "unknown_placeholder", "distinct"]]
before_tbl = table(before.values.tolist(), ["Column", "Type", "NaN", "'Unknown'", "Distinct"], "Before cleaning - raw profile (21 columns)", "tiny")
after_summary = [["Rows", "10,127", "10,127"], ["Columns", "21", "36 (12 derived + target encoding + flags)"],
                 ["System missing (NaN)", "0", "0"], ["'Unknown' placeholders", "3,380 cells in 3 columns", "Retained as category; 3,046 rows flagged"],
                 ["Duplicate customers", "0", "0"], ["Label format", "F/M codes; text target", "Female/Male; Churned 1/0"],
                 ["Business-rule violations", "0", "0"]]
after_tbl = table(after_summary, ["Quality dimension", "Before", "After"], "Before-and-after data-quality summary", "small")

code_files = ["src/01_data_preparation.py", "src/02_analysis_kpis.py", "src/03_build_dashboard.py", "src/04_capture_screenshots.py",
              "src/report_tables.py", "src/05_build_report.py", "src/06_build_deck.js", "src/07_build_word_report.py", "requirements.txt", "README.md"]
def code_text(p):
    return (ROOT / p).read_text(encoding="utf-8")

code_html = "".join(f'<h3>C.{i} {p}</h3><pre class="code">{html.escape(code_text(p))}</pre>' for i, p in enumerate(code_files, 1))

CSS = """
@page{size:A4;margin:18mm 16mm 18mm 16mm}
body{font-family:'Segoe UI','DejaVu Sans',Arial,sans-serif;font-size:10.5pt;line-height:1.5;color:#1a1a1a}
.cover{height:250mm;display:flex;flex-direction:column;justify-content:center;page-break-after:always}
.cover .band{background:#0d366b;color:#fff;padding:28px 30px;border-radius:6px}
.cover h1{font-size:22pt;margin:0 0 6px;border:0;color:#fff}.cover h2{font-size:13pt;font-weight:400;margin:0;color:#dbe7f7}
.cover table{margin-top:28px;width:100%;font-size:11pt}.cover td{padding:6px 4px;border-bottom:1px solid #ddd}.cover td:first-child{width:38%;color:#555}
h1{font-size:15pt;color:#0d366b;border-bottom:2px solid #0d366b;padding-bottom:3px;margin:22px 0 8px;page-break-after:avoid}
h2{font-size:12pt;color:#0d366b;margin:14px 0 4px;page-break-after:avoid}h3{font-size:10.5pt;margin:12px 0 4px;color:#0d366b;page-break-after:avoid}
p{margin:5px 0 8px;text-align:justify}ul{margin:4px 0 8px 18px;padding:0}li{margin-bottom:3px}
code{font-family:'DejaVu Sans Mono',monospace;font-size:8.8pt;background:#f2f1ee;padding:0 3px;border-radius:3px}
table{border-collapse:collapse;width:100%;margin:8px 0 12px;font-size:9.2pt;page-break-inside:avoid}
caption{caption-side:top;text-align:left;font-weight:600;font-size:9.5pt;color:#333;padding-bottom:4px}
th{background:#0d366b;color:#fff;text-align:left;padding:5px 6px;font-weight:600}
td{padding:4px 6px;border-bottom:1px solid #e1dfda;vertical-align:top}tr:nth-child(even) td{background:#f7f6f3}
table.small{font-size:8.6pt}table.tiny{font-size:7.4pt}table.tiny td,table.tiny th{padding:2px 4px}
figure{margin:8px 0 12px;text-align:center;page-break-inside:avoid}figcaption{font-size:9pt;color:#555;margin-top:3px}
.toc p{margin:2px 0}.pb{page-break-before:always}
.term{background:#111;color:#d6f5d6;border-radius:5px;padding:8px 10px;margin:8px 0;page-break-inside:auto}
.term .tt{color:#9ab;font-size:8pt;margin-bottom:4px;font-family:'DejaVu Sans Mono',monospace}
.term pre{margin:0;font-family:'DejaVu Sans Mono',monospace;font-size:6.9pt;white-space:pre-wrap;line-height:1.35}
pre.code{font-family:'DejaVu Sans Mono',monospace;font-size:6.8pt;line-height:1.35;background:#f7f6f3;border:1px solid #e1dfda;padding:8px;white-space:pre-wrap;word-break:break-all}
.refs p{padding-left:24px;text-indent:-24px;text-align:left}
.note{font-size:9pt;color:#555}
"""

cover = f"""
<div class="cover"><div class="band"><h2>Miva Open University &middot; School of Postgraduate Studies &middot; Master of Information Technology</h2>
<h1>Customer Retention and Performance Intelligence for a Nigerian Commercial Bank</h1>
<h2>MIT 8339 &ndash; Business Intelligence and Decision Support Systems (Virtual Lab) &middot; Continuous Assessment, 2026/2027</h2></div>
<table>
<tr><td>Student name</td><td>{STUDENT['name']}</td></tr><tr><td>Student ID</td><td>{STUDENT['id']}</td></tr>
<tr><td>Student email</td><td>{STUDENT['email']}</td></tr><tr><td>Course</td><td>MIT 8339 &ndash; Business Intelligence and Decision Support Systems</td></tr>
<tr><td>Dataset</td><td>Credit Card Customers / BankChurners (Goyal, 2020)</td></tr>
<tr><td>Tools</td><td>Python 3 (Pandas, SciPy, scikit-learn, Matplotlib), Plotly.js dashboard</td></tr>
<tr><td>Report length</td><td>{words:,} words (Sections 1&ndash;8, excluding tables, figures, appendices and references)</td></tr>
<tr><td>Date</td><td>November 2026</td></tr></table>
<div style="margin-top:22px" class="toc"><b>Contents</b>
<p>1. Business Understanding and KPI Definition &middot; 2. Data Collection, Cleaning and Transformation &middot; 3. Exploratory Analysis &middot;
4. Retention-Risk Classification &middot; 5. Dashboard Design &middot; 6. Recommendations &middot; 7. Limitations and Governance &middot; 8. Conclusion &middot; References</p>
<p>Appendix A &ndash; Data preparation and KPI evidence &middot; Appendix B &ndash; Dashboard screenshots &middot; Appendix C &ndash; Complete code base &middot; Appendix D &ndash; Submission files</p></div></div>
"""

files_tbl = table([
    ["Cleaned dataset", "BankChurners_cleaned.csv; BankChurners_cleaned.xlsx (data, field dictionary, quality log, before/after profiles)"],
    ["Technical evidence", "src/01–05 Python scripts; outputs/log_01.txt, log_02.txt; outputs/*.csv"],
    ["Dashboard file", "MIT8339_Retention_Dashboard.html (opens offline in any browser)"],
    ["Screenshots", "Appendix A (data preparation, KPI output) and Appendix B (dashboard pages, filtered view)"],
    ["Analytical report", "This document, Sections 1–8"],
    ["References", "APA 7th edition, below"],
], ["Deliverable", "File / location"], "Submission contents")

repro = """<p class="note"><b>Reproduce:</b> <code>pip install -r requirements.txt</code>, <code>python -m playwright install chromium</code>, place <code>BankChurners.csv</code> in <code>data/</code>, then run scripts 01 to 05 in order from the project root. Fixed random seed (42) for the hold-out split.</p>"""

doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
{cover}
{body}
<h1>References</h1><div class="refs">{refs}</div>
<h1 class="pb">Appendix A &ndash; Data Preparation and KPI Evidence</h1>
{repro}
{after_tbl}
{before_tbl}
{term('outputs/log_01.txt', '$ python src/01_data_preparation.py')}
{sample}
{term('outputs/log_02.txt', '$ python src/02_analysis_kpis.py')}
<h1 class="pb">Appendix B &ndash; Dashboard Screenshots</h1>
<figure>{img('figures/dash_p1_overview.png')}<figcaption>B1. Page 1 &ndash; Executive overview (no filters).</figcaption></figure>
<figure class="pb">{img('figures/dash_p2_retention.png')}<figcaption>B2. Page 2 &ndash; Customer retention analysis.</figcaption></figure>
<figure class="pb">{img('figures/dash_p1_filtered.png')}<figcaption>B3. Slicers applied (Female, income &lt; $40K, Blue card): all KPIs and visuals recalculate for 3,146 customers.</figcaption></figure>
<h1 class="pb">Appendix C &ndash; Complete Code Base</h1>
<p class="note">The dashboard script embeds the Plotly.js library at build time; the listing below is the full source that generates the HTML.</p>
{code_html}
<h1 class="pb">Appendix D &ndash; Submission Files</h1>
{files_tbl}
</body></html>"""

out_html = ROOT / "report" / "report_full.html"
out_html.write_text(doc, encoding="utf-8")
pdf = SUB / f"{FILE_STEM}.pdf"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(out_html.as_uri()); pg.wait_for_timeout(500)
    pg.pdf(path=str(pdf), format="A4", print_background=True, display_header_footer=True,
           header_template="<span></span>",
           footer_template="<div style='font-size:7pt;color:#777;width:100%;padding:0 16mm;display:flex;justify-content:space-between'>"
                           "<span>MIT 8339 &ndash; BI &amp; DSS Virtual Lab</span><span><span class='pageNumber'></span> / <span class='totalPages'></span></span></div>",
           margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
    b.close()
print(f"Saved {pdf.relative_to(ROOT)}")
