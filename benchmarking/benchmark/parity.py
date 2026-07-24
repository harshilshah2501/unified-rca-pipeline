"""Fair-parity helpers: shared threshold detect before Lean / Federated RCA."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DETECT_DIR = REPO / "ingestion-poc" / "detect"
if str(DETECT_DIR) not in sys.path:
    sys.path.insert(0, str(DETECT_DIR))

from threshold_detect import DetectResult, detect_uc, write_detect_artifacts  # noqa: E402

# Files RCA needs beyond detect artifacts (Lean diagnose / Fed store).
_BUNDLE_COPY = (
    "topology.json",
    "events.json",
    "ground_truth.json",
    "manifest.json",
    "changes.jsonl",
    "changes.json",
)


def run_shared_detect(uc_id: str, corpus: Path) -> DetectResult:
    return detect_uc(corpus / uc_id)


def resolve_changes_path(uc_id: str, corpus: Path) -> Path | None:
    """Optional per-UC change feed for D2 annotation on the scoreboard."""
    base = corpus / uc_id
    for name in ("changes.jsonl", "changes.json"):
        p = base / name
        if p.is_file():
            return p
    return None


def annotate_change_near_onset(
    detect: DetectResult,
    changes_path: Path | None,
    *,
    change_window_minutes: int = 30,
) -> DetectResult:
    """Attach D2 ``change_context`` onto ``detect`` when a change feed exists."""
    if changes_path is None:
        return detect
    from change_near_onset import change_near_onset, load_changes

    changes = load_changes(changes_path)
    ctx = change_near_onset(
        incident_start=detect.anomalies.get("incident_start"),
        changes=changes,
        window_minutes=change_window_minutes,
    )
    detect.change_context = ctx
    if detect.symptom_seed:
        detect.symptom_seed = {
            **detect.symptom_seed,
            "change_near_onset": ctx["change_near_onset"],
            "change_count_in_window": ctx["change_count_in_window"],
        }
    return detect


def materialize_parity_corpus(
    uc_id: str,
    corpus: Path,
    detect: DetectResult,
    parity_root: Path,
    *,
    changes_path: Path | None = None,
    change_window_minutes: int = 30,
) -> Path:
    """Build a mini corpus dir where anomalies/seed come from shared detect.

    Returns the parity corpus root (parent of ``uc_id/``).
    """
    src = corpus / uc_id
    dst = parity_root / uc_id
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in _BUNDLE_COPY:
        p = src / name
        if p.exists():
            shutil.copy2(p, dst / name)
    metrics_src = src / "metrics"
    if metrics_src.is_dir():
        shutil.copytree(metrics_src, dst / "metrics")
    ch = changes_path or resolve_changes_path(uc_id, corpus)
    write_detect_artifacts(
        detect,
        dst,
        changes_path=ch,
        change_window_minutes=change_window_minutes,
    )
    return parity_root


def apply_detect_to_bundle(bundle: dict, detect: DetectResult) -> dict:
    """Overlay shared detect artifacts onto an in-memory Federated bundle."""
    bundle = dict(bundle)
    bundle["anomalies"] = detect.anomalies
    bundle["symptom_seed"] = detect.symptom_seed
    return bundle


def detect_meta_for_scoreboard(detect: DetectResult) -> dict:
    """D1 fields for bakeoff ``run_meta.json`` (includes ``C_detect`` alias)."""
    meta = detect.to_meta()
    # Explicit cost-model alias used in docs / cheatsheet.
    meta["C_detect_ms"] = meta.get("detect_latency_ms")
    if detect.change_context is not None:
        meta["change_near_onset"] = detect.change_context.get("change_near_onset")
        meta["change_count_in_window"] = detect.change_context.get(
            "change_count_in_window"
        )
        meta["change_window_minutes"] = detect.change_context.get("window_minutes")
    elif "change_near_onset" not in meta:
        meta["change_near_onset"] = False
        meta["change_count_in_window"] = 0
    return meta
