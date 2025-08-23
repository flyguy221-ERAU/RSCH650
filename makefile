# Use bash
SHELL := /bin/bash

# Virtual env paths
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: help venv install freeze run app test clean build

help:
	@echo "make venv      - create virtual env (.venv)"
	@echo "make install   - install dependencies from requirements.txt into .venv"
	@echo "make freeze    - write exact versions to requirements.txt"
	@echo "make build     - run pipeline (main.py) to generate Parquets"
	@echo "make run       - run Streamlit app"
	@echo "make test      - run pytest"
	@echo "make clean     - remove caches"

# Create venv once
$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install -U pip

venv: $(VENV)/bin/python
	@echo "Virtual env ready at $(VENV)"

# Install requirements into venv
install: $(VENV)/bin/python
	$(PIP) install -r requirements.txt

# Freeze exact versions
freeze: $(VENV)/bin/python
	$(PIP) freeze > requirements.txt

# Build Parquets by running your pipeline
build: $(VENV)/bin/python install
	$(PY) main.py

# Run Streamlit
run: $(VENV)/bin/python install
	$(PY) -m streamlit run app.py

app: run

# Run tests
test: $(VENV)/bin/python install
	$(PY) -m pytest -q

# Clean caches
clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +; \
	find . -name "*.pyc" -delete; \
	rm -rf .pytest_cache