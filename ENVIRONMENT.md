# Environment & Reproducibility Guide

This document ensures that collaborators and researchers can **reproduce analyses** consistently.

## 📦 Python Environment

- **Python Version**: 3.11.x
- **Package Manager**: pip or make

### Create Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Freeze Dependencies

```bash
pip freeze > requirements-freeze.txt
```

Include `requirements-freeze.txt` when publishing research outputs.

---

## 🌐 External Tools

| Tool      | Version | Purpose                 |
|-----------|--------|-------------------------|
| Streamlit | 1.35+  | UI visualization        |
| DuckDB    | Latest | In-memory parquet ops   |
| Pytest    | Latest | Testing framework       |
| Black     | Latest | Code formatting         |
| Ruff      | Latest | Linting                 |

---

## 📄 Notes

- Raw CAROL CSVs are excluded from version control.
- Outputs are stored in `data/out/` and `reports/`.
