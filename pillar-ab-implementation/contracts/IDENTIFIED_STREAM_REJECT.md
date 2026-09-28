# Identified stream — reject contract

**Purpose:** Single list of reason codes both Pillar A (sketch writer) and Pillar B (graph writer) use when dropping an `ingest.v1` line. Writers do not invent extra drop reasons without adding them here.

**Applies after:** E1 Collect + E2 Identity overlay. This workstream does not implement Collect or Identity.

---

## Reason codes

| Code | Who applies it | When |
|------|----------------|------|
| `identity_unresolved` | Identity gate (both writers) | `identity.status` is missing or `unattributed` |
| `identity_synthesized` | Identity gate (both writers) | `identity.status` is `synthesized` — not a localize or ticket target |
| `never_ci_vertex` | Graph builder | `ci_type` (or Motadata name) is Change, Alert, Incident, ITSMTicket, Metric, LogPattern, or Trace |
| `unknown_relation` | Graph builder | `relation` is not in the fifteen-name catalog |
| `missing_endpoint_type` | Graph builder | Source or destination Motadata storage type cannot be resolved (no map type, no `dst_ci_type` / `src_ci_type`) |
| `illegal_edge_triplet` | Graph builder | `(src_type, relation, dst_type)` is not on the wave-1 allowlist — [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md) |
| `unknown_metric_id` | Sketch admit | `metric_id` / `name` is outside the wave-1 allowlist |

Wave-1 metric allowlist: `request.latency_ms`, `cpu.utilization_pct`.

Wave-1 graph emit allowlist (schema still lists all fifteen): `runs_on`, `hosted_on`, `depends_on`, `communicates_with`, `part_of`.

Relations that are in the catalog but not wave-1 are **not** `unknown_relation`. They are skipped by the phased emitter, not rejected as illegal ingest.

Endpoint pairing for wave-1 emit relations is **hard reject** when illegal — see [`EDGE_TRIPLET_ALLOWLIST.md`](./EDGE_TRIPLET_ALLOWLIST.md).

---

## Identity gate (shared stub)

Pass only `identity.status = resolved`.

Drop:

- missing `identity` block → `identity_unresolved`
- `unattributed` → `identity_unresolved`
- `synthesized` → `identity_synthesized`

---

## On-disk rooms (Gate B file dest)

Topology publish always writes the three **map** keys. Sketch and change-fact paths are history-room artifacts (change facts only when that writer runs).

```text
poc/out/<tenant>/
  map/graph_snapshot.json    # graph_snapshot.v1 (pretty JSON)
  map/nodes.jsonl            # graph_node.v1 per line
  map/edges.jsonl            # graph_edge.v1 per line
  history/sketches.jsonl     # sketch.v1 (Pillar A)
  history/change_facts.jsonl # change_fact.v1 (optional; not part of publish_snapshot)
```

Normative map encoding: [`MAP_WRITE_READ_RECORD.md`](./MAP_WRITE_READ_RECORD.md).

Logical rooms stay separate: map vs history. Same `tenant` + `ci_id` / `entity_id` namespace.
