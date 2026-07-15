# Comparative evaluation dashboard

Static Web UI for two tracks:

1. **UC-1..UC-5** — GT bakeoff (Lean vs Federated): accuracy, repro, axes, roadblocks
2. **OpenObserve 29** — **three-method peer** (Lean · Federated · OpenObserve platform RCA): agreement & behavior only — **no accuracy / GT claim**

## Serve

```bash
cd benchmarking/dashboard
python3 -m http.server 8765
# open http://127.0.0.1:8765/
```

## Refresh data

```bash
python3 benchmarking/benchmark/compare_openobserve.py
python3 benchmarking/dashboard/build_data.py
```
