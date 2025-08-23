from pathlib import Path

# Base path for data and outputs
DATA = Path("data/raw")

# Data dictionary (master source)
DICT_CSV = DATA / "eADMSPUB_DataDictionary.csv"

# Inputs
EVENTS_CSV          = DATA / "events.csv"
FINDINGS_CSV        = DATA / "findings.csv"
AIRCRAFT_CSV        = DATA / "aircraft.csv"
EVENTS_SEQUENCE_CSV = DATA / "events_sequence.csv"

# Columns to load
EVENTS_COLS   = ["ev_id", "ev_year", "ev_date", "ev_highest_injury"]
FINDINGS_COLS = [
    "ev_id","Aircraft_Key","finding_no","finding_code","finding_description",
    "category_no","subcategory_no","section_no","subsection_no","modifier_no","Cause_Factor"
]
AIRCRAFT_COLS = ["ev_id","Aircraft_Key","acft_make","acft_model"]
SEQ_COLS      = ["ev_id","Aircraft_Key","Occurrence_No","phase_no","eventsoe_no","Occurrence_Code","Defining_ev"]

# Date formats seen in CAROL/eADMS exports
DATE_FORMATS = [
    "%m/%d/%y %H:%M",         # 1/10/08 0:00
    "%m/%d/%Y %H:%M",         # 1/10/2008 00:00
    "%b %d, %Y %I:%M:%S %p",  # Jan 10, 2008 12:00:00 AM
]

# Outputs (Parquet)
OUT_EVENT_LEVEL           = Path("data/out/event_level.parquet")
OUT_FINDING_LEVEL         = Path("data/out/finding_level.parquet")
OUT_FINDING_LEVEL_LABELED = Path("data/out/finding_level_labeled.parquet")
OUT_SEQ_LABELED           = Path("data/out/events_sequence_labeled.parquet")