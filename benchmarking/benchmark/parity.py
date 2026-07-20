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
)


def run_shared_detect(uc_id: str, corpus: Path) -> DetectResult:
    return detect_uc(corpus / uc_id)


def materialize_parity_corpus(
    uc_id: str,
    corpus: Path,
    detect: DetectResult,
    parity_root: Path,
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
    write_detect_artifacts(detect, dst)
    return parity_root


def apply_detect_to_bundle(bundle: dict, detect: DetectResult) -> dict:
    """Overlay shared detect artifacts onto an in-memory Federated bundle."""
    bundle = dict(bundle)
    bundle["anomalies"] = detect.anomalies
    bundle["symptom_seed"] = detect.symptom_seed
    return bundle
