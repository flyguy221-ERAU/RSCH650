# RSCH650 – NTSB/CAROL Accident Analytics (Streamlit)

A Streamlit app and data pipeline for analyzing NTSB/CAROL accident data.
Focus areas:
- Event-level accident trends (year, severity, make/model)
- Phase × Occurrence cross‑tabs from the NTSB sequence table
- Finding-level analysis with derived **system buckets** (incl. Flight Controls)
- Chi‑square and odds‑ratio summary (Flight Controls vs Other systems)

## Quick start

```bash
# 1) create virtual environment (or use make venv)
python3 -m venv .venv
source .venv/bin/activate

# 2) install dependencies
python -m pip install -U pip
pip install -r requirements.txt

# 3) build Parquets from CAROL CSVs (place raw CSVs under data/raw/)
make build

# 4) launch the app
make run   # or: streamlit run app.py
