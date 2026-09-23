# Interleaved `fact_kind` scenario — customer checkout

**Purpose:** One worked production-intent story where many `ingest.v1` lines of different **fact kinds** arrive on the **same post-Identity stream**. Writers filter; GraphWriter never turns a span or metric into an edge in place.

**Audience:** Teammates reviewing Pillar A ∥ B fan-out and how topology is captured when telemetry *suggests* relationships.

**Estate:** Motadata-shaped “customer checkout” (`checkout-api`, `app-runtime-jvm`, `linux-server-app-01`, `payments-db`, `bs-checkout`). Lab topo-only tape: [`../poc/sample_estate/customer_checkout/stream.resolved.jsonl`](../poc/sample_estate/customer_checkout/stream.resolved.jsonl). Shape samples: [`../poc/sample_estate/customer_checkout/expected/ingest.example.json`](../poc/sample_estate/customer_checkout/expected/ingest.example.json).

**Companions:** [`TEAM_WALKTHROUGH.md`](./TEAM_WALKTHROUGH.md) §3–5 · [`fact-kind-fanout.svg`](./fact-kind-fanout.svg) · **[Stream → graph demo](../../../docs/fabric/pillar-b-stream-graph-demo.html)** ([`:8765`](http://127.0.0.1:8765/pillar-b-stream-graph-demo.html)) · [`PILLAR_B_POC_CHAT_QNA.md`](./PILLAR_B_POC_CHAT_QNA.md) §9–10 · [`../../E2_INPUT_FIXTURES.md`](../../E2_INPUT_FIXTURES.md).

---

## 1. Rules this scenario teaches

1. **Optional estate bootstrap before the stream.** Lab CMDB stand-in: `GraphWriter.load_estate_bootstrap`. In the [stream → graph demo](../../../docs/fabric/pillar-b-stream-graph-demo.html), step **B0** loads **CI nodes only** so the map can grow **one edge per** later `topo_update` WRITE (in sync with Forward). The full lab file [`../poc/sample_estate/customer_checkout/topology.bootstrap.json`](../poc/sample_estate/customer_checkout/topology.bootstrap.json) may also carry declared edges — that is optional product bootstrap, not required for the teaching demo. Bootstrap is **not** CaseSeed and **not** an `ingest.v1` line.
2. **One wire after E2.** Every stream line is still `ingest.v1` with `fact_kind` + `identity`.  
3. **Writers filter; they do not reclassify.** Collect/adapters stamp `fact_kind`.  
4. **SketchWriter** admits `metric_sample` only (in this PoC).  
5. **GraphWriter** admits `topo_update` only — then NOOP / WRITE / DROP / phased skip. Each stream WRITE **adds or upserts** one named `relation` edge on `map/`.  
6. A WRITE always names **`relation` + `src_ci_id` → `dst_ci_id`**, not bare “edge A → B”.  
7. Spans / events / anomalies may **suggest** topology; an **upstream emitter** must publish a **separate** `topo_update` line. GraphWriter does not invent that line.

---

## 2. Wave-1 relations used here

| `relation` | Plain meaning | In this story |
|------------|---------------|---------------|
| `runs_on` | A **executes on** B | JVM and API on the Linux host |
| `part_of` | A is a **child / component** of parent B | API belongs under business service `bs-checkout` |
| `depends_on` | A **needs** B to function | Catalog: checkout needs `payments-db` |
| `communicates_with` | A **calls / talks to** B | APM saw traffic to `payments-db` (can coexist with `depends_on`) |

Lab wave-1 also includes `hosted_on` (not used in this tape). Full fifteen-name catalog: [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../../contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) §4.2.

---

## 3. Story timeline (at a glance)

**Before the incident window:** estate bootstrap places known **CI nodes** on the map (demo step **B0**). Edges arrive afterward, one per stream `topo_update` WRITE.

Checkout starts to degrade around `03:30`. Inventory, catalog, and APM publish topology lines; Detect fires a latency anomaly. Everything after B0 shares one stream — Forward in the demo grows `map/` in lockstep.

```text
(pre)     estate bootstrap  CI nodes only                              load_estate_bootstrap (demo)
03:29:50  topo_update       runs_on            JVM → host              WRITE · +edge authoritative
03:30:00  metric_sample     latency 92ms                               SketchWriter admit · GraphWriter NOOP
03:30:05  metric_sample     error_rate                                 SketchWriter admit · GraphWriter NOOP
03:30:08  topo_update       part_of            api → bs-checkout       WRITE · +edge declared
03:30:08  topo_update       depends_on         api → payments-db       WRITE · +edge declared
03:30:10  trace_span        POST /checkout     peer=payments-db        A/B NOOP (emitter may watch)
03:30:11  event             log.error                                  A/B NOOP
03:30:12  metric_sample     latency 980ms                              SketchWriter admit · GraphWriter NOOP
03:30:15  anomaly           latency high                               Detect · A/B NOOP
03:30:20  topo_update       communicates_with  api → payments-db       WRITE · +edge corroborating
03:30:22  topo_update       runs_on            api → host              WRITE · +edge corroborating
```

### Admit outcomes for every topology line

| Time | SketchWriter | GraphWriter |
|------|--------------|-------------|
| (pre) | **NOOP** | **BOOTSTRAP** CI nodes only (demo; not a wire line) |
| 03:29:50 | **NOOP** | **WRITE** `runs_on`: `app-runtime-jvm` → `linux-server-app-01` (inventory → authoritative) |
| 03:30:08 | **NOOP** | **WRITE** `part_of`: `checkout-api` → `bs-checkout` (catalog) |
| 03:30:08 | **NOOP** | **WRITE** `depends_on`: `checkout-api` → `payments-db` (catalog) |
| 03:30:20 | **NOOP** | **WRITE** `communicates_with`: `checkout-api` → `payments-db` (APM → corroborating) |
| 03:30:22 | **NOOP** | **WRITE** `runs_on`: `checkout-api` → `linux-server-app-01` (look-up → corroborating) |

---

## 4. Sample JSON — each step

Comments with `_note` are narrative only (not required on the wire).

### T0 — Inventory places the JVM on the host (`topo_update`)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:29:50Z",
  "tenant": "default",
  "ci_id": "app-runtime-jvm",
  "ci_type": "Runtime",
  "fact_kind": "topo_update",
  "relation": "runs_on",
  "src_ci_id": "app-runtime-jvm",
  "dst_ci_id": "linux-server-app-01",
  "identity": { "status": "resolved", "bind_source": "inventory" },
  "_note": "SketchWriter NOOP. GraphWriter WRITE runs_on (authoritative hosting)."
}
```

### T1 — Steady metrics (not topology)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:00Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 92.1,
  "labels": { "source": "lab-node", "trace_id": "abc123" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "SketchWriter admits → history/. GraphWriter NOOP."
}
```

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:05Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.error_rate",
  "value": 0.02,
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "SketchWriter admits. GraphWriter NOOP."
}
```

### T2 — Catalog declares composition and dependency (`topo_update`)

`part_of` = child of business service. `depends_on` = functional need. Two different edges.

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:08Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "part_of",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "bs-checkout",
  "identity": { "status": "resolved", "bind_source": "service-catalog" },
  "_note": "SketchWriter NOOP. GraphWriter WRITE part_of (declared composition)."
}
```

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:08Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "depends_on",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": { "status": "resolved", "bind_source": "service-catalog" },
  "_note": "SketchWriter NOOP. GraphWriter WRITE depends_on (declared need)."
}
```

### T3 — APM span shows a peer (still not an edge)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:10Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "trace_span",
  "name": "POST /checkout",
  "value": 210.0,
  "labels": {
    "route": "POST /checkout",
    "trace_id": "abc123",
    "span_id": "span-7",
    "peer.service": "payments-db"
  },
  "identity": { "status": "resolved", "bind_source": "apm" },
  "_note": "Pillar A/B NOOP. peer.service may feed a future topo_update emitter — not GraphWriter."
}
```

### T4 — Error log + slow metric (interleaved)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:11Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "event",
  "name": "log.error",
  "value": 1.0,
  "labels": {
    "level": "error",
    "msg": "payment gateway timeout",
    "downstream": "payments-db"
  },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "Logs are fact_kind event. A/B NOOP. Labels do not become edges inside GraphWriter."
}
```

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:12Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "metric_sample",
  "name": "request.latency_ms",
  "value": 980.0,
  "labels": { "trace_id": "abc123" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "SketchWriter admits. GraphWriter NOOP."
}
```

### T5 — Detect publishes an anomaly (not a map write)

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:15Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "anomaly",
  "name": "request.latency_ms",
  "value": 980.0,
  "threshold": 500.0,
  "severity": "high",
  "labels": { "layer": "app" },
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "Detect / Curate. Pillar A/B NOOP. Later stages may read map/; they do not write it here."
}
```

### T6 — Edge emitter closes the loop (span peers → separate `topo_update`)

After enough spans with `peer.service=payments-db`, an **APM service-map adapter** (upstream of GraphWriter) emits:

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:20Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "communicates_with",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "payments-db",
  "identity": { "status": "resolved", "bind_source": "apm" },
  "_note": "SketchWriter NOOP. GraphWriter WRITE communicates_with (corroborating traffic). Catalog depends_on may already exist."
}
```

That is how “span caused topology” shows up: **same stream, new line, new `fact_kind`**, not a mutation of the span row. This PoC does **not** implement the emitter; Case A’s `stream.resolved.jsonl` already includes an equivalent `communicates_with` line as the lab stand-in.

### T7 — Host placement for the service

```json
{
  "schema_version": "ingest.v1",
  "ts": "2026-08-20T03:30:22Z",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "fact_kind": "topo_update",
  "relation": "runs_on",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "linux-server-app-01",
  "identity": { "status": "resolved", "bind_source": "topology_lookup" },
  "_note": "SketchWriter NOOP. GraphWriter WRITE runs_on."
}
```

---

## 5. What lands on `map/` after the topo lines

If only the `topo_update` lines above are admitted (wave-1 + resolved), GraphWriter’s in-memory estate then `publish_map` can include edges such as:

| `relation` | Source → destination | Typical evidence feel |
|------------|----------------------|------------------------|
| `runs_on` | `app-runtime-jvm` → `linux-server-app-01` | Inventory / authoritative |
| `runs_on` | `checkout-api` → `linux-server-app-01` | Topology look-up |
| `part_of` | `checkout-api` → `bs-checkout` | Catalog / declared |
| `depends_on` | `checkout-api` → `payments-db` | Catalog / declared |
| `communicates_with` | `checkout-api` → `payments-db` | APM / corroborating |

Metrics, events, spans, and anomalies **do not** appear as edges. They join later investigations by shared `tenant` + `ci_id` (and time).

Case A lab spine (five topo lines, same estate): [`SAMPLE_IO.md`](../poc/sample_estate/customer_checkout/SAMPLE_IO.md).

---

## 6. Lab vs production

| | Production | This scenario / PoC |
|--|------------|---------------------|
| Carrier | Continuous post-E2 `ingest.v1` feed (bus TBD — NATS optional) | Narrative JSON above; topo subset also in `stream.resolved.jsonl` |
| Mixed kinds | Interleaved on one stream | Same — writers filter |
| Span → edge | Upstream APM / inventory / catalog emitters | Simulated as an explicit `topo_update` at T6; emitter **not** coded in Pillar B |
| Bus brand | Not locked | Files / docs only |

---

## Document history

| When | What |
|------|------|
| 2026-09-22 | Standalone interleaved scenario with relation-named WRITEs, SketchWriter NOOP on every topo line, and full sample JSON |
