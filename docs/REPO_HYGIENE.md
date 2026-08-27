# Repo hygiene — what to edit where (current stage)

**Stage:** Motadata Pillar A+B freeze + ObserveOps E1–E5 always-on fabric (2026-08-27).  
**Reading path:** [`NAVIGATION.md`](./NAVIGATION.md).

## Hub folder map (`docs/`)

Real articles live in topic folders. Flat names at `docs/<file>` are **compatibility symlinks** so `:8765` URLs and old bookmarks keep working.

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
| JSON schemas | [`pillar-ab-implementation/contracts/`](../pillar-ab-implementation/contracts/) (mirrored into packages for tests) |
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

1. Build from `pillar-a/` (or `pillar-b/`) **after** docs are symlink-clean.  
2. Exclude `.venv/`, `__pycache__/`, `*.pyc`, local `poc/out/`.  
3. Name with date: `pillar-a-handoff-YYYY-MM-DD.zip`.  
4. Zip should resolve teaching docs via package `docs/` symlinks (or include the linked files when archiving — `zip -y` keeps symlinks; prefer including content with `zip -r` following links for teammate machines without the monorepo).

**Preferred teammate zip:** follow symlinks so the archive is self-contained (`zip -r --symlinks` off / use `rsync -L` into a staging dir, then zip).

## Local bulk (not day-to-day Motadata edit)

| Path | Notes |
|------|--------|
| `datasets/ingest_samples/` | Large dumps (~GBs); gitignored patterns already |
| `federated-pipeline/Nezha/` | Vendor tree; bakeoff comparator only |
| `*/.venv/` | Local; never commit or ship in handoff |

## Hub publish rule

Edit `docs/` or `pillar-ab-implementation/` only. Dashboard mounts them. See root [`README.md`](../README.md).
