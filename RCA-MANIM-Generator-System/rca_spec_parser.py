"""Parse raw scenario text / markdown into validated RCA-SPEC."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "rca_spec.schema.json"
_DEFAULTS = {
    "seed": 42,
    "simulation": {
        "inner_sweeps": 4,
        "outer_samples": 5000,
        "model": "ridge + gibbs",
    },
    "visualization": {
        "style": "wave",
        "show_counterfactual": True,
        "show_drift": False,
    },
}

_SYSTEM_DEFAULTS = {
    "murphy": {"simulation": {"model": "ridge + gibbs"}, "visualization": {"style": "wave"}},
    "nezha": {"simulation": {"model": "event_graph"}, "visualization": {"style": "graph", "show_drift": True}},
    "panorama": {"simulation": {"model": "voting"}, "visualization": {"style": "vote"}},
}


@dataclass
class FaultSpec:
    type: str
    target: str
    metrics: list[str] = field(default_factory=list)
    multiplier: float = 8.0
    diverge_at: str | None = None


@dataclass
class SimulationConfig:
    inner_sweeps: int = 4
    outer_samples: int = 5000
    model: str = "ridge + gibbs"


@dataclass
class VisualizationConfig:
    style: str = "wave"
    show_counterfactual: bool = True
    show_drift: bool = False


@dataclass
class RCASpec:
    system: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    fault: FaultSpec
    seed: int = 42
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    symptom: dict[str, str] | None = None
    reports: list[dict[str, Any]] = field(default_factory=list)
    incident_time: str | None = None
    app_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "seed": self.seed,
            "nodes": self.nodes,
            "edges": self.edges,
            "fault": {
                "type": self.fault.type,
                "target": self.fault.target,
                "metrics": self.fault.metrics,
                "multiplier": self.fault.multiplier,
                **({"diverge_at": self.fault.diverge_at} if self.fault.diverge_at else {}),
            },
            "simulation": {
                "inner_sweeps": self.simulation.inner_sweeps,
                "outer_samples": self.simulation.outer_samples,
                "model": self.simulation.model,
            },
            "visualization": {
                "style": self.visualization.style,
                "show_counterfactual": self.visualization.show_counterfactual,
                "show_drift": self.visualization.show_drift,
            },
            **({"symptom": self.symptom} if self.symptom else {}),
            **({"reports": self.reports} if self.reports else {}),
            **({"incident_time": self.incident_time} if self.incident_time else {}),
            **({"app_id": self.app_id} if self.app_id else {}),
        }


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    spec = _deep_merge(_DEFAULTS, raw)
    system = spec.get("system", "murphy").lower()
    if system in _SYSTEM_DEFAULTS:
        spec = _deep_merge(spec, _SYSTEM_DEFAULTS[system])
        spec = _deep_merge(spec, raw)
    spec.setdefault("edges", [])
    spec.setdefault("nodes", [])
    return spec


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    merged = _apply_defaults(spec)
    schema = _load_schema()
    jsonschema.validate(instance=merged, schema=schema)
    return merged


def _parse_yaml_list_item(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line.startswith("- "):
        return None
    content = line[2:].strip()
    if content.startswith("{"):
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
        except yaml.YAMLError:
            pass
    try:
        parsed = yaml.safe_load("{" + content + "}")
        if isinstance(parsed, dict):
            return parsed
    except yaml.YAMLError:
        pass
    if ":" not in content:
        return None
    result: dict[str, Any] = {}
    for part in _split_top_level_commas(content):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        key = key.strip()
        val = val.strip()
        try:
            result[key] = yaml.safe_load(val)
        except yaml.YAMLError:
            result[key] = val.strip("\"'")
    return result


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return parts


def _parse_markdown_sections(body: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _parse_markdown_body(body: str) -> dict[str, Any]:
    sections = _parse_markdown_sections(body)
    result: dict[str, Any] = {}

    if "nodes" in sections:
        nodes = []
        for line in sections["nodes"]:
            item = _parse_yaml_list_item(line)
            if item:
                nodes.append(item)
        result["nodes"] = nodes

    if "edges" in sections:
        edges = []
        for line in sections["edges"]:
            item = _parse_yaml_list_item(line)
            if item:
                if "from" in item and "to" in item:
                    edges.append(item)
        result["edges"] = edges

    if "fault" in sections:
        fault: dict[str, Any] = {}
        for line in sections["fault"]:
            line = line.strip()
            if line.startswith("- ") or not line or line.startswith("#"):
                item = _parse_yaml_list_item(line) if line.startswith("- ") else None
                if item:
                    fault.update(item)
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                fault[key.strip()] = yaml.safe_load(val.strip())
        result["fault"] = fault

    if "symptom" in sections:
        symptom: dict[str, str] = {}
        for line in sections["symptom"]:
            if ":" in line:
                key, val = line.split(":", 1)
                symptom[key.strip()] = str(yaml.safe_load(val.strip()))
        result["symptom"] = symptom

    if "reports" in sections:
        reports = []
        for line in sections["reports"]:
            item = _parse_yaml_list_item(line)
            if item:
                reports.append(item)
        result["reports"] = reports

    return result


def parse_markdown(text: str) -> dict[str, Any]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("Markdown scenario must start with YAML frontmatter delimited by ---")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body_spec = _parse_markdown_body(match.group(2))
    return _deep_merge(frontmatter, body_spec)


def parse_input(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raw = parse_markdown(text)
    return validate_spec(raw)


def spec_from_dict(data: dict[str, Any]) -> RCASpec:
    validated = validate_spec(data)
    fault_data = validated["fault"]
    sim_data = validated.get("simulation", {})
    vis_data = validated.get("visualization", {})
    return RCASpec(
        system=validated["system"],
        seed=validated.get("seed", 42),
        nodes=validated["nodes"],
        edges=validated.get("edges", []),
        fault=FaultSpec(
            type=fault_data["type"],
            target=fault_data["target"],
            metrics=fault_data.get("metrics", []),
            multiplier=float(fault_data.get("multiplier", 8.0)),
            diverge_at=fault_data.get("diverge_at"),
        ),
        simulation=SimulationConfig(
            inner_sweeps=int(sim_data.get("inner_sweeps", 4)),
            outer_samples=int(sim_data.get("outer_samples", 5000)),
            model=str(sim_data.get("model", "ridge + gibbs")),
        ),
        visualization=VisualizationConfig(
            style=str(vis_data.get("style", "wave")),
            show_counterfactual=bool(vis_data.get("show_counterfactual", True)),
            show_drift=bool(vis_data.get("show_drift", False)),
        ),
        symptom=validated.get("symptom"),
        reports=validated.get("reports", []),
        incident_time=validated.get("incident_time"),
        app_id=validated.get("app_id"),
    )
