"""Part B — comprehensive map walk-through proofs.

Part A (build/maintain) is covered by test_p1_map_fabric / test_maintain / SAMPLE_IO.
This module proves Dest ``map/`` is diagnostically walkable: hops, direction,
relation filters, WorkingSet-lite reachability, leaf paths, and E5 confidence marks.
"""

from __future__ import annotations

from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.graph_builder import load_estate_bootstrap_state
from graph.graph_writer import GraphWriter
from graph.maintain import MAINTAIN_HARD_DOWNGRADED, apply_declared_freshness
from graph.neighbors import find_paths, neighbor_ids, neighbors, reachable_ci_ids
from graph.read_api import get_neighbors, get_paths, get_reachable
from graph.snapshot import build_snapshot, load_snapshot


def _checkout_snap() -> dict:
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    return writer.publish_map(MemoryDest())


def _chain_snap() -> dict:
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "walk_chain.bootstrap.json")
    return build_snapshot(state)


# ---------------------------------------------------------------------------
# B1 — one-hop / filters on customer_checkout (build output)
# ---------------------------------------------------------------------------


def test_b1_one_hop_outbound_checkout_api():
    snap = _checkout_snap()
    ids = get_neighbors(snap, "checkout-api", hops=1, direction="out")
    assert set(ids) >= {"linux-server-app-01", "payments-db", "bs-checkout"}


def test_b1_relation_filter_runs_on_only():
    snap = _checkout_snap()
    ids = neighbor_ids(snap, "checkout-api", hops=1, relation="runs_on")
    assert ids == ["linux-server-app-01"]
    edges = neighbors(snap, "checkout-api", hops=1, relations={"depends_on", "part_of"})
    rels = {e["relation"] for e in edges}
    assert rels <= {"depends_on", "part_of"}
    assert "runs_on" not in rels


def test_b1_inbound_who_points_at_payments_db():
    snap = _checkout_snap()
    ids = neighbor_ids(snap, "payments-db", hops=1, direction="in")
    assert "checkout-api" in ids
    # Outbound from DB is empty on this estate (leaf).
    assert neighbor_ids(snap, "payments-db", hops=1, direction="out") == []


def test_b1_inbound_host_has_two_runtimes():
    snap = _checkout_snap()
    ids = neighbor_ids(snap, "linux-server-app-01", hops=1, direction="in")
    assert set(ids) == {"checkout-api", "app-runtime-jvm"}


def test_b1_missing_seed_returns_empty():
    snap = _checkout_snap()
    assert neighbor_ids(snap, "no-such-ci", hops=3) == []
    assert reachable_ci_ids(snap, "no-such-ci", hops=3) == []
    assert find_paths(snap, "no-such-ci", target_ci="payments-db") == []


def test_b1_hops_zero_returns_empty():
    snap = _checkout_snap()
    assert neighbors(snap, "checkout-api", hops=0) == []


# ---------------------------------------------------------------------------
# B2 — multi-hop chain + WorkingSet-lite + leaf paths
# ---------------------------------------------------------------------------


def test_b2_multihop_storefront_to_db_host():
    snap = _chain_snap()
    # 1 hop: only checkout-api
    assert neighbor_ids(snap, "storefront-web", hops=1) == ["checkout-api"]
    # 2 hops: checkout-api + payments-db + app host
    two = set(neighbor_ids(snap, "storefront-web", hops=2))
    assert "checkout-api" in two
    assert "payments-db" in two
    assert "linux-server-app-01" in two
    assert "db-host-01" not in two  # needs 3 hops
    # 3 hops reaches db host
    three = set(neighbor_ids(snap, "storefront-web", hops=3))
    assert "db-host-01" in three


def test_b2_working_set_lite_includes_seed_and_neighborhood():
    snap = _chain_snap()
    ws = get_reachable(snap, "storefront-web", hops=3, direction="out")
    assert ws[0] == "checkout-api" or "storefront-web" in ws
    assert "storefront-web" in ws
    assert "db-host-01" in ws
    assert "payments-db" in ws
    # Without seed
    no_seed = reachable_ci_ids(
        snap, "storefront-web", hops=2, include_seed=False
    )
    assert "storefront-web" not in no_seed
    assert "checkout-api" in no_seed


def test_b2_path_to_named_leaf():
    snap = _chain_snap()
    paths = get_paths(
        snap,
        "storefront-web",
        target_ci="db-host-01",
        max_hops=4,
        direction="out",
    )
    assert paths
    assert paths[0] == [
        "storefront-web",
        "checkout-api",
        "payments-db",
        "db-host-01",
    ]


def test_b2_path_to_host_ci_type():
    snap = _chain_snap()
    paths = find_paths(
        snap,
        "storefront-web",
        target_ci_types=["Host"],
        max_hops=4,
    )
    leaves = {p[-1] for p in paths}
    assert leaves <= {"db-host-01", "linux-server-app-01"}
    assert "db-host-01" in leaves or "linux-server-app-01" in leaves
    for p in paths:
        assert p[0] == "storefront-web"
        assert len(p) >= 2


def test_b2_relation_scoped_path_depends_on_chain():
    snap = _chain_snap()
    # depends_on alone never reaches a Host (runs_on needed for db-host).
    paths = find_paths(
        snap,
        "storefront-web",
        target_ci="db-host-01",
        max_hops=4,
        relations=["depends_on"],
    )
    assert paths == []
    # Mixed allow-list reaches host
    paths2 = find_paths(
        snap,
        "storefront-web",
        target_ci="db-host-01",
        max_hops=4,
        relations=["depends_on", "runs_on"],
    )
    assert paths2 and paths2[0][-1] == "db-host-01"


def test_b2_undirected_both_from_db_host():
    snap = _chain_snap()
    # From leaf host, outbound is empty; both walks back up the chain.
    assert neighbor_ids(snap, "db-host-01", hops=1, direction="out") == []
    up = neighbor_ids(snap, "db-host-01", hops=2, direction="both")
    assert "payments-db" in up
    assert "checkout-api" in up


# ---------------------------------------------------------------------------
# B3 — walk after Dest publish + after E5 maintain marks
# ---------------------------------------------------------------------------


def test_b3_dest_roundtrip_still_walkable():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = MemoryDest()
    writer.publish_map(dest)
    loaded = load_snapshot(dest)
    assert loaded is not None
    assert "payments-db" in get_neighbors(loaded, "checkout-api")
    assert reachable_ci_ids(loaded, "checkout-api", hops=1)


def test_b3_expire_removes_edge_from_walk():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = MemoryDest()
    before = writer.publish_map(dest, version="1")
    # Expire the depends_on edge to payments-db
    victim = None
    for e in writer.state.edges.values():
        if e["relation"] == "depends_on" and e["dst_ci_id"] == "payments-db":
            e["valid_to"] = "2026-08-20T03:00:00Z"
            victim = e["edge_id"]
            break
    assert victim
    assert "payments-db" in neighbor_ids(before, "checkout-api")
    stats = writer.maintain_map("2026-08-20T04:00:00Z")
    assert stats["expired_edges"] >= 1
    after = writer.publish_map(dest, version="2")
    # depends_on gone; communicates_with may still reach payments-db
    dep_only = neighbor_ids(after, "checkout-api", hops=1, relation="depends_on")
    assert "payments-db" not in dep_only
    assert victim not in {e["edge_id"] for e in after["edges"]}


def test_b3_hard_downgrade_excluded_from_confidence_bearing_walk():
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "walk_chain.bootstrap.json")
    # Age the storefront→checkout declared edge past hard window
    eid = "e_storefront-web_depends_on_checkout-api"
    assert eid in state.edges
    state.edges[eid]["valid_from"] = "2025-01-01T00:00:00Z"
    apply_declared_freshness(state, "2026-08-20T00:00:00Z", hard_downgrade_days=30)
    assert state.edges[eid]["maintain_status"] == MAINTAIN_HARD_DOWNGRADED
    snap = build_snapshot(state)

    # Full walk still sees the edge (hard mark stays on published map)
    assert "checkout-api" in neighbor_ids(snap, "storefront-web", hops=1)

    # Confidence-bearing walk skips it → storefront cannot reach deeper seeds
    assert neighbor_ids(
        snap, "storefront-web", hops=3, confidence_bearing_only=True
    ) == []
    assert (
        find_paths(
            snap,
            "storefront-web",
            target_ci="db-host-01",
            max_hops=4,
            confidence_bearing_only=True,
        )
        == []
    )
    # From checkout-api onward still works under the filter
    assert "db-host-01" in neighbor_ids(
        snap, "checkout-api", hops=2, confidence_bearing_only=True
    )


def test_b3_maintain_reflush_working_set_still_nonempty():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    dest = MemoryDest()
    writer.publish_map(dest, version="1")
    writer.maintain_map("2026-08-20T04:00:00Z")
    after = writer.publish_map(dest, version="2")
    ws = get_reachable(after, "checkout-api", hops=1)
    assert "checkout-api" in ws
    assert len(ws) >= 2
