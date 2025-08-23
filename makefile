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
	python3 -M venv .venv
	@echo "Run: source .venv/bin/activate"

install:
	. .venv/bin/activate && $(PY) -m pip install -U pip && \
	$(PY) -m pip install -r requirements.txt


freeze:
	source .venv/bin/activate && \
	python -m pip freeze > requirements.txt

run:
	. .venv/bin/activate && streamlit run app.py

app: run

test:
	. .venv/bin/activate && pytest -q

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +; \
	find . -name "*.pyc" -delete; \
	rm -rf .pytest_cache

build:
	# runs your pipeline to generate Parquets into data/out
	. .venv/bin/activate && $(PY) main.py