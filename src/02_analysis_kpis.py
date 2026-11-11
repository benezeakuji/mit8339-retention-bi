"""
MIT 8339 - Stage 2: Exploratory analysis, KPI development, segmentation and risk validation

Input : data/BankChurners_cleaned.csv  (from 01_data_preparation.py)
Output: outputs/kpis.csv, outputs/kpi_by_segment.csv, outputs/attrited_vs_existing.csv,
        outputs/risk_band_summary.csv, outputs/risk_validation.csv, outputs/summary.json,
        figures/*.png  (static charts used in the report)

Run   : python src/02_analysis_kpis.py   (output is also saved to outputs/log_02.txt)
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, chi2_contingency
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "outputs", ROOT / "figures"
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
class _Tee:
    """Print to the screen and save the same text to a UTF-8 log file (evidence for the report)."""
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.o = sys.stdout
        try:
            self.o.reconfigure(errors="replace")   # Windows consoles cannot show every character
        except AttributeError:
            pass

    def write(self, s):
        self.o.write(s); self.f.write(s)

    def flush(self):
        self.o.flush(); self.f.flush()


sys.stdout = _Tee(OUT / "log_02.txt")


df = pd.read_csv(ROOT / "data" / "BankChurners_cleaned.csv")
N = len(df)
summary = {}

# Palette (validated reference palette; status colours for risk bands)
BLUE, ORANGE = "#2a78d6", "#eb6834"         # Existing, Attrited
RISK = {"Low": "#0ca30c", "Medium": "#fab219", "High": "#d03b3b"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": INK})

# ---------------------------------------------------------------------------
# 1. Portfolio KPIs
# ---------------------------------------------------------------------------
kpis = {
    "Total customers": N,
    "Attrited customers": int(df["Churned"].sum()),
    "Attrition rate (%)": round(df["Churned"].mean() * 100, 2),
    "Active customer ratio (%)": round((df["Months_Inactive_12_mon"] <= 2).mean() * 100, 2),
    "Average credit limit ($)": round(df["Credit_Limit"].mean(), 2),
    "Average utilisation ratio (%)": round(df["Avg_Utilization_Ratio"].mean() * 100, 2),
    "Total transaction amount ($)": int(df["Total_Trans_Amt"].sum()),
    "Avg transactions per customer (12m)": round(df["Total_Trans_Ct"].mean(), 1),
    "Avg product relationship count": round(df["Total_Relationship_Count"].mean(), 2),
    "High-value customer share (%)": round((df["Customer_Value_Class"] == "High value").mean() * 100, 2),
    "High retention-risk customers": int((df["Risk_Band"] == "High").sum()),
    "Transaction value lost to attrition (%)":
        round(df.loc[df["Churned"] == 1, "Total_Trans_Amt"].sum() / df["Total_Trans_Amt"].sum() * 100, 2),
}
pd.Series(kpis, name="value").to_csv(OUT / "kpis.csv", header=True)
summary["kpis"] = kpis
print("PORTFOLIO KPIs"); [print(f"  {k:<42}{v:>14,}") for k, v in kpis.items()]

# ---------------------------------------------------------------------------
# 2. KPIs by segment
# ---------------------------------------------------------------------------
seg_dims = ["Gender", "Age_Band", "Income_Category", "Card_Category", "Education_Level",
            "Marital_Status", "Utilisation_Category", "Txn_Frequency_Category",
            "Customer_Value_Class", "Product_Depth", "Service_Contact_Band", "Tenure_Band", "Risk_Band"]
rows = []
for dim in seg_dims:
    g = df.groupby(dim).agg(customers=("CLIENTNUM", "size"), attrited=("Churned", "sum"),
                            attrition_rate=("Churned", "mean"), avg_credit_limit=("Credit_Limit", "mean"),
                            avg_utilisation=("Avg_Utilization_Ratio", "mean"),
                            avg_trans_amt=("Total_Trans_Amt", "mean"), avg_trans_ct=("Total_Trans_Ct", "mean"),
                            avg_products=("Total_Relationship_Count", "mean")).reset_index()
    g.insert(0, "dimension", dim); g = g.rename(columns={dim: "segment"})
    rows.append(g)
seg = pd.concat(rows)
seg["attrition_rate"] = (seg["attrition_rate"] * 100).round(1)
seg["share_of_customers"] = (seg["customers"] / N * 100).round(1)
seg["lift_vs_portfolio"] = (seg["attrition_rate"] / kpis["Attrition rate (%)"]).round(2)
seg.round(2).to_csv(OUT / "kpi_by_segment.csv", index=False)

# Demographic churn spread (min/max rate across categories) - to test demographic hypotheses
demo_spread = {}
for dim in ["Gender", "Age_Band", "Income_Category", "Education_Level", "Marital_Status", "Card_Category"]:
    s = seg[seg.dimension == dim]
    ct = pd.crosstab(df[dim], df["Churned"])
    demo_spread[dim] = {"min": float(s.attrition_rate.min()), "max": float(s.attrition_rate.max()),
                        "chi2_p": float(chi2_contingency(ct)[1])}
summary["demographic_spread"] = demo_spread

# ---------------------------------------------------------------------------
# 3. Attrited vs existing comparison (>= 4 variables) with Mann-Whitney U tests
# ---------------------------------------------------------------------------
comp_vars = ["Total_Trans_Ct", "Total_Trans_Amt", "Total_Ct_Chng_Q4_Q1", "Total_Amt_Chng_Q4_Q1",
             "Total_Revolving_Bal", "Avg_Utilization_Ratio", "Total_Relationship_Count",
             "Months_Inactive_12_mon", "Contacts_Count_12_mon", "Credit_Limit", "Customer_Age", "Months_on_book"]
a, e = df[df.Churned == 1], df[df.Churned == 0]
comp = []
for v in comp_vars:
    p = mannwhitneyu(a[v], e[v]).pvalue
    comp.append({"variable": v, "attrited_mean": a[v].mean(), "existing_mean": e[v].mean(),
                 "attrited_median": a[v].median(), "existing_median": e[v].median(),
                 "pct_difference_of_means": (a[v].mean() / e[v].mean() - 1) * 100,
                 "mann_whitney_p": p, "significant_at_0.01": p < 0.01})
comp = pd.DataFrame(comp)
comp.round(4).to_csv(OUT / "attrited_vs_existing.csv", index=False)
summary["comparison"] = comp.set_index("variable").round(3).to_dict(orient="index")
print("\nATTRITED vs EXISTING"); print(comp.round(3).to_string(index=False))

# ---------------------------------------------------------------------------
# 4. Pattern evidence
# ---------------------------------------------------------------------------
def rate(mask):
    return float(round(df.loc[mask, "Churned"].mean() * 100, 1)), int(mask.sum())

patterns = {
    "trans_ct_le_60": rate(df.Total_Trans_Ct <= 60), "trans_ct_gt_60": rate(df.Total_Trans_Ct > 60),
    "ct_chng_lt_0.6": rate(df.Total_Ct_Chng_Q4_Q1 < 0.6), "ct_chng_ge_0.6": rate(df.Total_Ct_Chng_Q4_Q1 >= 0.6),
    "zero_revolving": rate(df.Total_Revolving_Bal == 0), "revolving_gt_0": rate(df.Total_Revolving_Bal > 0),
    "products_1_2": rate(df.Total_Relationship_Count <= 2), "products_3_plus": rate(df.Total_Relationship_Count >= 3),
    "contacts_0_1": rate(df.Contacts_Count_12_mon <= 1), "contacts_4_plus": rate(df.Contacts_Count_12_mon >= 4),
    "contacts_6": rate(df.Contacts_Count_12_mon == 6),
    "inactive_1": rate(df.Months_Inactive_12_mon == 1), "inactive_3_plus": rate(df.Months_Inactive_12_mon >= 3),
    "low_freq_and_decline": rate((df.Total_Trans_Ct <= 60) & (df.Total_Ct_Chng_Q4_Q1 < 0.6)),
}
summary["patterns"] = patterns
print("\nPATTERNS (attrition %, n)"); [print(f"  {k:<24}{v}") for k, v in patterns.items()]

# ---------------------------------------------------------------------------
# 5. Risk-band summary and validation
# ---------------------------------------------------------------------------
order = ["Low", "Medium", "High"]
rb = df.groupby("Risk_Band").agg(customers=("CLIENTNUM", "size"), attrited=("Churned", "sum"),
                                  avg_trans_amt=("Total_Trans_Amt", "mean"),
                                  total_trans_amt=("Total_Trans_Amt", "sum")).reindex(order)
rb["share_of_customers_pct"] = rb.customers / N * 100
rb["attrition_rate_pct"] = rb.attrited / rb.customers * 100
rb["share_of_all_attriters_pct"] = rb.attrited / df.Churned.sum() * 100
rb.round(2).to_csv(OUT / "risk_band_summary.csv")
summary["risk_bands"] = rb.round(2).to_dict(orient="index")
print("\nRISK BANDS"); print(rb.round(1).to_string())

# Hold-out validation: the rule score has no fitted parameters, so we evaluate it on an unseen
# 30% test split and benchmark it against a logistic regression trained on the 70% split.
feat = ["Total_Trans_Ct", "Total_Ct_Chng_Q4_Q1", "Total_Revolving_Bal", "Total_Relationship_Count",
        "Months_Inactive_12_mon", "Contacts_Count_12_mon", "Total_Trans_Amt", "Total_Amt_Chng_Q4_Q1",
        "Avg_Utilization_Ratio", "Credit_Limit", "Customer_Age", "Dependent_count", "Months_on_book"]
tr, te = train_test_split(df, test_size=0.3, random_state=42, stratify=df.Churned)
logit = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(tr[feat], tr.Churned)
auc_rule = roc_auc_score(te.Churned, te.Risk_Score)
auc_logit = roc_auc_score(te.Churned, logit.predict_proba(te[feat])[:, 1])
te_hi = te.Risk_Band == "High"
val = {"test_customers": len(te), "auc_rule_score": round(auc_rule, 3), "auc_logistic_benchmark": round(auc_logit, 3),
       "high_band_precision_pct": round(te.loc[te_hi, "Churned"].mean() * 100, 1),
       "high_band_recall_pct": round(te.loc[te_hi, "Churned"].sum() / te.Churned.sum() * 100, 1),
       "high_or_medium_recall_pct": round(te.loc[te.Risk_Band != "Low", "Churned"].sum() / te.Churned.sum() * 100, 1),
       "low_band_attrition_pct": round(te.loc[te.Risk_Band == "Low", "Churned"].mean() * 100, 1)}
pd.Series(val).to_csv(OUT / "risk_validation.csv", header=["value"])
summary["validation"] = val
print("\nHOLD-OUT VALIDATION"); [print(f"  {k:<28}{v}") for k, v in val.items()]

# Point contribution of each rule (attrition when rule fires vs not)
rules = {"Trans count <= 60 (+3)": df.Total_Trans_Ct <= 60, "Q4/Q1 count change < 0.6 (+2)": df.Total_Ct_Chng_Q4_Q1 < 0.6,
         "Revolving balance < $500 (+2)": df.Total_Revolving_Bal < 500, "Products <= 2 (+1)": df.Total_Relationship_Count <= 2,
         "Inactive >= 3 months (+1)": df.Months_Inactive_12_mon >= 3, "Contacts >= 4 (+1)": df.Contacts_Count_12_mon >= 4}
rule_tbl = pd.DataFrame([{"rule": k, "customers_flagged": int(m.sum()), "attrition_if_true_pct": df.loc[m, "Churned"].mean() * 100,
                          "attrition_if_false_pct": df.loc[~m, "Churned"].mean() * 100} for k, m in rules.items()])
rule_tbl.round(1).to_csv(OUT / "risk_rules.csv", index=False)
summary["rules"] = rule_tbl.round(1).to_dict(orient="records")
print("\nRULES"); print(rule_tbl.round(1).to_string(index=False))

# Heatmap data: attrition by transaction frequency x product depth
hm = df.pivot_table(index="Txn_Frequency_Category", columns="Product_Depth", values="Churned", aggfunc="mean") * 100
hm = hm.reindex(["Very low (<=40)", "Low (41-60)", "Medium (61-80)", "High (>80)"])[["Thin (1-2)", "Moderate (3-4)", "Deep (5-6)"]]
hm.round(1).to_csv(OUT / "heatmap_freq_x_products.csv")
summary["heatmap"] = hm.round(1).to_dict()

(OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")

# ---------------------------------------------------------------------------
# 6. Static figures for the report
# ---------------------------------------------------------------------------
def bar_rate(ax, dim, order_, title):
    s = seg[seg.dimension == dim].set_index("segment").reindex(order_)
    ax.bar(range(len(s)), s.attrition_rate, color=BLUE, width=0.6)
    ax.axhline(kpis["Attrition rate (%)"], color=MUTED, lw=1, ls="--")
    for i, v in enumerate(s.attrition_rate):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(s))); ax.set_xticklabels(order_, fontsize=8)
    ax.set_ylabel("Attrition rate (%)"); ax.set_title(title, loc="left"); ax.grid(axis="y", color=GRID, lw=.6)
    ax.set_axisbelow(True)

fig, axs = plt.subplots(2, 2, figsize=(11, 7))
bar_rate(axs[0, 0], "Txn_Frequency_Category", ["Very low (<=40)", "Low (41-60)", "Medium (61-80)", "High (>80)"],
         "Attrition by transaction frequency (12 months)")
bar_rate(axs[0, 1], "Product_Depth", ["Thin (1-2)", "Moderate (3-4)", "Deep (5-6)"], "Attrition by product relationship depth")
bar_rate(axs[1, 0], "Service_Contact_Band", ["0-1 contacts", "2-3 contacts", "4+ contacts"], "Attrition by service contacts (12 months)")
bar_rate(axs[1, 1], "Utilisation_Category", ["Zero (0%)", "Low (0-30%)", "Moderate (30-70%)", "High (>70%)"],
         "Attrition by credit utilisation")
fig.text(0.01, 0.005, f"Dashed line = portfolio attrition rate ({kpis['Attrition rate (%)']:.1f}%). n = {N:,} customers.",
         color=MUTED, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig_segment_attrition.png", dpi=170); plt.close(fig)

fig, axs = plt.subplots(1, 4, figsize=(12, 3.6))
for ax, v, lab in zip(axs, ["Total_Trans_Ct", "Total_Ct_Chng_Q4_Q1", "Total_Revolving_Bal", "Total_Relationship_Count"],
                      ["Transactions (12m)", "Q4/Q1 count change", "Revolving balance ($)", "Products held"]):
    bp = ax.boxplot([e[v], a[v]], tick_labels=["Existing", "Attrited"], patch_artist=True, widths=.5,
                    medianprops=dict(color=INK), flierprops=dict(marker=".", markersize=2, alpha=.3))
    for patch, c in zip(bp["boxes"], [BLUE, ORANGE]):
        patch.set_facecolor(c); patch.set_alpha(.75); patch.set_edgecolor(c)
    ax.set_title(lab, loc="left", fontsize=10); ax.grid(axis="y", color=GRID, lw=.6); ax.set_axisbelow(True)
fig.suptitle("Attrited vs existing customers - distribution of key behaviour variables", x=0.01, ha="left",
             fontweight="bold", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig_attrited_vs_existing.png", dpi=170); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 3.6))
x = np.arange(3)
ax.bar(x - .18, rb.share_of_customers_pct, .34, color="#86b6ef", label="Share of customers")
ax.bar(x + .18, rb.share_of_all_attriters_pct, .34, color=[RISK[k] for k in order], label="Share of all attriters")
for i in range(3):
    ax.text(i - .18, rb.share_of_customers_pct.iloc[i] + 1, f"{rb.share_of_customers_pct.iloc[i]:.0f}%", ha="center", fontsize=8)
    ax.text(i + .18, rb.share_of_all_attriters_pct.iloc[i] + 1, f"{rb.share_of_all_attriters_pct.iloc[i]:.0f}%", ha="center", fontsize=8)
    ax.text(i, -11, f"churn rate {rb.attrition_rate_pct.iloc[i]:.1f}%", ha="center", fontsize=8, color=MUTED)
ax.set_xticks(x); ax.set_xticklabels([f"{k} risk" for k in order]); ax.set_ylim(-14, 85)
ax.axhline(0, color=GRID); ax.set_ylabel("%")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#86b6ef", label="Share of customers"),
                   Patch(color="#7a7974", label="Share of all attriters (coloured by risk band)")],
          frameon=False, fontsize=8, loc="upper left")
ax.set_title("Risk bands: customer share vs share of attriters", loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig_risk_bands.png", dpi=170); plt.close(fig)

print("\nSaved outputs/*.csv, outputs/summary.json and figures/*.png")
