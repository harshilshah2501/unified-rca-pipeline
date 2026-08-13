# Agent task · RESOURCE_CONTENTION (CPU / memory)

**Status:** Observed (negative Detect) — code-only **2026-08-12** · **no Problem**  
**Docs Timeline:** http://127.0.0.1:8765/dt-cat-resource-contention-lab.html  
**Hub:** http://127.0.0.1:8765/dt-davis-category-hub.html?cat=resource_contention  
**Lab root:** `dynatrace-rca-lab/`  
**Snapshot:** `docs/vendor-source/dynatrace/code-only-rc-2026-08-12-snapshot.json`

## Goal

Produce a Dynatrace **RESOURCE_CONTENTION** Problem whose Detect tip is **host/process CPU (or memory) saturation** on the inventory side — Smartscape `runsOn` should matter for seed ranking. Heal, snapshot, promote Timeline → Observed.

## Why this category (vs SLOWDOWN)

| Category | Leaf shape |
|----------|------------|
| SLOWDOWN | HTTP duration↑ (may be app CPU in a request path); Detect = response_time |
| **RESOURCE_CONTENTION** | Host/process **resource gauges** saturate; Detect = CPU/mem; may *also* slow callers |

Prefer a **background CPU burn** that keeps `/inventory` HTTP reasonably fast so the primary Event type is resource contention, not SERVICE_SLOWDOWN. If both fire, document which Davis packaged as primary.

## Constraints

- Induce the fault by **Python code change only** (RESOURCE_BURN markers in `inventory/app.py`).
- Do **not** reuse ledger-scan SLOWDOWN as the only fault (that lab already Observed P-260820).
- Do not stop the container (AVAILABILITY) or disable telemetry (MONITORING_UNAVAILABLE).
- Heal before finishing.
- Prefer real Problems API evidence.

## Steps

1. Confirm healthy probe ~40–50 ms.
2. Break: `./scripts/break_inventory_resource_burn.sh` — injects a background CPU-burn thread in inventory (HTTP path stays O(1)).
3. Sustain load + burn 10–15 min: `./scripts/run_resource_contention_rca.sh --minutes 15`.
4. Poll Dynatrace for RESOURCE_CONTENTION / high CPU on inventory process or HOST. Record Problem id, whether SLOWDOWN co-fired, `rootCauseEntity`, runsOn path.
5. Heal: `./scripts/heal_inventory_resource_burn.sh`.
6. Snapshot + rewrite Timeline to Observed; update `dt-davis-categories.js`.

## Comprehensive rerun evidence pack

- Capture 3 snapshots: pre-break, sustained burn (~8–10 min), post-heal.
- Save CPU/process metrics and Event list side-by-side with any co-fired SLOWDOWN evidence.
- Record UTC anchors: burn-start, first CPU Event, first Problem open, any slowdown co-fire, heal, close.

## Success criteria

- [x] Background burn induced by Python only; HTTP stayed fast 200.
- [ ] Host or process CPU (or mem) clearly elevated in Dynatrace — **blocked**: Metrics API `403` (`metrics.read` not on token).
- [x] Primary teaching claim documented: **no** RESOURCE_CONTENTION Problem in-window (Detect honesty).
- [x] UTC on Timeline; code healed to IDLE / HEALTHY.

## Code-only rerun (2026-08-12)

- Break ~**10:00:30 UTC** · load+burn → heal **10:15:53 UTC**.
- HTTP **200** fast throughout (load ok=10/10; post-heal ~28ms).
- Organic Problems for RC / HIGH_CPU / SLOWDOWN in window: **none**.
- Insight: resource-gauge Detect ≠ request-path SLOWDOWN; burn alone did not package an RC card here.
- Combined pack: `docs/vendor-source/dynatrace/code-only-rerun-2026-08-12-snapshot.json`.

## Scripts

| Script | Role |
|--------|------|
| `scripts/break_inventory_resource_burn.sh` | Inject CPU burn thread |
| `scripts/heal_inventory_resource_burn.sh` | Remove burn thread |
| `scripts/run_resource_contention_rca.sh` | Break → load → optional heal |

## Teaching cross-links

- Breakdown `?cat=resource_contention` — Detect tip = cpu/mem  
- Dual-track — Smartscape runsOn HOST-B ↔ INV  
- Contrast SLOWDOWN P-260820 (latency Detect, not host gauge)
