# P3 stub harness — EvidenceBundle → VerdictCard

**Doc job:** Optional **lab close** stubs after a leaf path is chosen.  
**Not the PoC mission.** Core knowledge-graph use cases → [Pillar B PoC hub](../../../docs/fabric/pillar-b-poc-hub.html). Prior stub → [`MAP_P2_CASE_PATH.md`](./MAP_P2_CASE_PATH.md).

**Stance:** Identify / Package evidence and narrative are **assumed or stubbed** (default lab evidence, no live ticket create). Useful only to show “walk found a leaf → operator-shaped card.” Graph truth still comes from build/maintain + walk.

**Run proofs:**

```bash
cd pillar-ab-implementation/pillar-b/poc
make test-all
# Stub harness: graph/tests/unit/test_identify_package.py
```

---

## Vocabulary

| Term | Meaning | Not |
|------|---------|-----|
| **Identify (E10)** | Build multimodal `EvidenceBundle` for the leaf | Not E2 Identity / Normalize |
| **EvidenceBundle** | Metrics / logs / traces / changes / topology refs + confidence tier | Not raw lake dump |
| **Package (E11)** | Operator `VerdictCard` (D4 required) | Not optional narrative-only close |
| **Verify** | Confidence judgment inside E10, locked on the E11 card | Not a separate E-stage |

---

## Spine

```text
LeafClaim ──build_evidence_bundle──► EvidenceBundle ──package_verdict──► VerdictCard
              (lab stubs or provider)                    (D4 card + optional narrative)
```

| Stage | Module | Proof |
|-------|--------|-------|
| E10 | [`../poc/graph/case_path/identify.py`](../poc/graph/case_path/identify.py) | Bundle has metrics/logs/traces/topology; changes may be empty; tier + weakest channel |
| E11 | [`../poc/graph/case_path/package.py`](../poc/graph/case_path/package.py) | VerdictCard summary, blast, actions, ServiceOps handoff `ci_id`, narrative optional |

---

## Teaching golden

| Artifact | Path |
|----------|------|
| Expected | [`../poc/sample_estate/customer_checkout/cases/stub_diagnose_close/expected_verdict.json`](../poc/sample_estate/customer_checkout/cases/stub_diagnose_close/expected_verdict.json) |
| Upstream storm | stub case-path harness `cases/stub_case_path/signal_storm.json` |

| Check | Expected |
|-------|----------|
| Root CI | `payments-db` / Database |
| Path | `checkout-api → payments-db` |
| Confidence tier | `2` (changes empty → weakest=`changes`) |
| Handoff | `serviceops_handoff.ci_id = payments-db` (no live ticket id) |

---

## Related

- Fabric film 2 (plays through Localize only): [`../../../docs/fabric/edge-platform-case-simulation.html`](../../../docs/fabric/edge-platform-case-simulation.html)  
- Simulation locks: [`../../../docs/fabric/SIMULATION_THREAD.md`](../../../docs/fabric/SIMULATION_THREAD.md)  
