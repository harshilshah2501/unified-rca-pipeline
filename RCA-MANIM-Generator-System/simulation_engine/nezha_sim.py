"""Nezha event-graph drift simulation."""

from __future__ import annotations

from rca_spec_parser import RCASpec
from simulation_engine.base import SimulationFrame


def _build_paths(spec: RCASpec) -> tuple[list[str], list[str]]:
    expected: list[str] = []
    actual: list[str] = []
    both_nodes: list[str] = []
    expected_only: dict[str, str] = {}
    actual_only: dict[str, str] = {}

    for node in spec.nodes:
        node_id = node["id"]
        path_kind = node.get("path", "both")
        if path_kind in ("both", "expected"):
            if path_kind == "expected" and path_kind != "both":
                expected_only[node_id] = node_id
            else:
                both_nodes.append(node_id)
        if path_kind == "actual":
            actual_only[node_id] = node_id

    ordered_both = sorted(
        both_nodes,
        key=lambda nid: next(
            (n.get("cluster_id", 0) for n in spec.nodes if n["id"] == nid), 0
        ),
    )

    diverge_at = spec.fault.diverge_at or spec.fault.target
    for node_id in ordered_both:
        expected.append(node_id)
        actual.append(node_id)
        if node_id == diverge_at:
            break

    for node in spec.nodes:
        if node.get("path") == "expected" and node["id"] not in expected:
            expected.append(node["id"])
        if node.get("path") == "actual" and node["id"] not in actual:
            actual.append(node["id"])

    if spec.fault.target not in actual:
        actual.append(spec.fault.target)

    for node_id in ordered_both:
        if node_id in expected and node_id in actual:
            continue
        if node_id not in expected and node_id not in actual:
            idx = next((i for i, n in enumerate(spec.nodes) if n["id"] == node_id), -1)
            if idx >= 0:
                expected.append(node_id)
                actual.append(node_id)

    tail = [n["id"] for n in spec.nodes if n["id"] == "evt_4"]
    for node_id in tail:
        if node_id not in expected:
            expected.append(node_id)
        if node_id not in actual:
            actual.append(node_id)

    return expected, actual


def _path_edges(path: list[str], spec: RCASpec) -> list[tuple[str, str]]:
    edge_set = {(e["from"], e["to"]) for e in spec.edges}
    path_edges: list[tuple[str, str]] = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        if (a, b) in edge_set:
            path_edges.append((a, b))
        else:
            for fr, to in edge_set:
                if fr == a and to in path[i + 1 :]:
                    path_edges.append((fr, to))
                    break
    return path_edges


def _find_drift_index(expected: list[str], actual: list[str]) -> int:
    for i, (e, a) in enumerate(zip(expected, actual)):
        if e != a:
            return i
    max_len = max(len(expected), len(actual))
    for i in range(max_len):
        e = expected[i] if i < len(expected) else None
        a = actual[i] if i < len(actual) else None
        if e != a:
            return i
    return -1


class NezhaSimulator:
    def run(self, spec: RCASpec) -> list[SimulationFrame]:
        expected_path, actual_path = _build_paths(spec)
        drift_index = _find_drift_index(expected_path, actual_path)
        if drift_index < 0:
            for i, (e, a) in enumerate(zip(expected_path, actual_path)):
                if e != a:
                    drift_index = i
                    break

        node_labels = {
            n["id"]: n.get("template", n["id"]) for n in spec.nodes
        }
        max_steps = max(len(expected_path), len(actual_path))
        frames: list[SimulationFrame] = []

        for step in range(max_steps + 1):
            visible_expected = expected_path[: min(step, len(expected_path))]
            visible_actual = actual_path[: min(step, len(actual_path))]
            active_edges: list[tuple[str, str]] = []
            if step > 0:
                if step - 1 < len(expected_path) - 1:
                    active_edges.append((expected_path[step - 1], expected_path[step]))
                if step - 1 < len(actual_path) - 1:
                    edge = (actual_path[step - 1], actual_path[step])
                    if edge not in active_edges:
                        active_edges.append(edge)

            node_states: dict[str, float | str] = {}
            for nid in visible_expected:
                node_states[f"expected:{nid}"] = node_labels.get(nid, nid)
            for nid in visible_actual:
                node_states[f"actual:{nid}"] = node_labels.get(nid, nid)

            drift_edge: tuple[str, str] | None = None
            if drift_index >= 0 and step > drift_index:
                if drift_index < len(actual_path) - 1:
                    drift_edge = (actual_path[drift_index], actual_path[drift_index + 1])
                elif drift_index < len(expected_path) - 1:
                    drift_edge = (expected_path[drift_index], expected_path[drift_index + 1])

            frames.append(
                SimulationFrame(
                    step=step,
                    node_states=node_states,
                    distributions={},
                    edges_active=active_edges,
                    metadata={
                        "phase": "trace_evolution",
                        "expected_path": visible_expected,
                        "actual_path": visible_actual,
                        "drift_index": drift_index,
                        "drift_edge": drift_edge,
                        "drift_pair": (
                            (
                                node_labels.get(expected_path[drift_index], ""),
                                node_labels.get(actual_path[drift_index], ""),
                            )
                            if drift_index >= 0
                            and drift_index < len(expected_path)
                            and drift_index < len(actual_path)
                            else None
                        ),
                    },
                )
            )

        return frames
