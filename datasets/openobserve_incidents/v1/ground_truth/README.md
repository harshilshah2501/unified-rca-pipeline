# OpenObserve Option B — convention GT

**Goal:** A **corpus-local scoring baseline** for Lean · Federated · OpenObserve on a stratified sample of the frozen 29.  
**Not:** platform `suggested_root_cause` as GT · not physical certainty · not all 29 required.

## Rubric (labelers)

For each sampled incident, open `incidents/<id>.json` + optional peer hints in the GT draft file. Fill **Label A** and **Label B** independently, then adjudicate.

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

| Method verdict | Hit if |
|----------------|--------|
| Layer accuracy | method `layer` == GT `root_layer` |
| Root-alert accuracy | method `root_alert` == GT `root_alert` |
| OpenObserve | same fields derived from platform narrative / title fallback (engine C) |

Ambiguous / `include_in_accuracy=false` → report separately; do not fold into the main accuracy % without calling it out.

## Sample (n=12)

See [`SAMPLE.json`](./SAMPLE.json) and per-incident drafts under this folder.  
Regenerate blank drafts: `python3 benchmarking/benchmark/init_oo_gt_sample.py`

## Status of this track

| Track | Mode |
|-------|------|
| UC-1..UC-5 | Designed GT bakeoff (already) |
| OpenObserve 29 peer | Agreement / behavior (no GT) |
| **This sample (n=12)** | **Option B finals populated** — solo dual-pass (`labeling_mode: solo_dual_pass` in `SAMPLE.json`); 10 accuracy-eligible, 2 ambiguous. Prefer independent human A/B when available. |

See [`SAMPLE.json`](./SAMPLE.json) for status / roots. When ready: score Lean · Federated · OpenObserve vs top-level `root_layer` / `root_alert` where `include_in_accuracy: true`.
