//! Synthetic Motadata map_nodes / map_edges estates for cold-load experiments.

use clap::ValueEnum;

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

pub fn generate_estate(nodes_n: usize, edges_n: usize, seed: u64) -> (Vec<NodeRow>, Vec<EdgeRow>) {
    let nodes_n = nodes_n.max(2);
    let mut nodes = Vec::with_capacity(nodes_n);
    for i in 0..nodes_n {
        let r = mix(seed, i as u64);
        let type_ = NODE_TYPES[(r as usize) % NODE_TYPES.len()];
        let entity_id = format!("{type_}-{:05}", i);
        nodes.push(NodeRow {
            entity_id: entity_id.clone(),
            type_: type_.into(),
            name: entity_id,
            env: Some(if r % 3 == 0 { "prod" } else { "rca-lab" }.into()),
            region: Some(if r % 2 == 0 { "ap-south-1" } else { "us-east-1" }.into()),
            owner: Some(format!("team-{}", r % 16)),
            namespace: if type_ == "service" {
                Some(format!("ns-{}", r % 8))
            } else {
                None
            },
            last_seen: 1_787_196_600_000 + (r % 86_400_000),
            valid_from: Some(1_787_184_000_000),
            valid_to: None,
            version: 1 + (r % 5) as u32,
        });
    }

    let mut edges = Vec::with_capacity(edges_n);
    for i in 0..edges_n {
        let r = mix(seed ^ 0xC0FFEE, i as u64);
        let src = &nodes[(r as usize) % nodes_n];
        let dst = &nodes[((r >> 11) as usize) % nodes_n];
        if src.entity_id == dst.entity_id {
            continue;
        }
        let edge_type = EDGE_TYPES[(r as usize) % EDGE_TYPES.len()];
        edges.push(EdgeRow {
            edge_id: 7_146_828_800_000_000 + i as u64,
            source_id: src.entity_id.clone(),
            target_id: dst.entity_id.clone(),
            edge_type: edge_type.into(),
            valid_from: Some(1_787_184_000_000),
            valid_to: None,
            evidence_event_id: 7_146_828_900_000_000 + i as u64,
        });
    }
    // Top up if self-loops skipped shrunk the list.
    let mut i = edges_n;
    while edges.len() < edges_n {
        let r = mix(seed ^ 0xBEEF, i as u64);
        let src = &nodes[(r as usize) % nodes_n];
        let dst = &nodes[((r >> 7) as usize + 1) % nodes_n];
        if src.entity_id != dst.entity_id {
            edges.push(EdgeRow {
                edge_id: 7_146_828_800_000_000 + i as u64,
                source_id: src.entity_id.clone(),
                target_id: dst.entity_id.clone(),
                edge_type: EDGE_TYPES[(r as usize) % EDGE_TYPES.len()].into(),
                valid_from: Some(1_787_184_000_000),
                valid_to: None,
                evidence_event_id: 7_146_828_900_000_000 + i as u64,
            });
        }
        i += 1;
    }
    (nodes, edges)
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

fn mix(a: u64, b: u64) -> u64 {
    let mut x = a ^ b.wrapping_mul(0x9E37_79B9_7F4A_7C15);
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x.wrapping_mul(0x94D0_49BB_1331_11EB)
}
