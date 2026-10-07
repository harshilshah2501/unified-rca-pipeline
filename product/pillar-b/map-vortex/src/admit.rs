//! GraphWriter admit triage — four gates from ``EDGE_TRIPLET_ALLOWLIST.md`` §2.
//!
//! Port of ``poc/graph/edge_catalog.py`` + ``edge_triplets.py`` + gate order in
//! ``graph_builder.apply_topo_stream``.

use crate::ci_qualify::{may_emit_vertex, storage_type_or_none, to_storage_type};
use crate::edge_type::EdgeType;
use crate::error::{Error, Result};
use std::collections::HashSet;
use std::str::FromStr;
use std::sync::LazyLock;

/// Per-line admit result (matches Python GraphWriter / ``MAP_HOT_COLD_LIFECYCLE`` §2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdmitOutcome {
    /// Incomplete topology claim — no estate change.
    Noop,
    /// Legal write — mutate hot store.
    Write {
        src_storage: String,
        dst_storage: String,
        edge_type: EdgeType,
    },
    /// Reject with a stable code (see ``IDENTIFIED_STREAM_REJECT.md``).
    Drop(RejectCode),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RejectCode {
    Identity,
    NeverCiVertex,
    UnknownRelation,
    MissingEndpointType,
    IllegalEdgeTriplet,
}

impl RejectCode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Identity => "identity_unresolved",
            Self::NeverCiVertex => "never_ci_vertex",
            Self::UnknownRelation => "unknown_relation",
            Self::MissingEndpointType => "missing_endpoint_type",
            Self::IllegalEdgeTriplet => "illegal_edge_triplet",
        }
    }
}

impl std::fmt::Display for RejectCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Topology claim extracted from a writer / lab ``topo_update`` line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TopologyClaim {
    pub src_ci_id: String,
    pub dst_ci_id: String,
    pub relation: String,
    pub identity_resolved: bool,
    /// Subject / source declared type (ingest PascalCase or Motadata).
    pub src_ci_type: Option<String>,
    /// Destination declared type — **no Service default**.
    pub dst_ci_type: Option<String>,
    /// Types already known on the hot map for endpoints (preferred over stream).
    pub src_map_type: Option<String>,
    pub dst_map_type: Option<String>,
}

impl TopologyClaim {
    /// Gate 1 — all three claim fields present?
    pub fn is_complete(&self) -> bool {
        !self.src_ci_id.is_empty() && !self.dst_ci_id.is_empty() && !self.relation.is_empty()
    }
}

/// Normalize ingest snake_case or Motadata SCREAMING to ingest snake_case.
pub fn normalize_relation(name: &str) -> Option<&'static str> {
    let key = name.trim();
    if let Ok(et) = EdgeType::from_str(&key.to_ascii_uppercase()) {
        return Some(et.ingest_relation());
    }
    for et in EdgeType::ALL {
        if et.ingest_relation() == key {
            return Some(et.ingest_relation());
        }
    }
    None
}

/// Map relation name to Motadata ``edge_type``.
pub fn to_edge_type(relation: &str) -> Result<EdgeType> {
    normalize_relation(relation)
        .and_then(|r| EdgeType::from_ingest(r))
        .ok_or_else(|| Error::UnknownEdgeType(relation.to_string()))
}

/// Classify relation: emit vs unknown.
pub fn classify_relation(relation: &str) -> std::result::Result<EdgeType, RejectCode> {
    to_edge_type(relation).map_err(|_| RejectCode::UnknownRelation)
}

type Pair = (&'static str, &'static str);

fn cart(src: &[&'static str], dst: &[&'static str]) -> HashSet<Pair> {
    let mut out = HashSet::new();
    for s in src {
        for d in dst {
            out.insert((*s, *d));
        }
    }
    out
}

static NETWORKABLE: &[&str] = &[
    "service", "host", "pod", "container", "db", "queue", "endpoint", "network", "node",
    "process",
];

static ALL_CI: LazyLock<Vec<&'static str>> = LazyLock::new(|| {
    let mut v = NETWORKABLE.to_vec();
    v.extend([
        "business_service",
        "k8s_deployment",
        "namespace",
        "volume",
        "customer",
    ]);
    v
});

static RUNS_ON: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["process", "service", "pod", "container", "db", "queue"],
        &["host", "node"],
    )
});

static HOSTED_ON: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &[
            "process", "service", "pod", "container", "db", "queue", "host",
        ],
        &["host"],
    )
});

static DEPENDS_OR_USES: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    for t in ["service", "db", "queue", "endpoint", "business_service"] {
        s.insert(("service", t));
    }
    for t in ["service", "db", "queue"] {
        s.insert(("business_service", t));
    }
    for t in ["service", "db", "queue", "endpoint"] {
        s.insert(("pod", t));
        s.insert(("k8s_deployment", t));
    }
    s.insert(("customer", "business_service"));
    s.insert(("customer", "service"));
    s
});

static PART_OF: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    s.insert(("service", "business_service"));
    for child in ["process", "container", "volume"] {
        for parent in ["host", "pod", "service", "db"] {
            s.insert((child, parent));
        }
    }
    s.insert(("endpoint", "service"));
    s.insert(("endpoint", "host"));
    s.insert(("pod", "k8s_deployment"));
    s.insert(("pod", "namespace"));
    s
});

static COMMUNICATES_WITH: LazyLock<HashSet<Pair>> =
    LazyLock::new(|| cart(NETWORKABLE, NETWORKABLE));

static CONNECTS_TO: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["host", "node", "network", "endpoint", "service"],
        &["host", "node", "network", "endpoint", "service"],
    )
});

static MEMBER_OF: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["host", "node", "pod", "service", "db", "queue", "network"],
        &["namespace", "service", "business_service", "k8s_deployment"],
    )
});

static MOUNTS: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["host", "pod", "container", "service", "process"],
        &["volume"],
    )
});

static BACKS: LazyLock<HashSet<Pair>> =
    LazyLock::new(|| cart(&["db", "volume", "host", "service"], &["db", "volume", "host", "service"]));

static BACKED_UP_BY: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["db", "volume", "host", "service"],
        &["service", "host", "db", "volume"],
    )
});

static ROUTES_THROUGH: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["service", "host", "pod", "endpoint"],
        &["network", "service", "host", "endpoint"],
    )
});

static AUTHENTICATES_VIA: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    cart(
        &["service", "host", "pod", "customer"],
        &["service", "endpoint"],
    )
});

static MONITORED_BY: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    let mut s = HashSet::new();
    for src in ALL_CI.iter() {
        s.insert((*src, "service"));
    }
    s
});

static CLUSTERED_WITH: LazyLock<HashSet<Pair>> = LazyLock::new(|| {
    ["host", "node", "service", "db", "pod", "queue"]
        .into_iter()
        .map(|t| (t, t))
        .collect()
});

fn pairs_for(edge_type: EdgeType) -> &'static HashSet<Pair> {
    match edge_type {
        EdgeType::RunsOn => &RUNS_ON,
        EdgeType::HostedOn => &HOSTED_ON,
        EdgeType::DependsOn | EdgeType::Uses => &DEPENDS_OR_USES,
        EdgeType::PartOf => &PART_OF,
        EdgeType::CommunicatesWith => &COMMUNICATES_WITH,
        EdgeType::ConnectsTo => &CONNECTS_TO,
        EdgeType::MemberOf => &MEMBER_OF,
        EdgeType::Mounts => &MOUNTS,
        EdgeType::Backs => &BACKS,
        EdgeType::BackedUpBy => &BACKED_UP_BY,
        EdgeType::RoutesThrough => &ROUTES_THROUGH,
        EdgeType::AuthenticatesVia => &AUTHENTICATES_VIA,
        EdgeType::MonitoredBy => &MONITORED_BY,
        EdgeType::ClusteredWith => &CLUSTERED_WITH,
    }
}

/// Check ``(src_storage, relation, dst_storage)`` against the Motadata allowlist.
pub fn check_edge_triplet(
    relation: &str,
    src_storage: Option<&str>,
    dst_storage: Option<&str>,
) -> std::result::Result<(), RejectCode> {
    let src = src_storage.filter(|s| !s.is_empty());
    let dst = dst_storage.filter(|s| !s.is_empty());
    if src.is_none() || dst.is_none() {
        return Err(RejectCode::MissingEndpointType);
    }
    let src = src.unwrap();
    let dst = dst.unwrap();
    let edge_type = classify_relation(relation)?;
    if edge_type == EdgeType::PartOf && src == dst {
        return Err(RejectCode::IllegalEdgeTriplet);
    }
    let pairs = pairs_for(edge_type);
    if !pairs.contains(&(src, dst)) {
        return Err(RejectCode::IllegalEdgeTriplet);
    }
    Ok(())
}

fn resolve_endpoint_type(map_type: Option<&str>, declared: Option<&str>) -> Option<String> {
    if let Some(t) = map_type.filter(|s| !s.is_empty()) {
        return to_storage_type(t).or_else(|| Some(t.to_string()));
    }
    storage_type_or_none(declared)
}

/// Full admit: gates 1→4. On ``Write``, returns resolved Motadata types + ``edge_type``.
pub fn admit_topology_claim(claim: &TopologyClaim) -> AdmitOutcome {
    // Gate 1 — complete claim
    if !claim.is_complete() {
        return AdmitOutcome::Noop;
    }
    // Gate 2 — identity resolved
    if !claim.identity_resolved {
        return AdmitOutcome::Drop(RejectCode::Identity);
    }
    // Gate 3 — both ends may be CI vertices (when types are declared)
    for declared in [&claim.src_ci_type, &claim.dst_ci_type] {
        if let Some(t) = declared.as_deref().filter(|s| !s.is_empty()) {
            if !may_emit_vertex(t) {
                return AdmitOutcome::Drop(RejectCode::NeverCiVertex);
            }
        }
    }
    // Gate 4 — relation catalog + types + triplet
    let edge_type = match classify_relation(&claim.relation) {
        Ok(et) => et,
        Err(code) => return AdmitOutcome::Drop(code),
    };
    let src_storage = resolve_endpoint_type(
        claim.src_map_type.as_deref(),
        claim.src_ci_type.as_deref(),
    );
    let dst_storage = resolve_endpoint_type(
        claim.dst_map_type.as_deref(),
        claim.dst_ci_type.as_deref(),
    );
    if let Err(code) = check_edge_triplet(
        &claim.relation,
        src_storage.as_deref(),
        dst_storage.as_deref(),
    ) {
        return AdmitOutcome::Drop(code);
    }
    AdmitOutcome::Write {
        src_storage: src_storage.expect("checked"),
        dst_storage: dst_storage.expect("checked"),
        edge_type,
    }
}
