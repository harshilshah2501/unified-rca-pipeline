"""Edge triplet allowlist checks — Motadata fifteen-relation catalog."""

from ab_shared import reject_codes as rc
from ab_shared.dest import MemoryDest
from ab_shared.ingest_source import ListIngestSource
from graph.edge_triplets import check_edge_triplet
from graph.graph_writer import GraphWriter
from ab_shared.paths import SAMPLE_ESTATE


def test_runs_on_service_to_host_ok():
    assert check_edge_triplet("runs_on", "service", "host") == ("ok", None)


def test_runs_on_service_to_service_illegal():
    action, reason = check_edge_triplet("runs_on", "service", "service")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_depends_on_service_to_host_illegal_use_runs_on():
    action, reason = check_edge_triplet("depends_on", "service", "host")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_depends_on_service_to_db_ok():
    assert check_edge_triplet("depends_on", "service", "db") == ("ok", None)


def test_part_of_service_to_business_service_ok():
    assert check_edge_triplet("part_of", "service", "business_service") == ("ok", None)


def test_part_of_wrong_direction_illegal():
    action, reason = check_edge_triplet("part_of", "business_service", "service")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_missing_endpoint_type():
    action, reason = check_edge_triplet("runs_on", "service", None)
    assert action == "reject"
    assert reason == rc.MISSING_ENDPOINT_TYPE


def test_writer_drops_illegal_triplet_without_writing_edge():
    writer = GraphWriter()
    writer.load_estate_bootstrap(SAMPLE_ESTATE / "topology.bootstrap.json")
    writer.write_topo_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "fact_kind": "topo_update",
                    "relation": "depends_on",
                    "src_ci_id": "checkout-api",
                    "dst_ci_id": "linux-server-app-01",
                    "dst_ci_type": "Host",
                    "identity": {"status": "resolved", "bind_source": "bad-catalog"},
                }
            ]
        )
    )
    reasons = {r for _, r in writer.rejects}
    assert rc.ILLEGAL_EDGE_TRIPLET in reasons
    # Bootstrap already has depends_on to payments-db; ensure we did not add depends_on to host.
    snapshot = writer.publish_map(MemoryDest())
    bad = [
        e
        for e in snapshot["edges"]
        if e["edge_type"] == "DEPENDS_ON"
        and e["source_id"] == "checkout-api"
        and e["target_id"] == "linux-server-app-01"
    ]
    assert not bad


def test_mounts_host_to_volume_ok():
    assert check_edge_triplet("mounts", "host", "volume") == ("ok", None)


def test_mounts_service_to_service_illegal():
    action, reason = check_edge_triplet("mounts", "service", "service")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_member_of_pod_to_namespace_ok():
    assert check_edge_triplet("member_of", "pod", "namespace") == ("ok", None)


def test_member_of_pod_to_node_illegal():
    action, reason = check_edge_triplet("member_of", "pod", "node")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_clustered_with_same_tier_ok():
    assert check_edge_triplet("clustered_with", "service", "service") == ("ok", None)


def test_clustered_with_cross_tier_illegal():
    action, reason = check_edge_triplet("clustered_with", "service", "db")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_uses_same_pairs_as_depends_on():
    assert check_edge_triplet("uses", "service", "db") == ("ok", None)
    action, reason = check_edge_triplet("uses", "service", "host")
    assert action == "reject"
    assert reason == rc.ILLEGAL_EDGE_TRIPLET


def test_writer_drops_when_dst_type_unknown_and_not_on_map():
    writer = GraphWriter()
    writer.write_topo_stream(
        ListIngestSource(
            [
                {
                    "schema_version": "ingest.v1",
                    "ts": "2026-08-20T03:30:00Z",
                    "tenant": "default",
                    "ci_id": "checkout-api",
                    "ci_type": "Service",
                    "fact_kind": "topo_update",
                    "relation": "depends_on",
                    "src_ci_id": "checkout-api",
                    "dst_ci_id": "mystery-db",
                    # no dst_ci_type, and mystery-db not on map
                    "identity": {"status": "resolved"},
                }
            ]
        )
    )
    reasons = {r for _, r in writer.rejects}
    assert rc.MISSING_ENDPOINT_TYPE in reasons
