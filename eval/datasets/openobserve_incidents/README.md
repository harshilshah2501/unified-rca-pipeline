# OpenObserve incident corpus (evaluation)

Frozen snapshot of live alerts/incidents for comparative RCA beyond ObserveOps UC-1..UC-5.

| Path | Contents |
|------|----------|
| `v1/list.json` | Incident list |
| `v1/alerts.json` | Alert definitions |
| `v1/incidents/*.json` | Full incident payloads (triggers, topology_context, platform RCA narrative) |
| `v1/ground_truth/` | **Option B** convention GT (stratified sample, dual-label) |

**Credentials are not stored here.** Refresh with:

```bash
export OPENOBSERVE_URL=http://172.16.14.77:5080
export OPENOBSERVE_USER='...'
export OPENOBSERVE_PASSWORD='...'
python3 benchmarking/benchmark/fetch_openobserve_incidents.py --out datasets/openobserve_incidents/v1
```

## Evaluation modes

| Mode | What |
|------|------|
| **Peer (default)** | Lean · Federated · OpenObserve agreement/behavior — no accuracy claim. `python3 benchmarking/benchmark/compare_openobserve.py` |
| **Option B convention GT** | Human dual-label on n=12 sample → later score all three vs labels. See [`v1/ground_truth/README.md`](v1/ground_truth/README.md) |

**Important:** `topology_context.suggested_root_cause` is **OpenObserve method output**, not GT. Do not score Lean/Fed against it as accuracy.

## Start Option B labeling

```bash
python3 benchmarking/benchmark/init_oo_gt_sample.py   # (re)create pending drafts
# then two labelers fill labels.A / labels.B independently in each ground_truth/<id>.json
```

## Caveats

- Topology edges are sparse; not a classic VMware typed CI inventory.
- Many scenarios are microservice / cloud / payment-gateway style, wider than UC-1..UC-5.
