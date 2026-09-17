# Comparative evaluation + PoC console

Static Web UI for **ObserveOps UC** and **Motadata** bakeoffs (Lean · Federated), plus a **PoC Conduct** control plane to run Motadata broaden, UC bakeoff, lab EPS, and Motadata L1.

1. **Guide** — newcomer overview + interactive ingest / Lean·Federated pipeline widget
2. **Incident Analysis** — `#incident` — ObserveOps UC + Motadata L1 human reports (Lean / Fed / OO tabs)
3. **RCA workflow sim** — [`rca-workflow-sim.html`](../../docs/rca-workflow-sim.html) (`:8765/rca-workflow-sim.html`; source under `docs/reference/`) — shared Detect → Lean vs Federated (for “how”)
4. **Samples** — manual-verify strip (fault buckets · GT vs Lean vs Fed)
5. **PoC Conduct** — status rail + run jobs + live logs (requires `server.py`)
6. **Overview** — UC / Motadata L1 / lab EPS KPIs
7. **4 Axes · 5 Roadblocks · UC Bakeoff · Verdict** — comparative evaluation panels

Motadata L1 is a **Conduct job** and Overview KPI (not a separate TOC section).

OpenObserve peer / Option B metrics are **out of scope** for this PoC console (DOM retained but CSS-hidden; not part of the Motadata ingest story).

**Walkthrough:** [`../../docs/POC_DEMO_GUIDE.md`](../../docs/POC_DEMO_GUIDE.md)

**Hosted docs hub:** [`http://127.0.0.1:8765/docs.html`](http://127.0.0.1:8765/docs.html) · Unified pipeline workflow: [`/motadata-unified-pipeline-workflow.html`](http://127.0.0.1:8765/motadata-unified-pipeline-workflow.html) · Comparable DT vs DD: [`/comparable-pipeline-dt-dd.html`](http://127.0.0.1:8765/comparable-pipeline-dt-dd.html) · Fed vs DT gaps: [`/federated-vs-dt-pipeline-gaps.html`](http://127.0.0.1:8765/federated-vs-dt-pipeline-gaps.html)

## Serve (control plane)

**systemd (preferred — starts on boot):**

```bash
sudo cp benchmarking/dashboard/deploy/unified-rca-dashboard.service \
  /etc/systemd/system/unified-rca-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now unified-rca-dashboard.service
# open http://127.0.0.1:8765/
sudo systemctl restart unified-rca-dashboard.service   # after code updates
```

**Ad-hoc:**

```bash
# From repo root — binds 127.0.0.1:8765
.venv/bin/python benchmarking/dashboard/server.py
# open http://127.0.0.1:8765/
```

Optional env:

| Var | Meaning |
|-----|---------|
| `POC_DASHBOARD_TOKEN` | If set, require `X-PoC-Token` (or `?token=`) |
| `POC_SSH_HOST` | Default `pro6000-server` |
| `POC_REMOTE_REPO` | Default `/home/harshil/Projects/Unified-RCA` |

**API:** `GET /api/status` · `POST /api/jobs` · `GET /api/jobs/{id}/log` (SSE) · `GET /api/results/{motadata\|lab\|uc}`
