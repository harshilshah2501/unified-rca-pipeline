# Vendor RCA benchmarks — Datadog & Dynatrace

**Status:** Research note for PoC evaluation discipline (2026-07-22)  
**Related:** [`FAULT_BUCKET_COVERAGE.md`](./FAULT_BUCKET_COVERAGE.md) · [`Lean_RCA_PRD.md`](./Lean_RCA_PRD.md) Appendix E · [`RCA_Vendor_Comparison_NOTES.md`](./RCA_Vendor_Comparison_NOTES.md)

---

## Short answer

**Datadog and Dynatrace do not publish a public, reproducible RCA accuracy bakeoff** you can put next to our UC / Motadata scoreboard.

There is no frozen vendor corpus + shared GT + top-1 / AC@k number released for Davis or Watchdog-style RCA that third parties can re-run. Public material is product marketing, case studies, and operational proxies (MTTR, noise reduction) — not an open scoreboard.

---

## What vendors *do* use (as far as public evidence goes)

| Kind | Datadog / Dynatrace practice | Usable as competitor score? |
|------|------------------------------|-----------------------------|
| Sales / customer metrics | MTTR, alert volume, “time to root cause” anecdotes | No — not controlled GT |
| Internal red-team / synthetic inject | Likely (opaque) | No — not published |
| Product demos | Scripted happy paths | No |
| Academic-style AC@k on open corpus | **Not published** for these products | — |

**Implication for decks:** Cite Dynatrace Davis as *causal / topology-first packaging AI* (default Problem path) and Datadog as *evidence-first fabric + separable Watchdog ML Detect + optional Bits agent* — not as measured top-1 rivals, and **not** as “Datadog has more AI.” Same discipline as Lean PRD Appendix E. See [`COMPARABLE_PIPELINE_DT_DD.md`](./COMPARABLE_PIPELINE_DT_DD.md) §0.4.

---

## What *is* citeable for RCA evaluation (academia)

Use these when stakeholders ask “what do people use as benchmarks?” — not as DD/DT numbers:

| Resource | What it measures | Notes |
|----------|------------------|-------|
| **RCAEval** ([arxiv](https://arxiv.org/html/2412.17015v3), FSE’25 companion) | Coarse (service) + fine (indicator) RCA; **AC@k**, **Avg@k** on telemetry corpora | Open framework + baselines |
| Fault-propagation-aware microservice corpora (e.g. recent arXiv eval papers) | Inject → multi-signal → ranked root | Stronger causal chains than classic single-hop injects |

Our ObserveOps convention is closer to **root_ci + signature match on frozen packs** — transparent and re-runnable. Optionally map to AC@1 language (“fraction of incidents where top root equals GT”) when talking to research audiences.

---

## Our PoC contract (keep this)

1. **Frozen pack** (`stream` + `topology` + `ground_truth`).
2. **Human GT** (`root_ci`, `signature`, now also `fault_bucket` / `fault_type`).
3. **Engine output** vs GT (Lean + Federated).
4. **Manual sample review** on the dashboard Samples strip — automation flags mismatches; humans confirm evidence.

Do **not** invent a fake “Datadog scored X% on our corpus” claim without a licensed/partner eval.

---

## Tomorrow / follow-ups (optional)

- One-slide table: Vendor public eval = none; Our eval = UC 5/5 + Motadata 7/7 + sample cards.
- If a customer later demands vendor parity numbers: design a **joint frozen lab** (same injects, same GT) — out of current PoC scope.
