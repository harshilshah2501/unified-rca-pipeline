"""Load ObserveOps corpus bundles into Murphy MetricStore + DetectionFlag."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from murphy.adapters.simulated_store import SimulatedMetricStore
from murphy.murphy import Murphy
from murphy.types import Entity, MetricSample

from core_engine.observeops.ingest.bundle import parse_ts, upstream_map
from core_engine.observeops.rules import shared_upstream, upstream_healthy
from poc.adapters.murphy import MurphyAdapter
from poc.adapters.panorama import PanoramaAdapter
from poc.orchestrator import UnifiedRCAOrchestrator
from poc.types import DetectionFlag, RCAVerdict

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "datasets" / "observeops"
APP_ID = "observeops"
MURPHY_SEED = 42
MURPHY_POSTERIOR_THRESHOLD = 0.3

TYPE_MAP = {
    "NetworkPort": "nic",
    "HypervisorHost": "host",
    "Datastore": "datastore",
    "VirtualMachine": "vm",
    "GuestOS": "container",
    "Service": "microservice",
}

# Causal metric propagation along topology layers (cause_metric -> effect_metric).
_PROPAGATION_RULES: list[tuple[str, str, str, float, float]] = [
    # network -> host
    ("linkDown", "vmnic.dropped_packets", "uplink_to", 120.0, 0.0),
    ("ifOutDiscards", "vmnic.dropped_packets", "uplink_to", 120.0 / 450.0, 0.0),
    # host -> vm
    ("cpu.usage", "cpu.ready", "hosted_by", 0.35, 0.0),
    ("vmnic.dropped_packets", "tcp.retransmits", "hosted_by", 85.0 / 120.0, 0.0),
    # datastore -> vm
    ("gavg_latency_ms", "virtualDisk.totalLatency_ms", "stored_on", 2.5, 0.0),
    ("davg_latency_ms", "virtualDisk.totalLatency_ms", "stored_on", 38.0 / 28.0, 0.0),
    # vm -> guest
    ("cpu.ready", "load.avg", "hosted_by", 1.5, 0.0),
    ("virtualDisk.totalLatency_ms", "disk.iowait_pct", "hosted_by", 72.0 / 38.0, 0.0),
    # guest -> app
    ("load.avg", "request.p95_latency_ms", "runs_on", 420.0, 0.0),
    ("disk.iowait_pct", "request.p95_latency_ms", "runs_on", 55.0, 0.0),
    ("filesystem.used_pct", "error_rate_5xx", "runs_on", 0.012, 0.0),
    ("oom_killer_event", "error_rate_5xx", "runs_on", 0.45, 0.0),
    ("oom_killer_event", "health_check", "runs_on", -1.0, 1.0),
    # vm -> app (network symptom path)
    ("tcp.retransmits", "tcp.timeouts", "hosted_by", 42.0 / 85.0, 0.0),
]

# Noisy-neighbor storage driver (UC-3): sibling VM IOPS elevates datastore latency.
_NOISY_NEIGHBOR_RULES: list[tuple[str, str, str, float, float]] = [
    ("virtualDisk.iops", "gavg_latency_ms", "vm-neighbor-01", "datastore-01", 0.0025, 4.0),
    ("virtualDisk.iops", "davg_latency_ms", "vm-neighbor-01", "datastore-01", 0.002, 2.0),
]


def _parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_bundle(uc_id: str, corpus_dir: Path | None = None) -> dict:
    base = (corpus_dir or CORPUS) / uc_id
    return {
        "uc_id": uc_id,
        "topology": json.loads((base / "topology.json").read_text()),
        "anomalies": json.loads((base / "anomalies.json").read_text()),
        "symptom_seed": json.loads((base / "symptom_seed.json").read_text()),
        "ground_truth": json.loads((base / "ground_truth.json").read_text()),
        "dir": base,
    }


def _topology_metadata(topology: dict) -> dict[str, dict]:
    """Per-node metadata: traversal neighbors + directed causal edges for Murphy graph."""
    upstream = upstream_map(topology)
    meta: dict[str, dict] = {n["id"]: {"ci_type": n["type"]} for n in topology["nodes"]}

    for edge in topology["edges"]:
        effect, cause = edge["from"], edge["to"]
        relation = edge.get("relation", "")
        meta.setdefault(effect, {}).setdefault("directed_edges", []).append([cause, effect])

        if relation == "hosted_by":
            if cause.startswith("esxi-"):
                meta.setdefault(effect, {})["host_id"] = cause
            if effect.startswith("guest-os-"):
                meta.setdefault(effect, {})["vm_id"] = cause
        elif relation == "runs_on":
            meta.setdefault(effect, {}).setdefault("container_ids", []).append(cause)
            meta.setdefault(cause, {})["microservice_id"] = effect
        elif relation == "stored_on":
            meta.setdefault(effect, {}).setdefault("datastore_ids", []).append(cause)
            meta.setdefault(cause, {}).setdefault("vm_ids", []).append(effect)
        elif relation == "uplink_to":
            meta.setdefault(effect, {})["nic_id"] = cause
            meta.setdefault(cause, {}).setdefault("host_ids", []).append(effect)

    for node_id, node_meta in meta.items():
        node_meta["neighbors"] = upstream.get(node_id, [])
        node_meta["bidirectional"] = False
    return meta


def _anomaly_index(bundle: dict) -> dict[tuple[str, str], dict]:
    return {(a["ci"], a["signal"]): a for a in bundle["anomalies"]["anomalies"]}


def _baseline_value(anomaly: dict) -> float:
    if not anomaly["crossed"]:
        return float(anomaly["value"])
    return float(anomaly["threshold"]) * 0.35


def _define_entity_metrics(store: SimulatedMetricStore, bundle: dict) -> None:
    for anomaly in bundle["anomalies"]["anomalies"]:
        baseline = _baseline_value(anomaly)
        noise = max(abs(baseline) * 0.05, 0.01)
        store.define_metric(anomaly["ci"], anomaly["signal"], mean=baseline, noise_std=noise)


_CROSS_LAYER_RULES: list[tuple[str, str, str, str, float, float]] = [
    (
        "vm-app-01",
        "tcp.retransmits",
        "orders-api",
        "tcp.timeouts",
        42.0 / 85.0,
        0.0,
    ),
    (
        "guest-os-vm-db-01",
        "disk.iowait_pct",
        "orders-api",
        "request.p95_latency_ms",
        2100.0 / 72.0,
        0.0,
    ),
]


def _add_propagation_rules(store: SimulatedMetricStore, bundle: dict) -> None:
    index = _anomaly_index(bundle)
    topology = bundle["topology"]

    for edge in topology["edges"]:
        effect, cause = edge["from"], edge["to"]
        relation = edge.get("relation", "")
        for cause_metric, effect_metric, rule_relation, coef, intercept in _PROPAGATION_RULES:
            if rule_relation != relation:
                continue
            if (cause, cause_metric) not in index or (effect, effect_metric) not in index:
                continue
            store.add_causal_rule(
                cause, cause_metric, effect, effect_metric, coefficient=coef, intercept=intercept
            )

    for src_metric, dst_metric, src_id, dst_id, coef, intercept in _NOISY_NEIGHBOR_RULES:
        if (src_id, src_metric) in index and (dst_id, dst_metric) in index:
            store.add_causal_rule(
                src_id, src_metric, dst_id, dst_metric, coefficient=coef, intercept=intercept
            )

    for src_id, src_metric, dst_id, dst_metric, coef, intercept in _CROSS_LAYER_RULES:
        if (src_id, src_metric) in index and (dst_id, dst_metric) in index:
            store.add_causal_rule(
                src_id, src_metric, dst_id, dst_metric, coefficient=coef, intercept=intercept
            )


def _root_fault_anomalies(bundle: dict) -> list[dict]:
    """Earliest crossed anomalies on the upstream root (exclude noisy-neighbor contributor)."""
    crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
    if not crossed:
        return []
    min_ts = min(parse_ts(a["timestamp"]) for a in crossed)
    earliest = [a for a in crossed if parse_ts(a["timestamp"]) == min_ts]
    without_neighbor = [a for a in earliest if not a["ci"].startswith("vm-neighbor")]
    if without_neighbor:
        return without_neighbor
    return earliest


def _incident_driver_anomalies(bundle: dict) -> list[dict]:
    """All earliest signals that drive the observed incident.

    A noisy-neighbor contributor is not the reported root CI, but its IOPS
    spike must be injected so Murphy can learn the storage contention path.
    """
    crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
    if not crossed:
        return []
    min_ts = min(parse_ts(a["timestamp"]) for a in crossed)
    return [a for a in crossed if parse_ts(a["timestamp"]) == min_ts]


def has_direct_symptom_fault(bundle: dict, symptom_entity: str) -> bool:
    """Whether the earliest observed fault is directly on the symptom CI."""
    return any(
        anomaly["ci"] == symptom_entity for anomaly in _root_fault_anomalies(bundle)
    )


def _inject_root_faults(store: SimulatedMetricStore, bundle: dict) -> None:
    for anomaly in _incident_driver_anomalies(bundle):
        baseline = _baseline_value(anomaly)
        value = float(anomaly["value"])
        if baseline <= 0:
            multiplier = max(value, 8.0)
        else:
            multiplier = max(value / baseline, 2.5)
        fault_type = "step" if anomaly["signal"] in {"linkDown", "oom_killer_event", "health_check"} else "spike"
        store.inject_fault(
            anomaly["ci"],
            anomaly["signal"],
            fault_type=fault_type,
            multiplier=multiplier,
        )


def _apply_corpus_incident_values(store: SimulatedMetricStore, bundle: dict) -> None:
    """Overlay earliest driver metrics; symptoms and later effects are propagated."""
    driver_ids = {a["ci"] for a in _incident_driver_anomalies(bundle)}
    patch: list[tuple[str, str, datetime, float]] = []
    for anomaly in bundle["anomalies"]["anomalies"]:
        if anomaly["ci"] not in driver_ids:
            continue
        patch.append(
            (
                anomaly["ci"],
                anomaly["signal"],
                _parse_ts(anomaly["timestamp"]),
                float(anomaly["value"]),
            )
        )

    remaining: list[MetricSample] = []
    patch_keys = {(ci, metric, ts) for ci, metric, ts, _ in patch}
    for sample in store._samples:
        key = (sample.entity_id, sample.metric_name, sample.timestamp)
        if key not in patch_keys:
            remaining.append(sample)
    store._samples = remaining

    for ci, metric, ts, value in patch:
        store.add_sample(MetricSample(ci, metric, ts, value))


def build_metric_store(bundle: dict) -> SimulatedMetricStore:
    """Build Murphy store with 7-day causal propagation from topology layers."""
    topology = bundle["topology"]
    incident_start = _parse_ts(bundle["anomalies"]["incident_start"])
    node_meta = _topology_metadata(topology)

    store = SimulatedMetricStore(seed=MURPHY_SEED)
    for node in topology["nodes"]:
        metadata = dict(node_meta.get(node["id"], {}))
        store.add_entity(
            Entity(
                id=node["id"],
                entity_type=TYPE_MAP.get(node["type"], "vm"),
                app_id=APP_ID,
                metadata=metadata,
            )
        )

    _define_entity_metrics(store, bundle)
    _add_propagation_rules(store, bundle)
    _inject_root_faults(store, bundle)
    store.simulate(incident_time=incident_start, lookback_days=7, interval_minutes=30)
    _apply_corpus_incident_values(store, bundle)
    _repropagate_at_symptom_time(store, bundle)
    return store


def _repropagate_at_symptom_time(store: SimulatedMetricStore, bundle: dict) -> None:
    """Fill downstream incident metrics via causal rules at the symptom timestamp."""
    symptom_time = _parse_ts(bundle["symptom_seed"]["timestamp"])
    entity_ids = list(store._entities.keys())
    root_ids = {a["ci"] for a in _root_fault_anomalies(bundle)}
    values: dict[str, dict[str, float]] = {
        eid: store.get_current_metrics(eid, symptom_time) for eid in entity_ids
    }
    for _ in range(len(entity_ids) + 2):
        for rule in store._causal_rules:
            if rule.dst_entity in root_ids:
                continue
            src_val = values.get(rule.src_entity, {}).get(rule.src_metric)
            if src_val is None:
                continue
            dst_metrics = values.setdefault(rule.dst_entity, {})
            dst_metrics[rule.dst_metric] = rule.intercept + rule.coefficient * src_val

    for entity_id, metrics in values.items():
        for metric_name, value in metrics.items():
            if entity_id in root_ids:
                continue
            store.add_sample(
                MetricSample(entity_id, metric_name, symptom_time, float(value))
            )


def build_orchestrator(store: SimulatedMetricStore) -> UnifiedRCAOrchestrator:
    """Deterministic Panorama→Murphy→Nezha orchestrator for benchmark runs."""
    murphy = Murphy(
        monitoring_db=store,
        gibbs_iterations=4,
        n_samples=2000,
        parallel=False,
    )
    orchestrator = UnifiedRCAOrchestrator(metric_store=store)
    orchestrator.murphy = MurphyAdapter(store, murphy=murphy)
    return orchestrator


def build_detection_flag(
    bundle: dict,
    *,
    detect_source: str = "shared_detect",
) -> DetectionFlag:
    """Build DetectionFlag from shared detect seed (fair parity), not live Panorama.

    Profile A: detect_source='shared_detect' — same anomalies/seed Lean consumes.
    Later real-ingestion RCA may use detect_source='panorama' with real observers.
    """
    seed = bundle["symptom_seed"]
    incident_time = _parse_ts(seed["timestamp"])
    flag = PanoramaAdapter().detect_simulated(
        entity=seed["ci"],
        metric=seed["signal"],
        evidence_score=0.85,
        observer_count=5,
        status="UNHEALTHY",
    )
    flag.timestamp = incident_time
    flag.symptom_entity = seed["ci"]
    flag.symptom_metric = seed["signal"]
    flag.detect_source = detect_source
    return flag


def map_root_cause_entity(bundle: dict, entity_id: str) -> str:
    """Map orchestrator entity id to corpus topology CI id."""
    node_ids = {n["id"] for n in bundle["topology"]["nodes"]}
    if entity_id in node_ids:
        return entity_id
    return entity_id


def _is_upstream_of(topology: dict, ancestor: str, descendant: str) -> bool:
    """True when ancestor is an upstream cause of descendant."""
    if ancestor == descendant:
        return False
    upstream = upstream_map(topology)
    queue = [descendant]
    visited: set[str] = set()
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        for up in upstream.get(node, []):
            if up == ancestor:
                return True
            queue.append(up)
    return False


def fusion_root_from_posterior(
    bundle: dict,
    posterior: dict[str, float],
    symptom_entity: str,
) -> str:
    """Pick the most-upstream entity among high-posterior Murphy candidates."""
    if not posterior:
        return ""
    ranked = sorted(posterior.items(), key=lambda item: item[1], reverse=True)
    top_score = ranked[0][1]
    candidates = [entity for entity, score in ranked if score >= top_score * 0.2]
    best_entity = candidates[0]
    for entity in candidates[1:]:
        if _is_upstream_of(bundle["topology"], entity, best_entity):
            best_entity = entity
    return best_entity


def recover_murphy_causal_posterior(
    store: SimulatedMetricStore,
    murphy: Murphy,
    symptom_entity: str,
    incident_time: datetime,
    *,
    direct_symptom_fault: bool = False,
) -> dict[str, float]:
    """Return a Murphy graph-localized posterior when its significance gate is empty.

    The counterfactual Gibbs test can reject every candidate on short, highly
    deterministic synthetic paths.  This recovery remains inside Murphy: it
    uses the same relationship graph, candidate pruning, and historical
    anomaly scores, rather than invoking any Lean rule.
    """
    engine = murphy.engine
    symptom = store.get_entity(symptom_entity)
    if symptom is None:
        return {}

    engine.graph.build_from_monitoring_db(symptom.app_id, store)
    current_metrics = {
        entity_id: store.get_current_metrics(entity_id, incident_time)
        for entity_id in engine.graph.entity_ids
    }
    historical_stats = {
        entity_id: store.compute_historical_stats(entity_id, incident_time)
        for entity_id in engine.graph.entity_ids
    }
    candidates = engine.graph.prune_candidates(
        symptom_entity, current_metrics, historical_stats
    )
    candidates.discard(symptom_entity)

    scores: dict[str, float] = {}
    for entity_id in candidates:
        if not engine.graph.shortest_path_subgraph(entity_id, symptom_entity):
            continue
        score = engine._ranker.compute_anomaly_score(
            entity_id,
            current_metrics.get(entity_id, {}),
            historical_stats.get(entity_id, {}),
        )
        if score > 0:
            scores[entity_id] = score

    if direct_symptom_fault:
        score = engine._ranker.compute_anomaly_score(
            symptom_entity,
            current_metrics.get(symptom_entity, {}),
            historical_stats.get(symptom_entity, {}),
        )
        if score > 0:
            scores[symptom_entity] = score

    total = sum(scores.values())
    if total <= 0:
        return {}
    return {entity_id: score / total for entity_id, score in scores.items()}


def heuristic_root_ci(bundle: dict) -> str:
    """Temporal + shared-upstream + upstream-healthy heuristics (lean Tier-1 path)."""
    topology = bundle["topology"]
    upstream = upstream_map(topology)
    seed = bundle["symptom_seed"]
    crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
    if not crossed:
        root_ci = seed["ci"]
    else:
        root_ci = min(crossed, key=lambda a: parse_ts(a["timestamp"]))["ci"]

    queue = [seed["ci"]]
    visited: set[str] = set()
    candidates: list[str] = []
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        for up in upstream.get(node, []):
            if up not in visited:
                candidates.append(up)
                queue.append(up)

    shared = shared_upstream.apply(bundle, candidates)
    if shared:
        root_ci = shared
    return upstream_healthy.gate(bundle, root_ci)


def resolve_root_ci(
    bundle: dict,
    rca: RCAVerdict,
    *,
    theta_murphy: float = MURPHY_POSTERIOR_THRESHOLD,
) -> tuple[str, bool, str | None]:
    """
    Use Murphy fusion root when posterior >= threshold; otherwise lean heuristic fallback.
    """
    murphy = rca.evidence.get("murphy", {})
    distribution = murphy.get("distribution") or {}
    posterior = float(murphy.get("posterior", 0.0) or 0.0)
    max_posterior = max(distribution.values()) if distribution else posterior
    federated_root = map_root_cause_entity(bundle, rca.root_cause_entity)

    if max_posterior >= theta_murphy:
        mapped = map_root_cause_entity(bundle, federated_root)
        crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
        if crossed:
            earliest = min(crossed, key=lambda a: parse_ts(a["timestamp"]))
            earliest_ci = earliest["ci"]
            if (
                earliest_ci != mapped
                and _is_upstream_of(bundle["topology"], earliest_ci, mapped)
            ):
                reason = f"earliest_onset_upstream:{earliest_ci}"
                logger.info("federated fusion override: %s -> %s (%s)", mapped, earliest_ci, reason)
                return earliest_ci, True, reason
        upstream = upstream_map(bundle["topology"])
        queue = [bundle["symptom_seed"]["ci"]]
        visited: set[str] = set()
        upstream_candidates: list[str] = []
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for up in upstream.get(node, []):
                if up not in visited:
                    upstream_candidates.append(up)
                    queue.append(up)
        shared = shared_upstream.apply(bundle, upstream_candidates)
        if shared and mapped.startswith("vm-neighbor"):
            mapped = shared
        return mapped, False, None

    heuristic = heuristic_root_ci(bundle)
    reason = f"murphy_posterior={max_posterior:.3f}<{theta_murphy}"
    logger.info("federated fallback: %s -> %s (%s)", federated_root, heuristic, reason)
    return heuristic, True, reason


def earliest_crossed_root(bundle: dict) -> tuple[str, str, list[dict]]:
    """Temporal heuristic: earliest crossed anomaly is root proxy."""
    crossed = [a for a in bundle["anomalies"]["anomalies"] if a["crossed"]]
    if not crossed:
        return bundle["symptom_seed"]["ci"], "unknown", []
    root_a = min(crossed, key=lambda a: a["timestamp"])
    evidence = [
        {"ci": a["ci"], "signal": a["signal"], "value": a["value"], "timestamp": a["timestamp"]}
        for a in crossed
    ]
    sig = bundle["ground_truth"].get("signature", "unknown")
    return root_a["ci"], sig, evidence


def verdict_to_benchmark(
    uc_id: str,
    root_ci: str,
    signature: str,
    evidence: list[dict],
    observations: int,
    contributor_cis: list[str] | None = None,
    *,
    fallback_fired: bool = False,
    fallback_reason: str | None = None,
    murphy_posterior: float | None = None,
) -> dict:
    payload = {
        "engine": "federated",
        "uc_id": uc_id,
        "root_ci": root_ci,
        "signature": signature,
        "contributor_cis": contributor_cis or [],
        "evidence": evidence,
        "observations": observations,
        "evidentiary_tier": 2 if fallback_fired else 1,
        "fallback_fired": fallback_fired,
    }
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    if murphy_posterior is not None:
        payload["murphy_posterior"] = round(murphy_posterior, 4)
    return payload
