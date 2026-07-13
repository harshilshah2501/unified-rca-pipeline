#!/usr/bin/env python3
"""Validate ObserveOps corpus bundles (UC-1..UC-5 + UC-3b)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("ERROR: jsonschema not installed — pip install jsonschema in .venv", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "datasets" / "observeops"
SCHEMA_DIR = CORPUS / "schema"

REQUIRED_FILES = [
    "topology.json",
    "anomalies.json",
    "symptom_seed.json",
    "ground_truth.json",
    "injection_manifest.yaml",
    "events.json",
]

EVENTS_NONEMPTY = {"UC-2", "UC-4", "UC-3b"}

SCHEMA_MAP = {
    "topology.json": "topology.schema.json",
    "anomalies.json": "anomalies.schema.json",
    "symptom_seed.json": "symptom_seed.schema.json",
    "ground_truth.json": "ground_truth.schema.json",
    "events.json": "events.schema.json",
}


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def _validate_json(path: Path, schema: dict, label: str) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text())
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{label}: {loc}: {err.message}")
    return errors


def validate_uc(uc_dir: Path, schemas: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (uc_dir / name).exists():
            errors.append(f"{uc_dir.name}: missing {name}")
    for filename, schema_name in SCHEMA_MAP.items():
        path = uc_dir / filename
        if path.exists():
            errors.extend(_validate_json(path, schemas[schema_name], f"{uc_dir.name}/{filename}"))
    events_path = uc_dir / "events.json"
    if events_path.exists() and uc_dir.name in EVENTS_NONEMPTY:
        events = json.loads(events_path.read_text()).get("events") or []
        if not events:
            errors.append(f"{uc_dir.name}: events.json must contain ≥1 event")
    metrics = uc_dir / "metrics"
    if not metrics.is_dir() or not any(metrics.iterdir()):
        errors.append(f"{uc_dir.name}: metrics/ empty or missing")
    else:
        metrics_schema = schemas["metrics.schema.json"]
        for metric_file in sorted(metrics.glob("*.json")):
            errors.extend(
                _validate_json(
                    metric_file, metrics_schema, f"{uc_dir.name}/metrics/{metric_file.name}"
                )
            )
    return errors


def validate_manifest(topo_hash: str) -> list[str]:
    errors: list[str] = []
    manifest_yaml = CORPUS / "manifest.yaml"
    if not manifest_yaml.exists():
        errors.append("missing manifest.yaml — run build_corpus.py")
        return errors
    text = manifest_yaml.read_text()
    for key in ("corpus_version:", "use_cases:", "topology_sha256:"):
        if key not in text:
            errors.append(f"manifest.yaml: missing {key.rstrip(':')}")
    for line in text.splitlines():
        if line.startswith("topology_sha256:"):
            recorded = line.split(":", 1)[1].strip()
            if recorded != topo_hash:
                errors.append(
                    f"manifest.yaml: topology_sha256 mismatch (expected {topo_hash}, got {recorded})"
                )
    return errors


def main() -> int:
    if not CORPUS.exists():
        print(f"ERROR: corpus not found at {CORPUS}", file=sys.stderr)
        return 1
    schemas = {name: _load_schema(name) for name in SCHEMA_MAP.values()}
    schemas["metrics.schema.json"] = _load_schema("metrics.schema.json")
    shared_topology = CORPUS / "shared_topology.json"
    if not shared_topology.exists():
        print("ERROR: shared_topology.json missing", file=sys.stderr)
        return 1
    topo_hash = hashlib.sha256(shared_topology.read_bytes()).hexdigest()
    all_errors: list[str] = []
    all_errors.extend(validate_manifest(topo_hash))
    for uc_dir in sorted(CORPUS.glob("UC-*")):
        if uc_dir.is_dir():
            all_errors.extend(validate_uc(uc_dir, schemas))
    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}")
        return 1
    n_uc = len(list(CORPUS.glob("UC-*")))
    print(f"OK: {n_uc} use-case bundles validated (schemas + manifest.yaml topology_sha256)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
