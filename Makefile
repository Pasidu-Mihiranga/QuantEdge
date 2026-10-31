PY ?= .venv/bin/python

.PHONY: setup data pipeline run test test-all lint notebooks defence pdf

setup: .venv/.ready

# First run: build .venv with uv if it is installed, otherwise with Python 3.12 itself.
.venv/.ready: requirements.txt pyproject.toml
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --allow-existing --python 3.12 .venv && uv pip install --python $(PY) -r requirements.txt -e . ; \
	elif command -v python3.12 >/dev/null 2>&1; then \
		python3.12 -m venv .venv && $(PY) -m pip install -q -r requirements.txt -e . ; \
	else \
		echo "Python 3.12 is required: install it, or install uv (https://docs.astral.sh/uv/)"; exit 1 ; \
	fi
	@touch $@

data:
	$(PY) -m quantedge.data.download --refresh

pipeline: setup
	$(PY) -m quantedge.pipeline $(ARGS)

run: setup
	$(PY) -m streamlit run app/Home.py

test: setup
	$(PY) -m pytest -m "not slow and not network"

test-all:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests app scripts

notebooks:
	$(PY) -m pip install -q -r requirements-notebooks.txt
	$(PY) scripts/run_notebooks.py

pdf: setup
	$(PY) scripts/build_pdfs.py

defence: notebooks
	$(PY) scripts/build_defence_pack.py
