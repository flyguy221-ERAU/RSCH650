# loaders.py
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import (
    AIRCRAFT_COLS,
    AIRCRAFT_CSV,
    DATE_FORMATS,
    EVENTS_COLS,
    EVENTS_CSV,
    EVENTS_SEQUENCE_CSV,
    FINDINGS_COLS,
    FINDINGS_CSV,
    SEQ_COLS,
)
from normalize import normalize_make_model, parse_flexible_datetime

log = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when an input file is missing, empty, or unreadable."""


def read_csv_safe(path: str | Path, **kwargs) -> pd.DataFrame:
    """
    Read a CSV with strict error handling and clear messages.
    Defaults to dtype=string and low_memory=False; caller can override via **kwargs.
    Validates that the file contains usable data.
    """
    p = Path(path)
    try:
        df = pd.read_csv(
            p,
            dtype=kwargs.pop("dtype", "string"),
            low_memory=kwargs.pop("low_memory", False),
            on_bad_lines=kwargs.pop("on_bad_lines", "error"),
            **kwargs,
        )
        # Treat 0 rows/cols or all-NA as unusable.
        if df.shape[0] == 0 or df.shape[1] == 0 or df.isna().all().all():
            msg = f"CSV appears empty or contains no usable data: {p}"
            log.error(msg)
            raise DataLoadError(msg)
        return df

    except FileNotFoundError as e:
        msg = f"Missing input file: {p}\nPut required CSVs in data/raw and re-run."
        log.error(msg)
        raise DataLoadError(msg) from e
    except pd.errors.EmptyDataError as e:
        msg = f"Empty or corrupt CSV: {p}"
        log.error(msg)
        raise DataLoadError(msg) from e
    except pd.errors.ParserError as e:
        msg = f"Could not parse CSV: {p}\nPandas error: {e}"
        log.error(msg)
        raise DataLoadError(msg) from e
    except Exception as e:
        msg = f"Unexpected error reading {p}: {type(e).__name__}: {e}"
        log.error(msg)
        raise DataLoadError(msg) from e


# ------------ Events ---------------------------------------------------------


def read_events() -> pd.DataFrame:
    """
    Load events with strict dtypes, parse dates across known CAROL formats,
    and filter to the 2008-2023 analysis window.
    """
    df = read_csv_safe(
        EVENTS_CSV,
        usecols=[c for c in EVENTS_COLS if c],
        dtype={"ev_id": "string", "ev_year": "Int64", "ev_highest_injury": "string"},
    )

    # Normalize/parse event date
    if "ev_date" in df.columns:
        df["ev_date"] = parse_flexible_datetime(df["ev_date"], DATE_FORMATS)

    # Filter to analysis window (inclusive)
    if "ev_year" in df.columns:
        df = df[(df["ev_year"] >= 2008) & (df["ev_year"] <= 2023)].copy()

    # Strip spaces from string cols
    for col in df.select_dtypes(include="string").columns:
        df[col] = df[col].str.strip()

    return df


# ------------ Findings -------------------------------------------------------


def read_findings() -> pd.DataFrame:
    """
    Load findings; keep only the columns we care about; enforce dtypes that
    make joining/labeling deterministic.
    """
    df = read_csv_safe(
        FINDINGS_CSV,
        usecols=[c for c in FINDINGS_COLS if c],
        dtype={
            "ev_id": "string",
            "Aircraft_Key": "Int64",
            "finding_no": "Int64",
            "finding_code": "Int64",
            "finding_description": "string",
            "category_no": "Int64",
            "subcategory_no": "Int64",
            "section_no": "Int64",
            "subsection_no": "Int64",
            "modifier_no": "Int64",
            "Cause_Factor": "string",
        },
    )

    for col in df.select_dtypes(include="string").columns:
        df[col] = df[col].str.strip()

    return df


# ------------ Aircraft -------------------------------------------------------


def read_aircraft() -> pd.DataFrame:
    """
    Load aircraft table and normalize make/model tokens for consistent grouping.
    """
    df = read_csv_safe(
        AIRCRAFT_CSV,
        usecols=[c for c in AIRCRAFT_COLS if c],
        dtype={
            "ev_id": "string",
            "Aircraft_Key": "Int64",
            "acft_make": "string",
            "acft_model": "string",
        },
    )

    for col in ["acft_make", "acft_model"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    return normalize_make_model(df)


# ------------ Events Sequence ------------------------------------------------


def read_events_sequence() -> pd.DataFrame:
    """
    Load sequence-of-events and ensure the core keys/fields are correctly typed.
    If Occurrence_Code is missing, derive it deterministically as phase_no(3d)+eventsoe_no(3d).
    """
    df = read_csv_safe(EVENTS_SEQUENCE_CSV)

    # Keep only expected columns if present
    keep = [c for c in SEQ_COLS if c in df.columns]
    if keep:
        df = df[keep].copy()

    # Type coercions
    int_cols = ["Occurrence_No", "phase_no", "eventsoe_no", "Defining_ev", "Aircraft_Key"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "ev_id" in df.columns:
        df["ev_id"] = df["ev_id"].astype("string").str.strip()

    # Derive Occurrence_Code if missing
    if "Occurrence_Code" not in df.columns and {"phase_no", "eventsoe_no"}.issubset(df.columns):

        def mk_code(row):
            ph, ev = row.get("phase_no"), row.get("eventsoe_no")
            if pd.isna(ph) or pd.isna(ev):
                return pd.NA
            return f"{int(ph):03d}{int(ev):03d}"

        df["Occurrence_Code"] = df.apply(mk_code, axis=1).astype("string")

    if "Defining_ev" in df.columns:
        df["Defining_ev"] = df["Defining_ev"].fillna(0).astype("Int64")

    for col in df.select_dtypes(include="string").columns:
        df[col] = df[col].str.strip()

    return df
