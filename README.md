# NTSB CAROL / eADMS Audit Dashboard (RSCH 650)

Interactive Streamlit app + lightweight pipeline to explore NTSB CAROL-derived accident data:
- Event-level, finding-level, and sequence-of-events parquet outputs
- Phase × occurrence heatmap
- Finding categories with cause/factor splits
- System-risk view (derived from findings) with chi-square and odds ratio

## Quick start
git clone <repo>
cd <repo>
make venv
make install
make build   # generates Parquets into data/out
make run     # launches Streamlit
