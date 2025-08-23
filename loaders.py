import pandas as pd
from pathlib import Path
from config import (
    DATA,
    DATE_FORMATS,
    EVENTS_CSV,
    FINDINGS_CSV,
    AIRCRAFT_CSV,
    EVENTS_SEQUENCE_CSV,
    EVENTS_COLS,
    FINDINGS_COLS,
    AIRCRAFT_COLS,
    SEQ_COLS,
)
from normalize import parse_flexible_datetime, normalize_make_model


def read_events(path: Path = DATA) -> pd.DataFrame:
    df = pd.read_csv(
        EVENTS_CSV,
        usecols=EVENTS_COLS,
        dtype={"ev_id": "string", "ev_year": "Int64", "ev_highest_injury": "string"},
        low_memory=False,
    )
    df["ev_date"] = parse_flexible_datetime(df["ev_date"], DATE_FORMATS)
    df = df[df["ev_year"] >= 2009].copy()
    return df


def read_findings(path: Path = DATA) -> pd.DataFrame:
    return pd.read_csv(
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
    df = pd.read_csv(
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
    df = pd.read_csv(EVENTS_SEQUENCE_CSV, dtype="string", low_memory=False)
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
    if "ev_id" in df:
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
