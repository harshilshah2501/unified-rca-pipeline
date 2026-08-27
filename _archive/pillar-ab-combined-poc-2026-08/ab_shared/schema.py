from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "schemas"


@lru_cache
def _validator(name: str) -> Draft202012Validator:
    path = CONTRACTS / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate(name: str, instance: dict) -> None:
    _validator(name).validate(instance)


def is_valid(name: str, instance: dict) -> bool:
    return _validator(name).is_valid(instance)
