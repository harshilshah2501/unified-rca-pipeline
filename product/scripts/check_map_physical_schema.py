#!/usr/bin/env python3
"""Phase-1: hard sync check — JSON Schema ↔ physical overlay ↔ generated schema.rs.

Exit 0 on success; 1 on drift or Motadata rule violations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ on path when invoked as python3 scripts/check_map_physical_schema.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_physical_schema import (  # noqa: E402
    SCHEMA_RS,
    SOT,
    check_logical_vs_physical,
    generate_schema_rs,
    load_json,
)


def main() -> int:
    errors: list[str] = []

    node_phys = load_json(SOT / "graph_node_v1.physical.json")
    edge_phys = load_json(SOT / "graph_edge_v1.physical.json")
    node_logical = load_json(SOT / node_phys["logical_schema"])
    edge_logical = load_json(SOT / edge_phys["logical_schema"])

    check_logical_vs_physical(node_logical, node_phys, errors)
    check_logical_vs_physical(edge_logical, edge_phys, errors)

    expected_rs = generate_schema_rs(node_phys, edge_phys)
    if not SCHEMA_RS.is_file():
        errors.append(f"missing generated file: {SCHEMA_RS}")
    else:
        actual = SCHEMA_RS.read_text(encoding="utf-8")
        if actual != expected_rs:
            errors.append(
                "pillar-b/map-vortex/src/schema.rs is out of date with physical overlays. "
                "Run: make generate-map-arrow-schema"
            )
            # Show a short diff hint
            a_lines = actual.splitlines()
            e_lines = expected_rs.splitlines()
            for i, (a, e) in enumerate(zip(a_lines, e_lines)):
                if a != e:
                    errors.append(f"  first diff near line {i + 1}:")
                    errors.append(f"    have: {a}")
                    errors.append(f"    want: {e}")
                    break
            if len(a_lines) != len(e_lines):
                errors.append(
                    f"  line count have={len(a_lines)} want={len(e_lines)}"
                )

    if errors:
        print("Map physical schema check FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        "OK: graph_node/edge JSON Schema ↔ physical overlay ↔ "
        "map-vortex/src/schema.rs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
