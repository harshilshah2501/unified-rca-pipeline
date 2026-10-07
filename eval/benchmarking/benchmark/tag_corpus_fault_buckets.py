#!/usr/bin/env python3
"""Stamp fault_bucket / fault_type onto corpus ground_truth.json files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmarking" / "benchmark"))

from fault_taxonomy import apply_to_ground_truth  # noqa: E402

TARGETS = [
    REPO / "datasets" / "observeops",
    REPO / "datasets" / "ingest_samples" / "observeops-replay",
    REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "incidents",
]


def _pack_id(gt_path: Path) -> str:
    # …/UC-1/ground_truth.json or …/motadata-apm-001/ground_truth.json
    return gt_path.parent.name


def main() -> int:
    updated = 0
    for root in TARGETS:
        if not root.is_dir():
            continue
        for gt_path in sorted(root.rglob("ground_truth.json")):
            pack = _pack_id(gt_path)
            gt = json.loads(gt_path.read_text(encoding="utf-8"))
            new_gt = apply_to_ground_truth(gt, pack)
            if new_gt != gt:
                gt_path.write_text(json.dumps(new_gt, indent=2) + "\n", encoding="utf-8")
                updated += 1
                print(f"tagged {pack}: {new_gt['fault_bucket']} / {new_gt['fault_type']}")
            else:
                print(f"ok     {pack}: {gt.get('fault_bucket')} / {gt.get('fault_type')}")
    print(f"updated {updated} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
