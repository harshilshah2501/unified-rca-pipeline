"""Load ObserveOps signal registry from signals.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_REGISTRY_PATH = Path(__file__).resolve().parent / "signals.yaml"


@lru_cache(maxsize=1)
def load_registry() -> dict:
    return yaml.safe_load(_REGISTRY_PATH.read_text())


def ci_type_prefix(ci_type: str) -> str:
    return load_registry()["ci_types"][ci_type]["prefix"]


def rule(name: str) -> dict:
    return load_registry()["rules"][name]


def infra_prefixes() -> tuple[str, ...]:
    return tuple(rule("upstream_healthy")["infra_prefixes"])


def app_prefixes() -> tuple[str, ...]:
    return tuple(rule("upstream_healthy")["app_prefixes"])


def decisive_signals() -> set[str]:
    """All decisive telemetry signals from ci_types registry."""
    out: set[str] = set()
    for cfg in load_registry()["ci_types"].values():
        out.update(cfg["signals"])
    return out
