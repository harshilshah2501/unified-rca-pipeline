from graph.provenance import build_discovered_via, evidence_for_source


def test_evidence_types():
    a = build_discovered_via("authoritative", telemetry_source="agent/cgroup")
    assert a["evidence_type"] == "authoritative"
    d = build_discovered_via("declared", telemetry_source="service-catalog")
    assert d["evidence_type"] == "declared"
    c = build_discovered_via("corroborating", telemetry_source="apm/spans")
    assert c["evidence_type"] == "corroborating"


def test_source_heuristic():
    assert evidence_for_source("agent/process-inventory") == "authoritative"
    assert evidence_for_source("service-catalog/sync") == "declared"
    assert evidence_for_source("apm/spans") == "corroborating"
