# Docs hub web portal — audit

**Status:** Phase E2+ integrity lock (2026-10-09).  
**Catalog:** [`HUB_CATALOG.yaml`](./HUB_CATALOG.yaml) (curated) · [`HUB_CATALOG.generated.yaml`](./HUB_CATALOG.generated.yaml) (crawl)  
**Tier lock:** [`observeops/OUR_HLD_TIER1.md`](./observeops/OUR_HLD_TIER1.md)  
**Repo audit:** [`REPO_AUDIT.md`](./REPO_AUDIT.md)

## What the portal is for **now**

Served at `http://127.0.0.1:8765/` (PoC console) and **`/docs.html`** (documentation index).

**Primary job:** Orient Motadata / ObserveOps readers on the **always-on fabric (E1–E5)** and **Pillar A ∥ Pillar B** contracts, then deepen via Fabric and Implementer I/O.

**Not the primary job (still hosted, demoted):**

- Per-category Dynatrace / Datadog / Edge Delta lab timelines (Tier 3 — site bar **Vendor survey**)
- Lean / Federated bakeoff sims (site bar **Bakeoff** · eval **reference**)
- Print/PDF A4 exports
- Pre-merge HTML under `observeops/_consolidated_sources/` (backup only)

## Entry points (post E2 slim)

| Entry | Role |
|-------|------|
| `/observeops-pipeline-hld.html` | **Door** — Overview · Workflow · GraphWriter · Diagnose |
| `/docs.html` ([`index.html`](./index.html)) | **Short ladder** — Tier 1 Everyone + Implementers + Vendor survey + Bakeoff |
| `/docs/fabric/README.md` | Fabric teaching index |
| `/hld-archive.html` | Searchable Tier 2/3 depth |
| `/` PoC console | Bakeoff UI — not Motadata product docs |

**Cold start:** Our HLD door → Tier 1 Everyone (#0 Workflow … #5 Glossary). Optional companion: ERROR + SLOWDOWN narration. Former `motadata-unified-pipeline-workflow.html` redirects to `#workflow`.

## Integrity lock (2026-10-09)

| Item | Status |
|------|--------|
| Tier 1 #0 = Workflow tab (not redirect stub) | Done |
| Index · OUR_HLD_TIER1 · HLD band · HUB_CATALOG agree | Done |
| GRAPH_QNA G25/G31 = `writer_stream.v1` presence | Done |
| GraphWriter SoT = hub `#graphwriter` (not stub HTML) | Done |
| Dashboard `fcd-*.svg` symlink depth | Fixed |
| `check_doc_drift.sh` scans GRAPH_QNA + OUR_HLD_TIER1 | Done |

## Target information architecture

| Layer | URL | Contents |
|-------|-----|----------|
| Door | `/observeops-pipeline-hld.html` | Overview · Workflow · GraphWriter · Diagnose · Fabric shortcuts |
| Docs home | `/docs.html` | Short Tier 1 ladder · I/O · Vendor survey · Bakeoff · archive |
| Fabric | `/docs/fabric/README.md` | Map / Vortex / simulations · knowledge-graph use cases |
| Vendor labs | DT / DD / ED hubs | Own timelines (site bar group) |
| Eval / Bakeoff | `/eval-reference.html` · Fed vs DT | Not Motadata product path |
| Archive | `/hld-archive.html` | Tier 2/3 search |

## Governance rule

No new link on `docs/index.html` without a row in [`HUB_CATALOG.yaml`](./HUB_CATALOG.yaml) (`hub_tier` / audience section).

## Crawl snapshot

Regenerate: `python3 scripts/repo_inventory.py --hub-write`
