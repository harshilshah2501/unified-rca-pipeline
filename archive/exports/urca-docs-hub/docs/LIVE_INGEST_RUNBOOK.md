# LIVE ingest runbook — Connect stage

**Status:** Ready to execute next week (configs + checklist). Closing **LIVE** still requires one lab run with a non-replay source.  
**Owns:** Connect / [`RCA_WORKFLOW_AND_NEXT.md`](./RCA_WORKFLOW_AND_NEXT.md) §3 `LIVE`  
**Design:** [`INGESTION_PIPELINE_VECTOR.md`](./INGESTION_PIPELINE_VECTOR.md) · F1 sinks match [`../ingestion-poc/vector/vector.f1-smoke.toml`](../ingestion-poc/vector/vector.f1-smoke.toml)

---

## 1. Goal / exit criteria

| | |
|--|--|
| **Goal** | ≥1 **non-replay** source → Vector → same F1 sinks → shared Detect seed |
| **Exit** | `detect_source` recorded · sink line counts · note in Conduct / lab artifact under `benchmarking/capacity/lab/` or `ingestion-poc/out/live-<ts>/` |

Pick **one** source for the first smoke (do not require both):

| Option | Vector config | When to use |
|--------|---------------|-------------|
| **A · Syslog** | `vector.live-syslog.toml` | Host/network devices already emit syslog |
| **B · Prometheus** | `vector.live-prometheus.toml` | Scrapable `/metrics` endpoint in lab |

---

## 2. Prerequisites

```bash
cd /path/to/Unified-RCA
# Docker for Vector (same image as F1 smoke)
docker --version
# Optional: Python detect after sinks fill
test -x .venv/bin/python || python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt 2>/dev/null || true
```

- Free UDP **5140** (syslog) or TCP scrape access to Prometheus target.
- Writeable out dir: `ingestion-poc/out/live-<ts>/` (gitignored via `ingestion-poc/out/`).

---

## 3. Option A — Syslog → F1

### 3.1 Start Vector

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="ingestion-poc/out/live-$TS"
mkdir -p "$OUT"/{lean,structural,speed_tier,.vector-data}

docker run --rm -d --name urca-live-syslog \
  -p 5140:5140/udp \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/$OUT:/out" \
  -v "$PWD/$OUT/.vector-data:/var/lib/vector" \
  -e F1_OUT_DIR=/out \
  -e VECTOR_DATA_DIR=/var/lib/vector \
  -e LIVE_TENANT=lab \
  timberio/vector:0.41.1-alpine \
  --config /workspace/ingestion-poc/vector/vector.live-syslog.toml \
  --require-healthy false

echo "OUT=$OUT"
```

### 3.2 Emit a test event

```bash
# From host (maps to container UDP 5140)
logger -n 127.0.0.1 -P 5140 -d "urca-live-smoke host=lab-host1 metric=ping.latency.ms value=250"
# or:
echo '<14>$(date -u +%b\ %d\ %H:%M:%S) lab-host1 urca: ping.latency.ms=250 threshold=100' \
  | nc -u -w1 127.0.0.1 5140
```

Remap stores a best-effort `ingest.v1` `event` (and optional `metric_sample` if `name=value` pairs parse). **First smoke only needs sink bytes > 0.**

### 3.3 Compose alternative

```bash
F1_OUT_DIR="$PWD/$OUT" docker compose \
  -f ingestion-poc/compose/docker-compose.live.yml \
  --profile syslog up
```

---

## 4. Option B — Prometheus → F1

Edit scrape target in env before start:

```bash
export PROM_TARGETS='["http://host.docker.internal:9090/metrics"]'  # or lab exporter
# Linux: use host IP / --add-host=host.docker.internal:host-gateway
```

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="ingestion-poc/out/live-$TS"
mkdir -p "$OUT"/{lean,structural,speed_tier,.vector-data}

docker run --rm -d --name urca-live-prom \
  --add-host=host.docker.internal:host-gateway \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/$OUT:/out" \
  -v "$PWD/$OUT/.vector-data:/var/lib/vector" \
  -e F1_OUT_DIR=/out \
  -e VECTOR_DATA_DIR=/var/lib/vector \
  -e PROM_TARGETS="$PROM_TARGETS" \
  -e LIVE_TENANT=lab \
  timberio/vector:0.41.1-alpine \
  --config /workspace/ingestion-poc/vector/vector.live-prometheus.toml \
  --require-healthy false
```

Wait ~30–60s for scrape interval, then check sinks.

---

## 5. Verify sinks + Detect

```bash
# Sink counts (must be >0 on at least lean or structural)
wc -l "$OUT"/lean/events.jsonl "$OUT"/structural/stream.jsonl "$OUT"/speed_tier/feed.jsonl

# Shared threshold Detect on structural (or lean) feed
.venv/bin/python ingestion-poc/detect/threshold_detect.py \
  --ingest-jsonl "$OUT/structural/stream.jsonl" \
  --out-dir "$OUT/detect" \
  --empty-ok   # first smoke may be events-only

# Record meta
python3 - <<PY
import json, os, time
from pathlib import Path
out = Path(os.environ.get("OUT", "$OUT"))
meta = {
  "live_run_id": out.name,
  "detect_source": "shared_threshold",
  "sink_counts": {
    p.name: sum(1 for _ in p.open()) if p.is_file() else 0
    for p in [
      out/"lean/events.jsonl",
      out/"structural/stream.jsonl",
      out/"speed_tier/feed.jsonl",
    ]
  },
  "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
(out/"live_smoke_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta, indent=2))
PY
```

**Helper (same checks):**

```bash
.venv/bin/python ingestion-poc/lab/live_smoke_verify.py --out-dir "$OUT"
```

---

## 6. Stop & note Conduct

```bash
docker stop urca-live-syslog urca-live-prom 2>/dev/null || true
# Paste sink counts + live_smoke_meta.json into PoC console Conduct notes / lab LATEST.md
```

Dashboard:

```bash
.venv/bin/python benchmarking/dashboard/server.py
# → http://127.0.0.1:8765/#conduct
```

---

## 7. What this does *not* close

| Still open | Why |
|------------|-----|
| **CHANGE** | Needs real CI/CD or config audit → `change_near_onset` |
| Full CI-bind from live syslog hostnames | Lab smoke accepts `lab-*` / scrape labels |
| Panorama detect | No gray-failure corpus |
| Claiming LIVE Done in ROADMAP | Only after §5 meta exists from a real run |

---

## 8. Artifact index

| Path | Role |
|------|------|
| [`../ingestion-poc/vector/vector.live-syslog.toml`](../ingestion-poc/vector/vector.live-syslog.toml) | UDP syslog → ingest.v1 → F1 sinks |
| [`../ingestion-poc/vector/vector.live-prometheus.toml`](../ingestion-poc/vector/vector.live-prometheus.toml) | Prometheus scrape → ingest.v1 → F1 sinks |
| [`../ingestion-poc/compose/docker-compose.live.yml`](../ingestion-poc/compose/docker-compose.live.yml) | Optional compose profiles |
| [`../ingestion-poc/lab/live_smoke_verify.py`](../ingestion-poc/lab/live_smoke_verify.py) | Sink + meta checker |

*Prepared: 2026-07-24 — execute next week to mark LIVE Done.*
