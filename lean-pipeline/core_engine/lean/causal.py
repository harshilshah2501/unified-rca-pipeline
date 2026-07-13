"""Topology-constrained causal validation used after CARE."""

from __future__ import annotations

from core_engine.lean.invocation_graph import InvocationGraph
from core_engine.lean.temporal import onset_by_ci


def _is_upstream_of(graph: InvocationGraph, downstream: str, root: str) -> bool:
    """Whether following effect→cause edges from ``downstream`` reaches root."""
    queue = [downstream]
    visited: set[str] = set()
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node == root:
            return True
        queue.extend(graph.upstream_of(node))
    return False


def verify_care_root(
    graph: InvocationGraph,
    seed_ci: str,
    root_ci: str,
    crossed: list[dict],
) -> tuple[bool, list[dict]]:
    """
    Verify a CARE result with only incident topology and onset evidence.

    This deliberately is not a full causal-discovery algorithm: a verified
    root must be anomalous, reachable upstream of the symptom seed, and no
    earlier anomaly may exist on a topology-connected downstream path.
    """
    onset = onset_by_ci(crossed)
    log: list[dict] = []
    root_onset = onset.get(root_ci)
    if root_onset is None:
        log.append({"check": "root_anomalous", "passed": False, "root_ci": root_ci})
        return False, log
    log.append(
        {
            "check": "root_anomalous",
            "passed": True,
            "root_ci": root_ci,
            "onset": root_onset.isoformat(),
        }
    )

    reaches_seed = _is_upstream_of(graph, seed_ci, root_ci)
    log.append(
        {
            "check": "topology_upstream_of_seed",
            "passed": reaches_seed,
            "seed_ci": seed_ci,
            "root_ci": root_ci,
        }
    )
    if not reaches_seed:
        return False, log

    downstream = sorted(
        ci
        for ci in onset
        if ci != root_ci and _is_upstream_of(graph, ci, root_ci)
    )
    temporal_ok = all(root_onset <= onset[ci] for ci in downstream)
    log.append(
        {
            "check": "onset_precedes_connected_symptoms",
            "passed": temporal_ok,
            "root_onset": root_onset.isoformat(),
            "connected_downstream_cis": downstream,
        }
    )
    return bool(downstream) and temporal_ok, log
