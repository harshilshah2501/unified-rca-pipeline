"""Convert simulation frames into normalized animation frames."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from rca_spec_parser import RCASpec
from simulation_engine.base import SimulationFrame

COLORS = {
    "expected": "#22c55e",
    "actual": "#ef4444",
    "drift": "#f59e0b",
    "normal": "#60a5fa",
    "hot": "#f97316",
    "symptom": "#a855f7",
    "observer": "#38bdf8",
    "subject": "#f472b6",
    "D1": "#22c55e",
    "D2": "#ef4444",
}


@dataclass
class GraphState:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    colors: dict[str, str] = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)
    positions: dict[str, list[float]] = field(default_factory=dict)


@dataclass
class OverlayState:
    text: str = ""
    charts: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnimationFrame:
    frame_id: int
    graph_state: GraphState
    overlays: OverlayState
    metadata: dict[str, Any] = field(default_factory=dict)


def _layout_positions(node_ids: list[str], edges: list[tuple[str, str]]) -> dict[str, list[float]]:
    if not node_ids:
        return {}
    graph = nx.DiGraph()
    for nid in node_ids:
        graph.add_node(nid)
    for src, dst in edges:
        if src in node_ids and dst in node_ids:
            graph.add_edge(src, dst)
    if len(node_ids) == 1:
        return {node_ids[0]: [0.0, 0.0]}
    try:
        pos = nx.spring_layout(graph, seed=42, k=2.0)
    except Exception:
        pos = {nid: [float(i), 0.0] for i, nid in enumerate(node_ids)}
    return {nid: [float(pos[nid][0]), float(pos[nid][1])] for nid in node_ids if nid in pos}


def _histogram_bins(values: list[float], bins: int = 12) -> list[dict[str, Any]]:
    if not values:
        return []
    import numpy as np

    counts, edges = np.histogram(values, bins=bins)
    return [
        {"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def _murphy_frames(spec: RCASpec, sim_frames: list[SimulationFrame], positions: dict[str, list[float]]) -> list[AnimationFrame]:
    node_ids = [n["id"] for n in spec.nodes]
    static_edges = [(e["from"], e["to"]) for e in spec.edges]
    path_entities = sim_frames[0].metadata.get("path_entities", node_ids) if sim_frames else node_ids
    focus = spec.fault.target
    symptom_entity = (spec.symptom or {}).get("entity", node_ids[-1])

    result: list[AnimationFrame] = []
    for idx, sf in enumerate(sim_frames):
        colors = {nid: COLORS["normal"] for nid in node_ids}
        highlights: list[str] = []
        if sf.metadata.get("phase") == "propagation":
            for src, dst in sf.edges_active:
                colors[dst] = COLORS["hot"]
                highlights.append(dst)
        if focus in node_ids:
            colors[focus] = COLORS["hot"]
        if symptom_entity in node_ids:
            colors[symptom_entity] = COLORS["symptom"]

        edges = [
            {"from": src, "to": dst, "active": (src, dst) in sf.edges_active}
            for src, dst in static_edges
        ]
        charts: list[dict[str, Any]] = []
        counters: dict[str, Any] = {}
        text = sf.metadata.get("phase", "")

        if sf.distributions:
            d1 = sf.distributions.get("D1", [])
            d2 = sf.distributions.get("D2", [])
            charts.append(
                {
                    "type": "histogram",
                    "series": [
                        {"name": "D1", "color": COLORS["D1"], "bins": _histogram_bins(d1)},
                        {"name": "D2", "color": COLORS["D2"], "bins": _histogram_bins(d2)},
                    ],
                }
            )
            if sf.metadata.get("d1_mean") is not None:
                counters["D1_mean"] = round(sf.metadata["d1_mean"], 3)
            if sf.metadata.get("d2_mean") is not None:
                counters["D2_mean"] = round(sf.metadata["d2_mean"], 3)

        if sf.metadata.get("phase") == "result":
            text = sf.metadata.get("ttest", text)
            counters["p_value"] = sf.metadata.get("p_value")

        graph_nodes = [{"id": nid, "label": nid} for nid in node_ids]
        result.append(
            AnimationFrame(
                frame_id=idx,
                graph_state=GraphState(
                    nodes=graph_nodes,
                    edges=edges,
                    colors=colors,
                    highlights=highlights,
                    positions=positions,
                ),
                overlays=OverlayState(text=text, charts=charts, counters=counters),
                metadata=dict(sf.metadata),
            )
        )
    return result


def _nezha_dag_layout(
    expected: list[str],
    actual: list[str],
) -> dict[str, list[float]]:
    positions: dict[str, list[float]] = {}
    for i, nid in enumerate(expected):
        positions[nid] = [float(i) * 2.8 - len(expected) * 1.4, 1.4]
    for i, nid in enumerate(actual):
        if nid not in positions:
            positions[nid] = [float(i) * 2.8 - len(actual) * 1.4, -1.4]
    return positions


def _nezha_frames(spec: RCASpec, sim_frames: list[SimulationFrame]) -> list[AnimationFrame]:
    labels = {n["id"]: n.get("template", n["id"]) for n in spec.nodes}
    all_ids = list(labels.keys())
    static_edges = [(e["from"], e["to"]) for e in spec.edges]
    full_expected = sim_frames[-1].metadata.get("expected_path", []) if sim_frames else []
    full_actual = sim_frames[-1].metadata.get("actual_path", []) if sim_frames else []
    base_positions = _nezha_dag_layout(full_expected, full_actual)

    result: list[AnimationFrame] = []
    for idx, sf in enumerate(sim_frames):
        expected = sf.metadata.get("expected_path", [])
        actual = sf.metadata.get("actual_path", [])
        drift_edge = sf.metadata.get("drift_edge")
        drift_index = sf.metadata.get("drift_index", -1)

        colors: dict[str, str] = {}
        highlights: list[str] = []
        visible_ids = list(dict.fromkeys(expected + actual))
        visible_nodes: list[dict[str, Any]] = []

        for nid in visible_ids:
            if nid in expected and nid in actual:
                colors[nid] = COLORS["expected"] if sf.step <= drift_index else COLORS["drift"]
            elif nid in expected:
                colors[nid] = COLORS["expected"]
            else:
                colors[nid] = COLORS["actual"]
            visible_nodes.append({"id": nid, "label": labels.get(nid, nid)})

        if drift_edge and sf.step > drift_index:
            highlights.append(drift_edge[1])
            colors[drift_edge[1]] = COLORS["drift"]

        visible_set = set(visible_ids)
        edges = [
            {
                "from": src,
                "to": dst,
                "active": (src, dst) in sf.edges_active,
                "drift": drift_edge == (src, dst),
            }
            for src, dst in static_edges
            if src in visible_set and dst in visible_set
        ]

        positions = {nid: base_positions[nid] for nid in visible_ids if nid in base_positions}
        drift_pair = sf.metadata.get("drift_pair")

        if sf.step == 0:
            title = "Nezha: Event-graph drift detection"
            subtitle = "Building per-request execution DAG from traces + logs"
        elif drift_pair and sf.step > drift_index:
            title = f"DRIFT at step {sf.step}"
            subtitle = f"Expected: {drift_pair[0]}  vs  Actual: {drift_pair[1]}"
        else:
            last_evt = labels.get(visible_ids[-1], "") if visible_ids else ""
            title = f"Trace step {sf.step}"
            subtitle = f"Event: {last_evt}"

        text = subtitle if (drift_pair and sf.step > drift_index) else ""

        result.append(
            AnimationFrame(
                frame_id=idx,
                graph_state=GraphState(
                    nodes=visible_nodes,
                    edges=edges,
                    colors=colors,
                    highlights=highlights,
                    positions=positions,
                ),
                overlays=OverlayState(
                    text=text,
                    counters={"step": sf.step, "drift_index": drift_index},
                    charts=[{"type": "title", "title": title, "subtitle": subtitle}],
                ),
                metadata=dict(sf.metadata),
            )
        )
    return result


def _panorama_star_layout(observers: list[str], subject: str) -> dict[str, list[float]]:
    positions: dict[str, list[float]] = {subject: [2.5, 0.0]}
    n = len(observers)
    for i, obs in enumerate(observers):
        angle = 3.14159 * (i / max(n - 1, 1))
        positions[obs] = [-2.5 + 1.2 * math.cos(angle), 2.0 * math.sin(angle)]
    return positions


def _panorama_frames(spec: RCASpec, sim_frames: list[SimulationFrame]) -> list[AnimationFrame]:
    observers = [n["id"] for n in spec.nodes if n.get("role") == "observer"]
    subjects = [n["id"] for n in spec.nodes if n.get("role") == "subject"]
    subject = subjects[0] if subjects else spec.fault.target
    node_ids = observers + [subject]
    edges = [(obs, subject) for obs in observers]
    positions = _panorama_star_layout(observers, subject)
    metric_name = spec.fault.metrics[0] if spec.fault.metrics else "SyncThread"

    result: list[AnimationFrame] = []
    for idx, sf in enumerate(sim_frames):
        colors = {obs: COLORS["observer"] for obs in observers}
        colors[subject] = COLORS["subject"]
        highlights: list[str] = []
        if sf.metadata.get("consensus_locked"):
            highlights.append(subject)

        pano = sf.metadata.get("pano", {})
        batch = sf.metadata.get("batch_reports", [])
        tick = sf.metadata.get("tick", idx + 1)

        charts: list[dict[str, Any]] = [
            {
                "type": "panorama_dashboard",
                "title": f"Panorama: Who is unhealthy on {subject}?",
                "subtitle": f"Observers report {metric_name} status (tick {tick})",
                "batch_reports": batch,
                "view_summaries": sf.metadata.get("view_summaries", {}),
                "pano": pano,
                "consensus_locked": bool(sf.metadata.get("consensus_locked")),
            }
        ]

        vote_bars = sf.metadata.get("vote_bars", {})
        text = ""
        if sf.metadata.get("consensus_locked"):
            text = f"Consensus: {subject} is UNHEALTHY on {metric_name}"

        result.append(
            AnimationFrame(
                frame_id=idx,
                graph_state=GraphState(
                    nodes=[
                        {
                            "id": nid,
                            "label": nid,
                            "role": "observer" if nid in observers else "subject",
                        }
                        for nid in node_ids
                    ],
                    edges=[
                        {"from": src, "to": dst, "active": (src, dst) in sf.edges_active}
                        for src, dst in edges
                    ],
                    colors=colors,
                    highlights=highlights,
                    positions=positions,
                ),
                overlays=OverlayState(
                    text=text,
                    charts=charts,
                    counters={"tick": tick},
                ),
                metadata={**sf.metadata, "vote_bars": vote_bars},
            )
        )
    return result


def generate_frames(spec: RCASpec, sim_frames: list[SimulationFrame]) -> list[AnimationFrame]:
    if spec.system == "murphy":
        node_ids = [n["id"] for n in spec.nodes]
        static_edges = [(e["from"], e["to"]) for e in spec.edges]
        positions = _layout_positions(node_ids, static_edges)
        return _murphy_frames(spec, sim_frames, positions)
    if spec.system == "nezha":
        return _nezha_frames(spec, sim_frames)
    if spec.system == "panorama":
        return _panorama_frames(spec, sim_frames)
    raise ValueError(f"Unknown system: {spec.system}")
