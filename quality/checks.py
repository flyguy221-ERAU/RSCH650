# quality/checks.py
import pandas as pd


def event_expectations(df: pd.DataFrame) -> dict:
    out = {}
    out["has_ev_id"] = "ev_id" in df.columns and df["ev_id"].notna().all()
    out["ev_year_range_ok"] = (
        "ev_year" in df and df["ev_year"].between(2009, 2025, inclusive="both").mean() > 0.95
    )
    out["injury_present"] = (
        "ev_highest_injury" in df and df["ev_highest_injury"].notna().mean() > 0.9
    )
    out["system_present"] = "system_component" in df and df["system_component"].notna().mean() > 0.7
    return out
