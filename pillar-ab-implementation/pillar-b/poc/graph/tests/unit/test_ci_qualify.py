from graph.ci_qualify import Category, may_emit_vertex, qualify


def test_never_ci_types():
    for name in ("Alert", "Incident", "Change", "Trace", "Metric", "LogPattern", "ITSMTicket"):
        assert qualify(name) == Category.NEVER
        ok, reason = may_emit_vertex(name)
        assert not ok and reason == "never_ci_vertex"


def test_wave1_clearly():
    for name in ("Service", "Host", "Runtime", "BusinessService", "Database"):
        assert qualify(name) == Category.CLEARLY
        assert may_emit_vertex(name)[0]


def test_temporary():
    assert qualify("Pod") == Category.TEMPORARY
    assert may_emit_vertex("Pod")[0]
