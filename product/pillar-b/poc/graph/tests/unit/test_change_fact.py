from ab_shared.dest import MemoryDest
from graph.change_fact import append_change_fact, make_change_fact


def test_change_fact_append_to_history():
    fact = make_change_fact(
        tenant="default",
        change_id="chg-lab-1",
        ci_id="checkout-api",
        occurred_at="2026-08-20T03:00:00Z",
        change_kind="deploy",
        summary="lab rollout",
    )
    dest = MemoryDest()
    append_change_fact(dest, fact)
    raw = dest.get("history", "change_facts.jsonl")
    assert raw is not None
    assert b"chg-lab-1" in raw
    assert b"deploy" in raw
