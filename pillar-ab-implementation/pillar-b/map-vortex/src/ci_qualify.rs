//! CI vs observation qualification for map vertices (Motadata CI-only).
//!
//! Port of ``poc/graph/ci_qualify.py``.

use std::collections::HashSet;
use std::sync::LazyLock;

/// Ingest PascalCase → Motadata storage ``type``.
static INGEST_TO_STORAGE: LazyLock<Vec<(&'static str, &'static str)>> = LazyLock::new(|| {
    vec![
        ("Service", "service"),
        ("Host", "host"),
        ("Pod", "pod"),
        ("Container", "container"),
        ("Process", "process"),
        ("Runtime", "process"),
        ("Endpoint", "endpoint"),
        ("Deployment", "k8s_deployment"),
        ("K8sDeployment", "k8s_deployment"),
        ("Database", "db"),
        ("Datastore", "db"),
        ("Db", "db"),
        ("Queue", "queue"),
        ("Network", "network"),
        ("Customer", "customer"),
        ("BusinessService", "business_service"),
        ("Namespace", "namespace"),
        ("Node", "node"),
        ("Volume", "volume"),
        ("GuestOS", "host"),
        ("VirtualMachine", "host"),
        ("HypervisorHost", "host"),
        ("NetworkPort", "network"),
        ("Middleware", "service"),
        ("Monitor", "service"),
    ]
});

static ALLOWED_STORAGE: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    let mut s: HashSet<&'static str> = INGEST_TO_STORAGE.iter().map(|(_, v)| *v).collect();
    for t in [
        "service",
        "host",
        "pod",
        "container",
        "process",
        "endpoint",
        "k8s_deployment",
        "db",
        "queue",
        "network",
        "customer",
        "business_service",
        "namespace",
        "node",
        "volume",
    ] {
        s.insert(t);
    }
    s
});

static FORBIDDEN_STORAGE: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    [
        "alert",
        "incident",
        "itsm_ticket",
        "red_metric",
        "log_pattern",
        "trace",
        "change",
        "metric",
        "anomaly",
        "event",
        "ticket",
    ]
    .into_iter()
    .collect()
});

static FORBIDDEN_INGEST: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    [
        "Alert",
        "Incident",
        "Change",
        "ITSMTicket",
        "ItsmTicket",
        "Metric",
        "LogPattern",
        "Trace",
        "Anomaly",
        "Event",
        "Ticket",
        "RedMetric",
    ]
    .into_iter()
    .collect()
});

/// Map ingest ``ci_type`` (PascalCase or Motadata lowercase) to storage type.
pub fn to_storage_type(ci_type: &str) -> Option<String> {
    let key = ci_type.trim();
    if key.is_empty() {
        return None;
    }
    for (ingest, storage) in INGEST_TO_STORAGE.iter() {
        if *ingest == key {
            return Some((*storage).to_string());
        }
    }
    let lower = key.to_ascii_lowercase();
    if ALLOWED_STORAGE.contains(lower.as_str()) {
        return Some(lower);
    }
    None
}

/// Prefer type already on the map; else map declared ingest type. Never invent ``service``.
pub fn storage_type_or_none(ci_type: Option<&str>) -> Option<String> {
    to_storage_type(ci_type.unwrap_or(""))
}

/// Motadata storage → ingest PascalCase for first-time node upsert.
pub fn storage_to_ingest(storage: &str) -> Option<&'static str> {
    match storage {
        "service" => Some("Service"),
        "host" => Some("Host"),
        "process" => Some("Runtime"),
        "db" => Some("Database"),
        "business_service" => Some("BusinessService"),
        "queue" => Some("Queue"),
        "pod" => Some("Pod"),
        "container" => Some("Container"),
        "endpoint" => Some("Endpoint"),
        "node" => Some("Node"),
        "namespace" => Some("Namespace"),
        "volume" => Some("Volume"),
        "network" => Some("Network"),
        "k8s_deployment" => Some("Deployment"),
        "customer" => Some("Customer"),
        _ => None,
    }
}

/// Return ``Ok(())`` when the type may be a map vertex; else never-CI.
pub fn may_emit_vertex(ci_type: &str) -> bool {
    let key = ci_type.trim();
    if key.is_empty() {
        return false;
    }
    if FORBIDDEN_INGEST.contains(key) || FORBIDDEN_STORAGE.contains(key.to_ascii_lowercase().as_str())
    {
        return false;
    }
    to_storage_type(key).is_some()
}
