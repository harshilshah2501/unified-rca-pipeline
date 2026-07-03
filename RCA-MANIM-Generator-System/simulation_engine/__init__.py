"""Simulation engines for Murphy, Nezha, and Panorama."""

from __future__ import annotations

from simulation_engine.base import BaseSimulator
from simulation_engine.murphy_sim import MurphySimulator
from simulation_engine.nezha_sim import NezhaSimulator
from simulation_engine.panorama_sim import PanoramaSimulator

_SIMULATORS: dict[str, type[BaseSimulator]] = {
    "murphy": MurphySimulator,
    "nezha": NezhaSimulator,
    "panorama": PanoramaSimulator,
}


def get_simulator(system: str) -> BaseSimulator:
    key = system.lower()
    if key not in _SIMULATORS:
        raise ValueError(f"Unknown system: {system!r}. Choose from {list(_SIMULATORS)}")
    return _SIMULATORS[key]()


__all__ = [
    "BaseSimulator",
    "MurphySimulator",
    "NezhaSimulator",
    "PanoramaSimulator",
    "get_simulator",
]
