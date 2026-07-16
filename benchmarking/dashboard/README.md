# Comparative evaluation dashboard

Static Web UI for comparative evaluation across **corpora** (ObserveOps UC · OpenObserve 29) and **engines** (Lean · Federated). OpenObserve platform narrative is a third *method* on the peer track.

1. **UC-1..UC-5** — designed GT bakeoff (Lean vs Federated): Accuracy, Repro, Verifiability, Efficiency
2. **OpenObserve 29** — peer agreement (Lean · Federated · OpenObserve); Option B convention Accuracy
3. **OpenObserve engine-pack bakeoff** — Lean vs Federated real engine runs on projected packs (wired to dashboard KPIs from `results/openobserve/engine_scoreboard.json`)

## Serve

**systemd (preferred):**

```bash
sudo systemctl enable --now unified-rca-dashboard.service
# open http://127.0.0.1:8765/
sudo systemctl restart unified-rca-dashboard.service   # after rebuild
```

**Ad-hoc:**

```bash
cd benchmarking/dashboard
python3 -m http.server 8765
# open http://127.0.0.1:8765/
```

## Refresh data

```bash
python3 benchmarking/benchmark/compare_openobserve.py
python3 benchmarking/benchmark/score_openobserve_gt.py   # Option B heuristic Accuracy
python3 benchmarking/benchmark/project_oo_engine_packs.py
.venv/bin/python benchmarking/benchmark/run_oo_engine_bakeoff.py
python3 benchmarking/benchmark/score_oo_engine_bakeoff.py
python3 benchmarking/dashboard/build_data.py
sudo systemctl restart unified-rca-dashboard.service
```
