"""Canonical paths for the reorganized Unified-RCA repo."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

DATASETS = REPO_ROOT / "datasets"
OBSERVEOPS_CORPUS = DATASETS / "observeops"
NEZHA_DATA = DATASETS / "nezha"
INGEST_SAMPLES = DATASETS / "ingest_samples"
JSONL_RESOLVED = INGEST_SAMPLES / "jsonl_resolved"

# Sole evaluation corpus specification (UC-1..UC-5 ObserveOps)
USE_CASES_SPEC = REPO_ROOT / "rca-use-cases-only.md"

DOCS = REPO_ROOT / "docs"
PILLAR_AB = REPO_ROOT / "pillar-ab-implementation"
PILLAR_AB_CONTRACTS = PILLAR_AB / "contracts"
PILLAR_A = PILLAR_AB / "pillar-a"
PILLAR_B = PILLAR_AB / "pillar-b"
PILLAR_AB_INTEGRATION = PILLAR_AB / "integration"
INGESTION_POC = REPO_ROOT / "ingestion-poc"

FEDERATED_PIPELINE = REPO_ROOT / "federated-pipeline"
LEAN_PIPELINE = REPO_ROOT / "lean-pipeline"

BENCHMARKING = REPO_ROOT / "benchmarking"
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
