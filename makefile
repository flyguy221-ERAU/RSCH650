# Use bash shell
SHELL := /bin/bash

# Virtual env paths
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: help venv install freeze export-env run app test clean build lint format check hooks docs reset

help:
	@echo "make venv        - create virtual env (.venv)"
	@echo "make install     - install dependencies from requirements.txt"
	@echo "make freeze      - overwrite requirements.txt with exact versions"
	@echo "make export-env  - save pinned versions to requirements-freeze.txt"
	@echo "make build       - run pipeline (main.py) to generate Parquets"
	@echo "make run         - run Streamlit app"
	@echo "make test        - run pytest suite"
	@echo "make clean       - remove caches, data/out, reports"
	@echo "make lint        - run Ruff checks"
	@echo "make format      - run Black formatting"
	@echo "make check       - run Ruff + Black together"
	@echo "make hooks       - install pre-commit hooks"
	@echo "make docs        - open docs/README.md"
	@echo "make reset       - clean, rebuild, and start app fresh"

# Create venv once
$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install -U pip

venv: $(VENV)/bin/python
	@echo "Virtual env ready at $(VENV)"

# Install dependencies
install: $(VENV)/bin/python
	$(PIP) install -r requirements.txt

# Freeze into requirements.txt (overwrite)
freeze: $(VENV)/bin/python
	$(PIP) freeze > requirements.txt

# Save pinned versions separately for reproducibility
export-env: $(VENV)/bin/python
	$(PIP) freeze > requirements-freeze.txt

# Build Parquets by running the pipeline
build: $(VENV)/bin/python install
	$(PY) main.py

# Run Streamlit app
run: $(VENV)/bin/python install
	$(PY) -m streamlit run app.py

app: run

# Run pytest
test: $(VENV)/bin/python install
	$(PY) -m pytest -q

# Clean caches + outputs + reports
clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +; \
	find . -name "*.pyc" -delete; \
	rm -rf .pytest_cache .ruff_cache .streamlit/cache data/out/* reports/*

# Linting
lint:
	. $(VENV)/bin/activate && ruff check .

# Formatting
format:
	. $(VENV)/bin/activate && black .

# Check formatting & lint together
check:
	. $(VENV)/bin/activate && ruff check . && black --check .

# Install pre-commit hooks
hooks:
	. $(VENV)/bin/activate && pre-commit install

# Quick access to docs
docs:
	@echo "See project documentation in docs/README.md"

# Clean, rebuild, run fresh app
reset:
	make clean && make build && make run
