from graph.edge_catalog import ALL_RELATIONS, WAVE1_RELATIONS, classify_relation


def test_catalog_has_fifteen():
    assert len(ALL_RELATIONS) == 15


def test_unknown_relation_rejected():
    action, reason = classify_relation("CORRELATED_WITH")
    assert action == "reject"
    assert reason == "unknown_relation"


def test_wave2_skipped_not_rejected():
    action, reason = classify_relation("mounts")
    assert action == "skip"
    assert reason is None


def test_wave1_emitted():
    for r in WAVE1_RELATIONS:
        assert classify_relation(r) == ("emit", None)
