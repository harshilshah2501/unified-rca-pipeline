from ab_shared.dest import MemoryDest
from ab_shared.identity_gate import ResolvedOnlyGate


def test_graph_depends_only_on_shared_stubs():
    gate = ResolvedOnlyGate()
    dest = MemoryDest()
    rec = {"identity": {"status": "resolved"}, "ci_id": "checkout-api"}
    assert gate.admit(rec).accepted
    dest.put("map", "probe", b"ok")
    assert dest.get("map", "probe") == b"ok"
