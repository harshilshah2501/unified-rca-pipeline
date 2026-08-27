# Sample JSON — qualified configuration-item nodes and topology edges

**Status:** Discussion samples for the sit-down (logical `graph_node.v1` / `graph_edge.v1`). Not Signed.  
**Parent brief:** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md)  
**What counts as a configuration item:** [`GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](./GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) §2

These examples use one shared lab tenant (`default`) and one small estate so you can read any sample in isolation and still see how identities join. Every node that may appear in a `GraphSnapshot` has `identity_status: "resolved"`. Facts and events (Change, Alert, Incident, ticket, Metric, LogPattern, Trace) have **no** node samples here — they are never topology vertices.

---

## Shared field meaning (read once)

### Node (`graph_node.v1`)

| Field | Meaning |
|-------|---------|
| `tenant` | Namespace for all joins |
| `ci_id` | Stable identity within the tenant (same string as sketch `entity_id` after identity bind) |
| `ci_type` | Closed enum value for this kind of configuration item |
| `ci_name` | Human display name |
| `identity_status` | Must be `resolved` to write into the topology snapshot |
| `tier` | Stack layer for localization descent (names can be tenant-shaped; the idea is required) |
| `instance_scope` | `single` or `multi-instance` |
| `scope_parent` | Required when the item is multi-instance or ephemeral under a parent |
| `monitored_via` | How this item is observed |
| `aliases` | Other strings that bind to the same `ci_id` |
| `labels` | Free key/value context (environment, version, …) |
| `valid_from` / `valid_to` | Lifetime; required when the item is ephemeral |

### Edge (`graph_edge.v1`)

| Field | Meaning |
|-------|---------|
| `edge_id` | Stable id for this directed fact within the tenant |
| `src_ci_id` / `dst_ci_id` | Ends must both exist as resolved configuration items |
| `relation` | One of the fifteen locked relation names |
| `discovered_via` | Provenance: how we learned the edge and how strong the evidence is |
| `valid_from` / `valid_to` | When the relationship was true |

---

## 1) Sample nodes — clearly qualifies (durable ticket roots)

### 1.1 `BusinessService`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "bs-checkout",
  "ci_type": "BusinessService",
  "ci_name": "Customer checkout",
  "ci_class": "business",
  "tier": "business_service",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["synthetic", "apm"],
  "aliases": ["checkout-journey"],
  "labels": { "env": "rca-lab", "owner": "payments" },
  "valid_from": null,
  "valid_to": null
}
```

### 1.2 `Service` (technical)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "checkout-api",
  "ci_type": "Service",
  "ci_name": "checkout-api",
  "ci_class": "application",
  "tier": "technical_service",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["agent", "apm"],
  "aliases": ["svc:checkout-api", "DD_SERVICE:checkout-api"],
  "labels": { "env": "rca-lab", "version": "1.4.2" },
  "valid_from": null,
  "valid_to": null
}
```

### 1.3 `Customer` (tenant / account as a configuration item)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "customer-acme-corp",
  "ci_type": "Customer",
  "ci_name": "Acme Corp",
  "ci_class": "business",
  "tier": "business_service",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["crm"],
  "aliases": ["acct:acme"],
  "labels": { "segment": "enterprise" },
  "valid_from": null,
  "valid_to": null
}
```

### 1.4 `Host`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "linux-server-app-01",
  "ci_type": "Host",
  "ci_name": "app-01",
  "ci_class": "compute",
  "tier": "os",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["agent"],
  "aliases": ["app-01.lab.local", "host.id:a1b2c3"],
  "labels": { "env": "rca-lab", "role": "app" },
  "valid_from": null,
  "valid_to": null
}
```

### 1.5 `Queue` (only as a **named** broker destination)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "queue-orders-v1",
  "ci_type": "Queue",
  "ci_name": "orders.v1",
  "ci_class": "messaging",
  "tier": "middleware",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["broker-api"],
  "aliases": ["kafka:orders.v1"],
  "labels": { "env": "rca-lab", "broker": "kafka-lab-01" },
  "valid_from": null,
  "valid_to": null
}
```

### 1.6 `Database` — qualifies **only when** the instance or cluster is named

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "db-checkout-primary",
  "ci_type": "Database",
  "ci_name": "checkout-primary",
  "ci_class": "data",
  "tier": "data",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["agent", "db-exporter"],
  "aliases": ["postgres://checkout-db:5432/checkout"],
  "labels": { "env": "rca-lab", "engine": "postgres", "role": "primary" },
  "valid_from": null,
  "valid_to": null
}
```

Until the instance or cluster identity is chosen, do **not** emit a `Database` node — leave it in the “not decided yet” bucket.

---

## 2) Sample nodes — other durable types from the locked catalog

These appear in the operational-graph / ObserveOps catalog and pass the durable-identity test when the identity is named.

### 2.1 `Runtime` (for example a named JVM runtime under a service)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "app-runtime-jvm",
  "ci_type": "Runtime",
  "ci_name": "checkout-api JVM",
  "ci_class": "runtime",
  "tier": "runtime",
  "instance_scope": "multi-instance",
  "scope_parent": "checkout-api",
  "identity_status": "resolved",
  "monitored_via": ["agent"],
  "aliases": ["jmx:checkout-api"],
  "labels": { "env": "rca-lab", "java_version": "17" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.2 `Middleware` (for example named nginx)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "mw-nginx-edge",
  "ci_type": "Middleware",
  "ci_name": "nginx-edge",
  "ci_class": "middleware",
  "tier": "middleware",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["agent"],
  "aliases": ["nginx:edge"],
  "labels": { "env": "rca-lab" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.3 `Datastore`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "ds-san-lun-checkout",
  "ci_type": "Datastore",
  "ci_name": "checkout-lun",
  "ci_class": "storage",
  "tier": "storage",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["vcenter", "agent"],
  "aliases": ["lun:checkout-01"],
  "labels": { "env": "rca-lab" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.4 `GuestOS`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "guestos-app-01",
  "ci_type": "GuestOS",
  "ci_name": "app-01 guest OS",
  "ci_class": "compute",
  "tier": "os",
  "instance_scope": "single",
  "scope_parent": "vm-app-01",
  "identity_status": "resolved",
  "monitored_via": ["agent"],
  "aliases": [],
  "labels": { "env": "rca-lab", "os": "linux" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.5 `VirtualMachine`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "vm-app-01",
  "ci_type": "VirtualMachine",
  "ci_name": "vm-app-01",
  "ci_class": "compute",
  "tier": "virtualization",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["vcenter"],
  "aliases": ["vmware:vm-app-01"],
  "labels": { "env": "rca-lab" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.6 `HypervisorHost`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "esxi-rack-a-03",
  "ci_type": "HypervisorHost",
  "ci_name": "esxi-rack-a-03",
  "ci_class": "compute",
  "tier": "virtualization",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["vcenter"],
  "aliases": ["esxi:rack-a-03"],
  "labels": { "env": "rca-lab", "rack": "A" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.7 `NetworkPort`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "nic-app-01-eth0",
  "ci_type": "NetworkPort",
  "ci_name": "app-01 eth0",
  "ci_class": "network",
  "tier": "network",
  "instance_scope": "multi-instance",
  "scope_parent": "linux-server-app-01",
  "identity_status": "resolved",
  "monitored_via": ["agent", "snmp"],
  "aliases": ["mac:00:11:22:33:44:55"],
  "labels": { "env": "rca-lab", "ifname": "eth0" },
  "valid_from": null,
  "valid_to": null
}
```

### 2.8 `Monitor` (collector / monitor configuration item, if modeled)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "monitor-agent-app-01",
  "ci_type": "Monitor",
  "ci_name": "agent on app-01",
  "ci_class": "observation",
  "tier": "identity_security",
  "instance_scope": "single",
  "identity_status": "resolved",
  "monitored_via": ["control-plane"],
  "aliases": ["dd-agent:app-01"],
  "labels": { "env": "rca-lab" },
  "valid_from": null,
  "valid_to": null
}
```

---

## 3) Sample nodes — qualifies temporarily (graph for a window, not ticket roots)

Always set `valid_from` / `valid_to` (or a non-null end when known) and `scope_parent` to the durable parent.

### 3.1 `Pod`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "pod-checkout-api-7f9c2",
  "ci_type": "Pod",
  "ci_name": "checkout-api-7f9c2",
  "ci_class": "container_platform",
  "tier": "container_platform",
  "instance_scope": "multi-instance",
  "scope_parent": "checkout-api",
  "identity_status": "resolved",
  "monitored_via": ["kubernetes", "agent"],
  "aliases": ["k8s.pod.uid:7f9c2a1b-...."],
  "labels": { "env": "rca-lab", "namespace": "checkout" },
  "valid_from": "2026-08-20T02:10:00Z",
  "valid_to": "2026-08-20T06:40:00Z"
}
```

### 3.2 `Container`

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "ctr-checkout-api-main-7f9c2",
  "ci_type": "Container",
  "ci_name": "checkout-api",
  "ci_class": "container_platform",
  "tier": "container_platform",
  "instance_scope": "multi-instance",
  "scope_parent": "pod-checkout-api-7f9c2",
  "identity_status": "resolved",
  "monitored_via": ["kubernetes", "agent"],
  "aliases": ["container.id:sha256:abcd…"],
  "labels": { "env": "rca-lab", "image": "checkout-api:1.4.2" },
  "valid_from": "2026-08-20T02:10:00Z",
  "valid_to": "2026-08-20T06:40:00Z"
}
```

### 3.3 `Endpoint` (only with a durable URL / port / route identity)

```json
{
  "schema_version": "graph_node.v1",
  "tenant": "default",
  "ci_id": "ep-checkout-https",
  "ci_type": "Endpoint",
  "ci_name": "https://checkout.lab.local/api",
  "ci_class": "network",
  "tier": "technical_service",
  "instance_scope": "single",
  "scope_parent": "checkout-api",
  "identity_status": "resolved",
  "monitored_via": ["apm", "synthetic"],
  "aliases": ["route:/api", "port:443"],
  "labels": { "env": "rca-lab", "scheme": "https" },
  "valid_from": null,
  "valid_to": null
}
```

Do **not** invent an Endpoint from a one-off span IP. Do **not** emit a `Process` node from a process identifier alone — a process identifier is unique at a glance and then reused, so it fails the durable-identity test.

---

## 4) Not decided yet — no sample node until identity is chosen

| Name | Why there is no sample JSON yet |
|------|----------------------------------|
| `Database` (unscoped) | Instance vs cluster vs schema is unspecified |
| `Deployment` | Kubernetes Deployment unique id ≠ release version ≠ runbook id |
| `Network` | Too coarse; pick switch, interface, subnet, virtual network, or load balancer |

---

## 5) Sample edges — all fifteen relations

Every edge below uses resolved configuration-item ends from the samples above (or obvious siblings). Provenance is filled enough to show the pattern; lab writers may omit optional fields until Signed.

### 5.1 `depends_on`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_depends_on_db",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "db-checkout-primary",
  "relation": "depends_on",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "service-catalog",
    "direction_inference": "caller needs data store",
    "refresh": "poll 1h"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.2 `runs_on`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_jvm_runs_on_host",
  "src_ci_id": "app-runtime-jvm",
  "dst_ci_id": "linux-server-app-01",
  "relation": "runs_on",
  "discovered_via": {
    "evidence_type": "authoritative",
    "confidence": "high",
    "telemetry_source": "agent/process-inventory/cgroup",
    "signal_fields": ["host.name", "process.cgroup"],
    "direction_inference": "workload -> host",
    "refresh": "poll 5m"
  },
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null
}
```

### 5.3 `mounts`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_host_mounts_lun",
  "src_ci_id": "linux-server-app-01",
  "dst_ci_id": "ds-san-lun-checkout",
  "relation": "mounts",
  "discovered_via": {
    "evidence_type": "authoritative",
    "confidence": "high",
    "telemetry_source": "agent/filesystem",
    "signal_fields": ["mountpoint", "device"],
    "direction_inference": "host mounts volume",
    "refresh": "poll 15m"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.4 `connects_to`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_nic_connects_to_switch",
  "src_ci_id": "nic-app-01-eth0",
  "dst_ci_id": "switch-rack-a-01",
  "relation": "connects_to",
  "discovered_via": {
    "evidence_type": "corroborating",
    "confidence": "medium",
    "telemetry_source": "snmp/lldp",
    "direction_inference": "L2 adjacency",
    "refresh": "poll 30m"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.5 `backs`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_lun_backs_db_files",
  "src_ci_id": "ds-san-lun-checkout",
  "dst_ci_id": "db-checkout-primary",
  "relation": "backs",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "storage-inventory",
    "direction_inference": "volume backs database files",
    "refresh": "poll 1h"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.6 `uses`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_uses_queue",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "queue-orders-v1",
  "relation": "uses",
  "discovered_via": {
    "evidence_type": "corroborating",
    "confidence": "medium",
    "telemetry_source": "apm/trace",
    "signal_fields": ["messaging.destination"],
    "direction_inference": "producer -> destination",
    "refresh": "poll 5m"
  },
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null
}
```

### 5.7 `hosted_on`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_vm_hosted_on_esxi",
  "src_ci_id": "vm-app-01",
  "dst_ci_id": "esxi-rack-a-03",
  "relation": "hosted_on",
  "discovered_via": {
    "evidence_type": "authoritative",
    "confidence": "high",
    "telemetry_source": "vcenter",
    "direction_inference": "guest -> hypervisor",
    "refresh": "poll 10m"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.8 `member_of`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_host_member_of_cluster",
  "src_ci_id": "linux-server-app-01",
  "dst_ci_id": "cluster-app-a",
  "relation": "member_of",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "cmdb-export",
    "direction_inference": "member -> group",
    "refresh": "poll 1d"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.9 `part_of`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_part_of_bs",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "bs-checkout",
  "relation": "part_of",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "service-catalog",
    "direction_inference": "technical service -> business service",
    "refresh": "poll 1d"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.10 `routes_through`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_routes_through_nginx",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "mw-nginx-edge",
  "relation": "routes_through",
  "discovered_via": {
    "evidence_type": "corroborating",
    "confidence": "medium",
    "telemetry_source": "apm/trace",
    "direction_inference": "request path via middlebox",
    "refresh": "poll 5m"
  },
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null
}
```

### 5.11 `authenticates_via`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_auth_via_idp",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "idp-lab-oidc",
  "relation": "authenticates_via",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "config",
    "direction_inference": "app -> identity provider",
    "refresh": "poll 1d"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.12 `monitored_by`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_host_monitored_by_agent",
  "src_ci_id": "linux-server-app-01",
  "dst_ci_id": "monitor-agent-app-01",
  "relation": "monitored_by",
  "discovered_via": {
    "evidence_type": "authoritative",
    "confidence": "high",
    "telemetry_source": "agent/heartbeat",
    "direction_inference": "observed CI -> collector CI",
    "refresh": "poll 1m"
  },
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null
}
```

### 5.13 `backed_up_by`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_db_backed_up_by_target",
  "src_ci_id": "db-checkout-primary",
  "dst_ci_id": "backup-target-checkout",
  "relation": "backed_up_by",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "backup-catalog",
    "direction_inference": "primary -> backup target",
    "refresh": "poll 1d"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.14 `clustered_with`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_db_primary_clustered_with_replica",
  "src_ci_id": "db-checkout-primary",
  "dst_ci_id": "db-checkout-replica",
  "relation": "clustered_with",
  "discovered_via": {
    "evidence_type": "declared",
    "confidence": "high",
    "telemetry_source": "db-topology",
    "direction_inference": "peer same tier",
    "refresh": "poll 1h"
  },
  "valid_from": "2026-08-01T00:00:00Z",
  "valid_to": null
}
```

### 5.15 `communicates_with`

```json
{
  "schema_version": "graph_edge.v1",
  "tenant": "default",
  "edge_id": "e_checkout_communicates_with_inventory",
  "src_ci_id": "checkout-api",
  "dst_ci_id": "inventory-api",
  "relation": "communicates_with",
  "discovered_via": {
    "evidence_type": "corroborating",
    "confidence": "medium",
    "telemetry_source": "apm/trace",
    "signal_fields": ["peer.service"],
    "endpoint_binding": "service.name -> ci_id via identity bind",
    "direction_inference": "client -> server from span direction",
    "refresh": "poll 5m"
  },
  "valid_from": "2026-08-20T00:00:00Z",
  "valid_to": null
}
```

Some destination ids above (`switch-rack-a-01`, `cluster-app-a`, `idp-lab-oidc`, `backup-target-checkout`, `db-checkout-replica`, `inventory-api`) are implied siblings: emit matching `graph_node.v1` rows before those edges, or omit the edge until those configuration items exist.

---

## 6) Mini snapshot (how pieces join)

Illustrative only — not a full estate. Field name is **`version`** (string), matching PoC `graph_snapshot.v1` / [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md). Do not use `snapshot_id`.

```json
{
  "schema_version": "graph_snapshot.v1",
  "tenant": "default",
  "version": "1",
  "nodes": [
    { "ci_id": "bs-checkout", "ci_type": "BusinessService" },
    { "ci_id": "checkout-api", "ci_type": "Service" },
    { "ci_id": "linux-server-app-01", "ci_type": "Host" },
    { "ci_id": "db-checkout-primary", "ci_type": "Database" },
    { "ci_id": "app-runtime-jvm", "ci_type": "Runtime" }
  ],
  "edges": [
    { "edge_id": "e_checkout_part_of_bs", "relation": "part_of" },
    { "edge_id": "e_jvm_runs_on_host", "relation": "runs_on" },
    { "edge_id": "e_checkout_depends_on_db", "relation": "depends_on" }
  ]
}
```

Full node and edge bodies are the samples in sections 1–5; the mini snapshot only shows the join keys. PoC publish also writes `nodes.jsonl` / `edges.jsonl` beside `graph_snapshot.json`.

---

## 7) Explicit non-samples (never topology nodes)

Do not produce `graph_node.v1` for: Change, Alert, Incident, ITSMTicket, Metric, LogPattern, Trace, or Process-from-pid-only.

---

*When the room Signs enums, paste the closed `ci_type` and `relation` lists into LLD-E3 and keep these samples as the normative examples.*
