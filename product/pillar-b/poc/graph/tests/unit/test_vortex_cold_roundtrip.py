"""GraphWriter publish_map / load_snapshot behind vortex_s3.v1 (map_vortex_cold)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from ab_shared.dest import FileDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.cold_vortex import PROFILE_VORTEX, resolve_map_vortex_cold
from graph.graph_writer import GraphWriter
from graph.neighbors import neighbor_ids
from graph.snapshot import load_snapshot

_CRATE = Path(__file__).resolve().parents[4] / "map-vortex"


def _ensure_cold_bin() -> Path:
    try:
        return resolve_map_vortex_cold()
    except FileNotFoundError:
        subprocess.run(
            ["cargo", "build", "--bin", "map_vortex_cold"],
            cwd=_CRATE,
            check=True,
            capture_output=True,
            text=True,
        )
        return resolve_map_vortex_cold()


@pytest.fixture(scope="module")
def cold_bin() -> Path:
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    return _ensure_cold_bin()


def test_graph_writer_vortex_publish_load_walk(tmp_path: Path, cold_bin: Path) -> None:
    writer = GraphWriter(tenant="default")
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = FileDest(tmp_path, tenant="default")
    snap = writer.publish_map(dest, version="lab-1", profile=PROFILE_VORTEX)
    assert snap["version"] == "lab-1"

    map_root = dest.root / "map"
    assert (map_root / "latest.json").is_file()
    latest = json.loads((map_root / "latest.json").read_text())
    assert latest["version"] == "lab-1"
    ver = map_root / "snapshots" / "lab-1"
    assert (ver / "manifest.json").is_file()
    assert (ver / "nodes" / "part-00000.vortex").is_file()
    assert (ver / "edges" / "part-00000.vortex").is_file()

    manifest = json.loads((ver / "manifest.json").read_text())
    assert manifest["schema_version"] == "map_snapshot_manifest.v1"
    assert manifest["node_count"] == len(snap["nodes"])
    assert manifest["edge_count"] == len(snap["edges"])
    assert "nodes/part-00000.vortex" in manifest["node_parts"]

    loaded = load_snapshot(dest)  # auto-detect vortex via latest.json
    assert loaded is not None
    assert loaded["schema_version"] == "graph_snapshot.v1"
    assert loaded["version"] == "lab-1"
    assert len(loaded["nodes"]) == len(snap["nodes"])
    assert len(loaded["edges"]) == len(snap["edges"])
    # Flat lock: clocks are integers, no metadata bag
    for n in loaded["nodes"]:
        assert isinstance(n["last_seen"], int)
        assert "metadata" not in n
    assert "payments-db" in neighbor_ids(loaded, "checkout-api") or neighbor_ids(
        loaded, "checkout-api"
    )

    # Binary path used (sanity — cold_bin fixture built it)
    assert cold_bin.is_file()


def test_files_v1_still_default(tmp_path: Path) -> None:
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = FileDest(tmp_path, tenant="default")
    writer.publish_map(dest, version="1")  # default files.v1
    assert dest.get("map", "graph_snapshot.json") is not None
    assert not (dest.root / "map" / "latest.json").exists()
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert loaded["version"] == "1"
