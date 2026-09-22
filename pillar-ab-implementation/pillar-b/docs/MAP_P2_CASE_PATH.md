# P2 stub harness — CaseSeed → WorkingSet → LeafClaim

**Doc job:** Optional **drivers** that exercise walk-through APIs with diagnose-shaped names.  
**Not the PoC mission.** Core knowledge-graph use cases → [Pillar B PoC Navigator canvas](../reference/canvases/pillar-b-poc-navigator.canvas.tsx) · [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md).

**Stance:** Detect storm / Curate / Scope / Localize are **stubbed**. They do not write `map/`. They call `neighbors` / `reachable_ci_ids` / `find_paths` so we can demo a seed → neighborhood → leaf path without owning Detect or sketches.

**Run proofs:**

```bash
cd pillar-ab-implementation/pillar-b/poc
make test-all
# Stub harness: graph/tests/unit/test_case_path.py
```

---

## Vocabulary (do not blur)

| Term | Meaning | Not |
|------|---------|-----|
| **Signal** | E6 Detect emission — something is wrong | Not root cause |
| **CaseSeed** | E7 Curate tip — one merged case (D3) | Not estate bootstrap; does not write `map/` |
| **WorkingSet** | E8 Scope package — seed + map neighborhood (+ optional sketch refs) | Not a Dest room; not folder sync |
| **LeafClaim** | E9 Localize tip — where to look next | Not VerdictCard / Package |

Join key remains `tenant` + `ci_id` (sketch `entity_id` ≡ graph `ci_id` when sketches are attached).

---

## Pipeline spine (this increment)

```text
published GraphSnapshot (Part A)
        ▲
Signal storm ──curate_storm──► CaseSeed ──build_working_set──► WorkingSet ──localize_leaf──► LeafClaim
                                     │                              │
                              never writes map/              uses Part B walks
```

| Stage | Module | Proof |
|-------|--------|-------|
| E7 Curate | [`../poc/graph/case_path/curate.py`](../poc/graph/case_path/curate.py) | One seed from storm; prefer tip CI; merge rationale |
| E8 Scope | [`../poc/graph/case_path/scope.py`](../poc/graph/case_path/scope.py) | Reachable CIs, edges, paths to Host/Database; optional sketch hook |
| E9 Localize | [`../poc/graph/case_path/localize.py`](../poc/graph/case_path/localize.py) | Deepest Database leaf (teaching); Host fallback; prefer_ci lab override |

---

## Teaching golden (customer_checkout)

| Artifact | Path |
|----------|------|
| Storm | [`../poc/sample_estate/customer_checkout/cases/increment2/signal_storm.json`](../poc/sample_estate/customer_checkout/cases/increment2/signal_storm.json) |
| Expected spine | [`../poc/sample_estate/customer_checkout/cases/increment2/expected_case_path.json`](../poc/sample_estate/customer_checkout/cases/increment2/expected_case_path.json) |
| Map under test | Case A bootstrap + `stream.resolved.jsonl` → `publish_map` |

| Check | Expected |
|-------|----------|
| CaseSeed tip | `checkout-api` / `ERROR` |
| WorkingSet includes | checkout-api, payments-db, linux-server-app-01, bs-checkout |
| LeafClaim | `payments-db` path `[checkout-api, payments-db]` |
| Confidence filter | Hard-downgrade all edges into payments-db → no Database path → Host fallback |

---

## Related

- Part A/B walk: [`MAP_P1_FABRIC_EVAL.md`](./MAP_P1_FABRIC_EVAL.md)  
- Code tour: [`Codebase-go-through.md`](./Codebase-go-through.md)  
- Integration sketch join: [`../../integration/README.md`](../../integration/README.md)  
- Fabric locks: [`../../../docs/fabric/SIMULATION_THREAD.md`](../../../docs/fabric/SIMULATION_THREAD.md) Increment 2  
