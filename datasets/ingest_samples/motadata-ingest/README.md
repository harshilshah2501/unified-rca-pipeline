# Motadata ingest output (derived)

| Artifact | Notes |
|----------|--------|
| `ci_bind.json` | Monitor id → host/object name (+ plugin fallbacks) — **commit OK** |
| `broaden_summary.json` | Last Lean Localize smoke (root + signature) |
| `incidents/motadata-apm-001/` | APM: ProductCatalog `http.error_rate` → `app_error_rate` (Bucket 1 symptom) |
| `incidents/motadata-deps-001/` | **Bucket 3:** ProductCatalog + hibernate dependency graph (GT root=ProductCatalog; hibernate contributor) |
| `incidents/motadata-ping-001/` … `ping-004/` | Infra ping / packet loss variants |
| `incidents/motadata-cpu-001/` | Infra: `Fluentbit` CPU → `host_cpu_saturation` |
| `incidents/motadata-multi-001/` | Harder multi-signal host (CPU+mem+ping) |
| `stream*.jsonl` / `span_metrics.jsonl` | **gitignored** when large; regenerate locally |
| `manifest.json` | Last convert stats |

```bash
# CI bind + all Motadata incidents → Lean (root + signature)
python3 ingestion-poc/adapters/build_motadata_incident.py

# Bucket-3 dependency pack only
python3 ingestion-poc/adapters/build_motadata_incident.py --incident motadata-deps-001

# Single incident
python3 ingestion-poc/adapters/build_motadata_incident.py --incident motadata-ping-001
```

Source dumps: [`../jsonl_resolved/`](../jsonl_resolved/). Tools: [`../../../ingestion-poc/adapters/README.md`](../../../ingestion-poc/adapters/README.md).
