"""Shared simulation types and protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from rca_spec_parser import RCASpec


@dataclass
class SimulationFrame:
    step: int
    node_states: dict[str, float | str]
    distributions: dict[str, list[float]] = field(default_factory=dict)
    edges_active: list[tuple[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSimulator(Protocol):
    def run(self, spec: RCASpec) -> list[SimulationFrame]: ...
