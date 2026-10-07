"""Canonical paths for the Unified-RCA monorepo (zone layout + compatibility shims).

Zone names (preferred):
  product/     Motadata Pillar A/B (shim: pillar-ab-implementation/)
  knowledge/   Docs hub source (shim: docs/)
  eval/        Bakeoff + datasets (shims: benchmarking/, datasets/)
  reference/   Lean + Federated engines (shims: lean-pipeline/, federated-pipeline/)
  archive/     Parked snapshots (shim: _archive/)

Shim directories at the repo root keep old import paths and bookmarks working.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _first_existing(*candidates: Path) -> Path:
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


# --- Zones (prefer new names; fall back to shim names) ---
PRODUCT = _first_existing(REPO_ROOT / "product", REPO_ROOT / "pillar-ab-implementation")
KNOWLEDGE = _first_existing(REPO_ROOT / "knowledge", REPO_ROOT / "docs")
EVAL_ROOT = _first_existing(REPO_ROOT / "eval")
REFERENCE = _first_existing(REPO_ROOT / "reference")
ARCHIVE = _first_existing(REPO_ROOT / "archive", REPO_ROOT / "_archive")

DATASETS = _first_existing(REPO_ROOT / "datasets", EVAL_ROOT / "datasets")
OBSERVEOPS_CORPUS = DATASETS / "observeops"
NEZHA_DATA = DATASETS / "nezha"
INGEST_SAMPLES = DATASETS / "ingest_samples"
JSONL_RESOLVED = INGEST_SAMPLES / "jsonl_resolved"

# Sole evaluation corpus specification (UC-1..UC-5 ObserveOps)
USE_CASES_SPEC = REPO_ROOT / "rca-use-cases-only.md"

DOCS = KNOWLEDGE  # shim name docs/ → knowledge/
PILLAR_AB = PRODUCT  # shim name pillar-ab-implementation/ → product/
PILLAR_AB_CONTRACTS = PILLAR_AB / "contracts"
PILLAR_A = PILLAR_AB / "pillar-a"
PILLAR_B = PILLAR_AB / "pillar-b"
PILLAR_AB_INTEGRATION = PILLAR_AB / "integration"
INGESTION_POC = REPO_ROOT / "ingestion-poc"

FEDERATED_PIPELINE = _first_existing(
    REPO_ROOT / "federated-pipeline", REFERENCE / "federated-pipeline"
)
LEAN_PIPELINE = _first_existing(REPO_ROOT / "lean-pipeline", REFERENCE / "lean-pipeline")

BENCHMARKING = _first_existing(REPO_ROOT / "benchmarking", EVAL_ROOT / "benchmarking")
BENCHMARK_RESULTS = BENCHMARKING / "results"
CAPACITY_RESULTS = BENCHMARKING / "capacity"
DASHBOARD = BENCHMARKING / "dashboard"

# Reference algorithms live inside the federated pipeline
MURPHY = FEDERATED_PIPELINE / "murphy"
PANORAMA = FEDERATED_PIPELINE / "panorama"
NEZHA = FEDERATED_PIPELINE / "Nezha"

LABS = REPO_ROOT / "labs"
DATADOG_RCA_LAB = LABS / "datadog-rca-lab"
DYNATRACE_RCA_LAB = LABS / "dynatrace-rca-lab"
EDGEDELTA_LAB = LABS / "edgedelta"


def ensure_import_paths() -> None:
    """Insert repo + pipeline packages on sys.path (idempotent)."""
    import sys

    for path in (
        REPO_ROOT,
        FEDERATED_PIPELINE,
        LEAN_PIPELINE,
        BENCHMARKING,
        INGESTION_POC,
        PILLAR_AB,
    ):
        s = str(path)
        if s not in sys.path:
            sys.path.insert(0, s)
