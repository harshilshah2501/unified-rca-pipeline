# Ingestion PoC — shared front door

**Role:** turn telemetry into `ingest.v1`, run shared Detect, and (optionally) write Lean / Federated packs. This sits **before** Motadata Pillar A∥B writers and **before** the UC bakeoff engines diverge.

**Contract:** [`docs/INGEST_DATA_FORMAT.md`](../docs/INGEST_DATA_FORMAT.md) · design [`docs/INGESTION_PIPELINE_VECTOR.md`](../docs/INGESTION_PIPELINE_VECTOR.md)  
**Code map:** [`docs/CODE_GUIDE.md`](../docs/CODE_GUIDE.md) §5  
**Hygiene:** [`docs/REPO_HYGIENE.md`](../docs/REPO_HYGIENE.md) — large dumps stay local / gitignored

---

## Layout

| Path | Job |
|------|-----|
| [`replay/`](replay/) | ObserveOps UC bundles → `ingest.v1` (small, in git) |
| [`adapters/`](adapters/) | Motadata ClickHouse dumps → `ingest.v1` + incident packs (**needs local dumps**) |
| [`detect/`](detect/) | Shared threshold Detect → seeds |
| [`pipeline/`](pipeline/) | F1 smoke runner |
| [`builders/`](builders/) | Lean / Federated pack writers + `n45_chain` |
| [`vector/`](vector/) | Vector TOML skeletons (L0 / F1) |
| [`lab/`](lab/) | EPS / cost harness |
| `out/` | Runtime sinks (**gitignored**) |

```bash
# No Motadata dumps required — UC replay + Detect smoke
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all
PYTHONPATH=lean-pipeline:. python3 ingestion-poc/builders/n45_chain.py

# Motadata path — requires local jsonl_resolved/ (see below)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke
```

Pillar A∥B **lab fixtures** under `pillar-ab-implementation/*/poc/fixtures/` do **not** need these dumps.

---

## Local bulk dumps (why the tree is multi-GB)

These paths dominate disk. They are **gitignored on purpose**. Missing them does **not** break Lean UC bakeoff, docs hub, or Pillar unit tests.

| Path | Typical size | Needed for | Not needed for |
|------|--------------|------------|----------------|
| [`datasets/ingest_samples/jsonl_resolved/`](../datasets/ingest_samples/jsonl_resolved/) | **~4.3G** (`span.jsonl` alone ~3.8G) | Motadata adapters (`motadata_to_ingest_v1`, span metrics, incident builders, candidates) | ObserveOps UC replay, Pillar A/B `make test-all`, docs `:8765` |
| [`federated-pipeline/Nezha/rca_data/`](../federated-pipeline/Nezha/rca_data/) | **~2.8G** | Federated / Nezha comparator experiments | Motadata Pillar A∥B, ObserveOps UC bakeoff |
| [`datasets/nezha/`](../datasets/nezha/) | symlinks → Nezha trees | Same as Nezha | Same as Nezha |

**Gitignore (already set):** `.gitignore` lines for `datasets/ingest_samples/jsonl_resolved/*.jsonl`, `motadata-ingest/*.jsonl`, `federated-pipeline/Nezha/rca_data/`, `construct_data/`. **Do not commit or push** these files (GitHub 100MB limit).

### Motadata dump checklist

Place ClickHouse-resolved exports here (filenames the adapters expect):

```text
datasets/ingest_samples/jsonl_resolved/
  README.md                 ← tracked
  log.jsonl                 ← ~40M local
  metric_numeric.jsonl      ← ~300M local
  metric_string.jsonl       ← small
  trace.jsonl               ← ~120M local
  span.jsonl                ← ~3.8G local  (optional for metric-only smoke)
```

Details: [`datasets/ingest_samples/jsonl_resolved/README.md`](../datasets/ingest_samples/jsonl_resolved/README.md) · parent [`datasets/ingest_samples/README.md`](../datasets/ingest_samples/README.md).

If an adapter cannot find the dump, it exits with a short message pointing at this README (see `adapters/local_dumps.py`).

### Thin / CI path (no multi-GB lake)

| Goal | Use |
|------|-----|
| Ingest contract + Vector smoke | `datasets/ingest_samples/observeops-replay/` (in git) |
| Pillar A∥B writers | `pillar-ab-implementation/*/poc/fixtures/lab_checkout/` |
| Motadata L1 bakeoff packs already built | `datasets/ingest_samples/motadata-ingest/incidents/` (committed packs; rebuild needs dumps) |
| Full Motadata lake convert | Local `jsonl_resolved/` only |

There is **no** checked-in thin `span.jsonl` — CI should not download the Motadata lake.

---

## Quick commands

```bash
# ObserveOps → ingest.v1
python3 ingestion-poc/replay/observeops_to_ingest_v1.py --all

# Shared Detect on a replay stream
python3 ingestion-poc/detect/threshold_detect.py \
  --ingest-jsonl datasets/ingest_samples/observeops-replay/UC-1/stream.jsonl

# Motadata smoke (dumps required)
python3 ingestion-poc/adapters/motadata_to_ingest_v1.py --smoke

# F1 → packs → Lean root check
PYTHONPATH=lean-pipeline:. python3 ingestion-poc/builders/n45_chain.py
```

Per-area detail: [`adapters/README.md`](adapters/README.md) · [`replay/README.md`](replay/README.md) · [`detect/README.md`](detect/README.md) · [`builders/README.md`](builders/README.md) · [`vector/README.md`](vector/README.md) · [`lab/README.md`](lab/README.md) · [`pipeline/README.md`](pipeline/README.md).
