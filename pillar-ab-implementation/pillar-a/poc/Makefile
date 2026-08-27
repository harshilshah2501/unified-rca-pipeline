.PHONY: venv install test-unit test-shared test-sketch test-all

PY ?= .venv/bin/python

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install -r requirements.txt

test-shared:
	$(PY) -m pytest ab_shared

test-sketch:
	$(PY) -m pytest sketch/tests/unit

test-unit test-all:
	$(PY) -m pytest
