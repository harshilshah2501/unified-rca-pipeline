"""Corpus helpers for ObserveOps / OO engine_packs / Motadata incidents."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OBSERVEOPS = REPO / "datasets" / "observeops"
OO_PACKS = REPO / "datasets" / "openobserve_incidents" / "v1" / "engine_packs"
MOTADATA_INCIDENTS = (
    REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "incidents"
)


def is_observeops_uc_corpus(corpus: Path) -> bool:
    return corpus.resolve() == DEFAULT_OBSERVEOPS.resolve() or corpus.name == "observeops"


def is_frozen_pack_corpus(corpus: Path) -> bool:
    """OO engine_packs or Motadata incidents — frozen anomalies, no metrics/ detect."""
    resolved = corpus.resolve()
    if resolved == OO_PACKS.resolve() or corpus.name == "engine_packs":
        return True
    if resolved == MOTADATA_INCIDENTS.resolve() or (
        corpus.name == "incidents"
        and corpus.parent.name == "motadata-ingest"
    ):
        return True
    # Heuristic: directory of packs with topology.json and no UC-1 layout
    if not corpus.is_dir():
        return False
    kids = [p for p in corpus.iterdir() if p.is_dir() and (p / "topology.json").is_file()]
    if not kids:
        return False
    if (corpus / "UC-1").is_dir():
        return False
    return True


def results_subdir(corpus: Path) -> str | None:
    """Optional results nesting: oo / motadata / ecom / None (ObserveOps flat)."""
    resolved = corpus.resolve()
    if resolved == OO_PACKS.resolve() or corpus.name == "engine_packs":
        return "oo"
    if resolved == MOTADATA_INCIDENTS.resolve() or (
        corpus.name == "incidents" and corpus.parent.name == "motadata-ingest"
    ):
        return "motadata"
    if corpus.name == "incidents" and corpus.parent.name == "ecom_checkout":
        return "ecom"
    return None


def pack_ids(corpus: Path) -> list[str]:
    if is_observeops_uc_corpus(corpus) or (
        not is_frozen_pack_corpus(corpus) and (corpus / "UC-1").is_dir()
    ):
        return [f"UC-{i}" for i in range(1, 6)]
    return sorted(
        p.name
        for p in corpus.iterdir()
        if p.is_dir() and (p / "topology.json").is_file()
    )


def results_dir(results_root: Path, corpus: Path, uc_id: str, run_id: str) -> Path:
    sub = results_subdir(corpus)
    if sub:
        return results_root / sub / uc_id / f"run-{run_id}"
    return results_root / uc_id / f"run-{run_id}"
