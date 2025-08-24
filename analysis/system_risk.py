# analysis/system_risk.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SEV_FATAL = {"FATL", "FATAL", "Fatal", "DEAD"}  # normalize as needed


@dataclass
class FilterSpec:
    years: tuple[int, int] = (2009, 2025)
    include_far_parts: set[str] | None = None  # e.g., {"91","121","135"}
    exclude_rotorcraft: bool = True
    severity: list[str] | None = None
    phases: list[str] | None = None
    occurrences: list[str] | None = None
    defining_only: bool = False
    makes: list[str] | None = None
    model_contains: str | None = None
    parts: list[str] | None = None


def _is_fatal(s: pd.Series) -> pd.Series:
    # robust fatal flag across possible encodings
    s = s.astype("string").str.upper().str.strip()
    return s.eq("FATL") | s.eq("FATAL") | s.eq("DEAD") | s.eq("F") | s.eq("1")


def _normalize_system(s: pd.Series) -> pd.Series:
    # Expect a structured “system/component” label your pipeline derives.
    # Map common synonyms → canonical buckets; adjust as your decoder matures.
    m = {
        "FLIGHT CONTROL": "Flight Control",
        "FLT CTRL": "Flight Control",
        "CONTROLS": "Flight Control",
        "AVIONICS": "Avionics",
        "ELECTRICAL": "Electrical",
        "PROPULSION": "Propulsion",
        "ENGINE": "Propulsion",
        "LANDING GEAR": "Landing Gear",
        "HYDRAULIC": "Hydraulic",
    }
    s = s.astype("string").str.upper().str.strip()
    return s.map(m).fillna(s.str.title())


def filter_event_level(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    if spec is None:
        spec = FilterSpec()
    d = df.copy()
    if "ev_year" in d:
        d = d[
            (pd.to_numeric(d["ev_year"], errors="coerce") >= spec.years[0])
            & (pd.to_numeric(d["ev_year"], errors="coerce") <= spec.years[1])
        ]
    if spec.include_far_parts and "far_part" in d:
        d = d[d["far_part"].astype("string").isin(spec.include_far_parts)]
    if spec.exclude_rotorcraft and "acft_category" in d:
        d = d[~d["acft_category"].astype("string").str.contains("ROTOR", case=False, na=False)]
    return d


def build_contingency(
    event_df: pd.DataFrame,
    system_col: str = "system_component",
    injury_col: str = "ev_highest_injury",
    spec: FilterSpec | None = None,
) -> pd.DataFrame:
    if spec is None:
        spec = FilterSpec()
    d = filter_event_level(event_df, spec)
    if system_col not in d or injury_col not in d:
        raise KeyError(f"Missing required columns: {system_col}, {injury_col}")
    d = d[[system_col, injury_col]].copy()
    d["fatal"] = _is_fatal(d[injury_col])
    d["system_bucket"] = _normalize_system(d[system_col])
    ct = (
        d.groupby("system_bucket")["fatal"]
        .agg(total="count", fatals="sum")
        .assign(pct_fatal=lambda x: np.where(x["total"] > 0, 100 * x["fatals"] / x["total"], np.nan))
        .sort_values("pct_fatal", ascending=False)
        .reset_index()
    )
    return ct


def chisq_table(
    event_df: pd.DataFrame,
    spec: FilterSpec | None = None,
    flight_control_label: str = "Flight Control",
    system_col: str = "system_component",
    injury_col: str = "ev_highest_injury",
) -> pd.DataFrame:
    if spec is None:
        spec = FilterSpec()
    d = filter_event_level(event_df, spec)
    d = d[[system_col, injury_col]].dropna().copy()
    d["fatal"] = _is_fatal(d[injury_col])
    d["system_bucket"] = _normalize_system(d[system_col])
    d["is_fc"] = d["system_bucket"].eq(flight_control_label)
    # 2x2: Flight Control vs Other x Fatal vs Nonfatal
    a = int(((d["is_fc"]) & (d["fatal"])).sum())
    b = int(((d["is_fc"]) & (~d["fatal"])).sum())
    c = int((~d["is_fc"] & d["fatal"]).sum())
    e = int((~d["is_fc"] & ~d["fatal"]).sum())
    return pd.DataFrame(
        {"Fatal": [a, c], "Nonfatal": [b, e]},
        index=[flight_control_label, "Other systems"],
    )
