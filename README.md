# Customer Retention & Performance Intelligence (MIT 8339 BI/DSS Virtual Lab)

A reproducible business-intelligence and decision-support workflow for credit-card customer attrition,
built on the BankChurners dataset (10,127 customers). It covers data profiling and cleaning, KPI
development, attrited-vs-existing analysis, a rule-based retention-risk score, an interactive two-page
dashboard, and the written report.

**Course:** MIT 8339 – Business Intelligence and Decision Support Systems, Master of Information Technology, Miva Open University
**Author:** Benjamin Ezeakuji

## Key results

| Measure | Value |
|---|---|
| Customers / attrited | 10,127 / 1,627 |
| Attrition rate | 16.1% |
| Churn, ≤ 60 transactions vs > 60 (12 months) | 34.4% vs 3.9% |
| High risk band: share of customers / share of attriters | 18.0% / 68.4% |
| High band attrition rate | 61.2% |
| Risk score hold-out AUC (logistic regression benchmark) | 0.883 (0.910) |

## Repository structure

```
data/         BankChurners.csv (raw input)
              BankChurners_cleaned.csv / .xlsx (cleaned output, field dictionary, quality log)
src/          01_data_preparation.py     profiling, cleaning, derived fields, export
              02_analysis_kpis.py        KPIs, segment tables, statistical tests, risk validation, report figures
              03_build_dashboard.py      two-page interactive dashboard (single offline HTML file)
              04_capture_screenshots.py  dashboard screenshots (headless Chromium)
              report_tables.py           shared report tables and references
              05_build_report.py         report as PDF
              06_build_deck.js           presentation deck (.pptx)
              07_build_word_report.py    report as editable Word (.docx)
report/       report_body.html (narrative source for the PDF and Word report)
outputs/      KPI, quality, comparison and risk tables (CSV), summary.json, run logs
figures/      report charts and dashboard screenshots
dashboard/    MIT8339_Retention_Dashboard.html (open in any browser)
```

## How to run

Requires Python 3.10+ and, for the deck only, Node.js 18+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

python src/01_data_preparation.py
python src/02_analysis_kpis.py
python src/03_build_dashboard.py
python src/04_capture_screenshots.py
python src/05_build_report.py
python src/07_build_word_report.py

npm install          # deck only
node src/06_build_deck.js
```

Built files go to `submission/`, which git ignores. The hold-out split uses a fixed random seed (42), so the results are reproducible.

## Method notes

- **Missing values:** no system nulls. "Unknown" in Education, Marital status and Income (30.1% of rows) is kept as a category and flagged, not imputed or deleted.
- **Outliers:** flagged with the 1.5 × IQR rule and kept, because they are valid customer behaviour.
- **Risk score (0–10):** ≤ 60 transactions (+3), Q4/Q1 count change < 0.6 (+2), revolving balance < $500 (+2), ≤ 2 products (+1), ≥ 3 inactive months (+1), ≥ 4 contacts (+1). Bands: Low 0–3, Medium 4–5, High 6–10.
- **Privacy:** the dashboard watchlist shows pseudonymised references only.

## Data source

Goyal, S. (2020). *Credit card customers* [Data set]. Kaggle.
https://www.kaggle.com/datasets/sakshigoyal7/credit-card-customers

`data/BankChurners.csv` was taken from a public GitHub mirror of this dataset and checked against the published counts (10,127 rows, 1,627 attrited). The data is US-origin and in USD.
