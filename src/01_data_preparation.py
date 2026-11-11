"""
MIT 8339 - Business Intelligence and Decision Support Systems (Virtual Lab)
Stage 1: Data collection, profiling, cleaning and transformation

Input : data/BankChurners.csv  (Credit Card Customers / BankChurners dataset, Goyal, 2020)
Output: data/BankChurners_cleaned.csv
        data/BankChurners_cleaned.xlsx   (cleaned data + data dictionary + quality log)
        outputs/dq_before.csv, outputs/dq_after.csv, outputs/dq_checks.csv, outputs/outlier_profile.csv

Run   : python src/01_data_preparation.py   (from the project root; output is also saved to outputs/log_01.txt)
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "BankChurners.csv"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
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


sys.stdout = _Tee(OUT / "log_01.txt")


EXPECTED_ROWS = 10_127          # documented size of the Kaggle dataset
EXPECTED_ATTRITED = 1_627       # documented number of attrited customers


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Column-level data-quality profile: type, missing, 'Unknown' placeholders, distinct values."""
    rows = []
    for c in df.columns:
        s = df[c]
        unknown = int((s.astype(str).str.strip().str.lower() == "unknown").sum())
        rows.append({
            "column": c,
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "missing_nan": int(s.isna().sum()),
            "unknown_placeholder": unknown,
            "missing_or_unknown_pct": round((s.isna().sum() + unknown) / len(s) * 100, 2),
            "distinct": int(s.nunique()),
            "example": s.iloc[0],
        })
    return pd.DataFrame(rows)


def iqr_outliers(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Tukey IQR rule (1.5 x IQR) - flags, does not delete."""
    rows = []
    for c in cols:
        q1, q3 = df[c].quantile([.25, .75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n = int(((df[c] < lo) | (df[c] > hi)).sum())
        rows.append({"column": c, "q1": q1, "q3": q3, "lower_fence": round(lo, 2),
                     "upper_fence": round(hi, 2), "min": df[c].min(), "max": df[c].max(),
                     "outliers": n, "outlier_pct": round(n / len(df) * 100, 2)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Load and verify acquisition
# ---------------------------------------------------------------------------
raw = pd.read_csv(RAW)
print(f"Loaded {RAW.name}: {raw.shape[0]:,} rows x {raw.shape[1]} columns")
assert len(raw) == EXPECTED_ROWS, "Row count does not match the documented dataset"
assert (raw["Attrition_Flag"] == "Attrited Customer").sum() == EXPECTED_ATTRITED

before = profile(raw)
before.to_csv(OUT / "dq_before.csv", index=False)
print("\nBEFORE - data-quality profile")
print(before[["column", "dtype", "missing_nan", "unknown_placeholder", "distinct"]].to_string(index=False))

df = raw.copy()
checks = []          # data-quality log: check, result, action


def log(check, result, action):
    checks.append({"check": check, "result": result, "action": action})
    print(f"  [{check}] {result} -> {action}")


print("\nCLEANING LOG")

# ---------------------------------------------------------------------------
# 2. Remove leakage / non-analytical columns
# ---------------------------------------------------------------------------
nb_cols = [c for c in df.columns if c.startswith("Naive_Bayes")]
df = df.drop(columns=nb_cols)
log("Leakage columns (Naive_Bayes_*)", f"{len(nb_cols)} present in this copy",
    "Dropped" if nb_cols else
    "Nothing to drop; code removes them if present (they are classifier outputs built from the target)")

# ---------------------------------------------------------------------------
# 3. Duplicates
# ---------------------------------------------------------------------------
dup_id = int(df["CLIENTNUM"].duplicated().sum())
dup_row = int(df.drop(columns="CLIENTNUM").duplicated().sum())
log("Duplicate CLIENTNUM", dup_id, "None to remove" if dup_id == 0 else "Removed")
log("Duplicate records (all attributes)", dup_row, "None to remove" if dup_row == 0 else "Removed")
df = df.drop_duplicates(subset="CLIENTNUM")

# ---------------------------------------------------------------------------
# 4. Label standardisation (whitespace, case, codes)
# ---------------------------------------------------------------------------
cat_cols = df.select_dtypes(exclude="number").columns
for c in cat_cols:
    df[c] = df[c].astype(str).str.strip()
df["Gender"] = df["Gender"].map({"F": "Female", "M": "Male"})
df["Income_Category"] = df["Income_Category"].replace({"$120K +": "$120K+"})
log("Inconsistent labels", "Whitespace trimmed; Gender codes F/M; income label spacing",
    "Standardised to readable, consistent labels")

# Target: binary churn flag
df["Churned"] = (df["Attrition_Flag"] == "Attrited Customer").astype(int)
df["Customer_Status"] = df["Attrition_Flag"].map(
    {"Attrited Customer": "Attrited", "Existing Customer": "Existing"})
log("Target variable", "Text flag 'Attrition_Flag'", "Encoded as Churned (1/0) + Customer_Status")

# ---------------------------------------------------------------------------
# 5. Missing / invalid values
# ---------------------------------------------------------------------------
nan_total = int(df.isna().sum().sum())
log("System missing values (NaN)", nan_total, "None to impute")

unk_cols = ["Education_Level", "Marital_Status", "Income_Category"]
for c in unk_cols:
    n = int((df[c] == "Unknown").sum())
    rate = df.loc[df[c] == "Unknown", "Churned"].mean() * 100
    log(f"'Unknown' placeholder in {c}", f"{n:,} rows ({n / len(df) * 100:.1f}%), churn {rate:.1f}%",
        "Retained as explicit 'Unknown' category (not imputed, not dropped)")
df["Has_Unknown_Profile"] = df[unk_cols].eq("Unknown").any(axis=1).astype(int)
log("Rows with >=1 Unknown demographic", f"{df['Has_Unknown_Profile'].sum():,} "
    f"({df['Has_Unknown_Profile'].mean() * 100:.1f}%)",
    "Flagged in Has_Unknown_Profile; listwise deletion would discard ~30% of the portfolio")

# Business-rule validity checks
bad_util = int(((df["Avg_Utilization_Ratio"] < 0) | (df["Avg_Utilization_Ratio"] > 1)).sum())
log("Utilisation ratio outside [0,1]", bad_util, "None invalid")
bal_gap = int((abs(df["Credit_Limit"] - df["Total_Revolving_Bal"] - df["Avg_Open_To_Buy"]) > 1).sum())
log("Credit_Limit = Revolving_Bal + Open_To_Buy", f"{bal_gap} violations", "Identity holds - no correction")
neg = int((df.select_dtypes("number") < 0).sum().sum())
log("Negative numeric values", neg, "None invalid")
bad_age = int(((df["Customer_Age"] < 18) | (df["Customer_Age"] > 100)).sum())
log("Implausible ages (<18 or >100)", bad_age, "None invalid")

# ---------------------------------------------------------------------------
# 6. Outliers (IQR) - flag and retain
# ---------------------------------------------------------------------------
num_cols = [c for c in df.select_dtypes("number").columns
            if c not in ("CLIENTNUM", "Churned", "Has_Unknown_Profile")]
outl = iqr_outliers(df, num_cols)
outl.to_csv(OUT / "outlier_profile.csv", index=False)
log("IQR outliers", f"{outl['outliers'].sum():,} flags across {int((outl['outliers'] > 0).sum())} columns "
    f"(largest: Contacts_Count_12_mon, Credit_Limit, Avg_Open_To_Buy, Total_Trans_Amt)",
    "Retained - values are plausible (e.g. premium-card limits, high spenders) and carry churn signal")
q1, q3 = df["Total_Trans_Amt"].quantile([.25, .75])
df["Is_Outlier_Trans_Amt"] = (df["Total_Trans_Amt"] > q3 + 1.5 * (q3 - q1)).astype(int)

# ---------------------------------------------------------------------------
# 7. Derived analytical fields
# ---------------------------------------------------------------------------
df["Age_Band"] = pd.cut(df["Customer_Age"], [0, 35, 45, 55, 120],
                        labels=["<35", "35-44", "45-54", "55+"], right=False).astype(str)

income_order = ["Less than $40K", "$40K - $60K", "$60K - $80K", "$80K - $120K", "$120K+", "Unknown"]
income_seg = {"Less than $40K": "Low (<$40K)", "$40K - $60K": "Lower-middle ($40-60K)",
              "$60K - $80K": "Upper-middle ($60-80K)", "$80K - $120K": "High ($80K+)",
              "$120K+": "High ($80K+)", "Unknown": "Unknown"}
df["Income_Segment"] = df["Income_Category"].map(income_seg)
df["Income_Rank"] = df["Income_Category"].map({k: i for i, k in enumerate(income_order[:-1], 1)}).fillna(0).astype(int)

df["Utilisation_Category"] = pd.cut(df["Avg_Utilization_Ratio"], [-0.001, 0, 0.30, 0.70, 1.0],
                                     labels=["Zero (0%)", "Low (0-30%)", "Moderate (30-70%)", "High (>70%)"]).astype(str)

df["Txn_Frequency_Category"] = pd.cut(df["Total_Trans_Ct"], [0, 40, 60, 80, 200],
                                      labels=["Very low (<=40)", "Low (41-60)", "Medium (61-80)", "High (>80)"]).astype(str)

df["Customer_Value_Class"] = pd.qcut(df["Total_Trans_Amt"], [0, .25, .75, 1],
                                     labels=["Low value", "Core value", "High value"]).astype(str)

df["Product_Depth"] = pd.cut(df["Total_Relationship_Count"], [0, 2, 4, 6],
                             labels=["Thin (1-2)", "Moderate (3-4)", "Deep (5-6)"]).astype(str)

df["Tenure_Band"] = pd.cut(df["Months_on_book"], [0, 24, 36, 48, 100],
                           labels=["<=2 yrs", "2-3 yrs", "3-4 yrs", ">4 yrs"]).astype(str)

df["Service_Contact_Band"] = pd.cut(df["Contacts_Count_12_mon"], [-1, 1, 3, 10],
                                    labels=["0-1 contacts", "2-3 contacts", "4+ contacts"]).astype(str)

df["Activity_Decline_Flag"] = (df["Total_Ct_Chng_Q4_Q1"] < 0.6).astype(int)  # Q4 count < 60% of Q1

# Rule-based retention-risk score (0-10). Thresholds are documented in the report (Section 4)
df["Risk_Score"] = (
    3 * (df["Total_Trans_Ct"] <= 60)            # low transaction frequency
    + 2 * (df["Total_Ct_Chng_Q4_Q1"] < 0.6)     # falling activity Q4 vs Q1
    + 2 * (df["Total_Revolving_Bal"] < 500)     # little/no revolving balance (card not 'in use')
    + 1 * (df["Total_Relationship_Count"] <= 2) # thin product relationship
    + 1 * (df["Months_Inactive_12_mon"] >= 3)   # prolonged inactivity
    + 1 * (df["Contacts_Count_12_mon"] >= 4)    # heavy service contact (complaint proxy)
).astype(int)
df["Risk_Band"] = pd.cut(df["Risk_Score"], [-1, 3, 5, 10], labels=["Low", "Medium", "High"]).astype(str)

log("Derived fields", "12 created",
    "Age_Band, Income_Segment, Income_Rank, Utilisation_Category, Txn_Frequency_Category, "
    "Customer_Value_Class, Product_Depth, Tenure_Band, Service_Contact_Band, "
    "Activity_Decline_Flag, Risk_Score, Risk_Band")

# ---------------------------------------------------------------------------
# 8. After-cleaning checks and export
# ---------------------------------------------------------------------------
df = df.drop(columns=["Attrition_Flag"])
after = profile(df)
after.to_csv(OUT / "dq_after.csv", index=False)
assert df.isna().sum().sum() == 0, "Cleaned data must contain no NaN"
assert df["CLIENTNUM"].is_unique
assert len(df) == EXPECTED_ROWS

pd.DataFrame(checks).to_csv(OUT / "dq_checks.csv", index=False)
df.to_csv(ROOT / "data" / "BankChurners_cleaned.csv", index=False)

dictionary = pd.DataFrame([
    ("Churned", "1 = attrited (closed account), 0 = existing"),
    ("Has_Unknown_Profile", "1 if Education, Marital or Income is 'Unknown'"),
    ("Is_Outlier_Trans_Amt", "1 if Total_Trans_Amt above IQR upper fence"),
    ("Age_Band", "<35, 35-44, 45-54, 55+"),
    ("Income_Segment", "Income category grouped into 4 segments + Unknown"),
    ("Income_Rank", "Ordinal income 1 (<$40K) to 5 ($120K+); 0 = Unknown"),
    ("Utilisation_Category", "Avg_Utilization_Ratio: Zero / Low / Moderate / High"),
    ("Txn_Frequency_Category", "Total_Trans_Ct (12 months): <=40, 41-60, 61-80, >80"),
    ("Customer_Value_Class", "Total_Trans_Amt quartiles: bottom 25% Low, middle 50% Core, top 25% High"),
    ("Product_Depth", "Total_Relationship_Count: 1-2 Thin, 3-4 Moderate, 5-6 Deep"),
    ("Tenure_Band", "Months_on_book grouped"),
    ("Service_Contact_Band", "Contacts_Count_12_mon: 0-1, 2-3, 4+"),
    ("Activity_Decline_Flag", "1 if Total_Ct_Chng_Q4_Q1 < 0.6"),
    ("Risk_Score", "Rule-based score 0-10 (see report Section 4)"),
    ("Risk_Band", "Low (0-3), Medium (4-5), High (6-10)"),
], columns=["field", "definition"])

with pd.ExcelWriter(ROOT / "data" / "BankChurners_cleaned.xlsx") as xw:
    df.to_excel(xw, sheet_name="cleaned_data", index=False)
    dictionary.to_excel(xw, sheet_name="derived_field_dictionary", index=False)
    pd.DataFrame(checks).to_excel(xw, sheet_name="quality_log", index=False)
    before.to_excel(xw, sheet_name="profile_before", index=False)
    after.to_excel(xw, sheet_name="profile_after", index=False)

print(f"\nAFTER - {df.shape[0]:,} rows x {df.shape[1]} columns, NaN = {int(df.isna().sum().sum())}, "
      f"duplicate IDs = {int(df['CLIENTNUM'].duplicated().sum())}")
print("Saved data/BankChurners_cleaned.csv and .xlsx")
