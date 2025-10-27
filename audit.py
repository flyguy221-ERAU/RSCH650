# audit.py
from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd


def pct(num: int, den: int) -> str:
    if den == 0 or den is None or math.isnan(den):
        return "0.0%"
    return f"{(num / den) * 100:0.1f}%"


def coverage(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """
    Returns a tiny table: column, non_null, total, coverage_pct
    """
    rows = []
    total = len(df)
    for c in cols:
        nn = int(df[c].notna().sum()) if c in df.columns else 0
        rows.append({"column": c, "non_null": nn, "total": total, "coverage_pct": pct(nn, total)})
    return pd.DataFrame(rows)


def uniques(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    rows, total = [], len(df)
    for c in cols:
        if c in df.columns:
            rows.append({"column": c, "n_unique": int(df[c].nunique(dropna=True)), "total": total})
        else:
            rows.append({"column": c, "n_unique": 0, "total": total})
    return pd.DataFrame(rows)


def quick_audit(name: str, df: pd.DataFrame, key_cols: Iterable[str] | None = None, show: bool = True) -> None:
    """
    Print a concise audit summary for a dataframe.
    """
    print(f"\n=== AUDIT: {name} ===")
    print(f"rows: {len(df):,} | cols: {len(df.columns)}")
    if key_cols:
        cov = coverage(df, key_cols)
        print("key coverage:")
        print(cov.to_string(index=False))
        uq = uniques(df, key_cols)
        print("key unique counts:")
        print(uq.to_string(index=False))
