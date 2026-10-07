# Sample JSON — Motadata-aligned configuration-item nodes and topology edges

- **Status:** Normative samples for Pillar B PoC `graph_node.v1` / `graph_edge.v1` (Motadata table alignment).
- **Parent brief:** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)
- **Write/read keys:** [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md)
- **Lifecycle:** [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md)
- **Triplet gate:** [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md)

**Estate notes**

- These examples use one shared lab Dest tenant (`default`) and one small estate.
- **Tenant is not stored on node/edge rows** — it lives on `graph_snapshot.v1` and the Dest path `poc/out/<tenant>/map/`.
- Alert, Incident, ticket, Metric, LogPattern, Trace, and Change are **never** topology vertices.
- Ingest still uses PascalCase `ci_type` and snake_case `relation`; GraphWriter maps at the boundary to Motadata `type` / `edge_type`.
- Every Motadata `edge_type` below has one full `graph_edge.v1` body. Pairs are allowlist-legal; snowflake ids are illustrative PoC numbers.

---

## Shared field meaning (read once)

### Node (`graph_node.v1`)

| Field | Meaning |
|-------|---------|
| `entity_id` | Stable CI id within the Dest tenant (same string as ingest `ci_id` / sketch `entity_id` after bind) |
| `type` | Motadata lowercase CI type (`service`, `host`, `db`, …). Non-CI Motadata names are rejected |
| `name` | Human display name |
| `env` / `region` / `owner` / `namespace` | Closed promoted tags (`attr_catalog.v1`); nullable |
| `last_seen` | Unix epoch **milliseconds** UTC; refreshed on every upsert |
| `valid_from` / `valid_to` | Epoch ms UTC; `null` means open-ended |
| `version` | Monotonic integer per `entity_id` (latest-wins) |

Admit still requires ingest `identity.status == resolved`; that status is **not** persisted on the node.

### Edge (`graph_edge.v1`)

| Field | Meaning |
|-------|---------|
| `edge_id` | Snowflake UInt64 (JSON number). Stable across upserts of the same logical edge |
| `source_id` / `target_id` | Ends must both exist as CI vertices (`entity_id`) |
| `edge_type` | Motadata SCREAMING_SNAKE (`DEPENDS_ON`, `RUNS_ON`, …) — fifteen-name catalog |
| `evidence_event_id` | Snowflake UInt64 of the ingest/event row that proved this edge |
| `valid_from` / `valid_to` | Epoch ms UTC; when the relationship was believed true |

**Upsert identity**

- Key is `(source_id, edge_type, target_id)` — not the snowflake.
- GraphState reuses the same `edge_id` on refresh and updates `valid_from` / `evidence_event_id`.
- Same endpoints may hold **multiple** edges only when `edge_type` differs.
- `discovered_via` is **not** stored.
- PoC may keep optional `origin` / `telemetry_source` additionalProperties for E5 maintain only.
- Lifecycle (hot vs cold, two-level removal): [`MAP_HOT_COLD_LIFECYCLE.md`](./MAP_HOT_COLD_LIFECYCLE.md).

---

## 1) Sample nodes — durable CI roots

### 1.1 `business_service`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "bs-checkout",
  "type": "business_service",
  "name": "Customer checkout",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": "payments",
  "namespace": null
}
```

### 1.2 `service` (checkout API)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "checkout-api",
  "type": "service",
  "name": "checkout-api",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.3 `service` (inventory peer)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "inventory-api",
  "type": "service",
  "name": "inventory-api",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.4 `service` (IdP / auth)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "svc-idp-lab",
  "type": "service",
  "name": "lab-idp",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.5 `service` (monitor / collector)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "svc-otel-collector",
  "type": "service",
  "name": "otel-collector",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.6 `service` (backup job)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "svc-backup-agent",
  "type": "service",
  "name": "backup-agent",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.7 `customer`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "customer-acme-corp",
  "type": "customer",
  "name": "Acme Corp",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.8 `host` (app-01)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "linux-server-app-01",
  "type": "host",
  "name": "app-01",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.9 `host` (app-02 HA peer)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "linux-server-app-02",
  "type": "host",
  "name": "app-02",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.10 `queue`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "queue-orders-v1",
  "type": "queue",
  "name": "orders.v1",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.11 `db`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "db-checkout-primary",
  "type": "db",
  "name": "checkout-primary",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.12 `volume`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "vol-checkout-data",
  "type": "volume",
  "name": "checkout-data",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.13 `network`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "net-checkout-vlan",
  "type": "network",
  "name": "checkout-vlan",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.14 `endpoint`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "ep-checkout-public",
  "type": "endpoint",
  "name": "checkout.lab.example",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.15 `namespace`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "ns-checkout",
  "type": "namespace",
  "name": "checkout",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 1.16 `k8s_deployment`

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "deploy-checkout-api",
  "type": "k8s_deployment",
  "name": "checkout-api",
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": "checkout"
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
  "last_seen": 1787196600000,
  "valid_from": null,
  "valid_to": null,
  "version": 1,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": null
}
```

### 2.2 `pod` (temporary window)

```json
{
  "schema_version": "graph_node.v1",
  "entity_id": "pod-checkout-api-7f9c2",
  "type": "pod",
  "name": "checkout-api-7f9c2",
  "last_seen": "2026-08-20T06:40:00Z",
  "valid_from": "2026-08-20T02:10:00Z",
  "valid_to": "2026-08-20T06:40:00Z",
  "version": 3,
  "env": "rca-lab",
  "region": null,
  "owner": null,
  "namespace": "checkout"
}
```

---

## 3) Sample edges — all fifteen Motadata `edge_type` values

Snowflake ids below are illustrative PoC numbers. Upsert identity remains `(source_id, edge_type, target_id)`. Each sample uses an allowlist-legal `(source type, edge_type, target type)` pair from [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md).

| # | Ingest `relation` | Stored `edge_type` | Sample endpoints (types) |
|---|-------------------|--------------------|--------------------------|
| 3.1 | `depends_on` | `DEPENDS_ON` | `service` → `db` |
| 3.2 | `runs_on` | `RUNS_ON` | `process` → `host` |
| 3.3 | `mounts` | `MOUNTS` | `host` → `volume` |
| 3.4 | `connects_to` | `CONNECTS_TO` | `host` → `network` |
| 3.5 | `backs` | `BACKS` | `volume` → `db` |
| 3.6 | `uses` | `USES` | `service` → `queue` |
| 3.7 | `hosted_on` | `HOSTED_ON` | `service` → `host` |
| 3.8 | `member_of` | `MEMBER_OF` | `pod` → `namespace` |
| 3.9 | `part_of` | `PART_OF` | `service` → `business_service` |
| 3.10 | `routes_through` | `ROUTES_THROUGH` | `service` → `network` |
| 3.11 | `authenticates_via` | `AUTHENTICATES_VIA` | `service` → `service` |
| 3.12 | `monitored_by` | `MONITORED_BY` | `service` → `service` |
| 3.13 | `backed_up_by` | `BACKED_UP_BY` | `db` → `service` |
| 3.14 | `clustered_with` | `CLUSTERED_WITH` | `host` → `host` |
| 3.15 | `communicates_with` | `COMMUNICATES_WITH` | `service` → `service` |

Wave-1 writers historically started with five names. **Current GraphWriter admit:** all fifteen Motadata names may emit; illegal pairs DROP via the allowlist (no phased skip for “not wave-1 relation”).

### 3.1 `DEPENDS_ON` — declared functional need

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

### 3.2 `RUNS_ON` — guest executes on substrate

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000002,
  "source_id": "app-runtime-jvm",
  "target_id": "linux-server-app-01",
  "edge_type": "RUNS_ON",
  "valid_from": 1787184000000,
  "valid_to": null,
  "evidence_event_id": 7146828800000102
}
```

### 3.3 `MOUNTS` — mounts a volume / filesystem

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000003,
  "source_id": "linux-server-app-01",
  "target_id": "vol-checkout-data",
  "edge_type": "MOUNTS",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000103
}
```

### 3.4 `CONNECTS_TO` — L2/L3 / adjacency

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000004,
  "source_id": "linux-server-app-01",
  "target_id": "net-checkout-vlan",
  "edge_type": "CONNECTS_TO",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000104
}
```

### 3.5 `BACKS` — provides backing capacity

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000005,
  "source_id": "vol-checkout-data",
  "target_id": "db-checkout-primary",
  "edge_type": "BACKS",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000105
}
```

### 3.6 `USES` — soft dependency

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000006,
  "source_id": "checkout-api",
  "target_id": "queue-orders-v1",
  "edge_type": "USES",
  "valid_from": "2026-08-15T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000106
}
```

### 3.7 `HOSTED_ON` — guest / VM on host family

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000007,
  "source_id": "checkout-api",
  "target_id": "linux-server-app-01",
  "edge_type": "HOSTED_ON",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000107
}
```

### 3.8 `MEMBER_OF` — membership in a collection

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000008,
  "source_id": "pod-checkout-api-7f9c2",
  "target_id": "ns-checkout",
  "edge_type": "MEMBER_OF",
  "valid_from": "2026-08-20T02:10:00Z",
  "valid_to": "2026-08-20T06:40:00Z",
  "evidence_event_id": 7146828800000108
}
```

### 3.9 `PART_OF` — child → parent composition

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000009,
  "source_id": "checkout-api",
  "target_id": "bs-checkout",
  "edge_type": "PART_OF",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000109
}
```

### 3.10 `ROUTES_THROUGH` — path via middlebox / hop

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000010,
  "source_id": "checkout-api",
  "target_id": "net-checkout-vlan",
  "edge_type": "ROUTES_THROUGH",
  "valid_from": 1787196600000,
  "valid_to": null,
  "evidence_event_id": 7146828800000110
}
```

### 3.11 `AUTHENTICATES_VIA` — auth dependency

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000011,
  "source_id": "checkout-api",
  "target_id": "svc-idp-lab",
  "edge_type": "AUTHENTICATES_VIA",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000111
}
```

### 3.12 `MONITORED_BY` — observed by collector / monitor

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000012,
  "source_id": "checkout-api",
  "target_id": "svc-otel-collector",
  "edge_type": "MONITORED_BY",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000112
}
```

### 3.13 `BACKED_UP_BY` — backed up by sink / job

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000013,
  "source_id": "db-checkout-primary",
  "target_id": "svc-backup-agent",
  "edge_type": "BACKED_UP_BY",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000113
}
```

### 3.14 `CLUSTERED_WITH` — peer in same tier / HA set

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000014,
  "source_id": "linux-server-app-01",
  "target_id": "linux-server-app-02",
  "edge_type": "CLUSTERED_WITH",
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null,
  "evidence_event_id": 7146828800000114
}
```

### 3.15 `COMMUNICATES_WITH` — observed traffic

```json
{
  "schema_version": "graph_edge.v1",
  "edge_id": 7146828800000015,
  "source_id": "checkout-api",
  "target_id": "inventory-api",
  "edge_type": "COMMUNICATES_WITH",
  "valid_from": 1787196600000,
  "valid_to": null,
  "evidence_event_id": 7146828800000115
}
```

---

## 4) Mini snapshot (tenant on the envelope only)

Abbreviated body for publish shape. Full node/edge fields are the samples above. PoC publish also writes `nodes.jsonl` / `edges.jsonl` beside `graph_snapshot.json`.

```json
{
  "schema_version": "graph_snapshot.v1",
  "tenant": "default",
  "version": "1",
  "nodes": [
    {
      "entity_id": "bs-checkout",
      "type": "business_service"
    },
    {
      "entity_id": "checkout-api",
      "type": "service"
    },
    {
      "entity_id": "inventory-api",
      "type": "service"
    },
    {
      "entity_id": "svc-idp-lab",
      "type": "service"
    },
    {
      "entity_id": "svc-otel-collector",
      "type": "service"
    },
    {
      "entity_id": "svc-backup-agent",
      "type": "service"
    },
    {
      "entity_id": "customer-acme-corp",
      "type": "customer"
    },
    {
      "entity_id": "linux-server-app-01",
      "type": "host"
    },
    {
      "entity_id": "linux-server-app-02",
      "type": "host"
    },
    {
      "entity_id": "queue-orders-v1",
      "type": "queue"
    },
    {
      "entity_id": "db-checkout-primary",
      "type": "db"
    },
    {
      "entity_id": "vol-checkout-data",
      "type": "volume"
    },
    {
      "entity_id": "net-checkout-vlan",
      "type": "network"
    },
    {
      "entity_id": "ep-checkout-public",
      "type": "endpoint"
    },
    {
      "entity_id": "ns-checkout",
      "type": "namespace"
    },
    {
      "entity_id": "deploy-checkout-api",
      "type": "k8s_deployment"
    },
    {
      "entity_id": "app-runtime-jvm",
      "type": "process"
    },
    {
      "entity_id": "pod-checkout-api-7f9c2",
      "type": "pod"
    }
  ],
  "edges": [
    {
      "source_id": "checkout-api",
      "edge_type": "DEPENDS_ON",
      "target_id": "db-checkout-primary"
    },
    {
      "source_id": "app-runtime-jvm",
      "edge_type": "RUNS_ON",
      "target_id": "linux-server-app-01"
    },
    {
      "source_id": "linux-server-app-01",
      "edge_type": "MOUNTS",
      "target_id": "vol-checkout-data"
    },
    {
      "source_id": "linux-server-app-01",
      "edge_type": "CONNECTS_TO",
      "target_id": "net-checkout-vlan"
    },
    {
      "source_id": "vol-checkout-data",
      "edge_type": "BACKS",
      "target_id": "db-checkout-primary"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "USES",
      "target_id": "queue-orders-v1"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "HOSTED_ON",
      "target_id": "linux-server-app-01"
    },
    {
      "source_id": "pod-checkout-api-7f9c2",
      "edge_type": "MEMBER_OF",
      "target_id": "ns-checkout"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "PART_OF",
      "target_id": "bs-checkout"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "ROUTES_THROUGH",
      "target_id": "net-checkout-vlan"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "AUTHENTICATES_VIA",
      "target_id": "svc-idp-lab"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "MONITORED_BY",
      "target_id": "svc-otel-collector"
    },
    {
      "source_id": "db-checkout-primary",
      "edge_type": "BACKED_UP_BY",
      "target_id": "svc-backup-agent"
    },
    {
      "source_id": "linux-server-app-01",
      "edge_type": "CLUSTERED_WITH",
      "target_id": "linux-server-app-02"
    },
    {
      "source_id": "checkout-api",
      "edge_type": "COMMUNICATES_WITH",
      "target_id": "inventory-api"
    }
  ]
}
```

---

## 5) Explicit non-samples (never topology nodes)

Do not produce `graph_node.v1` for Motadata non-CI types: `alert`, `incident`, `itsm_ticket`, `red_metric`, `log_pattern`, `trace`, `change` — or ingest PascalCase `Alert`, `Incident`, `Change`, `Metric`, `Trace`, `LogPattern`, `ITSMTicket`.

---

*Schemas: [`schemas/graph_node_v1.schema.json`](./schemas/graph_node_v1.schema.json), [`schemas/graph_edge_v1.schema.json`](./schemas/graph_edge_v1.schema.json).*
