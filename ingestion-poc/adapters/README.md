# Motadata → ingest.v1 adapter (+ depth / broaden)

Converts local Motadata dumps in `datasets/ingest_samples/jsonl_resolved/` (gitignored large files, ~4.3G) into `ingest.v1` JSONL.

**Dump policy / when dumps are optional:** [`../README.md`](../README.md) · helper [`local_dumps.py`](local_dumps.py) (clear exit if dumps missing).

## Depth / broaden tools

| Script | Role |
|--------|------|
| [`build_motadata_ci_bind.py`](build_motadata_ci_bind.py) | `object.name` / `system.name` / plugin fallback → `ci_bind.json` |
| [`motadata_threshold_catalog.json`](motadata_threshold_catalog.json) | Default Detect thresholds (ping/cpu/mem/http.error_rate) |
| [`motadata_span_metrics.py`](motadata_span_metrics.py) | Spans → per-minute `http.error_rate` / duration metrics |
| [`build_motadata_topology.py`](build_motadata_topology.py) | APM stub topology (services + host) — fallback only |
| [`build_motadata_inventory_topology.py`](build_motadata_inventory_topology.py) | **Inventory** from `ci_bind` + span `runs_on` → `topology.json` (+ incident subgraphs) |
| [`motadata_incident_lib.py`](motadata_incident_lib.py) | Shared extract / pack / diagnose helpers |
| [`build_motadata_incident.py`](build_motadata_incident.py) | **Broaden:** APM + ping + CPU incidents → Lean (stamps `fault_bucket` via taxonomy) |
| [`propose_motadata_candidates.py`](propose_motadata_candidates.py) | **A1:** scan lake for threshold-crossing **candidates** (no GT) → `candidate_windows.md` |

Fault tags (all corpora): [`../../benchmarking/benchmark/tag_corpus_fault_buckets.py`](../../benchmarking/benchmark/tag_corpus_fault_buckets.py) · [`FAULT_BUCKET_COVERAGE.md`](../../docs/FAULT_BUCKET_COVERAGE.md)

```bash
# A1 — propose new Motadata windows (human still writes GT)
python3 ingestion-poc/adapters/propose_motadata_candidates.py
# → datasets/ingest_samples/motadata-ingest/candidate_windows.md

# Inventory topology (full graph + refresh pack subgraphs)
python3 ingestion-poc/adapters/build_motadata_inventory_topology.py --refresh-incidents

# All Motadata incidents (APM + ping + CPU) — Localize root + I1 signature
python3 ingestion-poc/adapters/build_motadata_incident.py

# Lean diagnose one pack
OBSERVEOPS_CORPUS=datasets/ingest_samples/motadata-ingest/incidents \
  PYTHONPATH=lean-pipeline:. python3 -m lean_rca diagnose motadata-ping-001 --format report
```

### Incident packs (GT)

| ID | Root CI | Signature (I1) |
|----|---------|----------------|
| `motadata-apm-001` | `ProductCatalog_dotnet.` | `app_error_rate` |
| `motadata-ping-001` | `dlink-48` | `ping_degradation` |
| `motadata-ping-002` | `Netgear Switch` | `ping_degradation` (A1 **human-confirmed**) |
| `motadata-ping-003` | `proxmox-ve-129` | `ping_degradation` (A1 **human-confirmed**) |
| `motadata-ping-004` | `localhost.localdomain` | `ping_degradation` (A1 **human-confirmed**) |
| `motadata-cpu-001` | `Fluentbit` | `host_cpu_saturation` |
| `motadata-multi-001` | `HB1-…-735.hb1.com` | `host_cpu_saturation` (A1 harder; **human-confirmed**) |
| `motadata-deps-001` | `ProductCatalog_dotnet.` (+ hibernate contributor) | `app_error_rate` (**Bucket 3**; authored — confirm `#samples`) |

## Base convert

```bash
# Smoke (applies ci_bind.json + threshold catalog when present)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke

# Append span-derived metrics for Detect
python3 ingestion-poc/adapters/motadata_span_metrics.py --smoke
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke \
  --append-span-metrics datasets/ingest_samples/motadata-ingest/span_metrics.jsonl
```

**Output:** `datasets/ingest_samples/motadata-ingest/` (`stream*.jsonl` gitignored; `ci_bind.json`, `incidents/`, `manifest.json` OK to commit)

| Source | → fact_kind | ci_id |
|--------|----------------|-------|
| `log.jsonl` | `event` | hostname / `event_source` |
| `metric_numeric.jsonl` | `metric_sample` + **threshold** | bound name or `monitor-{id}` |
| `metric_string.jsonl` | `event` | bound name or `monitor-{id}` |
| `trace.jsonl` / `span.jsonl` | `trace_span` | service name |
| span-derived | `metric_sample` (`http.error_rate`, …) | service name |

Contract: [`docs/INGEST_DATA_FORMAT.md`](../../docs/INGEST_DATA_FORMAT.md)
