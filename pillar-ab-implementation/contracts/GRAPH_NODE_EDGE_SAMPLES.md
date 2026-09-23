# Sample JSON — Motadata-aligned configuration-item nodes and topology edges

**Status:** Normative samples for Pillar B PoC `graph_node.v1` / `graph_edge.v1` (Motadata table alignment).  
**Parent brief:** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)  
**Write/read keys:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md)

These examples use one shared lab Dest tenant (`default`) and one small estate. **Tenant is not stored on node/edge rows** — it lives on `graph_snapshot.v1` and the Dest path `poc/out/<tenant>/map/`. Alert, Incident, ticket, Metric, LogPattern, Trace, and Change are **never** topology vertices.

Ingest still uses PascalCase `ci_type` and snake_case `relation`; GraphWriter maps at the boundary to Motadata `type` / `edge_type`.

---

## Shared field meaning (read once)

### Node (`graph_node.v1`)

| Field | Meaning |
|-------|---------|
| `entity_id` | Stable CI id within the Dest tenant (same string as ingest `ci_id` / sketch `entity_id` after bind) |
| `type` | Motadata lowercase CI type (`service`, `host`, `db`, …). Non-CI Motadata names are rejected |
| `name` | Human display name |
| `metadata` | JSON object encoded as a **string** (tags, aliases, …) |
| `last_seen` | ISO-8601 timestamp refreshed on every upsert |
| `valid_from` / `valid_to` | Lifetime; `null` means open-ended |
| `version` | Monotonic integer per `entity_id` (latest-wins) |

Admit still requires ingest `identity.status == resolved`; that status is **not** persisted on the node.

### Edge (`graph_edge.v1`)

| Field | Meaning |
|-------|---------|
| `edge_id` | Snowflake UInt64 (JSON number). Stable across upserts of the same logical edge |
| `source_id` / `target_id` | Ends must both exist as CI vertices (`entity_id`) |
| `edge_type` | Motadata SCREAMING_SNAKE (`DEPENDS_ON`, `RUNS_ON`, …) — fifteen-name catalog |
| `evidence_event_id` | Snowflake UInt64 of the ingest/event row that proved this edge |
| `valid_from` / `valid_to` | When the relationship was true |

**Upsert identity** is `(source_id, edge_type, target_id)` — not the snowflake. GraphState reuses the same `edge_id` on refresh and updates `valid_from` / `evidence_event_id`.

`discovered_via` is **not** stored. PoC may keep optional `origin` / `telemetry_source` additionalProperties for E5 maintain only.

---

## 1) Sample nodes — durable CI roots

### 1.1 `business_service`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "bs-checkout",
  "type": "business_service",
  "name": "Customer checkout",
  "metadata": "{\"aliases\":[\"checkout-journey\"],\"env\":\"rca-lab\",\"owner\":\"payments\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 1.2 `service`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "checkout-api",
  "type": "service",
  "name": "checkout-api",
  "metadata": "{\"aliases\":[\"svc:checkout-api\"],\"env\":\"rca-lab\",\"version\":\"1.4.2\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 1.3 `customer`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "customer-acme-corp",
  "type": "customer",
  "name": "Acme Corp",
  "metadata": "{\"aliases\":[\"acct:acme\"],\"segment\":\"enterprise\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 1.4 `host`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "linux-server-app-01",
  "type": "host",
  "name": "app-01",
  "metadata": "{\"aliases\":[\"app-01.lab.local\"],\"env\":\"rca-lab\",\"role\":\"app\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 1.5 `queue`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "queue-orders-v1",
  "type": "queue",
  "name": "orders.v1",
  "metadata": "{\"aliases\":[\"kafka:orders.v1\"],\"broker\":\"kafka-lab-01\",\"env\":\"rca-lab\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 1.6 `db`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "db-checkout-primary",
  "type": "db",
  "name": "checkout-primary",
  "metadata": "{\"aliases\":[\"postgres://checkout-db:5432/checkout\"],\"engine\":\"postgres\",\"env\":\"rca-lab\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

Ingest still says `Database` / `BusinessService` / `Runtime`; storage maps to `db` / `business_service` / `process`.

---

## 2) Sample nodes — process / ephemeral CI

### 2.1 `process` (ingest `Runtime`)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "app-runtime-jvm",
  "type": "process",
  "name": "checkout-api JVM",
  "metadata": "{\"env\":\"rca-lab\",\"java_version\":\"17\",\"scope_parent\":\"checkout-api\"}",
  "last_seen": "2026-08-20T03:30:00Z",
  "valid_from": null,
  "valid_to": null,
  "version": 1
}
```

### 2.2 `pod` (temporary window)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "pod-checkout-api-7f9c2",
  "type": "pod",
  "name": "checkout-api-7f9c2",
  "metadata": "{\"env\":\"rca-lab\",\"namespace\":\"checkout\",\"scope_parent\":\"checkout-api\"}",
  "last_seen": "2026-08-20T06:40:00Z",
  "valid_from": "2026-08-20T02:10:00Z",
  "valid_to": "2026-08-20T06:40:00Z",
  "version": 3
}
```

---

## 3) Sample edges — Motadata `edge_type`

Snowflake ids below are illustrative PoC numbers. Upsert identity remains `(source_id, edge_type, target_id)`.

### 3.1 `DEPENDS_ON`

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000001,
  "source_id": "checkout-api",
  "target_id": "db-checkout-primary",
  "edge_type": "DEPENDS_ON",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000101
}
```

### 3.2 `RUNS_ON`

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000002,
  "source_id": "app-runtime-jvm",
  "target_id": "linux-server-app-01",
  "edge_type": "RUNS_ON",
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000102
}
```

### 3.3 `PART_OF`

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000003,
  "source_id": "checkout-api",
  "target_id": "bs-checkout",
  "edge_type": "PART_OF",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000103
}
```

### 3.4 `COMMUNICATES_WITH`

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000004,
  "source_id": "checkout-api",
  "target_id": "payments-db",
  "edge_type": "COMMUNICATES_WITH",
  "valid_from": "2026-08-20T03:30:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000104
}
```

### 3.5 Full fifteen Motadata names

| Ingest `relation` | Stored `edge_type` |
|-------------------|--------------------|
| `depends_on` | `DEPENDS_ON` |
| `runs_on` | `RUNS_ON` |
| `mounts` | `MOUNTS` |
| `connects_to` | `CONNECTS_TO` |
| `backs` | `BACKS` |
| `uses` | `USES` |
| `hosted_on` | `HOSTED_ON` |
| `member_of` | `MEMBER_OF` |
| `part_of` | `PART_OF` |
| `routes_through` | `ROUTES_THROUGH` |
| `authenticates_via` | `AUTHENTICATES_VIA` |
| `monitored_by` | `MONITORED_BY` |
| `backed_up_by` | `BACKED_UP_BY` |
| `clustered_with` | `CLUSTERED_WITH` |
| `communicates_with` | `COMMUNICATES_WITH` |

Wave-1 writers may emit only `RUNS_ON`, `HOSTED_ON`, `DEPENDS_ON`, `COMMUNICATES_WITH`, `PART_OF`; other catalog names are phased skip (map unchanged, not DROP).

---

## 4) Mini snapshot (tenant on the envelope only)

```json
{
  "schema_version": "graph_snapshot.v1",
  "tenant": "default",
  "version": "1",
  "nodes": [
    { "entity_id": "bs-checkout", "type": "business_service" },
    { "entity_id": "checkout-api", "type": "service" },
    { "entity_id": "linux-server-app-01", "type": "host" },
    { "entity_id": "db-checkout-primary", "type": "db" },
    { "entity_id": "app-runtime-jvm", "type": "process" }
  ],
  "edges": [
    { "source_id": "checkout-api", "edge_type": "PART_OF", "target_id": "bs-checkout" },
    { "source_id": "app-runtime-jvm", "edge_type": "RUNS_ON", "target_id": "linux-server-app-01" },
    { "source_id": "checkout-api", "edge_type": "DEPENDS_ON", "target_id": "db-checkout-primary" }
  ]
}
```

Full bodies are the samples above. PoC publish also writes `nodes.jsonl` / `edges.jsonl` beside `graph_snapshot.json`.

---

## 5) Explicit non-samples (never topology nodes)

Do not produce `graph_node.v1` for Motadata non-CI types: `alert`, `incident`, `itsm_ticket`, `red_metric`, `log_pattern`, `trace`, `change` — or ingest PascalCase `Alert`, `Incident`, `Change`, `Metric`, `Trace`, `LogPattern`, `ITSMTicket`.

---

*Schemas: [`schemas/graph_node_v1.schema.json`](./schemas/graph_node_v1.schema.json), [`schemas/graph_edge_v1.schema.json`](./schemas/graph_edge_v1.schema.json).*
