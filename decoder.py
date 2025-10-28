# decoder.py
from __future__ import annotations

from pathlib import Path

import pandas as pd

# ---- Public API -------------------------------------------------------------


def build_phase_numeric_lookup(dict_csv: Path | str) -> pd.DataFrame:
    """
    Returns a dataframe with columns:
      - phase_code (int) : normalized numeric code (e.g., 1..99)
      - phase_desc (str) : human-readable phase name
    Tries to infer column names from the eADMS dictionary CSV or a denormalized map.
    """
    df = _read_csv(dict_csv)
    # heuristics to find code/meaning cols
    code_col = _first(df, ["phase_code", "phase", "code", "phase_cd", "ph_code"])
    desc_col = _first(df, ["phase_desc", "phase_name", "description", "meaning", "desc"])
    if not code_col or not desc_col:
        # fallback: try to detect pairs like ("Code","Meaning")
        candidates = _find_code_meaning_pair(df)
        if candidates:
            code_col, desc_col = candidates
        else:
            # last resort: empty → caller can fall back to _builtin_phase_map()
            return _builtin_phase_map()
    out = df[[code_col, desc_col]].rename(columns={code_col: "phase_code", desc_col: "phase_desc"}).copy()
    out["phase_code"] = _to_int_series(out["phase_code"])
    out["phase_desc"] = out["phase_desc"].astype("string").str.strip()
    out = out.dropna(subset=["phase_code"]).drop_duplicates(subset=["phase_code"])
    if out.empty:
        return _builtin_phase_map()
    return out.reset_index(drop=True)


def decode_occurrence_code(ct_seqevt_csv: Path | str) -> pd.DataFrame:
    """
    Returns a dataframe with columns:
      - occ_code (string or int) : event/occurrence code used in sequence table
      - occ_desc (str)           : CAST/ICAO event description
    Works with a CAST/ICAO 'ct_seqevt.csv' style file or a generic two-column mapping.
    """
    df = _read_csv(ct_seqevt_csv)
    code_col = _first(df, ["event_code", "ev_code", "occ_code", "code"])
    desc_col = _first(df, ["event_desc", "description", "meaning", "desc", "name"])
    if not code_col or not desc_col:
        candidates = _find_code_meaning_pair(df)
        if candidates:
            code_col, desc_col = candidates
        else:
            raise ValueError("Could not infer columns for occurrence mapping.")
    out = df[[code_col, desc_col]].rename(columns={code_col: "occ_code", desc_col: "occ_desc"}).copy()
    # keep code as string to preserve leading zeros if any
    out["occ_code"] = out["occ_code"].astype("string").str.strip()
    out["occ_desc"] = out["occ_desc"].astype("string").str.strip()
    out = out.dropna(subset=["occ_code"]).drop_duplicates(subset=["occ_code"])
    return out.reset_index(drop=True)


# ---- Helpers ----------------------------------------------------------------


def _read_csv(p: Path | str) -> pd.DataFrame:
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p, dtype="string", encoding="utf-8", on_bad_lines="skip")


def _first(df: pd.DataFrame, names: list[str]) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    return None


def _find_code_meaning_pair(df: pd.DataFrame) -> tuple[str, str] | None:
    lower = {c.lower(): c for c in df.columns}
    code_keys = [k for k in lower if "code" in k or k in {"id"}]
    desc_keys = [k for k in lower if any(x in k for x in ["desc", "meaning", "name", "label"])]
    if code_keys and desc_keys:
        return lower[code_keys[0]], lower[desc_keys[0]]
    return None


def _to_int_series(s: pd.Series) -> pd.Series:
    return s.astype("string").str.extract(r"(\d+)", expand=False).astype("Int64")


def _builtin_phase_map() -> pd.DataFrame:
    # Minimal, widely used phases — safe fallback if dictionary file is unavailable.
    data = [
        (1, "STANDING"),
        (2, "TAXI"),
        (3, "TAKEOFF"),
        (4, "CLIMB"),
        (5, "CRUISE"),
        (6, "DESCENT"),
        (7, "APPROACH"),
        (8, "LANDING"),
        (9, "GO-AROUND"),
    ]
    return pd.DataFrame(data, columns=["phase_code", "phase_desc"])
