# decoder.py
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _eadms_occ_rows(dict_csv: Path | str) -> pd.DataFrame:
    """
    Filter the eADMS dictionary down to Events_Sequence:Occurrence_Code rows,
    returning columns: code_iaids, meaning (both string).
    """
    df = pd.read_csv(dict_csv, dtype="string", low_memory=False)

    # Tolerant header access
    cols = {c.lower(): c for c in df.columns}

    def get(name: str) -> str:
        c = cols.get(name.lower())
        if not c:
            raise ValueError(f"Expected column '{name}' not found in {dict_csv}. Found: {list(df.columns)}")
        return c

    table_col = get("Table")
    column_col = get("Column")
    code_col = get("code_iaids")
    meaning_col = get("meaning")

    occ = (
        df[(df[table_col] == "Events_Sequence") & (df[column_col] == "Occurrence_Code")][[code_col, meaning_col]]
        .rename(columns={code_col: "code_iaids", meaning_col: "meaning"})
        .dropna()
        .copy()
    )
    occ["code_iaids"] = occ["code_iaids"].astype("string").str.strip()
    occ["meaning"] = occ["meaning"].astype("string").str.strip()
    return occ.drop_duplicates()


def build_occ_phase_maps(dict_csv: Path | str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Build three lookup Series from the eADMS dictionary:

      exact_occ_map:   index='PPPFFF' (6 digits), value='event meaning'
      right3_map:      index='FFF'    from 'xxxFFF', value='event meaning'
      left3_phase_map: index='PPP'    from 'PPPxxx', value='phase/family meaning'
    """
    occ = _eadms_occ_rows(dict_csv)

    # Exact 6-digit codes (rare but first-class if present)
    exact = occ[occ["code_iaids"].str.fullmatch(r"\d{6}", na=False)].copy()
    exact["key"] = exact["code_iaids"]
    exact_occ_map = pd.Series(exact["meaning"].values, index=exact["key"].values, dtype="string")

    # Right-3 event map: xxxFFF → FFF
    r3 = occ[occ["code_iaids"].str.fullmatch(r"xxx\d{3}", na=False)].copy()
    r3["key"] = r3["code_iaids"].str[-3:]
    right3_map = pd.Series(r3["meaning"].values, index=r3["key"].values, dtype="string")

    # Left-3 phase map: PPPxxx → PPP
    l3 = occ[occ["code_iaids"].str.fullmatch(r"\d{3}xxx", na=False)].copy()
    l3["key"] = l3["code_iaids"].str[:3]
    left3_phase_map = pd.Series(l3["meaning"].values, index=l3["key"].values, dtype="string")

    return exact_occ_map, right3_map, left3_phase_map
