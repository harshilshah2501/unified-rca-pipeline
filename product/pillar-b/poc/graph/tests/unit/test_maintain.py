from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.graph_builder import GraphState
from graph.graph_writer import GraphWriter
from graph.maintain import drop_stale_corroborating, expire_edges, maintain_graph_validity
from graph.tests.unit.edge_fixtures import motadata_edge


def test_expire_edges_drops_past_valid_to():
    state = GraphState()
    state.edges["a|DEPENDS_ON|b"] = motadata_edge(
        source_id="a",
        target_id="b",
        edge_type="DEPENDS_ON",
        edge_id=10,
        valid_to="2026-08-20T03:00:00Z",
        origin="declared",
    )
    removed = expire_edges(state, "2026-08-20T04:00:00Z")
    assert removed == 1
    assert "a|DEPENDS_ON|b" not in state.edges


def test_drop_stale_corroborating():
    state = GraphState()
    state.edges["a|COMMUNICATES_WITH|b"] = motadata_edge(
        source_id="a",
        target_id="b",
        edge_type="COMMUNICATES_WITH",
        edge_id=11,
        valid_from="2026-08-20T01:00:00Z",
        origin="stream",
        telemetry_source="apm",
    )
    removed = drop_stale_corroborating(state, "2026-08-20T04:00:00Z", max_age_seconds=3600)
    assert removed == 1
    assert "a|COMMUNICATES_WITH|b" not in state.edges


def test_maintain_graph_validity_combined():
    state = GraphState()
    state.edges["expired"] = motadata_edge(
        source_id="a",
        target_id="b",
        edge_id=12,
        valid_to="2026-08-20T03:00:00Z",
        origin="declared",
    )
    state.edges["stale"] = motadata_edge(
        source_id="a",
        target_id="c",
        edge_type="COMMUNICATES_WITH",
        edge_id=13,
        valid_from="2026-08-20T01:00:00Z",
        origin="stream",
        telemetry_source="apm",
    )
    stats = maintain_graph_validity(state, "2026-08-20T04:00:00Z")
    assert stats["expired_edges"] == 1
    assert stats["stale_corroborating"] == 1
    assert not state.edges


def test_apply_declared_soft_stale():
    from graph.maintain import MAINTAIN_SOFT_STALE, apply_declared_freshness

    state = GraphState()
    state.edges["e_decl"] = motadata_edge(
        source_id="a",
        target_id="b",
        edge_id=14,
        origin="declared",
    )
    stats = apply_declared_freshness(state, "2026-08-28T00:00:00Z")  # 8 days
    assert stats["declared_soft_stale"] == 1
    assert state.edges["e_decl"]["maintain_status"] == MAINTAIN_SOFT_STALE


def test_writer_maintain_and_reflush():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = MemoryDest()
    before = writer.publish_map(dest, version="1")
    for edge in writer.state.edges.values():
        if edge.get("telemetry_source") == "apm":
            edge["valid_to"] = "2026-08-20T03:00:00Z"
            break
    stats = writer.maintain_map("2026-08-20T04:00:00Z")
    assert stats["expired_edges"] >= 1
    after = writer.publish_map(dest, version="2")
    assert after["version"] == "2"
    assert len(after["edges"]) < len(before["edges"])
