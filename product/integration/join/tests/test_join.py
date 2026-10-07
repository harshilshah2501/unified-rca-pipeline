from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import JsonlIngestSource
from ab_shared.paths import SAMPLE_ESTATE
from graph.change_fact import append_change_fact, make_change_fact
from graph.graph_builder import apply_topo_stream, load_estate_bootstrap_state
from graph.snapshot import build_snapshot, publish_snapshot
from join.harness import door_c_flags, identity_join, working_set_embryo
from join.maintain import maintain
from sketch.sketch_flush import SketchWriter


def _build_both(dest: MemoryDest):
    state = load_estate_bootstrap_state(SAMPLE_ESTATE / "topology.bootstrap.json")
    apply_topo_stream(state, JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    snap = build_snapshot(state)
    publish_snapshot(dest, snap)
    writer = SketchWriter()
    writer.ingest(JsonlIngestSource(SAMPLE_ESTATE / "stream.resolved.jsonl"))
    writer.flush(dest)
    return state, writer, snap


def test_identity_join_ok():
    dest = MemoryDest()
    _, _, snap = _build_both(dest)
    result = identity_join(snap, dest)
    assert result["ok"]
    assert "checkout-api" in result["sketch_entities"]
    assert "linux-server-app-01" in result["sketch_entities"]


def test_working_set_embryo():
    dest = MemoryDest()
    _, _, snap = _build_both(dest)
    ws = working_set_embryo(snap, dest, seed_ci="checkout-api")
    assert ws["seed_ci"] == "checkout-api"
    assert "linux-server-app-01" in ws["neighbors"] or "payments-db" in ws["neighbors"]
    assert any(s["metric_id"] == "request.latency_ms" for s in ws["sketches"])


def test_door_c_no_false_fire_on_lab():
    dest = MemoryDest()
    _build_both(dest)
    flags = door_c_flags(dest, entity_id="checkout-api", ratio=1.5)
    # First window seeds baseline from itself → should not fire
    assert flags["fired"] is False


def test_e5_maintain_bumps_version_and_expires():
    dest = MemoryDest()
    state, writer, _ = _build_both(dest)
    # Force one edge expired
    eid = next(iter(state.edges))
    state.edges[eid]["valid_to"] = "2026-08-20T03:00:00Z"
    out = maintain(state, writer, dest, as_of="2026-08-20T04:00:00Z", bump_version="2")
    assert out["expired_edges"] == 1
    assert out["snapshot_version"] == "2"


def test_change_fact_not_a_vertex():
    dest = MemoryDest()
    fact = make_change_fact(
        tenant="default",
        change_id="chg-1",
        ci_id="checkout-api",
        occurred_at="2026-08-20T02:00:00Z",
        change_kind="deploy",
        summary="rollout",
    )
    append_change_fact(dest, fact)
    raw = dest.get("history", "change_facts.jsonl")
    assert raw and b"change_fact.v1" in raw
    assert b"graph_node" not in raw
