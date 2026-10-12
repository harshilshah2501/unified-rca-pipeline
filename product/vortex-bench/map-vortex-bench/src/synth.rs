//! Synthetic Motadata map_nodes / map_edges estates for cold-load experiments.

use clap::ValueEnum;
use serde::Serialize;

/// Motadata SCREAMING edge types used in synthetic estates (subset + full catalog mix).
pub const EDGE_TYPES: &[&str] = &[
    "DEPENDS_ON",
    "RUNS_ON",
    "USES",
    "COMMUNICATES_WITH",
    "PART_OF",
    "MEMBER_OF",
    "HOSTED_ON",
    "MOUNTS",
    "CONNECTS_TO",
    "BACKS",
    "ROUTES_THROUGH",
    "AUTHENTICATES_VIA",
    "MONITORED_BY",
    "BACKED_UP_BY",
    "CLUSTERED_WITH",
];

pub const NODE_TYPES: &[&str] = &[
    "service",
    "host",
    "database",
    "queue",
    "runtime",
    "middleware",
];

#[derive(Debug, Clone)]
pub struct NodeRow {
    pub entity_id: String,
    pub type_: String,
    pub name: String,
    pub env: Option<String>,
    pub region: Option<String>,
    pub owner: Option<String>,
    pub namespace: Option<String>,
    pub last_seen: u64,
    pub valid_from: Option<u64>,
    pub valid_to: Option<u64>,
    pub version: u32,
}

#[derive(Debug, Clone)]
pub struct EdgeRow {
    pub edge_id: u64,
    pub source_id: String,
    pub target_id: String,
    pub edge_type: String,
    pub valid_from: Option<u64>,
    pub valid_to: Option<u64>,
    pub evidence_event_id: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum EdgeSort {
    /// Generation order (interleaved sources / types).
    Natural,
    /// Cluster for prune-friendly scans: source_id → edge_type → target_id.
    Clustered,
}

/// How source endpoints are sampled when generating edges.
/// Stage 4 adds power_law / hierarchical / community / layered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum EstateShape {
    /// Near-uniform source and target over all nodes (original lab).
    Uniform,
    /// A small hub set emits most edges (preferential / Motadata-like skew).
    Hubby,
    PowerLaw,
    Hierarchical,
    Community,
    Layered,
}

impl EstateShape {
    pub fn id(self) -> &'static str {
        match self {
            Self::Uniform => "uniform",
            Self::Hubby => "hubby",
            Self::PowerLaw => "power_law",
            Self::Hierarchical => "hierarchical",
            Self::Community => "community",
            Self::Layered => "layered",
        }
    }
}

/// Out-degree distribution summary for fairness / realism checks.
#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct DegreeStats {
    pub mean_out_degree: f64,
    pub sources_with_edges: usize,
    pub max_out_degree: usize,
    pub p50_out_degree: usize,
    pub p95_out_degree: usize,
    pub p99_out_degree: usize,
    /// Share of edges whose source is among the top 1% sources by out-degree.
    pub top1pct_sources_edge_share: f64,
}

pub struct EstateConfig {
    pub nodes_n: usize,
    pub edges_n: usize,
    pub seed: u64,
    pub shape: EstateShape,
    /// Fraction of nodes treated as hubs when `shape == Hubby` (default 0.01).
    pub hub_fraction: f64,
    /// Fraction of edges whose source is drawn from the hub set (default 0.50).
    pub hub_edge_share: f64,
}

impl Default for EstateConfig {
    fn default() -> Self {
        Self {
            nodes_n: 10_000,
            edges_n: 50_000,
            seed: 42,
            shape: EstateShape::Uniform,
            hub_fraction: 0.01,
            hub_edge_share: 0.50,
        }
    }
}

/// Derive node count from edge count so mean out-degree stays fixed across scales.
pub fn nodes_for_density(edges_n: usize, mean_out_degree: f64) -> usize {
    let d = mean_out_degree.max(0.1);
    ((edges_n as f64) / d).round().max(2.0) as usize
}

pub fn generate_estate(cfg: &EstateConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, DegreeStats) {
    use crate::estate::{EstateFamily, FamilyConfig, generate_family};
    let family = match cfg.shape {
        EstateShape::Uniform => EstateFamily::Uniform,
        EstateShape::Hubby => EstateFamily::Hubby,
        EstateShape::PowerLaw => EstateFamily::PowerLaw,
        EstateShape::Hierarchical => EstateFamily::Hierarchical,
        EstateShape::Community => EstateFamily::Community,
        EstateShape::Layered => EstateFamily::Layered,
    };
    let fcfg = FamilyConfig {
        family,
        nodes_n: cfg.nodes_n,
        edges_n: cfg.edges_n,
        seed: cfg.seed,
        hub_fraction: cfg.hub_fraction,
        hub_edge_share: cfg.hub_edge_share,
        pa_softener: 1.0,
    };
    let (nodes, edges, _meta) = generate_family(&fcfg);
    let stats = degree_stats(&edges, nodes.len());
    (nodes, edges, stats)
}

pub fn sort_edges(edges: &mut [EdgeRow], order: EdgeSort) {
    match order {
        EdgeSort::Natural => {}
        EdgeSort::Clustered => {
            edges.sort_by(|a, b| {
                a.source_id
                    .cmp(&b.source_id)
                    .then_with(|| a.edge_type.cmp(&b.edge_type))
                    .then_with(|| a.target_id.cmp(&b.target_id))
            });
        }
    }
}

pub fn degree_stats(edges: &[EdgeRow], nodes_n: usize) -> DegreeStats {
    let mut counts: HashMapCount = HashMapCount::new();
    for e in edges {
        counts.inc(&e.source_id);
    }
    let mut degrees: Vec<usize> = counts.into_values();
    degrees.sort_unstable();
    let sources = degrees.len();
    let max = *degrees.last().unwrap_or(&0);
    let mean = if nodes_n == 0 {
        0.0
    } else {
        edges.len() as f64 / nodes_n as f64
    };
    let pct = |p: f64| -> usize {
        if degrees.is_empty() {
            return 0;
        }
        let idx = ((p / 100.0) * (degrees.len() as f64 - 1.0)).round() as usize;
        degrees[idx.min(degrees.len() - 1)]
    };
    let top_n = ((sources as f64) * 0.01).ceil().max(1.0) as usize;
    let top_n = top_n.min(sources.max(1));
    let top_edges: usize = degrees.iter().rev().take(top_n).sum();
    let share = if edges.is_empty() {
        0.0
    } else {
        top_edges as f64 / edges.len() as f64
    };
    DegreeStats {
        mean_out_degree: mean,
        sources_with_edges: sources,
        max_out_degree: max,
        p50_out_degree: pct(50.0),
        p95_out_degree: pct(95.0),
        p99_out_degree: pct(99.0),
        top1pct_sources_edge_share: share,
    }
}

/// Tiny string→count map without pulling in extra deps beyond std.
struct HashMapCount {
    inner: std::collections::HashMap<String, usize>,
}

impl HashMapCount {
    fn new() -> Self {
        Self {
            inner: std::collections::HashMap::new(),
        }
    }
    fn inc(&mut self, k: &str) {
        *self.inner.entry(k.to_string()).or_default() += 1;
    }
    fn into_values(self) -> Vec<usize> {
        self.inner.into_values().collect()
    }
}

pub fn mix(a: u64, b: u64) -> u64 {
    let mut x = a ^ b.wrapping_mul(0x9E37_79B9_7F4A_7C15);
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x.wrapping_mul(0x94D0_49BB_1331_11EB)
}
