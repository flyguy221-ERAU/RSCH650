from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import (
    AIRCRAFT_COLS,
    AIRCRAFT_CSV,
    DATA,
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
    """Raised when an input file is missing or unreadable."""


# loaders.py
def read_csv_safe(path: str | Path, **kwargs) -> pd.DataFrame:
    """
    Read a CSV with clear error messages.
    Default dtype=string and low_memory=False for stable parsing.
    Also validates that the file contains usable data.
    """
    p = Path(path)
    try:
        df = pd.read_csv(
            p,
            dtype="string",
            low_memory=False,
            on_bad_lines="error",  # be strict about malformed lines
            **kwargs,
        )
        # ---- Post-parse validation: treat all-NaN / 0 rows/cols as unusable ----
        if df.shape[0] == 0 or df.shape[1] == 0 or df.isna().all().all():
            msg = f"CSV appears empty or contains no usable data: {p}"
            log.error(msg)
            raise DataLoadError(msg)
        return df

    except FileNotFoundError as e:
        msg = f"Missing input file: {p}\nPut required CSVs in data/raw (see README) and re-run `make build`."
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


def read_events(path: Path = DATA) -> pd.DataFrame:
    df = read_csv_safe(
        EVENTS_CSV,
        usecols=EVENTS_COLS,
        dtype={"ev_id": "string", "ev_year": "Int64", "ev_highest_injury": "string"},
        low_memory=False,
    )
    df["ev_date"] = parse_flexible_datetime(df["ev_date"], DATE_FORMATS)
    df = df[df["ev_year"] >= 2009].copy()
    return df


def read_findings(path: Path = DATA) -> pd.DataFrame:
    return read_csv_safe(
        FINDINGS_CSV,
        usecols=FINDINGS_COLS,
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
        low_memory=False,
    )


def read_aircraft(path: Path = DATA) -> pd.DataFrame:
    df = read_csv_safe(
        AIRCRAFT_CSV,
        usecols=AIRCRAFT_COLS,
        dtype={
            "ev_id": "string",
            "Aircraft_Key": "Int64",
            "acft_make": "string",
            "acft_model": "string",
        },
        low_memory=False,
    )
    return normalize_make_model(df)


def read_events_sequence(path: Path = DATA) -> pd.DataFrame:
    df = read_csv_safe(EVENTS_SEQUENCE_CSV, dtype="string", low_memory=False)
    keep = [c for c in SEQ_COLS if c in df.columns]
    df = df[keep].copy()
    for col in [
        "Occurrence_No",
        "phase_no",
        "eventsoe_no",
        "Defining_ev",
        "Aircraft_Key",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    if "ev_id" in df.columns:
        df["ev_id"] = df["ev_id"].astype("string")
    # Derive Occurrence_Code if missing (phase_no + eventsoe_no → 6 digits)
    if "Occurrence_Code" not in df.columns and {"phase_no", "eventsoe_no"}.issubset(df.columns):

        def mk_code(row):
            if pd.isna(row["phase_no"]) or pd.isna(row["eventsoe_no"]):
                return pd.NA
            return f"{int(row['phase_no']):03d}{int(row['eventsoe_no']):03d}"

        df["Occurrence_Code"] = df.apply(mk_code, axis=1).astype("string")
    if "Defining_ev" in df.columns:
        df["Defining_ev"] = df["Defining_ev"].fillna(0).astype("Int64")
    return df
