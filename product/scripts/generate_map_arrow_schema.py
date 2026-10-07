#!/usr/bin/env python3
"""Phase-2: generate map-vortex/src/schema.rs from Motadata physical overlays.

Edit:
  contracts/schemas/graph_node_v1.physical.json
  contracts/schemas/graph_edge_v1.physical.json

Then:
  python3 scripts/generate_map_arrow_schema.py
  # or: make generate-map-arrow-schema
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from map_physical_schema import SCHEMA_RS, SOT, generate_schema_rs, load_json


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    node = load_json(SOT / "graph_node_v1.physical.json")
    edge = load_json(SOT / "graph_edge_v1.physical.json")
    body = generate_schema_rs(node, edge)
    SCHEMA_RS.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_RS.write_text(body, encoding="utf-8")
    print(f"OK: wrote {SCHEMA_RS.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
