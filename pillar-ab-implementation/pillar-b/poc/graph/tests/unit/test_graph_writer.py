from ab_shared.dest import FileDest, MemoryDest
from ab_shared.ingest_source import JsonlIngestSource, ListIngestSource
from ab_shared.paths import FIXTURES
from graph.graph_writer import GraphWriter
from graph.neighbors import neighbor_ids
from graph.read_api import get_neighbors
from graph.snapshot import load_snapshot


def test_graph_writer_happy_path_flush():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    dest = MemoryDest()
    snapshot = writer.publish_map(dest)
    assert snapshot["version"] == "1"
    assert len(snapshot["nodes"]) >= 4
    assert len(snapshot["edges"]) >= 4
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert "payments-db" in get_neighbors(loaded, "checkout-api")


def test_graph_writer_file_dest_roundtrip(tmp_path):
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    dest = FileDest(tmp_path, tenant="default")
    writer.publish_map(dest)
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert neighbor_ids(loaded, "checkout-api")


def test_graph_writer_silent_skip_non_topo():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "signal_class": "metric_sample",
                    "name": "request.latency_ms",
                    "value": 42.0,
                    "identity": {"status": "resolved"},
                },
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "signal_class": "topo_update",
                    "relation": "depends_on",
                    "src_ci_id": "checkout-api",
                    "dst_ci_id": "payments-db",
                    "identity": {"status": "resolved"},
                },
            ]
        )
    )
    assert not writer.rejects
    snapshot = writer.publish_map(MemoryDest())
    assert any(e["relation"] == "depends_on" for e in snapshot["edges"])


def test_graph_writer_reject_tape():
    writer = GraphWriter()
    writer.load_estate_bootstrap(FIXTURES / "topology.bootstrap.json")
    writer.apply_stream(JsonlIngestSource(FIXTURES / "stream.reject.jsonl"))
    reasons = {reason for _, reason in writer.rejects}
    assert "identity_unresolved" in reasons
    assert "identity_synthesized" in reasons
    assert "never_ci_vertex" in reasons
    assert "unknown_relation" in reasons
    snapshot = writer.publish_map(MemoryDest())
    assert not any(n["ci_id"] == "alert-1" for n in snapshot["nodes"])
