from graph.edge_catalog import ALL_RELATIONS, WAVE1_RELATIONS, classify_relation


def test_catalog_has_fifteen():
    assert len(ALL_RELATIONS) == 15
    assert WAVE1_RELATIONS == ALL_RELATIONS


def test_unknown_relation_rejected():
    action, reason = classify_relation("CORRELATED_WITH")
    assert action == "reject"
    assert reason == "unknown_relation"


def test_all_catalog_relations_emit():
    for r in ALL_RELATIONS:
        assert classify_relation(r) == ("emit", None)


def test_mounts_emits_then_triplet_gates():
    """mounts is catalog-emit; legality is EDGE_TRIPLET_ALLOWLIST, not phased skip."""
    assert classify_relation("mounts") == ("emit", None)
