# Datadog RCA Lab — Reference Guide

Same three-service topology as `dynatrace-rca-lab`, instrumented with **ddtrace** → host **Datadog Agent** (`:8126`) so you can compare APM / Service Map / monitors with Dynatrace Smartscape / Grail / Davis.

---

## 1. Purpose

Generate controlled telemetry for Datadog’s detection and RCA surfaces (not an app demo).

For each injected fault, record:

| Fault | First Signal | Monitor / Watchdog | Root Cause hint | Service Map | Trace | Logs | Metrics |
| ----- | ------------ | ------------------ | --------------- | ----------- | ----- | ---- | ------- |

---

## 2. Lab Topology

```text
            curl :18080
              │
              ▼
      frontend:8080  ──ddtrace──► Agent :8126 ──► Datadog HQ
              │
              ▼
       product:8081
              │
              ▼
     inventory:8082
```

Prerequisites: Datadog Agent running on the host (`systemctl status datadog-agent`), APM enabled, preferably `apm_non_local_traffic: true` so Docker can reach `:8126`.

---

## 3. Quick start

```bash
cd datadog-rca-lab
docker compose up -d --build

# healthy path
./scripts/load.sh 20

# inventory fail (Dynatrace-lab parity)
./scripts/fault.sh inventory fail
./scripts/load.sh 40

# clear
./scripts/fault.sh inventory ok
```

Host URLs: `http://127.0.0.1:18080/api/checkout`, `:18081`, `:18082`.

In Datadog UI (env `rca-lab`): **APM → Services** (`frontend`, `product`, `inventory`), **Service Map**, **Traces** filtered by `env:rca-lab`, error traces on inventory 503.

---

## 4. What to compare vs Dynatrace

| Concern | Dynatrace (lab) | Datadog (this lab) |
| ------- | --------------- | ------------------ |
| Collect | OneAgent | Agent + ddtrace → Trace Agent |
| Topology | Smartscape | Service Map / USM / inferred services |
| Telemetry store | Grail | Metrics / Traces / Logs backends |
| Detect | Davis detectors / events | Monitors, Watchdog, Error Tracking |
| Case / RCA | Problem + Davis | Incident / Watchdog story / notebooks |

See also `docs/DATADOG_PRODUCTION_PIPELINE.md` (Clock A map).
