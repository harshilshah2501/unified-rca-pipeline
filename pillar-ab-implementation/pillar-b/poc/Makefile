.PHONY: venv install test-unit test-shared test-graph test-all

PY ?= .venv/bin/python

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install -r requirements.txt

test-shared:
	$(PY) -m pytest ab_shared

test-graph:
	$(PY) -m pytest graph/tests/unit

test-unit test-all:
	$(PY) -m pytest
