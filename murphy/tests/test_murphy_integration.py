"""Integration test — paper Figure 1 crawler incident."""

from murphy.murphy import Murphy
from murphy.tests.fixtures.crawler_incident import (
    INCIDENT_TIME,
    build_crawler_incident_store,
    build_crawler_symptom,
)


def test_crawler_vm_incident():
    """
    Reproduce paper Figure 1:
    Crawler VM -> Frontend -> Backend high CPU.
    """
    store = build_crawler_incident_store()
    symptom = build_crawler_symptom()

    murphy = Murphy(
        monitoring_db=store,
        gibbs_iterations=4,
        n_samples=800,
        max_graph_hops=5,
        parallel=False,
    )
    result = murphy.diagnose(symptom, incident_time=INCIDENT_TIME)

    ranked_ids = [rc.entity_id for rc in result.root_causes]
    assert "crawler_vm" in ranked_ids[:2], (
        f"Expected crawler_vm in top-2, got {ranked_ids}"
    )

    chain = result.explanation_chains.get("crawler_vm", [])
    if not chain:
        chain = result.explanation_chains.get(ranked_ids[0], [])

    path_entities = [chain[0].from_entity] + [s.to_entity for s in chain]
    assert "crawler_vm" in path_entities
    assert "frontend_ms" in path_entities or "backend_vm_1" in path_entities

    if chain:
        assert chain[0].from_entity == "crawler_vm" or any(
            s.from_entity == "crawler_vm" for s in chain
        )
