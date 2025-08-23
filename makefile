# Use bash for convenience
SHELL := /bin/bash

.PHONY: help venv install freeze run app test clean

help:
	@echo "make venv      - create virtual env (.venv)"
	@echo "make install   - install dependencies from requirements.txt"
	@echo "make freeze    - write exact versions to requirements.txt"
	@echo "make run       - run Streamlit app"
	@echo "make test      - run pytest"
	@echo "make clean     - remove caches and build artifacts"

venv:
	python3 -m venv .venv
	@echo "Run: source .venv/bin/activate"

install:
	source .venv/bin/activate && \
	python -m pip install -U pip setuptools wheel && \
	python -m pip install -r requirements.txt

freeze:
	source .venv/bin/activate && \
	python -m pip freeze > requirements.txt

run:
	source .venv/bin/activate && \
	streamlit run app.py

app: run

test:
	source .venv/bin/activate && \
	pytest -q

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +; \
	find . -name "*.pyc" -delete; \
	rm -rf .pytest_cache
