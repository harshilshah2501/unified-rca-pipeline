"""SRE-facing report enrichment for Lean ObserveOps verdicts."""

from __future__ import annotations

from collections import deque

from core_engine.lean.invocation_graph import InvocationGraph

REMEDIATION_BY_SIGNATURE = {
    "cpu_contention": [
        "vMotion or rebalance affected VMs.",
        "Check DRS placement and find runaway workloads.",
        "Right-size vCPUs for contended VMs.",
    ],
    "link_failure": [
        "Restore or replace the affected link.",
        "Check redundant uplinks and NIC teaming.",
        "Find and mitigate the traffic-spike source.",
    ],
    "storage_contention": [
        "Storage vMotion the noisy VM or database workload.",
        "Apply SIOC or I/O limits to competing workloads.",
        "Check latency on the backing storage array.",
    ],
    "os_resource_exhaustion": [
        "Free or extend the affected filesystem.",
        "Kill or limit runaway processes and add memory or fix leaks.",
        "Restart the affected service after resource recovery.",
    ],
    "app_resource_exhaustion": [
        "Increase heap capacity or fix the memory leak.",
        "Tune connection and worker pools.",
        "Autoscale and check downstream dependencies.",
    ],
    "cross_numa_irq_affinity": [
        "Roll back NP-17 node image 2026.06.18 → 2026.05.30.",
        "Pin RX-queue IRQs to CPUs on the same NUMA node as NIC queue memory.",
        "Confirm AAAA DNS and checkout p99 return to baseline after rollback.",
    ],
}


def _downstream(graph: InvocationGraph, root_ci: str) -> dict[str, list[str]]:
    """Return cause→effect adjacency from the effect→cause invocation graph."""
    result: dict[str, list[str]] = {ci: [] for ci in graph.upstream}
    for effect, causes in graph.upstream.items():
        for cause in causes:
            result.setdefault(cause, []).append(effect)
    return result


def _shortest_downstream_path(
    graph: InvocationGraph, root_ci: str, symptom_ci: str, prefer: set[str] | None = None
) -> list[str] | None:
    """Find a topology path from root to symptom; prefer evidence-rich ties."""
    prefer = prefer or set()
    downstream = _downstream(graph, root_ci)
    queue: deque[list[str]] = deque([[root_ci]])
    visited = {root_ci}
    best: list[str] | None = None
    best_score = -1
    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == symptom_ci:
            score = sum(1 for ci in path if ci in prefer)
            if best is None or len(path) < len(best) or (
                len(path) == len(best) and score > best_score
            ):
                best = path
                best_score = score
            continue
        # Stop expanding beyond known shortest length once found.
        if best is not None and len(path) >= len(best):
            continue
        # Prefer exploring evidence-bearing dependents first.
        dependents = sorted(
            downstream.get(current, []),
            key=lambda ci: (0 if ci in prefer else 1, ci),
        )
        for dependent in dependents:
            if dependent not in visited:
                visited.add(dependent)
                queue.append([*path, dependent])
    return best


def _blast_radius(graph: InvocationGraph, root_ci: str) -> list[str]:
    """Compute affected dependents only from topology, never ground truth."""
    if graph.node_types.get(root_ci) == "Service":
        return [root_ci]

    downstream = _downstream(graph, root_ci)
    queue: deque[str] = deque(downstream.get(root_ci, []))
    visited: set[str] = set()
    affected: list[str] = []
    while queue:
        ci = queue.popleft()
        if ci in visited:
            continue
        visited.add(ci)
        affected.append(ci)
        queue.extend(downstream.get(ci, []))
    return affected


def build_sre_report(verdict: dict, bundle: dict) -> dict:
    """Add the UC section (e) operational fields to a Lean verdict."""
    graph = InvocationGraph.from_topology(bundle["topology"])
    seed_ci = bundle["symptom_seed"]["ci"]
    root_ci = verdict["root_ci"]
    prefer = {item["ci"] for item in verdict.get("evidence", [])}
    prefer.update(verdict.get("contributor_cis") or [])
    causal_chain = _shortest_downstream_path(graph, root_ci, seed_ci, prefer)
    if causal_chain is None:
        causal_chain = [root_ci] if root_ci == seed_ci else [root_ci, seed_ci]

    return {
        **verdict,
        "causal_chain": causal_chain,
        "blast_radius": _blast_radius(graph, root_ci),
        "remediation": REMEDIATION_BY_SIGNATURE.get(
            verdict["signature"],
            ["Inspect correlated evidence and mitigate the earliest failing CI."],
        ),
    }


def format_human_report(report: dict) -> str:
    """Render a compact Markdown report for on-call use."""
    evidence_lines: list[str] = []
    for item in report["evidence"]:
        if item.get("source") == "event" or item.get("message"):
            evidence_lines.append(
                f"- `{item['ci']}` — event `{item['signal']}` at {item['timestamp']}: "
                f"{item.get('message') or item.get('value')}"
            )
        else:
            evidence_lines.append(
                f"- `{item['ci']}` — `{item['signal']}` = `{item['value']}` at {item['timestamp']}"
            )
    evidence = "\n".join(evidence_lines) or "- No crossed anomaly evidence."
    blast_radius = ", ".join(report["blast_radius"]) or "No downstream dependents found."
    remediation = "\n".join(f"- {hint}" for hint in report["remediation"])
    contribs = report.get("contributor_cis") or []
    contrib_line = (
        ", ".join(f"`{c}`" for c in contribs) if contribs else "_none_"
    )
    care_note = (
        "CARE fallback fired; causal verification is "
        f"`{report['causal_verified']}`."
        if report["fallback_fired"]
        else "Direct topology and temporal evidence; CARE fallback did not fire."
    )
    return "\n".join(
        [
            f"# Lean RCA report — {report['uc_id']}",
            "",
            f"**Root:** `{report['root_ci']}`  ",
            f"**Signature:** `{report['signature']}`  ",
            f"**Contributors:** {contrib_line}",
            "",
            "## Causal chain",
            " → ".join(f"`{ci}`" for ci in report["causal_chain"]),
            "",
            "## Evidence",
            evidence,
            "",
            "## Blast radius",
            blast_radius,
            "",
            "## Remediation",
            remediation,
            "",
            "## Evidence quality",
            f"Tier {report['evidentiary_tier']}. {care_note}",
        ]
    )
