PY ?= .venv/bin/python

.PHONY: setup data pipeline run test test-all lint

setup:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -r requirements.txt
	uv pip install --python $(PY) -e .

data:
	$(PY) -m quantedge.data.download --refresh

pipeline:
	$(PY) -m quantedge.pipeline

run:
	$(PY) -m streamlit run app/Home.py

test:
	$(PY) -m pytest -m "not slow and not network"

test-all:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests app scripts
