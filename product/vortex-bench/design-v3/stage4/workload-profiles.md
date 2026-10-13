# Workload profiles (Stage 4.0)

Percentages are **experimental scenarios**, not Motadata production estimates.

| Profile | Forward BFS | Reverse blast | Dependency chain |
| ------- | ----------: | ------------: | ---------------: |
| `forward_dominant` | 90% | 5% | 5% |
| `balanced` | 45% | 45% | 10% |
| `reverse_heavy` | 20% | 70% | 10% |
| `scope_policy_mixed` | 70% | 20% | 10% |

`scope_policy_mixed` is the **Action 2 approved** Motadata-facing mix for Milestone A (Scope default outbound + non-zero inbound/both for saturation / monitoring / ingress). It is **not** a measured production mix — approved via intake waiver; see [`../action2-synthetic-operating-envelope.md`](../action2-synthetic-operating-envelope.md).

## Trace rules

1. Emit a deterministic JSONL query trace from `(family, edges, seed, profile, trace_len)`.
2. Seeds drawn from out-degree bins p10 / p50 / p90; reverse-heavy also includes the max-degree hub.
3. Hops cycle `{1,2,3}` across ops.
4. **Identical trace file** is replayed against every layout for that estate.
5. Default `trace_len = 200` ops for screening (enough for per-class p50/p95 signal; not Stage 4.6 p99 confirmation).

## Fairness

Do not regenerate queries per layout. Checkpoint: SHA-256 of the query-trace JSONL recorded in the run manifest.
