"""Unit tests for RelationshipGraph."""

from murphy.graph import RelationshipGraph
from murphy.store import InMemoryMetricStore
from murphy.types import Entity


def test_bidirectional_edges_by_default():
    g = RelationshipGraph()
    g.add_entity(Entity("a", "vm", "app1"))
    g.add_entity(Entity("b", "vm", "app1"))
    g.add_edge("a", "b")
    assert "b" in g.neighbors("a")
    assert "a" in g.neighbors("b")
    assert "a" in g.in_neighbors("b")
    assert "b" in g.in_neighbors("a")


def test_cycle_detection_not_an_error():
    g = RelationshipGraph()
    n = 50
    for i in range(n):
        g.add_entity(Entity(f"e{i}", "vm", "app1"))
    for i in range(n):
        for j in range(i + 1, n):
            g.add_edge(f"e{i}", f"e{j}")
    assert len(g.entity_ids) == n
    reachable = g.bfs_from("e0", max_hops=3)
    assert len(reachable) > 1


def test_shortest_path_subgraph_includes_all_paths():
    g = RelationshipGraph()
    for node in ["a", "b", "c", "d", "e"]:
        g.add_entity(Entity(node, "vm", "app1"))
    g.add_edge("a", "b", bidirectional=False)
    g.add_edge("b", "d", bidirectional=False)
    g.add_edge("a", "c", bidirectional=False)
    g.add_edge("c", "d", bidirectional=False)
    g.add_edge("d", "e", bidirectional=False)

    subgraph = g.shortest_path_subgraph("a", "e")
    assert subgraph[0] == "a"
    assert "b" in subgraph
    assert "c" in subgraph
    assert "d" in subgraph
    assert subgraph[-1] == "e"
    assert len(subgraph) == 5


def test_prune_candidates_removes_normal_entities():
    g = RelationshipGraph()
    g.add_entity(Entity("symptom", "vm", "app1"))
    g.add_entity(Entity("anomaly", "vm", "app1"))
    g.add_entity(Entity("normal", "vm", "app1"))
    g.add_edge("symptom", "anomaly")
    g.add_edge("symptom", "normal")

    current_metrics = {
        "symptom": {"cpu_usage": 0.9},
        "anomaly": {"cpu_usage": 0.95},
        "normal": {"cpu_usage": 0.3},
    }
    historical_stats = {
        "symptom": {"cpu_usage": (0.3, 0.05)},
        "anomaly": {"cpu_usage": (0.3, 0.05)},
        "normal": {"cpu_usage": (0.3, 0.05)},
    }

    candidates = g.prune_candidates(
        "symptom", current_metrics, historical_stats, threshold_stdevs=1.0
    )
    assert "anomaly" in candidates
    assert "symptom" in candidates
    assert "normal" not in candidates


def test_build_from_monitoring_db():
    store = InMemoryMetricStore(
        entities=[
            Entity(
                "vm1",
                "vm",
                "app1",
                metadata={"host_id": "host1", "neighbors": ["ms1"]},
            ),
            Entity("host1", "host", "app1", metadata={}),
            Entity(
                "ms1",
                "microservice",
                "app1",
                metadata={"upstream": ["vm1"]},
            ),
        ]
    )
    g = RelationshipGraph()
    g.build_from_monitoring_db("app1", store)
    assert "vm1" in g.entity_ids
    assert "host1" in g.entity_ids
    assert "ms1" in g.entity_ids
