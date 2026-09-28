#!/usr/bin/env python3
"""Ensure JSON schemas live only under contracts/schemas/ (SoT).

Policy: edit schemas only in pillar-ab-implementation/contracts/schemas/.
Do **not** keep package mirrors under pillar-a|b/integration/contracts/schemas/
(symlink or copy). Validators load the SoT path directly.

Exit 0 on success; 1 if SoT is broken or a forbidden mirror directory exists.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOT = ROOT / "contracts" / "schemas"

FORBIDDEN_MIRRORS = (
    ROOT / "pillar-a" / "contracts" / "schemas",
    ROOT / "pillar-b" / "contracts" / "schemas",
    ROOT / "integration" / "contracts" / "schemas",
)

# Minimum set the PoC validators expect today.
REQUIRED = frozenset(
    {
        "ingest_v1.schema.json",
        "sketch_v1.schema.json",
        "graph_node_v1.schema.json",
        "graph_edge_v1.schema.json",
        "graph_snapshot_v1.schema.json",
        "change_fact_v1.schema.json",
        "writer_stream_v1.schema.json",
        "graph_write_intent_v1.schema.json",
        "sketch_admit_intent_v1.schema.json",
    }
)


def main() -> int:
    errors: list[str] = []

    if not SOT.is_dir():
        print(f"FAIL: SoT missing: {SOT}", file=sys.stderr)
        return 1

    present = {p.name for p in SOT.glob("*.schema.json")}
    missing = sorted(REQUIRED - present)
    if missing:
        errors.append(f"SoT missing schemas: {missing}")

    for name in sorted(present & REQUIRED):
        path = SOT / name
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    for mirror in FORBIDDEN_MIRRORS:
        if mirror.exists():
            errors.append(
                f"forbidden package schema mirror (remove it): "
                f"{mirror.relative_to(ROOT)}"
            )

    if errors:
        print("Schema check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "Edit only contracts/schemas/; do not add package mirrors "
            "(see scripts/check_schema_mirrors.py).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: SoT schemas parse ({SOT}); no package mirrors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
