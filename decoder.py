from __future__ import annotations
import pandas as pd
import re
from typing import Tuple
from functools import lru_cache
from config import DICT_CSV

WHITELIST = {
    ("Events_Sequence", "Occurrence_Code"),
    ("Occurrences", "Occurrence_Code"),
    ("Events_Sequence", "phase_no"),
    ("Occurrences", "Phase_of_Flight"),
    ("Findings", "modifier_no"),
}


@lru_cache(maxsize=1)
def _load_dict() -> pd.DataFrame:
    df = pd.read_csv(DICT_CSV, dtype="string", low_memory=False)
    need = {"Category of Data", "Table", "Column", "code_iaids", "meaning"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"Data dictionary missing columns: {miss}")
    df = df[df["Category of Data"].str.strip().str.lower() == "eadms data"].copy()
    df["Table_l"] = df["Table"].str.strip().str.lower()
    df["Column_l"] = df["Column"].str.strip().str.lower()
    wl = {(t.lower(), c.lower()) for t, c in WHITELIST}
    return df[df.apply(lambda r: (r["Table_l"], r["Column_l"]) in wl, axis=1)].copy()


def _clean_code_str(s: pd.Series) -> pd.Series:
    x = s.astype("string").str.replace(r"\D", "", regex=True)
    return x.str.zfill(6)  # normalize to 6-digit


def _is_left_family(t: str) -> bool:  # ###xxx
    return bool(re.fullmatch(r"\d{3}xxx", str(t).strip(), flags=re.IGNORECASE))


def _is_right_family(t: str) -> bool:  # xxx###
    return bool(re.fullmatch(r"xxx\d{3}", str(t).strip(), flags=re.IGNORECASE))


def _is_exact6(t: str) -> bool:  # ######
    return bool(re.fullmatch(r"\d{6}", str(t).strip()))


@lru_cache(maxsize=1)
def build_occ_code_decoders() -> Tuple[dict, dict, dict]:
    dd = _load_dict()
    occ = dd[
        (dd["Column_l"] == "occurrence_code") & (dd["meaning"].notna()) & (dd["code_iaids"].notna())
    ][["code_iaids", "meaning"]].copy()

    left = occ[occ["code_iaids"].apply(_is_left_family)].copy()
    right = occ[occ["code_iaids"].apply(_is_right_family)].copy()
    exact = occ[occ["code_iaids"].apply(_is_exact6)].copy()

    left["key"] = left["code_iaids"].str.extract(r"^(\d{3})", expand=False)
    right["key"] = right["code_iaids"].str.extract(r"(\d{3})$", expand=False)
    exact["key"] = exact["code_iaids"].str.extract(r"(\d{6})", expand=False)

    left3_map = dict(left.dropna(subset=["key"]).drop_duplicates("key")[["key", "meaning"]].values)
    right3_map = dict(
        right.dropna(subset=["key"]).drop_duplicates("key")[["key", "meaning"]].values
    )
    exact6_map = dict(
        exact.dropna(subset=["key"]).drop_duplicates("key")[["key", "meaning"]].values
    )
    return left3_map, right3_map, exact6_map


@lru_cache(maxsize=1)
def build_phase_numeric_lookup() -> pd.DataFrame:
    dd = _load_dict()
    m = dd[(dd["Table_l"] == "events_sequence") & (dd["Column_l"] == "phase_no")][
        ["code_iaids", "meaning"]
    ].dropna()
    if m.empty:
        m = dd[(dd["Table_l"] == "occurrences") & (dd["Column_l"] == "phase_of_flight")][
            ["code_iaids", "meaning"]
        ].dropna()
    if m.empty:
        return pd.DataFrame(columns=["code_int", "meaning"])
    code = (
        m["code_iaids"].str.extract(r"(\d+)$")[0].fillna(m["code_iaids"].str.extract(r"(\d+)")[0])
    )
    lk = pd.DataFrame(
        {
            "code_int": pd.to_numeric(code, errors="coerce").astype("Int64"),
            "meaning": m["meaning"],
        }
    )
    lk = lk.dropna(subset=["code_int"]).drop_duplicates("code_int")
    return lk.reset_index(drop=True)


def decode_occurrence_code(series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    left3_map, right3_map, exact6_map = build_occ_code_decoders()
    code = _clean_code_str(series)
    code6 = code.str[-6:]
    left3 = code6.str[:3]
    right3 = code6.str[-3:]
    occ_exact = code6.map(exact6_map).astype("string")
    occ_right = right3.map(right3_map).astype("string")
    phase_left = left3.map(left3_map).astype("string")
    return occ_exact, occ_right, phase_left
