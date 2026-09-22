from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource, ListIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from ab_shared.schema import is_valid
from graph.graph_builder import apply_topo_stream, load_estate_bootstrap_state
from graph.neighbors import neighbor_ids
from graph.snapshot import build_snapshot, load_snapshot, publish_snapshot


def test_bootstrap_and_neighbors():
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "topology.bootstrap.json")
    snap = build_snapshot(state)
    ids = neighbor_ids(snap, "checkout-api")
    assert "linux-server-app-01" in ids
    assert "payments-db" in ids
    assert "bs-checkout" in ids


def test_never_ci_not_emitted():
    bootstrap = {
        "nodes": [
            {"id": "checkout-api", "type": "Service", "name": "checkout-api"},
            {"id": "a1", "type": "Alert", "name": "alert"},
        ],
        "edges": [],
    }
    state = load_estate_bootstrap_state(bootstrap)
    assert "a1" not in state.nodes
    assert any(r[1] == "never_ci_vertex" for r in state.rejects)


def test_unknown_relation_rejected_from_updates():
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "topology.bootstrap.json")
    src = ListIngestSource(
        [
            {
                "schema_version": "ingest.v1",
                "ts": "2026-08-20T03:30:00Z",
                "tenant": "default",
                "ci_id": "checkout-api",
                "ci_type": "Service",
                "fact_kind": "topo_update",
                "relation": "CORRELATED_WITH",
                "src_ci_id": "checkout-api",
                "dst_ci_id": "payments-db",
                "identity": {"status": "resolved"},
            }
        ]
    )
    apply_topo_stream(state, src)
    assert any(r[1] == "unknown_relation" for r in state.rejects)


def test_snapshot_schema_and_dest():
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "topology.bootstrap.json")
    apply_topo_stream(state, JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    snap = build_snapshot(state)
    for n in snap["nodes"]:
        assert is_valid("graph_node_v1.schema.json", n)
        assert n["identity_status"] == "resolved"
    dest = MemoryDest()
    publish_snapshot(dest, snap)
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert neighbor_ids(loaded, "checkout-api")
