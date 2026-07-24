#!/usr/bin/env python3
"""Build Motadata APM topology stub (services + host) for Localize smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO
    / "datasets"
    / "ingest_samples"
    / "motadata-ingest"
    / "incidents"
    / "motadata-apm-001"
    / "topology.json"
)


def build_apm_topology() -> dict:
    """Typed CI graph for Motadata APM slice (effect → cause edges)."""
    return {
        "version": "1.0.0",
        "source": "motadata_depth",
        "nodes": [
            {
                "id": "apmagentanant",
                "type": "Host",
                "name": "apmagentanant",
            },
            {
                "id": "ProductCatalog_dotnet.",
                "type": "Service",
                "name": "ProductCatalog_dotnet.",
            },
            {
                "id": "hibernatewithmysql",
                "type": "Service",
                "name": "hibernatewithmysql",
            },
        ],
        "edges": [
            # effect → cause (Lean walks upstream from symptom)
            {
                "from": "ProductCatalog_dotnet.",
                "to": "apmagentanant",
                "relation": "runs_on",
            },
            {
                "from": "hibernatewithmysql",
                "to": "apmagentanant",
                "relation": "runs_on",
            },
            {
                "from": "ProductCatalog_dotnet.",
                "to": "hibernatewithmysql",
                "relation": "depends_on",
            },
        ],
        "note": (
            "Stub from Motadata span host_name + service_span_service_name. "
            "Not a full Motadata inventory export."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Motadata APM topology stub")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    topo = build_apm_topology()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(topo, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
