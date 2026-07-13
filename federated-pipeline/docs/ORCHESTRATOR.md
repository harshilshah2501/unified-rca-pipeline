# Orchestrator — Coordination & Fusion Layer

**Motadata note:** Lean is the primary ObserveOps engine ([ADR-001](../../docs/ADR-001-lean-primary-engine.md)). This document specifies the **federated** coordination contract (Panorama → Murphy → Nezha). Shipping Motadata diagnose path: [`../../lean-pipeline/docs/ARCHITECTURE.md`](../../lean-pipeline/docs/ARCHITECTURE.md). Federated overview: [`ARCHITECTURE.md`](./ARCHITECTURE.md).

The orchestrator is the **primary novel contribution of the federated synthesis**. None of the three papers (Panorama, Murphy, Nezha) define trigger routing, schema translation, search narrowing, or confidence fusion. It is **not** Motadata’s claim that federated is the default product brain — that decision is ADR-001 (lean primary).

## Responsibilities

| Job | Description |
|-----|-------------|
| **Trigger routing** | Decide when to invoke Murphy and Nezha from detection signals |
| **Arbitration** | Reconcile independent triggers (Panorama gray-failure vs. Murphy threshold scan) |
| **Schema translation** | Convert one algorithm's output into the next algorithm's input format |
| **Narrowing** | Map Murphy's whole-graph posterior to a single-service Nezha query |
| **Baseline lifecycle** | Manage Nezha fault-free vs. fault-suffering phase windows |
| **Fusion** | Combine three incompatible confidence representations into one verdict |

## Trigger rules (draft)

| Source | Condition | Action |
|--------|-----------|--------|
| Panorama | `evidence_score ≥ θ_pano` | Open incident; invoke Murphy with flagged entity |
| Murphy self-scan | Anomalous metric exceeds preset threshold (optional mode) | Open incident; invoke Murphy directly |
| Both fire | Same entity within `T_arb` window | Deduplicate — single incident, merge symptom set |
| Both fire | Different entities | Two parallel incidents OR escalate to operator (OD-1) |
| Murphy complete | `max(posterior) ≥ θ_murphy` | Invoke Nezha on top-1 (or top-k) entity |
| Murphy complete | `max(posterior) < θ_murphy` | Return low-confidence verdict; skip Nezha |

Default thresholds (`θ_pano`, `θ_murphy`, `T_arb`) are PoC tuning parameters.

## Data lifecycle management

| Algorithm | Data need | Lifecycle |
|-----------|-----------|-----------|
| Panorama | Continuous observer reports | Rolling LOS window; no per-incident reset |
| Murphy | Metric history + topology | 1-week lookback for ridge regression; topology on deploy |
| Nezha | Fault-free baseline + fault-suffering window | Baseline collected pre-incident; suffering window starts at trigger |

The orchestrator marks Nezha `phase` transitions:

1. **Baseline collection** — continuous; `pc:fault-free:*` keys populated during healthy periods.
2. **Incident open** — at trigger, snapshot baseline end time; begin `pc:fault-suffering:*` accumulation.
3. **Incident close** — stop suffering accumulation; optionally rotate baseline.

---

## Hop payload schemas

All payloads carry an `incident_id` (UUID) and `timestamp` (RFC 3339).

### Hop 1 → 2: Panorama flag to orchestrator

**`DetectionFlag`** — output of Panorama, input to orchestrator.

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:00Z",
  "entity": "auth-service",
  "evidence_score": 0.82,
  "observer_count": 7,
  "status": "UNHEALTHY",
  "metric": "latency_p99"
}
```

### Hop 2 → 3: Orchestrator to Murphy

**`MurphyRequest`** — constructed by orchestrator from `DetectionFlag`.

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:01Z",
  "symptom_entity": "frontend",
  "symptom_metric": "latency_p99",
  "flagged_entities": ["auth-service"],
  "lookback_hours": 168,
  "gibbs_iterations": 500
}
```

| Field | Source |
|-------|--------|
| `symptom_entity` | Downstream entity showing user-visible degradation, or same as flagged if edge case |
| `symptom_metric` | From Panorama flag, or operator-specified |
| `flagged_entities` | Panorama output; narrows Murphy's candidate set |
| `lookback_hours` | Murphy default (1 week) |

### Hop 3 → 4: Murphy posterior to orchestrator

**`MurphyResult`**

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:05Z",
  "symptom_entity": "frontend",
  "symptom_metric": "latency_p99",
  "posterior": {
    "auth-service": 0.71,
    "db-proxy": 0.18,
    "cache-service": 0.07
  },
  "converged": true
}
```

### Hop 4 → 5: Orchestrator to Nezha

**`NezhaRequest`** — orchestrator picks top entity and time window.

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:06Z",
  "tenant": "default",
  "service": "auth-service",
  "time_window": {
    "start": "2026-07-06T09:25:00Z",
    "end": "2026-07-06T09:30:00Z"
  },
  "baseline_window": {
    "start": "2026-07-06T08:00:00Z",
    "end": "2026-07-06T09:25:00Z"
  },
  "top_k": 5
}
```

| Field | Rationale |
|-------|-----------|
| `service` | Top-1 from Murphy posterior (or top-k for parallel queries) |
| `time_window` | Incident suffering period |
| `baseline_window` | Fault-free reference for pattern scoring |

### Hop 5 → 6: Nezha result to orchestrator

**`NezhaResult`**

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:08Z",
  "service": "auth-service",
  "ranked_patterns": [
    {
      "expected_pattern": "Auth→DB_Query",
      "actual_pattern": "Auth→DB_Timeout",
      "score": 0.89,
      "support_count": 142
    },
    {
      "expected_pattern": "Auth→Token_Validate",
      "actual_pattern": "Auth→Token_Validate",
      "score": 0.12,
      "support_count": 891
    }
  ]
}
```

### Hop 6: Fused verdict

**`RCAVerdict`** — final output to SRE/UI.

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-06T09:30:09Z",
  "root_cause_entity": "auth-service",
  "root_cause_pattern": "Auth→DB_Query → Auth→DB_Timeout",
  "confidence": 0.76,
  "evidence": {
    "panorama": { "evidence_score": 0.82, "status": "UNHEALTHY" },
    "murphy": { "posterior": 0.71, "entity": "auth-service" },
    "nezha": { "pattern_score": 0.89, "rank": 1 }
  },
  "summary": "auth-service gray failure; DB query timeouts replaced successful queries"
}
```

### Fusion logic (draft)

```
confidence = w_pano * norm(evidence_score)
           + w_murphy * max(posterior)
           + w_nezha * top_pattern.score

Default weights: w_pano=0.2, w_murphy=0.4, w_nezha=0.4
```

Weights and fusion strategy are open decision **OD-3** in [REQUIREMENTS.md](./REQUIREMENTS.md).

---

## Failure modes

| Condition | Behavior |
|-----------|----------|
| Panorama fires, Murphy has stale topology | Log warning; Murphy runs on last-known graph; flag `topology_stale: true` in verdict |
| Murphy posterior flat (no convergence) | Skip Nezha; return verdict with `confidence: low`, Murphy-only evidence |
| Nezha missing fault-free baseline | Reject Nezha hop; return Murphy-only verdict; alert operator |
| Duplicate triggers within `T_arb` | Merge into single incident; extend time window |
