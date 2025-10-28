from pathlib import Path

# Base paths
ROOT = Path("data")
RAW = ROOT / "raw"
DICT = ROOT / "dict"

# Data dictionary (master source)
DICT_CSV = RAW / "eADMSPUB_DataDictionary.csv"  # keep as-is (from eADMS)

# Inputs (raw exports)
EVENTS_CSV = RAW / "events.csv"
FINDINGS_CSV = RAW / "findings.csv"
AIRCRAFT_CSV = RAW / "aircraft.csv"
EVENTS_SEQUENCE_CSV = RAW / "events_sequence.csv"


# Columns to load
EVENTS_COLS = ["ev_id", "ev_year", "ev_date", "ev_highest_injury"]
FINDINGS_COLS = [
    "ev_id",
    "Aircraft_Key",
    "finding_no",
    "finding_code",
    "finding_description",
    "category_no",
    "subcategory_no",
    "section_no",
    "subsection_no",
    "modifier_no",
    "Cause_Factor",
]
AIRCRAFT_COLS = ["ev_id", "Aircraft_Key", "acft_make", "acft_model"]
SEQ_COLS = [
    "ev_id",
    "Aircraft_Key",
    "Occurrence_No",
    "phase_no",
    "eventsoe_no",
    "Occurrence_Code",
    "Defining_ev",
]

# Date formats seen in CAROL/eADMS exports
DATE_FORMATS = [
    "%m/%d/%y %H:%M",
    "%m/%d/%Y %H:%M",
    "%b %d, %Y %I:%M:%S %p",
]

# Outputs (Parquet)
OUT_EVENT_LEVEL = ROOT / "out/event_level.parquet"
OUT_FINDING_LEVEL = ROOT / "out/finding_level.parquet"
OUT_FINDING_LEVEL_LABELED = ROOT / "out/finding_level_labeled.parquet"
OUT_SEQ_LABELED = ROOT / "out/events_sequence_labeled.parquet"
