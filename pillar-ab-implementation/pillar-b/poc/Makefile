.PHONY: venv install test-unit test-shared test-graph test-all flush check-schemas

PY ?= .venv/bin/python
SLICE_ROOT := $(abspath ../..)

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install -r requirements.txt

check-schemas:
	python3 $(SLICE_ROOT)/scripts/check_schema_mirrors.py

test-shared:
	$(PY) -m pytest ab_shared

test-graph:
	$(PY) -m pytest graph/tests/unit

test-unit: check-schemas
	$(PY) -m pytest

test-all: check-schemas
	$(PY) -m pytest

flush:
	$(PY) -m graph.cli_flush --maintain-validity
