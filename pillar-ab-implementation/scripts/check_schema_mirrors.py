#!/usr/bin/env python3
"""Ensure package schema mirrors resolve to contracts/schemas/ (SoT).

Policy (F03): edit JSON schemas only under pillar-ab-implementation/contracts/schemas/.
Package trees under pillar-a|b/integration/contracts/schemas/ must be symlinks to SoT
(or, for zip handoffs that materialize files, byte-identical to SoT).

Exit 0 on success; 1 on drift / missing / unexpected real-file mismatch.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOT = ROOT / "contracts" / "schemas"

# Package mirror dirs → expected schema basenames (owner subsets).
MIRRORS: dict[Path, frozenset[str]] = {
    ROOT / "pillar-a" / "contracts" / "schemas": frozenset(
        {"ingest_v1.schema.json", "sketch_v1.schema.json"}
    ),
    ROOT / "pillar-b" / "contracts" / "schemas": frozenset(
        {
            "ingest_v1.schema.json",
            "graph_node_v1.schema.json",
            "graph_edge_v1.schema.json",
            "graph_snapshot_v1.schema.json",
            "change_fact_v1.schema.json",
        }
    ),
    ROOT / "integration" / "contracts" / "schemas": frozenset(
        {
            "ingest_v1.schema.json",
            "sketch_v1.schema.json",
            "graph_node_v1.schema.json",
            "graph_edge_v1.schema.json",
            "graph_snapshot_v1.schema.json",
            "change_fact_v1.schema.json",
        }
    ),
}


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    if not SOT.is_dir():
        print(f"FAIL: SoT missing: {SOT}", file=sys.stderr)
        return 1

    sot_files = {p.name: p for p in SOT.glob("*.schema.json")}
    errors: list[str] = []

    for mirror_dir, expected in MIRRORS.items():
        if not mirror_dir.is_dir():
            errors.append(f"missing mirror dir: {mirror_dir.relative_to(ROOT)}")
            continue

        present = {p.name for p in mirror_dir.glob("*.schema.json")}
        extra = present - expected
        missing = expected - present
        if extra:
            errors.append(
                f"{mirror_dir.relative_to(ROOT)}: unexpected {sorted(extra)}"
            )
        if missing:
            errors.append(
                f"{mirror_dir.relative_to(ROOT)}: missing {sorted(missing)}"
            )

        for name in sorted(present & expected):
            path = mirror_dir / name
            sot = sot_files.get(name)
            if sot is None:
                errors.append(f"{path.relative_to(ROOT)}: no SoT peer {name}")
                continue

            if path.is_symlink():
                resolved = path.resolve()
                if resolved != sot.resolve():
                    errors.append(
                        f"{path.relative_to(ROOT)}: symlink → {resolved} "
                        f"(want {sot.resolve()})"
                    )
                continue

            # Materialized copy (handoff zip): allow only if bytes match SoT.
            if _md5(path) != _md5(sot):
                errors.append(
                    f"{path.relative_to(ROOT)}: real file drifted from SoT "
                    f"(replace with symlink to ../../../contracts/schemas/{name})"
                )
            else:
                print(
                    f"WARN: {path.relative_to(ROOT)} is a real file "
                    f"(ok if handoff zip; prefer symlink in monorepo)",
                    file=sys.stderr,
                )

    if errors:
        print("Schema mirror check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "Edit only contracts/schemas/; re-link package mirrors "
            "(see scripts/check_schema_mirrors.py).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(MIRRORS)} package schema mirrors match SoT ({SOT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
