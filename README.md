# NTSB CAROL / eADMS Audit Dashboard (RSCH 650)

Interactive Streamlit app + lightweight pipeline to explore NTSB CAROL-derived accident data:
- Event-level, finding-level, and sequence-of-events parquet outputs
- Phase × occurrence heatmap
- Finding categories with cause/factor splits
- System-risk view (derived from findings) with chi-square and odds ratio

## Quick start
```bash
git clone <your-repo-url>
cd rsch650-ntsb-carol
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt