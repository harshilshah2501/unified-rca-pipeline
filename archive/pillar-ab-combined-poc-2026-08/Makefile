.PHONY: venv install test-unit test-shared test-graph test-sketch test-join test-all

PY ?= .venv/bin/python

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install -r requirements.txt

test-unit:
	$(PY) -m pytest ab_shared graph/tests/unit sketch/tests/unit

test-shared:
	$(PY) -m pytest ab_shared

test-graph:
	$(PY) -m pytest graph/tests/unit

test-sketch:
	$(PY) -m pytest sketch/tests/unit

test-join:
	$(PY) -m pytest join

test-all:
	$(PY) -m pytest
