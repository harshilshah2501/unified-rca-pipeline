# Report 20 — Action 6 priority 3: durability and replay (lab model)

**Milestone A remains frozen.** Per-segment journals are out of scope.

Lab durability model: durable `committed_gen` + `pending_batch` markers with crash injection at publication boundaries. **Not** Motadata's production commit protocol.

Source: `/root/Harshil-PoCs/Unified-RCA/product/vortex-bench/map-vortex-bench/out/design-v3/action6-durability` — 3 cells.

## Cell `1M-seg64-i10-d2`

Segments=64, batch inserts/deletes=10/2, all_ok=True.

| Crash point | OK | Gen before→after (expect) | Replayed | Lost | Recovery ms | Multiset | Sym | Notes |
| ----------- | -- | ------------------------: | -------: | ---: | ----------: | -------- | --- | ----- |
| `before_mutation_persist` | True | 0→0 (0) | 0 | 0 | 670.1 | True | True | no_pending_retained_previous_committed |
| `after_persist_before_publish` | True | 0→1 (1) | 12 | 0 | 545.8 | True | True | replayed_pending_to_gen_1 |
| `during_snapshot_construction` | True | 0→1 (1) | 12 | 0 | 506.9 | True | True | replayed_pending_to_gen_1 |
| `during_or_after_publication` | True | 0→1 (1) | 12 | 0 | 531.1 | True | True | replayed_pending_to_gen_1 |
| `after_publish_before_replay_progress` | True | 0→1 (1) | 0 | 0 | 269.9 | True | True | idempotent_clear_stale_pending |
| `none` | True | 0→1 (1) | 0 | 0 | 291.3 | True | True | no_pending_use_committed |

## Cell `200k-seg64-i10-d2`

Segments=64, batch inserts/deletes=10/2, all_ok=True.

| Crash point | OK | Gen before→after (expect) | Replayed | Lost | Recovery ms | Multiset | Sym | Notes |
| ----------- | -- | ------------------------: | -------: | ---: | ----------: | -------- | --- | ----- |
| `before_mutation_persist` | True | 0→0 (0) | 0 | 0 | 37.6 | True | True | no_pending_retained_previous_committed |
| `after_persist_before_publish` | True | 0→1 (1) | 12 | 0 | 71.7 | True | True | replayed_pending_to_gen_1 |
| `during_snapshot_construction` | True | 0→1 (1) | 12 | 0 | 70.8 | True | True | replayed_pending_to_gen_1 |
| `during_or_after_publication` | True | 0→1 (1) | 12 | 0 | 69.0 | True | True | replayed_pending_to_gen_1 |
| `after_publish_before_replay_progress` | True | 0→1 (1) | 0 | 0 | 48.2 | True | True | idempotent_clear_stale_pending |
| `none` | True | 0→1 (1) | 0 | 0 | 50.1 | True | True | no_pending_use_committed |

## Cell `200k-seg64-i1000-d200`

Segments=64, batch inserts/deletes=1000/200, all_ok=True.

| Crash point | OK | Gen before→after (expect) | Replayed | Lost | Recovery ms | Multiset | Sym | Notes |
| ----------- | -- | ------------------------: | -------: | ---: | ----------: | -------- | --- | ----- |
| `before_mutation_persist` | True | 0→0 (0) | 0 | 0 | 47.2 | True | True | no_pending_retained_previous_committed |
| `after_persist_before_publish` | True | 0→1 (1) | 1200 | 0 | 103.4 | True | True | replayed_pending_to_gen_1 |
| `during_snapshot_construction` | True | 0→1 (1) | 1200 | 0 | 98.7 | True | True | replayed_pending_to_gen_1 |
| `during_or_after_publication` | True | 0→1 (1) | 1200 | 0 | 102.7 | True | True | replayed_pending_to_gen_1 |
| `after_publish_before_replay_progress` | True | 0→1 (1) | 0 | 0 | 47.3 | True | True | idempotent_clear_stale_pending |
| `none` | True | 0→1 (1) | 0 | 0 | 46.1 | True | True | no_pending_use_committed |

## Gate call

For each injected failure point, recovery must yield the expected committed generation and typed-edge multiset, keep CSR⇔CSC symmetry, and never serve an incomplete snapshot as committed.

| Failure point | Lab outcome (all 3 cells) |
| ------------- | ------------------------- |
| Before mutation persist | Retains gen 0; uncommitted batch not applied |
| After persist, before publish | Replays pending → gen 1; multiset matches oracle |
| During snapshot construction | Incomplete never committed; replay → gen 1 |
| During/after publication (inflight) | Committed marker not advanced until recovery replay |
| After publish, before replay-progress clear | Idempotent clear of stale pending; no double-apply |
| Happy path | Committed gen 1; no pending |

**Priority 3 lab ladder:** **PASSED** (3/3 cells, all crash points).

This validates the **bench durability model** (committed marker + pending batch + crash injection). It does **not** claim Motadata already implements this protocol in production.

Action 6 subsequent priorities closed: mutation envelope ([`action6-synthetic-mutation-envelope.md`](../design-v3/action6-synthetic-mutation-envelope.md)), 5M ladder ([Report 21a](./21-action6-5m-thin-ladder.md)), consolidated decision ([Report 21](./21-action6-milestone-b-close.md)).

## Links

- Spec: [`../design-v3/action6-mutation-lifecycle.md`](../design-v3/action6-mutation-lifecycle.md)
- Prior: [Report 19](./19-action6-atomic-publish.md)

