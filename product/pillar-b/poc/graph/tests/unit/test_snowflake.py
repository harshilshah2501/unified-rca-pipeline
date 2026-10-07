from graph.snowflake import next_snowflake, reset_snowflake, snowflake_from_parts


def test_snowflake_monotonic_with_injectable_clock():
    reset_snowflake(clock=lambda: 1_700_000_000_000, seq=0)
    a = next_snowflake()
    b = next_snowflake()
    assert a < b
    assert isinstance(a, int)


def test_snowflake_from_parts_deterministic():
    assert snowflake_from_parts(1000, 7) == snowflake_from_parts(1000, 7)
    assert snowflake_from_parts(1000, 7) != snowflake_from_parts(1000, 8)
