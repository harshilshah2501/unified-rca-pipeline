# Repo hygiene — what to edit where (current stage)

**Stage:** Motadata Pillar A+B freeze + ObserveOps E1–E5 always-on fabric (2026-08-27).  
**Reading path:** [`NAVIGATION.md`](./NAVIGATION.md).

## Hub folder map (`docs/`)

Real articles live in topic folders. Flat names at `docs/<file>` are **compatibility symlinks** so `:8765` URLs and old bookmarks keep working.

**Edit topic folders only** (`fabric/`, `observeops/`, `motadata/`, `reference/`, `vendors/`). Do **not** create a second article that exists only as a flat `docs/<name>.html` with no topic-folder home — that grows the symlink farm and breaks GitHub nested browsing. After adding a topic-folder page, add a flat symlink if `:8765/<name>` must keep working.

| Folder | What belongs there |
|--------|-------------------|
| [`docs/`](./) (root only) | Hub spine: [`NAVIGATION.md`](./NAVIGATION.md), [`REPO_HYGIENE.md`](./REPO_HYGIENE.md), [`README.md`](./README.md), ingest contracts, roadmap, demo/code guides, `index.html` + hub JS |
| [`docs/fabric/`](./fabric/) | Motadata E1–E5 / Pillar A∥B teaching (deep dive, walkthrough, map/history/Vortex HTML) |
| [`docs/observeops/`](./observeops/) | Our HLD / Fusion / LLDs / FAC / glossary host CSS+JS |
| [`docs/motadata/`](./motadata/) | 3-pillars HTML + study / job-map markdown |
| [`docs/reference/`](./reference/) | Bakeoff / Lean–Federated / fault buckets / vendor-landscape notes (not Motadata lock list) |
| [`docs/vendors/`](./vendors/) | Dynatrace / Datadog / Edge Delta labs and production unveil pages |

## Canonical paths (edit these)

| Artifact | Edit here only |
|----------|----------------|
| Graph + sketch sit-down brief | [`pillar-ab-implementation/contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md`](../pillar-ab-implementation/contracts/GRAPH_CONTRACT_V1_DISCUSSION_BRIEF.md) (`docs/` is a symlink) |
| Fabric Q&A (E1–E5) | [`pillar-ab-implementation/contracts/GRAPH_QNA.md`](../pillar-ab-implementation/contracts/GRAPH_QNA.md) (`docs/GRAPH_QNA.md` is a symlink) |
| Node/edge samples | [`pillar-ab-implementation/contracts/GRAPH_NODE_EDGE_SAMPLES.md`](../pillar-ab-implementation/contracts/GRAPH_NODE_EDGE_SAMPLES.md) |
| JSON schemas | [`pillar-ab-implementation/contracts/schemas/`](../pillar-ab-implementation/contracts/schemas/) — **edit here only**. Do **not** keep package mirrors under `pillar-a|b/integration/contracts/schemas/`. Validators load this SoT path; `make check-schemas` / `scripts/check_schema_mirrors.py` fails if a mirror directory reappears. |
| Gate B / reject / map write prose | [`pillar-ab-implementation/contracts/`](../pillar-ab-implementation/contracts/) — link from packages; do not symlink-mirror prose under `*/contracts/` |
| Motadata kickoff scope | [`pillar-ab-implementation/scope/`](../pillar-ab-implementation/scope/) |
| Pillar A deep dive + fabric HTML | [`docs/fabric/`](./fabric/) |
| ObserveOps HLD / LLDs | [`docs/observeops/`](./observeops/) |
| Owner package **code** | [`pillar-a/poc/`](../pillar-ab-implementation/pillar-a/poc/), [`pillar-b/poc/`](../pillar-ab-implementation/pillar-b/poc/), [`integration/`](../pillar-ab-implementation/integration/) |

Owner-package `docs/` folders are **symlinks** into the paths above — do not replace them with real copies.

## Do not edit for the live hub

| Path | Why |
|------|-----|
| [`_archive/`](../_archive/) | Parked snapshots — not `:8765` |
| [`benchmarking/dashboard/`](../benchmarking/dashboard/) | Host + symlinks only — never a second article tree |
| [`_archive/pillar-ab-combined-poc-2026-08/`](../_archive/pillar-ab-combined-poc-2026-08/) | Former combined PoC — use `pillar-a` / `pillar-b` |
| Handoff `.zip` files | Rebuild after contract/doc changes; do not hand-edit insides |

## Handoff zip policy

1. Build from `pillar-a/` (or `pillar-b/`) **after** docs are clean.  
2. Exclude `.venv/`, `__pycache__/`, `*.pyc`, local `poc/out/`.  
3. Name with date: `pillar-a-handoff-YYYY-MM-DD.zip`.  
4. **Copy** needed JSON schemas from [`pillar-ab-implementation/contracts/schemas/`](../pillar-ab-implementation/contracts/schemas/) into the archive (or stage with `rsync -L` / explicit `cp`). Do not rely on package-local schema mirrors — those are forbidden in the monorepo.

## Local bulk (not day-to-day Motadata edit)

| Path | Typical size | Notes |
|------|--------------|--------|
| `datasets/ingest_samples/jsonl_resolved/` | **~4.3G** | Motadata ClickHouse dumps; `*.jsonl` gitignored. Needed only for Motadata adapters — see [`ingestion-poc/README.md`](../ingestion-poc/README.md) |
| `federated-pipeline/Nezha/rca_data/` | **~2.8G** | Nezha comparator telemetry; gitignored. Not Motadata Pillar A∥B |
| `datasets/nezha/` | symlinks | Points at Nezha trees; recreate links if missing ([`datasets/nezha/README.md`](../datasets/nezha/README.md)) |
| `*/.venv/` | hundreds of MB | Local; never commit or ship in handoff |

Missing Motadata dumps does **not** block ObserveOps UC bakeoff, Pillar unit tests, or the docs hub.

## Hub publish rule

Edit `docs/` or `pillar-ab-implementation/` only. Dashboard mounts them. See root [`README.md`](../README.md).
