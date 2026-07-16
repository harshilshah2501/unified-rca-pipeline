# RCA Auto-Generation — ObserveOps Use-Cases

Classic VMware-style stack: **Network Device → ESXi Host → VM → Guest OS → Application** (with a shared Datastore). Each primary use-case targets a **different root-cause layer**. Engine pattern: anomaly/event triggers → typed topology walk to the deepest common upstream CI → rule signature names it (and, in product, suppresses symptom alerts).

| # | Root-cause layer | Fault | Trap it avoids | Bakeoff role |
|---|------------------|-------|----------------|--------------|
| UC-1 | Hypervisor (host CPU) | ESXi CPU contention starving many VMs | Blaming the app / individual VMs | Primary |
| UC-2 | Network | Switch uplink/port saturation or link down | Blaming the app or the server | Primary |
| UC-3 | Storage | Shared datastore latency (noisy neighbor) | Blaming the DB app that "got slow" | Primary |
| **UC-3b** | Storage + confound | Same as UC-3 **plus** early unrelated network anomaly | Picking earliest abnormal CI (switch) | **Adversarial** (frozen v1.1.0) |
| UC-4 | Guest OS | Filesystem full / runaway process / OOM | Blaming the app code | Primary (+ events) |
| UC-5 | Application | JVM heap / DB connection-pool exhaustion | *False-blaming* the infra below | Primary |

Frozen corpus: `datasets/observeops/` **v1.1.0** (`manifest.json`) — UC-1..UC-5 (primary bakeoff), **UC-3b** (adversarial confound), and **`events.json`** on UC-2 / UC-4 / UC-3b. Matched bakeoff: **`bakeoff-phase-b-002`**.

---

## Roadblocks this corpus addresses (ObserveOps)

| Roadblock | Field-wide status | This corpus |
|-----------|-------------------|-------------|
| **1b** Cross-domain fragmentation | Org silos remain unsolved | **Mandatory where data is joined** — one typed multi-domain CI graph (net/host/storage/OS/app) |
| **4** No standardized ground truth | No universal industry benchmark | **Mandatory by convention** — shared `ground_truth.json` + same-bundle bakeoff (see Eval contract) |

Other roadblocks (1a blind spots, 2 non-stationary topology, 3 pod churn, 5 cost) are Optional / deferred / design constraints for this ObserveOps set — see [`docs/README.md`](./README.md).

---

## Non-goals / known limits (do not overclaim)

- **Circular / mutual service loops (A ↔ B):** These UCs use a **layered classic-infra graph**, not microservice call cycles. Temporal “who was first” on true cycles is a known lean limit; out of scope for the primary evaluation engine bakeoff (ADR-001). Optional honesty fixture may be added later; it is **not** an ObserveOps acceptance gate.
- **Live inject / live SNMP/vCenter ingest:** Sections (a) describe how a human would inject faults; the PoC evaluates **frozen bundles**, not live injection.
- **Full free-text log mining (Nezha-style):** Out of scope for the primary evaluation engine path (ADR-001; not a finalized product commitment). Use **structured synthetic events** (§ Events schema) instead.
- **Alert bus suppression:** (d) describes product behavior; bakeoff scores root/signature/contributor/evidence, not an alert pipeline.

---

## Events schema (synthetic log / trap channel)

Metrics stay in `anomalies.json` (and optional `metrics/` time series). **Events** are first-class evidence for log/trap-shaped signals without a raw log pipeline.

**Bundle file:** `events.json` (optional on UC-1/UC-3/UC-5; **required** on UC-2 and UC-4 once implemented).

```json
{
  "events": [
    {
      "timestamp": "2026-07-10T10:00:00Z",
      "ci": "switch-core-01:GigE0/2",
      "event_type": "snmp.linkDown",
      "severity": "critical",
      "message": "SNMP TRAP linkDown: ifIndex=2 ifDescr=GigE0/2 ifOperStatus=down"
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `timestamp` | Event onset (ISO-8601, UTC) |
| `ci` | Configuration item id (must exist in topology) |
| `event_type` | Stable enum (see per-UC (b2) tables) |
| `severity` | `info` \| `warning` \| `critical` |
| `message` | Human-readable synthetic log/trap line (for SRE report / verifiability) |

Lean (and federated adapters) **must** be able to cite events in the evidence trail. Events may reinforce the same CI/signal as an anomaly row; they are not a second root-cause channel by themselves.

---

## Eval contract (what bakeoff must score)

Aligned with [`datasets/observeops/COMPARISON_BENCHMARK.md`](../datasets/observeops/COMPARISON_BENCHMARK.md).

### Ground-truth fields (every UC / UC-3b)

| Field | Required | Meaning |
|-------|----------|---------|
| `root_ci` | Yes | Top-1 root configuration item |
| `signature` | Yes | Primary bakeoff label (see Signature policy) |
| `contributor_cis` | Yes (may be `[]`) | Contributing CIs (UC-3 / UC-3b: noisy neighbor) |
| `blast_radius` | Recommended | Expected affected CIs (soft check) |
| `upstream_healthy` | UC-5 | When true, infra blame is automatic fail |

### Pass / fail (Accuracy)

| UC | Pass | Fail |
|----|------|------|
| UC-1 | `root_ci = esxi-host-01`, `signature = cpu_contention` | Blame app/VM only |
| UC-2 | `root_ci = switch-core-01:GigE0/2`, `signature = link_failure` | Blame app/server |
| UC-3 | `root_ci = datastore-01`, `signature = storage_contention`, contributor includes noisy-neighbor VM | Blame DB/app only; omit contributor when neighbor IOPS present |
| **UC-3b** | Same as UC-3 **despite** earlier switch anomaly | Root = switch (earliest abnormal) |
| UC-4 | `root_ci = guest-os-vm-app-01`, `signature = os_resource_exhaustion` | Blame app code or infra below OS |
| UC-5 | `root_ci = orders-api`, `signature = app_resource_exhaustion` | Any infra root when upstream healthy |

### Signature policy (bakeoff primary label)

OR-branches in the narrative may describe variants; **bakeoff uses one primary signature per UC** unless aliases are listed:

| UC | Primary signature | Allowed narrative aliases (not separate GT rows unless split later) |
|----|-------------------|---------------------------------------------------------------------|
| UC-1 | `cpu_contention` | — |
| UC-2 | `link_failure` | `network_saturation` (utilization+discards path; same root) |
| UC-3 / UC-3b | `storage_contention` | — |
| UC-4 | `os_resource_exhaustion` | `filesystem_full`, `oom`, `runaway_process` (same root; optional future UC-4b split) |
| UC-5 | `app_resource_exhaustion` | `heap_exhaustion`, `connection_pool_exhaustion` |

---

## UC-1 — ESXi host CPU contention (host root cause, app symptom)

**(a) Fault & injection.** On `esxi-host-01`, over-commit vCPUs so VMs can't get scheduled. *Inject:* run `stress-ng --cpu N` inside 2–3 co-located VMs at once, or power on extra CPU-heavy VMs, so host CPU demand exceeds physical cores.

**(b) Telemetry signals & thresholds.**
| Layer | CI | Signal | Fires at |
|---|---|---|---|
| Hypervisor | esxi-host-01 | `cpu.usage` (%) | > 85–90% sustained |
| Hypervisor | esxi-host-01 / per-VM | `cpu.ready` (CPU Ready %) | > 5% per vCPU (10%+ severe) |
| Hypervisor | vm-* | `cpu.costop` (co-stop, SMP VMs) | > 3–5% |
| OS | guest OS | run-queue / load average | > #vCPU |
| App | orders-api | request p95 latency / SLO | breach (e.g., p95 > 1s) |

**(b2) Events.** Optional for UC-1 (metrics-dominant). None required for primary bakeoff.

**(c) Symptoms per layer.** *App owner sees:* "orders-api is slow; CPU inside my VM looks ~100% but throughput is low." *Real cause:* host has more vCPU demand than physical cores; VMs sit ready-waiting for a core (high CPU Ready). In-guest CPU% is misleading — the vCPU is starved at the scheduler.

**(d) Correlation logic.** Anomaly fires app latency + multiple VM CPU anomalies together. Topology: all affected VMs share `esxi-host-01` upstream; host shows high `cpu.usage` **and** high `cpu.ready` → causal. Signature: `host cpu.usage high AND cpu.ready high across ≥2 VMs → cpu_contention`. VM/app symptom alerts roll up under the host incident.

**(e) Auto RCA output.** Root cause = `esxi-host-01` (cpu_contention); chain host→VMs→OS→apps; evidence = ready% + usage%; blast-radius = every VM/app on the host; remediation = vMotion/rebalance, check DRS, find runaway VM, right-size vCPUs.

**(f) Ground truth (bakeoff).** `root_ci=esxi-host-01`, `signature=cpu_contention`, `contributor_cis=[]`.

---

## UC-2 — Network uplink / switch port saturation or link-down (network root cause)

**(a) Fault & injection.** Saturate or drop the uplink between `esxi-host-01` and `switch-core-01`. *Inject:* admin-down the switch port (linkDown), flood the link with iperf to drive utilization/discards, or disable one uplink NIC to force degraded redundancy.

**(b) Telemetry signals & thresholds.**
| Layer | CI | Signal | Fires at |
|---|---|---|---|
| Network | switch-core-01 : port | SNMP `linkDown` trap / `ifOperStatus=down` | immediate |
| Network | switch port | `ifInErrors`/`ifOutErrors`, `ifInDiscards`/`ifOutDiscards` | > 0 and rising |
| Network | switch port | utilization (in/out bps ÷ ifSpeed) | > 90% sustained |
| Hypervisor | esxi-host-01 | vmnic link state / dropped packets / net latency | link down / drops > 0 |
| OS/App | vm-*, app | TCP retransmits, timeouts, latency | rising / errors |

**(b2) Events (required once events channel ships).**
| CI | event_type | Example message |
|----|------------|-----------------|
| `switch-core-01:GigE0/2` | `snmp.linkDown` | `SNMP TRAP linkDown: ifDescr=GigE0/2 ifOperStatus=down` |
| `switch-core-01:GigE0/2` | `snmp.ifOutDiscards` (optional) | `ifOutDiscards rising on GigE0/2` |

**(c) Symptoms per layer.** *App owner sees:* intermittent timeouts, elevated latency, failed requests — "the app is flaky." *Real cause:* packet loss/saturation on the switch uplink feeding the host. Every VM on that host is affected identically — the tell that the cause is shared network, not app code.

**(d) Correlation logic.** SNMP `linkDown`/error-rate anomaly on the port is the seed. Topology: port → host uplink → host → all VMs/apps; the port is upstream of everything on the host and shows a hard fault, so it wins the root-cause score decisively. Signature: `linkDown OR (utilization>90% AND discards rising) on port feeding host → network_saturation/link_failure`. Downstream app/VM timeout alerts suppressed as effects.

**(e) Auto RCA output.** Root cause = `switch-core-01:GigE0/2` (primary bakeoff signature `link_failure`); chain port→host uplink→VMs→apps; evidence = linkDown trap / discards / utilization **including event message**; blast-radius = all VMs/apps behind that uplink; remediation = restore/replace link, check redundant uplink/NIC teaming, find traffic-spike source.

**(f) Ground truth (bakeoff).** `root_ci=switch-core-01:GigE0/2`, `signature=link_failure`, `contributor_cis=[]`.

---

## UC-3 — Shared datastore latency / noisy neighbor (storage root cause)

**(a) Fault & injection.** Drive I/O contention on the shared datastore hosting several VMs so the DB VM's disk slows. *Inject:* run a heavy `fio`/`dd` random-I/O workload inside one "noisy neighbor" VM on the same datastore as `vm-db-01`.

**(b) Telemetry signals & thresholds.**
| Layer | CI | Signal | Fires at |
|---|---|---|---|
| Storage/Hyp. | datastore-01 | total latency (GAVG) | > 20–30 ms (severe > 50) |
| Storage/Hyp. | datastore-01 | device latency (DAVG) / kernel latency (KAVG) | DAVG>20ms / KAVG>2ms |
| Hypervisor | vm-db-01 | `virtualDisk.totalLatency`, outstanding I/O | > 20–30 ms |
| OS | db guest OS | disk `await` / queue depth, %iowait | await high, iowait high |
| App | db / orders-api | query time, DB response, app p95 | slow queries / SLO breach |

**(b2) Events.** Optional. Neighbor IOPS may remain metric-only for primary UC-3.

**(c) Symptoms per layer.** *App owner sees:* "the database is slow, queries timing out" — looks like a DB problem. *Real cause:* the datastore is latency-bound because a *different* VM is saturating shared storage; the DB VM is a noisy-neighbor victim.

**(d) Correlation logic.** Anomaly on app/DB latency + VM disk latency seeds it. Topology: `vm-db-01` → `datastore-01`. Engine sees `datastore-01` latency high **and** the load source is a sibling VM on the same datastore → noisy neighbor surfaced as contributing CI; root cause = datastore contention, not the DB. Signature: `datastore GAVG high AND (≥2 VMs disk latency OR 1 victim VM latency + noisy-neighbor IOPS) → storage_contention`. DB "slow query" alerts suppressed.

**(e) Auto RCA output.** Root cause = `datastore-01` (storage_contention) + contributing CI = noisy-neighbor VM; chain datastore→vm-db-01 disk→OS iowait→DB queries→app; evidence = GAVG/DAVG, per-VM disk latency, noisy-neighbor IOPS; blast-radius = all VMs on the datastore; remediation = Storage vMotion the noisy VM or DB, apply Storage I/O Control/limits, check backing array.

**(f) Ground truth (bakeoff).** `root_ci=datastore-01`, `signature=storage_contention`, `contributor_cis` includes `vm-neighbor-01` (or equivalent noisy-neighbor id).

---

## UC-3b — Storage contention with early unrelated network anomaly (adversarial)

**Purpose.** Prove the engine does **not** equate “earliest abnormal CI” with root cause when an unrelated network blip precedes the storage story (the classic lean temporal confound).

**(a) Fault & injection.** Same as UC-3 (noisy neighbor → datastore congestion → DB/app slow). **Additionally:** at a slightly earlier timestamp, the switch port shows a **non-causal** abnormality (e.g. brief high utilization or a flapping metric that does **not** explain shared-storage latency). Do **not** inject a real linkDown that would correctly make the network the root.

**(b) Telemetry.** All UC-3 crossed storage/DB/app signals **plus** a crossed (or high) network signal on `switch-core-01:GigE0/2` with onset **before** batch/datastore onsets (within a few seconds so Δt is ambiguous).

**(b2) Events.** Optional switch utilization/syslog noise event with early timestamp — must not override storage root.

**(c) Symptoms.** Same user-visible app/DB slowness as UC-3. Network noise is **not** what the app owner is hitting.

**(d) Correlation logic.** Topology still reaches the switch via host uplink, so naïve earliest-onset would pick the switch. Correct path: storage shared-upstream / signature / CARE+rules must keep **`datastore-01`** as root and **noisy neighbor** as contributor. Switch may appear in evidence as concurrent noise, not root.

**(e) Auto RCA output.** Same as UC-3. Explicit note in evidence/report: concurrent network anomaly present but not causal for this incident.

**(f) Ground truth (bakeoff).** Identical to UC-3: `root_ci=datastore-01`, `signature=storage_contention`, contributor = noisy-neighbor VM. **Fail** if `root_ci` is the switch (or host) solely due to earlier onset.

**Status:** Specified for next corpus freeze (`datasets/observeops/UC-3b/`). Not yet in primary bakeoff until implemented.

---

## UC-4 — Guest OS filesystem full / runaway process (OS root cause)

**(a) Fault & injection.** Break the app via the OS, not the app. *Inject:* fill the filesystem the app writes to (`fallocate`/`dd` until 100%), spawn a runaway CPU/memory process, or exhaust memory to trigger the OOM-killer.

**(b) Telemetry signals & thresholds.**
| Layer | CI | Signal | Fires at |
|---|---|---|---|
| OS | guest OS | filesystem used % | > 90% (critical > 95–100%) |
| OS | guest OS | memory available / swap-in rate | low free / swapping |
| OS | guest OS | OOM-killer event (log) | present |
| OS | guest OS | per-process CPU/mem (top offender) | runaway process |
| OS | guest OS | service/process state | app service `down` |
| App | app | health check / error rate / down | failing writes, 5xx, down |

**(b2) Events (required once events channel ships).** Primary UC-4 bundle should include at least one of:
| CI | event_type | Example message |
|----|------------|-----------------|
| `guest-os-vm-app-01` | `syslog.oom_killer` | `kernel: Out of memory: Killed process 1842 (orders-api)` |
| `guest-os-vm-app-01` | `syslog.filesystem_full` | `No space left on device writing /var/log/orders-api` |
| `guest-os-vm-app-01` | `process.runaway` (optional) | `top: pid=991 cpu=198% cmd=stress-ng` |

Layers below OS (VM/host/network) remain **healthy** (`crossed: false` if present).

**(c) Symptoms per layer.** *App owner sees:* "app is throwing write errors / crashed / returning 500s." *Real cause:* OS out of disk (can't write logs/temp), OOM-killed the process, or a runaway process starved it — an OS-resource fault, not an app bug.

**(d) Correlation logic.** App-down/error anomaly seeds it; topology maps app → guest OS. On that OS the engine finds a concurrent hard resource event (disk 100% / OOM log / runaway process). OS CI is immediate upstream with a decisive fault → root cause. Signature: `app down/errors AND (fs>95% OR OOM event OR process killed) on its OS → os_resource_exhaustion`. Layers below (VM, host, network) checked and healthy, so the walk stops at the OS.

**(e) Auto RCA output.** Root cause = `guest-os-vm-app-01` (primary signature `os_resource_exhaustion`); evidence must cite **event message** when present (OOM line / fs full); blast-radius = the app(s) on this OS only (not the whole host — contrast with UC-1); remediation = free/extend disk, kill/limit runaway process, add memory / fix leak, restart service.

**(f) Ground truth (bakeoff).** `root_ci=guest-os-vm-app-01`, `signature=os_resource_exhaustion`, `contributor_cis=[]`.

---

## UC-5 — Application-layer exhaustion (app root cause; engine must NOT blame infra)

**(a) Fault & injection.** A genuine app-tier fault with all infra below healthy — the contrast case proving the engine localizes correctly. *Inject:* exhaust the JVM heap (GC thrash / OOM), saturate the DB connection pool (hold all connections), or exhaust the thread pool under load.

**(b) Telemetry signals & thresholds.**
| Layer | CI | Signal | Fires at |
|---|---|---|---|
| App | orders-api | JVM heap used % / GC pause / GC frequency | heap > 90%, long/frequent GC |
| App | orders-api | DB conn-pool active/max, thread-pool active/max | pool ≈ 100% |
| App | orders-api | p95 latency, error rate (5xx/timeouts) | SLO breach |
| OS | guest OS | CPU / mem / disk | **normal** (key: healthy) |
| Hypervisor/Net | host / switch | CPU-ready / datastore / link | **normal** (key: healthy) |

**(b2) Events.** Optional (e.g. GC log line). Not required for primary bakeoff.

**(c) Symptoms per layer.** *App owner sees:* latency + errors climbing. *Real cause:* the app itself — heap exhaustion / pool saturation. Everything below is healthy.

**(d) Correlation logic.** Anomaly on app latency/errors seeds it. Topology walk downstream (OS→VM→host→datastore→network) finds **all upstream CIs healthy** — no causal anomaly below the app — so the walk terminates at the app CI. Signature: `app latency/errors high AND (heap>90% OR pool exhausted) AND all upstream CIs healthy → app_resource_exhaustion`. This is the anti-false-positive test: the engine must resist pointing at infra when infra is clean.

**(e) Auto RCA output.** Root cause = `orders-api` (primary signature `app_resource_exhaustion`); chain app internal→app latency; evidence = heap%, GC, pool active/max, plus explicit "upstream infra verified healthy" note; blast-radius = this service and its consumers only; remediation = increase heap / fix leak, tune pool size, add instances / autoscale, investigate slow downstream dependency.

**(f) Ground truth (bakeoff).** `root_ci=orders-api`, `signature=app_resource_exhaustion`, `contributor_cis=[]`, `upstream_healthy=true`.

---

## Implementation checklist (spec → corpus)

| Item | Spec status | Corpus / engine |
|------|-------------|-----------------|
| UC-1..UC-5 primary stories | Done | Done (`datasets/observeops/UC-*`) |
| Events schema + UC-2/UC-4 (b2) | Done | Done — `events.json` + lean evidence ingest |
| UC-3b adversarial | Done | Done — `datasets/observeops/UC-3b/` + tests |
| Contributor scored on UC-3/UC-3b | Done | Done — compare + smoke tests |
| Circular-deps ObserveOps gate | Explicit non-goal | No bakeoff requirement |
| Alert suppression | Product (d) only | Out of PoC bakeoff scope |
