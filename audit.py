import pandas as pd

def quick_audit(df: pd.DataFrame, title: str):
    print(f"\n===== {title} =====")
    print("Shape:", df.shape)
    if "ev_id" in df:   print("Unique ev_id:", df["ev_id"].nunique())
    if "ev_year" in df: print("Year range:", df["ev_year"].min(), "→", df["ev_year"].max())
    miss = (df.isna().sum() / len(df) * 100).round(2).sort_values(ascending=False)
    print("\nMissingness (%):\n", miss.head(20))
    for col in ["ev_highest_injury","acft_make","acft_model","finding_code","finding_category","Cause_Factor"]:
        if col in df.columns:
            print(f"\nTop values in {col}:\n", df[col].value_counts(dropna=False).head(10))