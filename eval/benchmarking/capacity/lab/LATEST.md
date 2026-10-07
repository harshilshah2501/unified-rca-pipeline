# Lab EPS report

**Captured:** `2026-07-21T12:03:09Z`
**Hostname:** `DESKTOP-MBPAQK1`
**Tier:** `laptop` — WSL/laptop floor only — not for published 50K+ claims
**CPU / RAM:** 2 cores / 7.76 GiB

## Results

| Probe | EPS | Notes |
|-------|-----|-------|
| Dragonfly phase0 (Lua) | **27648.0** | p99=0.298 ms; workers=4; pipeline=128 |
| F1 Python fan-out | **128289.98** | events=20000 |
| N4 metric_slice read | **434144.33** rows/s | rows=13333; entities=50 |
| Speed→Dragonfly load | **9023.36** | rows=6667 |

## Headline eligibility

This host is **not** eligible for published ≥50K EPS claims. Re-run on `pro6000-server` and copy results into `federated-pipeline/docs/CAPACITY.md`.

## Reproduce

```bash
python3 ingestion-poc/lab/run_lab_eps.py
```

Artifacts: `benchmarking/capacity/lab/<run_id>/`


Run dir: `/root/Harshil-PoCs/Unified-RCA/benchmarking/capacity/lab/local-20260721T120309Z`
