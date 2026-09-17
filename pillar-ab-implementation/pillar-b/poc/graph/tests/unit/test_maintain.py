from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import FIXTURES
from graph.graph_builder import GraphState
from graph.graph_writer import GraphWriter
from graph.maintain import drop_stale_corroborating, expire_edges, maintain_graph_validity
from graph.provenance import build_discovered_via


def test_expire_edges_drops_past_valid_to():
    state = GraphState()
    state.edges["e_old"] = {
        "schema_version": "graph_edge.v1",
        "tenant": "default",
        "edge_id": "e_old",
        "src_ci_id": "a",
        "dst_ci_id": "b",
        "relation": "depends_on",
        "discovered_via": build_discovered_via("declared"),
        "valid_from": "2026-08-20T00:00:00Z",
        "valid_to": "2026-08-20T03:00:00Z",
    }
    removed = expire_edges(state, "2026-08-20T04:00:00Z")
    assert removed == 1
    assert "e_old" not in state.edges


def test_drop_stale_corroborating():
    state = GraphState()
    state.edges["e_stale"] = {
        "schema_version": "graph_edge.v1",
        "tenant": "default",
        "edge_id": "e_stale",
        "src_ci_id": "a",
        "dst_ci_id": "b",
        "relation": "communicates_with",
        "discovered_via": build_discovered_via("corroborating", telemetry_source="apm"),
        "valid_from": "2026-08-20T01:00:00Z",
        "valid_to": None,
    }
    removed = drop_stale_corroborating(state, "2026-08-20T04:00:00Z", max_age_seconds=3600)
    assert removed == 1
    assert "e_stale" not in state.edges


def test_maintain_graph_validity_combined():
    state = GraphState()
    state.edges["expired"] = {
        "schema_version": "graph_edge.v1",
        "tenant": "default",
        "edge_id": "expired",
        "src_ci_id": "a",
        "dst_ci_id": "b",
        "relation": "depends_on",
        "discovered_via": build_discovered_via("declared"),
        "valid_from": "2026-08-20T00:00:00Z",
        "valid_to": "2026-08-20T03:00:00Z",
    }
    state.edges["stale"] = {
        "schema_version": "graph_edge.v1",
        "tenant": "default",
        "edge_id": "stale",
        "src_ci_id": "a",
        "dst_ci_id": "c",
        "relation": "communicates_with",
        "discovered_via": build_discovered_via("corroborating", telemetry_source="apm"),
        "valid_from": "2026-08-20T01:00:00Z",
        "valid_to": None,
    }
    stats = maintain_graph_validity(state, "2026-08-20T04:00:00Z")
    assert stats == {"expired_edges": 1, "stale_corroborating": 1}
    assert not state.edges


def test_writer_maintain_and_reflush():
    writer = GraphWriter()
    writer.load_seed(FIXTURES / "topology.seed.json")
    writer.ingest(JsonlIngestSource(FIXTURES / "stream.resolved.jsonl"))
    dest = MemoryDest()
    before = writer.flush(dest, version="1")
    # Mark one stream edge as already expired.
    for edge in writer.state.edges.values():
        if edge.get("discovered_via", {}).get("telemetry_source") == "apm":
            edge["valid_to"] = "2026-08-20T03:00:00Z"
            break
    stats = writer.maintain_validity("2026-08-20T04:00:00Z")
    assert stats["expired_edges"] >= 1
    after = writer.flush(dest, version="2")
    assert after["version"] == "2"
    assert len(after["edges"]) < len(before["edges"])
