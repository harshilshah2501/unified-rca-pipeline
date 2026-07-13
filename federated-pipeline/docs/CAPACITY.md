# Capacity Planning

**Motadata note:** Lean is primary for ObserveOps ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). Capacity work here is for the **federated** speed/structural tier vision (Phase C/E deferred). Motadata critical path does **not** block on 1B EPS. Overview: [`ARCHITECTURE.md`](./ARCHITECTURE.md) · limits: [`LIMITATIONS_AND_FUTURE.md`](./LIMITATIONS_AND_FUTURE.md).

Two scopes: **PoC** (local Dragonfly/Redis probes) and **production vision** (1B EPS design anchor). PoC sizing is independent and should not be driven by the 1B number.

---

## PoC sizing

| Resource | Target | Rationale |
|----------|--------|-----------|
| Event rate | ~100K EPS sustained | Enough to stress Dragonfly Lua path without hyperscaler infra |
| Services | 10–50 microservices | TrainTicket / Online Boutique scale |
| Dragonfly | 1–3 nodes | Single-node benchmark first, then small cluster |
| Structural tier | 1 high-memory node | CSR graph + DashMap in-process; ~2M edges fits in GB |
| Orchestrator | 1 instance (Python PoC; Rust vision) | Incident rate << event rate |
| Network | < 1 Gbps aggregate | Non-issue at PoC scale |

### PoC memory estimate (speed tier)

```
100K EPS × 200 bytes/event × 300s (5-min window) ≈ 6 GB total
```

Trivial on a single Dragonfly node. Memory is not the PoC constraint — **Lua script throughput per node** is.

### PoC success criterion for capacity

Before scaling math, run a **single-node Dragonfly benchmark**:

1. Synthetic load generator emitting Nezha-shaped events.
2. Lua script performing pattern hash → ZSET/HSET write + score update.
3. Measure sustained EPS until p99 latency exceeds threshold.

Record the result here once measured (laptop floor already filled below):

| Metric | Value | Date |
|--------|-------|------|
| Single-node sustained EPS (Lua path) | **~21K Dragonfly / ~20K Redis** on 2-core WSL | 2026-07-13 |
| p99 write latency at sustained load | **~0.35 ms** (Dragonfly best) | 2026-07-13 |
| Hardware spec | WSL2 · 2 CPUs · 7.8 GiB — not server-class | 2026-07-13 |

---

## Production vision — 1B EPS

At 1B EPS sustained, this is hyperscaler internal-observability territory (Google Monarch, Meta Scuba, CDN edge telemetry) — not a typical enterprise deployment.

> **Naming:** These are **storage tiers** (data-plane role), not pipeline steps. Speed tier = Tier 1 below; Structural tier = Tier 2 below. Pipeline execution order (Panorama → Murphy → Nezha) is independent — see [STORAGE_TIERS.md](./STORAGE_TIERS.md) and [ARCHITECTURE.md](./ARCHITECTURE.md).

### Tier comparison (production vision)

| Metric | Tier 1 — Event Graph (Dragonfly / Nezha) | Tier 2 — Knowledge Graph (Vortex / DashMap · Panorama + Murphy) |
|--------|------------------------------------------|-------------------------------------------------------------------|
| **Scaling driver** | Ingress rate (events/sec) | Entity count + concurrent incident load |
| **Target throughput** | 1B events/sec (aggregate) | ~10M property updates/sec (aggregate, at 100/sec/entity × 100K entities) |
| **Per-node ceiling** (Phase 0) | Design: 200K–800K on 64+ core; **measured: ~21K Dragonfly / ~20K Redis on 2-core WSL** | N/A — driven by graph size, not per-node throughput |
| **Node count** | **1,250–5,000 nodes** | Tens to low hundreds |
| **CPU profile** | Continuous saturation (Lua scoring on every event) | Near-idle; bursts only during Gibbs sampling / CSR traversal per incident |
| **Event / record size** | ~200 bytes/event (assumption — needs validation) | N/A (graph edges + metric time series) |
| **Storage — hot data** | ~60 TB total across fleet (5-min rolling window @ 1B/sec × 200B) | Few GB (100K-entity graph, ~20 avg degree ≈ 2M edges) |
| **Storage per node** | 12–48 GB/node | Fits on a single high-memory node |
| **Retention model** | TTL-bound rolling window (5–15 min), not cumulative | Persistent (topology), continuously updated (metrics) |
| **Network — aggregate ingress** | ~1.6 Tbps | Low steady chatter; read-heavy bursts during blast-radius queries |
| **Network — per node** | 300 Mbps–1.3 Gbps/node | Not a bottleneck |
| **Query-time burst** | 256 concurrent Lua `EVALSHA` calls (hop 5) | Gibbs sampling convergence + CSR BFS traversal (hops 1–3) |
| **Hardware profile** | CPU-optimized, horizontally flat | Memory-optimized, few large nodes |
| **Deployment scale class** | Hyperscaler-internal-telemetry-tier | Standard microservice-scale backend |

**Caveats:**

- The per-node ceiling (200K–800K events/sec) is an **estimate**, not a measurement. Phase 0's benchmark replaces it with a real number; the node-count row is a linear derivative of that single figure.
- The 100K-entity assumption for Tier 2 is **illustrative** — swap in actual expected topology size when known.
- Event size (~200 bytes) must be validated against the Rust normalizer encoding.

### Phase 0 benchmark (replaces estimates)

Harness: `poc/benchmarks/phase0_dragonfly.py` — Lua `EVALSHA` doing ZADD + HSET (Nezha pattern write/score).

#### Measured on this host (2026-07-13)

Hardware: WSL2 · **2 CPUs** (i7-1185G7) · 7.8 GiB RAM — not server-class.

| Backend | Threads | Workers | Pipeline | EPS | p99 | Artifact |
|---------|---------|---------|----------|-----|-----|----------|
| **Dragonfly df-v1.25.1** (host net) | **2** | 4 | 128 | **20,979** | 0.348 ms | user re-run 2026-07-13 |
| Redis 7.0.15 | 1 (single-threaded) | 4 | 64 | 19,977 | 0.618 ms | `phase0_redis_w4.json` |
| Redis 7.0.15 | 1 | 1 | 64 | 13,764 | 0.363 ms | `phase0_redis_w1.json` |
| Dragonfly df-v1.25.1 (host net) | 2 | 4 | 128 | 13,856 | 0.716 ms | `phase0_dragonfly_hostnet_w4.json` (earlier) |
| Dragonfly df-v1.25.1 (bridge) | 2 | 4 | 64 | 8,333 | 1.227 ms | `phase0_dragonfly_w4.json` |
| Dragonfly df-v1.25.1 (bridge) | 2 | 2 | 64 | 6,165 | 1.072 ms | `phase0_dragonfly_w2.json` |
| Dragonfly df-v1.25.1 (bridge) | 2 | 1 | 64 | 4,369 | 0.582 ms | `phase0_dragonfly_w1.json` |

| Metric | Design estimate | Best measured (this host) |
|--------|-----------------|---------------------------|
| Single-node Lua EPS | 200K–800K on 64+ core Dragonfly | **~21K Dragonfly / ~20K Redis** on 2-core WSL |
| p99 write latency | — | **0.35 ms** (Dragonfly best) |
| Hardware | 64+ core server | 2 CPU WSL2 laptop |

**Interpretation:**

1. **Dragonfly multi-core works here** — EPS scales from ~4.4K (1 worker) to ~21K (4 workers, host-net, pipeline 128) on 2 proactor threads.
2. **Host networking + larger pipelines matter** — bridge/64-pipe left a lot on the table vs host-net/128-pipe.
3. **On 2 cores, Dragonfly now matches or beats Redis** on this Lua path (~21K vs ~20K), with better p99 (0.35 vs 0.62 ms).
4. **Do not** size a 1B EPS fleet from these numbers (`1B/21K ≈ 48K nodes` would be nonsense). Keep the **1,250–5,000** design range until a **64-core bare-metal/VM Dragonfly** run exists.
5. Use ~21K as the validated **2-core Dragonfly floor** for local PoC work.

**How to reproduce:**

```bash
# Dragonfly (2 threads, host network)
docker run -d --name poc-dragonfly --network host \
  docker.dragonflydb.io/dragonflydb/dragonfly:v1.25.1 \
  --proactor_threads=2 --port=6380

cd federated-pipeline
PYTHONPATH=..:. python -m poc.benchmarks.phase0_dragonfly \
  --port 6380 --workers 4 --pipeline-size 128 --seconds 20 \
  --output ../benchmarking/capacity/phase0_dragonfly_hostnet_w4.json
```

**Shard count (derived):**

```
1B EPS ÷ E_node = nodes_required
# Design estimate (200K–800K on server-class Dragonfly): 1,250 to 5,000 nodes
# 2-core WSL measurements: not used for production sizing
```

**Memory (not the constraint at 1B EPS):**

```
1B/sec × 200B × 300s ≈ 60 TB total ÷ nodes_required = per_node_mem
# At estimate range: 12–48 GB/node
```

**Bottom line:** Tier 1 dominates infrastructure footprint by orders of magnitude. Tier 2 is comparatively tiny and should be sized independently around graph size + concurrent incident load.

---

## Scaling formula

Once single-node EPS is measured (`E_node`):

```
nodes_required = target_EPS / E_node
total_memory   = target_EPS × event_bytes × hot_window_seconds
per_node_mem   = total_memory / nodes_required
per_node_net   = (target_EPS × event_bytes × 8) / nodes_required
```

Fill in `E_node` from the Phase 0 benchmark before using this for production planning.

---

## Next step

1. Re-run on a **64+ core** machine (bare metal or large VM), Dragonfly `--proactor_threads` = CPU count, `--network host`, workers ≥ thread count:
   ```bash
   docker run -d --name poc-dragonfly --network host \
     docker.dragonflydb.io/dragonflydb/dragonfly:v1.25.1 \
     --proactor_threads=$(nproc) --port=6379
   PYTHONPATH=..:. python -m poc.benchmarks.phase0_dragonfly \
     --workers $(nproc) --pipeline-size 128 --seconds 30 \
     --output phase0_dragonfly_server.json
   ```
2. Only then replace the 200K–800K design estimate and recompute `1B / E_node`.
3. Optional: compare non-Lua pipelined `ZADD`+`HINCRBY` vs EVALSHA to see how much Lua costs on Dragonfly.
