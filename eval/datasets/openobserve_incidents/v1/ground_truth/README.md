# OpenObserve Option B — convention GT

**Goal:** A **corpus-local Accuracy baseline** for the OpenObserve 29 scenarios (`root_layer` + `root_alert`).  
**Not:** platform `suggested_root_cause` as GT · not physical certainty.

## Framing

| Term | Meaning |
|------|---------|
| **Corpus / scenarios** | ObserveOps UC-1..UC-5 and OpenObserve 29 — two scenario sets |
| **Engines** | Lean and Federated (same code paths on both corpora when packs exist) |
| **OpenObserve platform** | Third *method* (narrative) on the peer track — not an engine pack |

Two OpenObserve evaluation surfaces (do **not** merge into one X/34 accuracy fraction):

1. **Convention Accuracy (alert heuristics)** — `score_openobserve_gt.py` scores Lean/Fed/OO principle analyzers vs these labels.
2. **Engine pack bakeoff** — project incidents → ObserveOps-shaped packs under [`../engine_packs/`](../engine_packs/), run real Lean/Federated, score `root_ci` vs Option B `root_alert` ([`ENGINE_SCOREBOARD.md`](../../../benchmarking/results/openobserve/ENGINE_SCOREBOARD.md)).

## Rubric (labelers)

For each incident, open `incidents/<id>.json` + optional peer hints in the GT file. Fill **Label A** and **Label B** independently, then adjudicate.

| Field | Rule |
|-------|------|
| `root_layer` | One of: firewall, network, storage, database, dns, filesystem, application, compute, unknown |
| `root_alert` | Prefer an alert name present on the incident. If only a CI/host is known, use that string consistently. |
| `confidence` | `confident` = clear single root · `ambiguous` = underdetermined · `multi-cause` = two+ co-equal causes |
| `include_in_accuracy` | `true` only for `confident` (and adjudicated `multi-cause` if you define a primary). Default `false` for ambiguous. |
| `evidence_note` | 1–3 sentences: evidence for root + decoys rejected (e.g. “title CPU is symptom; disk_io co-fire”). |
| **Do not** | Copy OpenObserve narrative or Lean/Fed outputs as the label without independent reasoning. |

### Dual-label process

1. Labeler A fills `labels.A` only.  
2. Labeler B fills `labels.B` only (no peeking).  
3. If A and B match on `(root_layer, root_alert)` → copy into top-level fields, `status: final`.  
4. Else → `status: conflict`, fill `adjudication`, then set top-level + `status: final` (or `excluded`).

### Scoring policy (once `final`)

| Track | Hit if |
|-------|--------|
| Heuristic Lean/Fed/OO | method `layer` / `root_alert` vs GT |
| Engine packs Lean/Fed | `verdict.root_ci` == GT `root_alert` (pack maps it to `root_ci`) |

Ambiguous / `include_in_accuracy=false` → report separately; do not fold into the main accuracy % without calling it out.

## Status

| Track | Mode |
|-------|------|
| UC-1..UC-5 | Designed GT bakeoff (4 pillars) |
| OpenObserve 29 peer | Agreement / behavior (`compare_openobserve.py`) — no GT claim |
| **Option B labels (n=29 · 24 eligible)** | Convention Accuracy + engine-pack Accuracy target |
| Engine packs | [`../engine_packs/`](../engine_packs/) — regenerate with `project_oo_engine_packs.py` |

See [`SAMPLE.json`](./SAMPLE.json) for status / roots.
