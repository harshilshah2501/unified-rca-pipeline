# Motadata L1 — Lean vs Federated

**Corpus:** `/root/Harshil-PoCs/Unified-RCA/datasets/ingest_samples/motadata-ingest/incidents`
**Generated:** `2026-07-22T09:30:22.455558+00:00`
**Run id:** `motadata-l1-20260722T093021Z`

## Verdict

**Overall better on this Motadata slice: `tie`**

Full pass (root+signature): Lean 7/7, Federated 7/7. Root-only: Lean 7/7, Federated 7/7.

## Scoreboard

| Metric | Lean | Federated |
|--------|------|-----------|
| Full pass (root+sig) | **7/7** | **7/7** |
| Root-CI match | 7/7 | 7/7 |
| Signature match | 7/7 | 7/7 |

## Per incident

| Incident | GT root / sig | Lean | Fed | Winner |
|----------|---------------|------|-----|--------|
| `motadata-apm-001` | `ProductCatalog_dotnet.` / `app_error_rate` | `ProductCatalog_dotnet.` / `app_error_rate` (pass) | `ProductCatalog_dotnet.` / `app_error_rate` (pass) | **lean** |
| `motadata-cpu-001` | `Fluentbit` / `host_cpu_saturation` | `Fluentbit` / `host_cpu_saturation` (pass) | `Fluentbit` / `host_cpu_saturation` (pass) | **lean** |
| `motadata-multi-001` | `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` / `host_cpu_saturation` | `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` / `host_cpu_saturation` (pass) | `HB1-2328-26-4992-4512-4320-4869-76-735.hb1.com` / `host_cpu_saturation` (pass) | **lean** |
| `motadata-ping-001` | `dlink-48` / `ping_degradation` | `dlink-48` / `ping_degradation` (pass) | `dlink-48` / `ping_degradation` (pass) | **lean** |
| `motadata-ping-002` | `Netgear Switch` / `ping_degradation` | `Netgear Switch` / `ping_degradation` (pass) | `Netgear Switch` / `ping_degradation` (pass) | **lean** |
| `motadata-ping-003` | `proxmox-ve-129` / `ping_degradation` | `proxmox-ve-129` / `ping_degradation` (pass) | `proxmox-ve-129` / `ping_degradation` (pass) | **lean** |
| `motadata-ping-004` | `localhost.localdomain` / `ping_degradation` | `localhost.localdomain` / `ping_degradation` (pass) | `localhost.localdomain` / `ping_degradation` (pass) | **lean** |

## Reproduce

```bash
RUN_ID=motadata-l1-$(date -u +%Y%m%dT%H%M%SZ)
.venv/bin/python benchmarking/benchmark/run_motadata_bakeoff.py --run-id "$RUN_ID"
```

