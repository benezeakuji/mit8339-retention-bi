// MIT 8339 - Stage 6: 5-minute presentation deck (PowerPoint, with speaker notes)
// Run: node src/06_build_deck.js   (after stages 01-04)
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
// Optional theme writer. Without it the deck uses fixed hex colours (identical look, just not re-themable in PowerPoint).
let applyTheme = null;
try { if (process.env.PPTX_THEME_HELPER) ({ applyTheme } = require(process.env.PPTX_THEME_HELPER)); } catch (e) { applyTheme = null; }

const ROOT = path.resolve(__dirname, "..");
const S = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/summary.json")));
const OUTFILE = path.join(ROOT, "submission", "MIT8339_StudentName_StudentID_Presentation.pptx");

const THEME = {
  name: "Retention Intelligence",
  headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "0D366B", lt2: "EEF3FA",
    accent1: "0D366B", accent2: "EB6834", accent3: "2A78D6", accent4: "0CA30C", accent5: "FAB219", accent6: "D03B3B",
    hlink: "2A78D6", folHlink: "6250D6" },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Customer Retention and Performance Intelligence";
pres.author = "[Student Name]";
const C = applyTheme ? pres.SchemeColor : {
  text1: HEX.dk1, text2: HEX.dk2, background1: HEX.lt1, background2: HEX.lt2,
  accent1: HEX.accent1, accent2: HEX.accent2, accent3: HEX.accent3, accent4: HEX.accent4, accent5: HEX.accent5, accent6: HEX.accent6 };

pres.defineSlideMaster({
  title: "Dark Title", background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.0, w: 11.9, h: 1.9, fontSize: 40, bold: true, color: C.background1, valign: "bottom", align: "left", fontFace: "Cambria" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.1, w: 11.9, h: 1.6, fontSize: 18, color: C.background2, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Dark Content", background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.5, w: 12.1, h: 0.9, fontSize: 32, bold: true, color: C.background1, valign: "middle", align: "left", fontFace: "Cambria", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 1.8, w: 12.1, h: 4.8, fontSize: 18, color: C.background1, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content", background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 32, bold: true, color: C.text2, valign: "middle", align: "left", fontFace: "Cambria", margin: 0 }, text: "" } },
    { text: { text: "MIT 8339 · BI & DSS Virtual Lab", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: "7A7974", margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "7A7974", align: "right" },
});

const sec = (t) => pres.addSection({ title: t });
const content = (title, section) => { const s = pres.addSlide({ masterName: "Content", sectionTitle: section }); s.addText(title, { placeholder: "title" }); return s; };
const card = (s, x, y, w, h, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: name });
const stat = (s, x, y, w, big, label, color, name) => {
  card(s, x, y, w, 1.55, name + " card");
  s.addText(big, { x: x + 0.25, y: y + 0.15, w: w - 0.5, h: 0.8, fontSize: 36, bold: true, color, fontFace: "Cambria", margin: 0, isTextBox: true, objectName: name + " value" });
  s.addText(label, { x: x + 0.25, y: y + 0.92, w: w - 0.5, h: 0.5, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: name + " label" });
};
const K = S.kpis, RB = S.risk_bands, V = S.validation, P = S.patterns;

// 1 Title ------------------------------------------------------------------
sec("Introduction");
let s = pres.addSlide({ masterName: "Dark Title", sectionTitle: "Introduction" });
s.addText("Customer Retention and Performance Intelligence", { placeholder: "title" });
s.addText([{ text: "A BI and decision-support system for a Nigerian commercial bank", options: { breakLine: true } },
  { text: "MIT 8339 · [Student Name] · [Student ID] · November 2026", options: { fontSize: 14 } }], { placeholder: "body" });
s.addNotes(`Good day. My name is [Student Name], and this is my MIT 8339 virtual lab: a business intelligence and decision support system for customer retention at a Nigerian commercial bank. In the next five minutes I will cover the business problem, how I prepared the data, what the analysis shows, the dashboard, and my recommendations.`);

// 2 Problem + KPIs ---------------------------------------------------------
s = content("1 in 6 card customers leave before the bank sees it", "Introduction");
s.addText([
  { text: "Decision to support", options: { bold: true, color: C.text2, breakLine: true } },
  { text: "Which existing customers should receive a retention intervention, of what type, and in what order?", options: {} },
], { x: 0.6, y: 1.5, w: 12.1, h: 0.9, fontSize: 18, color: C.text1, margin: 0, isTextBox: true, objectName: "decision statement" });
const kp = [[`${K["Attrition rate (%)"].toFixed(1)}%`, `attrition rate (${K["Attrited customers"].toLocaleString()} of ${K["Total customers"].toLocaleString()})`, C.accent2],
  [`${K["Active customer ratio (%)"].toFixed(1)}%`, "active customer ratio (inactive ≤ 2 months)", C.text2],
  [`${K["Average utilisation ratio (%)"].toFixed(1)}%`, "average credit utilisation", C.text2],
  [`$${(K["Total transaction amount ($)"] / 1e6).toFixed(1)}M`, `12-month spend; ${K["Transaction value lost to attrition (%)"].toFixed(1)}% from attriters`, C.text2]];
kp.forEach((k, i) => stat(s, 0.6 + i * 3.08, 2.75, 2.85, k[0], k[1], k[2], "KPI " + (i + 1)));
s.addText([
  { text: "Other KPIs tracked: ", options: { bold: true } },
  { text: `average credit limit $${Math.round(K["Average credit limit ($)"]).toLocaleString()} · ${K["Avg product relationship count"].toFixed(2)} products per customer · ${K["High retention-risk customers"].toLocaleString()} customers in the high-risk band` },
], { x: 0.6, y: 4.65, w: 12.1, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, objectName: "other KPIs" });
s.addText("Dataset: Credit Card Customers / BankChurners (Goyal, 2020), 10,127 customers. US-origin data; values in USD.", { x: 0.6, y: 6.4, w: 12.1, h: 0.35, fontSize: 11, color: "52514E", margin: 0, isTextBox: true, objectName: "source" });
s.addNotes(`The bank is losing retail card customers, but attrition is only visible after an account closes. The decision the system must support is forward-looking: which existing customers should get a retention intervention, what kind, and in what order. I used the recommended BankChurners dataset of 10,127 customers. Sixteen point one percent have attrited. Only about 55 percent were active in at least ten of the last twelve months, and average utilisation is 27 percent. Attriters generated 11 percent of transaction value, so the loss is real but recoverable if we act early.`);

// 3 Method -----------------------------------------------------------------
sec("Method");
s = content("A reproducible pipeline from raw file to decision", "Method");
const steps = [["1", "Data source", "BankChurners CSV, verified at 10,127 rows and 1,627 attriters"],
  ["2", "Transformation", "Python/Pandas: profiling, label fixes, 'Unknown' kept as a category, 12 derived fields"],
  ["3", "Analysis", "KPIs, segment rates, Mann-Whitney and χ² tests, rule-based risk score"],
  ["4", "Reporting", "Two-page interactive dashboard, six slicers, report PDF"],
  ["5", "Decision support", "Risk bands, watchlist, prioritised actions"]];
steps.forEach((st, i) => {
  const x = 0.6 + i * 2.48;
  card(s, x, 1.6, 2.3, 2.7, "step " + st[0]);
  s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 1.8, w: 0.55, h: 0.55, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: "step badge " + st[0] });
  s.addText(st[0], { x: x + 0.2, y: 1.8, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(st[1], { x: x + 0.2, y: 2.5, w: 1.95, h: 0.4, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText(st[2], { x: x + 0.2, y: 2.95, w: 1.95, h: 1.3, fontSize: 13, color: C.text1, margin: 0, valign: "top", isTextBox: true });
});
s.addText([
  { text: "Cleaning decisions", options: { bold: true, color: C.text2, breakLine: true } },
  { text: "No nulls or duplicates; 30% of rows had an 'Unknown' education, marital or income value, kept and flagged rather than deleted or imputed", options: { bullet: true, breakLine: true } },
  { text: "IQR outliers (e.g., high limits, heavy spenders) retained as valid behaviour and flagged; balance identity verified on every row", options: { bullet: true } },
], { x: 0.6, y: 4.6, w: 12.1, h: 1.7, fontSize: 15, color: C.text1, margin: 0, paraSpaceAfter: 6, isTextBox: true, objectName: "cleaning notes" });
s.addNotes(`The workflow follows the BI/DSS process and is fully scripted in Python, so anyone can re-run it. The data had no system nulls or duplicate customers, but 30 percent of rows had an "Unknown" education, marital or income value. I kept these as an explicit category and flagged them, because deleting them would remove almost a third of the portfolio and imputing would invent facts. Outliers such as very high credit limits were real customers, so I flagged rather than removed them. I then created twelve analytical fields, including age band, utilisation category, value class and a risk band.`);

// 4 Findings ---------------------------------------------------------------
sec("Findings");
s = content("Behaviour, not demographics, explains attrition", "Findings");
const freq = ["Very low (<=40)", "Low (41-60)", "Medium (61-80)", "High (>80)"];
const segFile = fs.readFileSync(path.join(ROOT, "outputs/kpi_by_segment.csv"), "utf8").trim().split("\n").map((l) => l.split(","));
const hdr = segFile[0]; const iD = hdr.indexOf("dimension"), iS = hdr.indexOf("segment"), iR = hdr.indexOf("attrition_rate");
const rate = (dim, seg) => +segFile.find((r) => r[iD] === dim && r[iS] === seg)[iR];
s.addChart(pres.charts.BAR, [{ name: "Attrition rate (%)", labels: ["≤40", "41–60", "61–80", ">80"], values: freq.map((f) => rate("Txn_Frequency_Category", f)) }], {
  x: 0.6, y: 1.5, w: 6.2, h: 4.9, barDir: "col", chartColors: [HEX.accent3], showLegend: false,
  showTitle: true, title: "Attrition rate (%) by transactions in last 12 months", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0\"%\"", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
  catAxisLabelColor: "52514E", valAxisLabelColor: "52514E", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  valGridLine: { color: "E4E3DF", size: 0.5 }, catGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 45, barGapWidthPct: 60, objectName: "frequency chart",
});
const pts = [
  ["Declining activity", `≤ 60 transactions: ${P.trans_ct_le_60[0]}% churn vs ${P.trans_ct_gt_60[0]}%. Falling Q4/Q1 activity: ${P["ct_chng_lt_0.6"][0]}% vs ${P["ct_chng_ge_0.6"][0]}%.`],
  ["Thin relationship, unused card", `1–2 products: ${P.products_1_2[0]}% vs ${P.products_3_plus[0]}%. Zero revolving balance: ${P.zero_revolving[0]}% vs ${P.revolving_gt_0[0]}%.`],
  ["Service friction", `4+ contacts: ${P.contacts_4_plus[0]}% churn; all ${P.contacts_6[1]} customers with 6 contacts left.`],
  ["Demographics are weak", "Income and gender move churn only 13.5–17.4%; age and card type not significant."],
];
pts.forEach((p, i) => {
  const y = 1.5 + i * 1.22;
  s.addShape(pres.shapes.OVAL, { x: 7.2, y: y + 0.08, w: 0.42, h: 0.42, fill: { color: i < 3 ? C.accent2 : C.background2 }, line: { color: i < 3 ? C.accent2 : C.background2 }, objectName: "finding marker " + (i + 1) });
  s.addText(i < 3 ? String(i + 1) : "–", { x: 7.2, y: y + 0.08, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: i < 3 ? C.background1 : C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText([{ text: p[0], options: { bold: true, color: C.text2, breakLine: true, fontSize: 16 } }, { text: p[1], options: { fontSize: 14 } }],
    { x: 7.8, y, w: 4.9, h: 1.1, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "finding " + (i + 1) });
});
s.addNotes(`Comparing attriters with existing customers, ten of twelve variables differ significantly. Three patterns stand out. First, declining activity: customers with sixty or fewer transactions a year churn at 34 percent, against under 4 percent above that level, and a falling quarter-on-quarter trend gives a similar signal. Second, thin relationships: customers with one or two products, or who never revolve a balance, churn at roughly three times the rate of others. Third, service friction: churn rises with every contact, and all 54 customers with six contacts left. By contrast, income and gender barely move the rate, so demographic targeting alone would waste budget.`);

// 5 Risk -------------------------------------------------------------------
s = content("18% of customers carry 68% of attrition", "Findings");
const bands = ["Low", "Medium", "High"];
s.addChart(pres.charts.BAR, [
  { name: "Share of customers (%)", labels: bands.map((b) => b + " risk"), values: bands.map((b) => +RB[b].share_of_customers_pct.toFixed(1)) },
  { name: "Share of all attriters (%)", labels: bands.map((b) => b + " risk"), values: bands.map((b) => +RB[b].share_of_all_attriters_pct.toFixed(1)) },
], {
  x: 0.6, y: 1.5, w: 6.6, h: 4.9, barDir: "col", chartColors: ["86B6EF", HEX.accent2], showLegend: true, legendPos: "t", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: "52514E",
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0\"%\"", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
  catAxisLabelColor: "52514E", valAxisLabelColor: "52514E", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  valGridLine: { color: "E4E3DF", size: 0.5 }, catGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 80, barGapWidthPct: 50, objectName: "risk band chart",
});
stat(s, 7.6, 1.5, 2.45, `${RB.High.attrition_rate_pct.toFixed(0)}%`, "churn in the High band", C.accent6, "high churn");
stat(s, 10.25, 1.5, 2.45, `${RB.Low.attrition_rate_pct.toFixed(1)}%`, "churn in the Low band", C.accent4, "low churn");
stat(s, 7.6, 3.25, 2.45, `${V.auc_rule_score.toFixed(2)}`, `hold-out AUC (logistic benchmark ${V.auc_logistic_benchmark.toFixed(2)})`, C.text2, "auc");
stat(s, 10.25, 3.25, 2.45, "706", "High-band customers still active", C.accent2, "watchlist");
s.addText([
  { text: "Score 0–10: ", options: { bold: true } },
  { text: "≤ 60 transactions (+3), falling activity (+2), revolving balance < $500 (+2), 1–2 products (+1), 3+ months inactive (+1), 4+ contacts (+1). Bands: Low 0–3, Medium 4–5, High 6–10." },
], { x: 7.6, y: 5.0, w: 5.1, h: 1.4, fontSize: 13, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "score rules" });
s.addNotes(`To turn this into action, I built a transparent rule-based score from those six behaviours, with points a relationship manager can explain. The High band holds 18 percent of customers but 68 percent of all attriters, with a 61 percent churn rate, while the Low band churns at under 3 percent. On a 30 percent hold-out sample the score reaches an AUC of 0.88, close to a logistic regression at 0.91, so we give up very little accuracy in exchange for explainability. 706 High-band customers are still active, and they form the immediate watchlist.`);

// 6 Dashboard --------------------------------------------------------------
sec("Dashboard and actions");
s = content("Dashboard: executive overview and retention analysis", "Dashboard and actions");
const shot = (f, x, name) => {
  s.addShape(pres.shapes.RECTANGLE, { x: x - 0.03, y: 1.47, w: 5.96, h: 3.86, fill: { color: "FFFFFF" }, line: { color: "D9D7D1", width: 1 }, shadow: { type: "outer", color: "000000", opacity: 0.18, blur: 6, offset: 2, angle: 90 }, objectName: name + " frame" });
  s.addImage({ path: path.join(ROOT, "figures", f), x, y: 1.5, w: 5.9, h: 3.8, sizing: { type: "cover", w: 5.9, h: 3.8 }, altText: name, objectName: name });
};
shot("dash_p1_overview.png", 0.6, "Page 1 executive overview screenshot");
shot("dash_p2_retention.png", 6.8, "Page 2 retention analysis screenshot");
s.addText("Page 1 · Executive overview", { x: 0.6, y: 5.45, w: 5.9, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true });
s.addText("Page 2 · Retention analysis", { x: 6.8, y: 5.45, w: 5.9, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true });
s.addText("7 KPI cards · 9 visuals · 6 slicers (gender, age, income, card, risk band, status) · watchlist with pseudonymised IDs · runs offline in any browser",
  { x: 0.6, y: 5.9, w: 12.1, h: 0.6, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, objectName: "dashboard summary" });
s.addNotes(`The dashboard has two pages. Page one is the executive overview: seven KPI cards, the risk segmentation, and attrition by income, card category and value class. Page two is for the retention team: transaction frequency, a heatmap of activity by product depth, inactivity and contact trends, a spend scatter, a live comparison table and the high-risk watchlist. Six slicers filter every visual at once. I used bars from zero for rates, showed sample sizes on small groups like Platinum cards, and avoided pie charts and dual axes so nothing is misread.`);

// 7 Recommendations --------------------------------------------------------
s = content("Four prioritised actions for management", "Dashboard and actions");
const recs = [["Now", "High-risk save programme", "706 active High-band customers to relationship managers within 30 days, with a usage incentive.", C.accent6],
  ["0–3 months", "Activity early warning", "Monthly trigger at ≤ 60 transactions or falling Q4/Q1 activity, followed by a usage campaign.", C.accent2],
  ["0–3 months", "Service recovery", "Route customers with 4+ contacts to a senior resolution team; capture contact-reason codes.", C.accent2],
  ["3–6 months", "Relationship deepening", "Cross-sell a second and third product to 2,153 thin-relationship customers.", C.text2]];
recs.forEach((r, i) => {
  const x = 0.6 + (i % 2) * 6.15, y = 1.5 + Math.floor(i / 2) * 2.35;
  card(s, x, y, 5.95, 2.15, "recommendation " + (i + 1));
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: y + 0.25, w: 1.5, h: 0.4, rectRadius: 0.2, fill: { color: r[3] }, line: { color: r[3] }, objectName: "priority tag " + (i + 1) });
  s.addText(r[0], { x: x + 0.25, y: y + 0.25, w: 1.5, h: 0.4, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(`${i + 1}. ${r[1]}`, { x: x + 0.25, y: y + 0.8, w: 5.45, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText(r[2], { x: x + 0.25, y: y + 1.25, w: 5.45, h: 0.8, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
});
s.addText("Measure every action against a control group so the bank knows what each campaign actually saved.", { x: 0.6, y: 6.35, w: 12.1, h: 0.4, fontSize: 13, italic: true, color: "52514E", margin: 0, isTextBox: true, objectName: "measurement note" });
s.addNotes(`My recommendations are prioritised. First, start a save programme now for the 706 active high-risk customers. Second, within three months, automate an early-warning trigger when activity falls, linked to a usage campaign. Third, treat repeated contacts as a complaint signal and route those customers to service recovery, while starting to capture contact reasons. Fourth, over three to six months, deepen thin relationships through cross-selling. Each action should be tested against a control group so the bank can measure what it actually saved.`);

// 8 Limits + close ---------------------------------------------------------
s = pres.addSlide({ masterName: "Dark Content", sectionTitle: "Dashboard and actions" });
s.addText("Limitations, governance and conclusion", { placeholder: "title" });
s.addText([
  { text: "Limits: one snapshot, so association not cause; US data must be recalibrated for Nigeria; contacts are only a complaint proxy.", options: { bullet: true, breakLine: true } },
  { text: "Governance: NDPA 2023 lawful basis and privacy notice, pseudonymised watchlist, role-based access, and no use of scores to cut limits or service.", options: { bullet: true, breakLine: true } },
  { text: "Conclusion: engagement, product depth and service friction drive attrition; an explainable score targets the 18% who matter most.", options: { bullet: true } },
], { placeholder: "body", fontSize: 20, paraSpaceAfter: 18 });
s.addNotes(`Finally, limitations. This is a single snapshot, so the patterns show association rather than cause. The data comes from a US card issuer, so thresholds must be recalibrated on the bank's own Nigerian data. And there is no complaint field, so contacts are a proxy. On governance, risk scoring is personal-data processing under the Nigeria Data Protection Act 2023, so the bank needs a lawful basis, a privacy notice, pseudonymised outputs and role-based access, and the score must never be used to reduce limits or service for flagged customers. In conclusion, attrition here is driven by engagement, product depth and service friction, and a simple, explainable score lets the bank focus its retention effort on the 18 percent of customers who matter most. Thank you.`);

(async () => {
  await pres.writeFile({ fileName: OUTFILE });
  if (applyTheme) await applyTheme(OUTFILE, THEME);
  console.log("Saved " + path.relative(ROOT, OUTFILE));
})();
