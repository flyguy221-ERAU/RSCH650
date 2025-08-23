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


Project layout
.
├── app.py                     # Streamlit UI
├── main.py                    # Pipeline: reads raw CSVs → writes Parquets
├── analysis/
│   └── system_risk.py         # System-bucket logic & 2×2 stats
├── loaders.py                 # CSV readers (CAROL/eADMS)
├── labelers.py                # Human-readable labels + system buckets
├── decoder.py                 # Coding/lookup helpers
├── lookups.py                 # Static maps (codes → labels)
├── normalize.py               # Light transforms/cleanups
├── config.py                  # Paths (data/raw, data/out, etc.)
├── data/
│   ├── raw/                   # place CAROL CSVs here
│   └── out/                   # parquet outputs written here
├── tests/
│   └── test_system_risk.py    # smoke tests
├── docs/
│   └── images/                # screenshots for README
├── requirements.txt
├── makefile
└── .pre-commit-config.yaml

Data expectations
Place CAROL CSVs in data/raw/. The pipeline expects the standard NTSB export tables:
	•	Events (accidents/incidents)
	•	Aircraft
	•	Findings
	•	Sequence (phase/occurrence records)

If files are named differently, adjust the readers in loaders.py or the paths in config.py.

What the app does

Overview tab
	•	Basic counts/filters by year and highest injury.

Phase×Occurrence tab
	•	Cross‑tab of phase (rows) by occurrence (columns), using NTSB sequence coding.

Findings tab
	•	Aggregations by finding categories and cause/factor flags.

System Risk tab
	•	Derives a per‑event system_bucket from findings (e.g., Flight Controls, Powerplant, Hydraulics, Avionics, Landing Gear, Airframe, Other/Unknown).
	•	Shows fatality percentage by system bucket.
	•	Builds a 2×2 table: Flight Controls vs Other × Fatal vs Nonfatal, with chi‑square and odds ratio.

Screenshots
docs/images/app-overview.png
docs/images/tab-findings.png
docs/images/tab-phase-occurrence.png
docs/images/tab-system-risk.png

Development
# format & lint (pre-commit)
pre-commit install
pre-commit run --all-files

# run tests
make test

Reproducibility (Make targets)
make venv      # create .venv
make install   # install requirements
make build     # run pipeline -> writes Parquets to data/out
make run       # start Streamlit app
make test      # pytest
make clean     # clean caches

License
MIT (see LICENSE).

Citation
If this code helps your work, you can cite this repository. See CITATION.cff.

---

## Dev setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pre-commit install

Workflow
	1.	Create a feature branch from main.
	2.	Run pre-commit run --all-files locally.
	3.	Add tests if you add functionality.
	4.	Open a PR; CI must pass before merge.

Code style
	•	black for formatting
	•	ruff for linting
	•	Keep functions < ~80 lines when possible
	•	Type hints encouraged

Tests
make test

Data
	•	Place raw CAROL CSVs in data/raw/. Do not commit raw data.
