# Docs hub web portal — audit

**Status:** Phase E0–E1 (2026-10-07).  
**Catalog:** [`HUB_CATALOG.yaml`](./HUB_CATALOG.yaml) (curated) · [`HUB_CATALOG.generated.yaml`](./HUB_CATALOG.generated.yaml) (crawl)  
**Tier lock:** [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md)  
**Repo audit:** [`REPO_AUDIT.md`](./REPO_AUDIT.md)

## What the portal is for **now**

Served at `http://127.0.0.1:8765/` (PoC console) and **`/docs.html`** (documentation index).

**Primary job:** Orient Motadata / ObserveOps readers on the **always-on fabric (E1–E5)** and **Pillar A ∥ Pillar B** contracts, then deepen via Fabric and Implementer I/O.

**Not the primary job (still hosted, demoted):**

- Per-category Dynatrace / Datadog / Edge Delta lab timelines (Tier 3 — live under vendor hubs)
- Cursor **agent-task** prompts for unfinished MCP pulls
- Lean / Federated bakeoff sims (eval **reference**)
- Print/PDF A4 exports

## Entry-point conflict (W10)

| Entry | Problem |
|-------|---------|
| `/docs.html` ([`index.html`](./index.html)) | Mega-scroll: Tier 1 + all vendor cards + fabric farm + eval |
| `/observeops-pipeline-hld.html` | Correct **door** per Tier 1 — under-linked as sole cold start |
| `/hld-archive.html` | Useful search, but duplicates Tier 1 and mixes stale `fact_kind` row copy |
| `/docs/NAVIGATION.md` | Long reading path — keep as lookup, not first screen |
| `/` PoC console | Bakeoff UI — must not look like Motadata product docs |

**Target:** Cold start = **Our HLD door** → Tier 1 six pages. `docs.html` becomes a **short ladder** + pointers.

## Clutter taxonomy (W11)

| Bucket | Paths | Action |
|--------|-------|--------|
| Past agent tasks | [`agent-tasks/`](./agent-tasks/) | Move → `_archive/hub/agent-tasks/`; symlink shim for one cycle |
| Vendor lab depth | `dd-lab-timeline-*`, `dt-cat-*`, MTL dissections | Keep files; surface only from DT/DD/ED hubs |
| Eval / engines | `rca-workflow-sim.html`, Federated gap cards on index | One [`eval-reference.html`](./reference/eval-reference.html) entry |
| Stale wire story | Index cards saying `ingest.v1` as Motadata router | Banner + WRITER_REGULATOR link |
| Redirect HTML | [`observeops/_consolidated_sources/`](./observeops/_consolidated_sources/) | Delist from archive TOC if already redirected |
| Print exports | [`print/`](./print/) | Tier 3 only |
| Fabric link farm | Index §4 (15+ bullets) | Collapse to [`fabric/README.md`](./fabric/README.md) / fabric index |

## Crawl snapshot

Regenerate: `python3 scripts/repo_inventory.py --hub-write`

| Metric | Value (2026-10-07) |
|--------|---------------------|
| Pages reachable from seeds | ~144 |
| Auto-tagged hub Tier 1 | few (classifier under-counts — curated catalog fixes) |
| `move-to-archive` candidates | agent-tasks + orphans |

## Target information architecture

| Layer | URL | Contents |
|-------|-----|----------|
| Door | `/observeops-pipeline-hld.html` | Overview · Workflow · GraphWriter · Diagnose · Fabric shortcuts |
| Docs home | `/docs.html` | Short Tier 1 ladder · I/O chain · vendor hub cards · eval reference · archive |
| Fabric | `/docs/fabric/README.md` | Map / Vortex / simulations |
| Vendor labs | DT / DD / ED hubs | Own timelines and lab refs |
| Eval reference | `/eval-reference.html` | Lean/Fed / ADR-001 / E-com — not Motadata path |
| Archive | `/hld-archive.html` | Tier 2/3 search |

## Governance rule (after slim)

No new link on `docs/index.html` without a row in [`HUB_CATALOG.yaml`](./HUB_CATALOG.yaml) (`hub_tier` + `audience`).
