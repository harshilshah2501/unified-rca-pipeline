# Cost report — L0 vs F1

**Run:** `cost-wsl-smoke`  
**Captured:** 2026-07-21T12:08:12Z  
**Host:** DESKTOP-MBPAQK1 · 2 CPU · None GiB · tier laptop

## Fairness contract

- Identical replay JSONL for L0 and F1.
- Only sink fan-out differs (L0 = lean; F1 = lean + structural + speed).
- GB/day is **extrapolated** from sink write rate (not retention-backed).
- Vector EPS includes container startup (conservative).

## Profile comparison

| Profile | Engine | Events | EPS | CPU-s / 1M evt | Sink bytes | GB/day (extrapolated) | Mean ingest ms |
|---------|--------|--------|-----|----------------|------------|----------------------|----------------|
| L0 | python_fanout | 50000 | 124706.44 | 8.23 | 11684997 | 2518.0318 | 0.0080 |
| F1 | python_fanout | 50000 | 115840.11 | 8.89 | 27165069 | 5437.6782 | 0.0086 |
## L0 → F1 delta (Python fan-out)

- EPS change: **-7.1%**
- Sink byte multiplier: **2.32×**
- Extra sinks: structural={'metric_sample', 'event', 'anomaly', 'trace_span'}, speed={'event', 'anomaly', 'trace_span'}

## Notes

- Headline ≥50K EPS gate is the **Dragonfly soak** (store path), not Vector/Python fan-out.
- RCA accuracy is measured separately (UC / Motadata bakeoff); this report is ingest cost only.
- Confidence: Python metrics = measured; GB/day = extrapolated; Vector EPS = measured wall incl. startup.
