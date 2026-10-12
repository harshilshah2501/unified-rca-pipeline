# Workload profiles (Stage 4.0)

Percentages are **experimental scenarios**, not Motadata production estimates.

| Profile | Forward BFS | Reverse blast | Dependency chain |
| ------- | ----------: | ------------: | ---------------: |
| `forward_dominant` | 90% | 5% | 5% |
| `balanced` | 45% | 45% | 10% |
| `reverse_heavy` | 20% | 70% | 10% |

## Trace rules

1. Emit a deterministic JSONL query trace from `(family, edges, seed, profile, trace_len)`.
2. Seeds drawn from out-degree bins p10 / p50 / p90; reverse-heavy also includes the max-degree hub.
3. Hops cycle `{1,2,3}` across ops.
4. **Identical trace file** is replayed against every layout for that estate.
5. Default `trace_len = 200` ops for screening (enough for per-class p50/p95 signal; not Stage 4.6 p99 confirmation).

## Fairness

Do not regenerate queries per layout. Checkpoint: SHA-256 of the query-trace JSONL recorded in the run manifest.
