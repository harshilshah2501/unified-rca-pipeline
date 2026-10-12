//! Six Stage-4 estate family generators (synthetic modeling assumptions).

use crate::synth::{EDGE_TYPES, EdgeRow, NODE_TYPES, NodeRow, mix};
use clap::ValueEnum;
use serde::Serialize;

/// Stage 4 estate families (extends Stage 1–3 uniform/hubby).
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum EstateFamily {
    Uniform,
    Hubby,
    PowerLaw,
    Hierarchical,
    Community,
    Layered,
}

impl EstateFamily {
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

    pub fn all() -> &'static [EstateFamily] {
        &[
            Self::Uniform,
            Self::Hubby,
            Self::PowerLaw,
            Self::Hierarchical,
            Self::Community,
            Self::Layered,
        ]
    }
}

#[derive(Debug, Clone)]
pub struct FamilyConfig {
    pub family: EstateFamily,
    pub nodes_n: usize,
    pub edges_n: usize,
    pub seed: u64,
    pub hub_fraction: f64,
    pub hub_edge_share: f64,
    /// Preferential-attachment softener (power_law); higher → flatter.
    pub pa_softener: f64,
}

impl Default for FamilyConfig {
    fn default() -> Self {
        Self {
            family: EstateFamily::Uniform,
            nodes_n: 10_000,
            edges_n: 50_000,
            seed: 42,
            hub_fraction: 0.01,
            hub_edge_share: 0.50,
            pa_softener: 1.0,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct EstateMeta {
    pub family: String,
    pub generator_notes: String,
    pub communities: Option<usize>,
    pub intra_edge_target: Option<f64>,
    pub hierarchy_levels: Option<Vec<usize>>,
    pub pa_softener: Option<f64>,
}

pub fn generate_family(cfg: &FamilyConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    match cfg.family {
        EstateFamily::Uniform => gen_uniform_hubby(cfg, false),
        EstateFamily::Hubby => gen_uniform_hubby(cfg, true),
        EstateFamily::PowerLaw => gen_power_law(cfg),
        EstateFamily::Hierarchical => gen_hierarchical(cfg),
        EstateFamily::Community => gen_community(cfg),
        EstateFamily::Layered => gen_layered(cfg),
    }
}

fn make_node(seed: u64, i: usize, type_: &str, prefix: &str) -> NodeRow {
    let r = mix(seed, i as u64);
    let entity_id = format!("{prefix}-{:06}", i);
    NodeRow {
        entity_id: entity_id.clone(),
        type_: type_.into(),
        name: entity_id,
        env: Some(if r % 3 == 0 { "prod" } else { "rca-lab" }.into()),
        region: Some(if r % 2 == 0 { "ap-south-1" } else { "us-east-1" }.into()),
        owner: Some(format!("team-{}", r % 16)),
        namespace: if type_ == "service" || type_ == "app" {
            Some(format!("ns-{}", r % 8))
        } else {
            None
        },
        last_seen: 1_787_196_600_000 + (r % 86_400_000),
        valid_from: Some(1_787_184_000_000),
        valid_to: None,
        version: 1 + (r % 5) as u32,
    }
}

fn push_edge(
    edges: &mut Vec<EdgeRow>,
    nodes: &[NodeRow],
    src: usize,
    dst: usize,
    edge_type: &str,
) {
    if src == dst || src >= nodes.len() || dst >= nodes.len() {
        return;
    }
    edges.push(EdgeRow {
        edge_id: 7_146_828_800_000_000 + edges.len() as u64,
        source_id: nodes[src].entity_id.clone(),
        target_id: nodes[dst].entity_id.clone(),
        edge_type: edge_type.into(),
        valid_from: Some(1_787_184_000_000),
        valid_to: None,
        evidence_event_id: 7_146_828_900_000_000 + edges.len() as u64,
    });
}

fn gen_uniform_hubby(cfg: &FamilyConfig, hubby: bool) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    let nodes_n = cfg.nodes_n.max(2);
    let mut nodes = Vec::with_capacity(nodes_n);
    for i in 0..nodes_n {
        let r = mix(cfg.seed, i as u64);
        let type_ = NODE_TYPES[(r as usize) % NODE_TYPES.len()];
        nodes.push(make_node(cfg.seed, i, type_, type_));
    }
    let hub_count = ((nodes_n as f64) * cfg.hub_fraction)
        .round()
        .clamp(1.0, (nodes_n as f64) - 1.0) as usize;
    let hub_threshold = ((cfg.hub_edge_share.clamp(0.0, 1.0)) * 10_000.0).round() as u64;
    let mut edges = Vec::with_capacity(cfg.edges_n);
    let mut i = 0usize;
    while edges.len() < cfg.edges_n {
        let r = mix(cfg.seed ^ 0xC0FFEE, i as u64);
        let src_idx = if hubby {
            if (r % 10_000) < hub_threshold {
                (r as usize) % hub_count
            } else {
                hub_count + ((r >> 17) as usize) % (nodes_n - hub_count)
            }
        } else {
            (r as usize) % nodes_n
        };
        let dst_idx = ((r >> 11) as usize) % nodes_n;
        i += 1;
        if src_idx == dst_idx {
            continue;
        }
        let et = EDGE_TYPES[(r as usize) % EDGE_TYPES.len()];
        push_edge(&mut edges, &nodes, src_idx, dst_idx, et);
    }
    let meta = EstateMeta {
        family: if hubby { "hubby" } else { "uniform" }.into(),
        generator_notes: if hubby {
            format!(
                "hub_fraction={} hub_edge_share={}",
                cfg.hub_fraction, cfg.hub_edge_share
            )
        } else {
            "near-uniform source/target".into()
        },
        communities: None,
        intra_edge_target: None,
        hierarchy_levels: None,
        pa_softener: None,
    };
    (nodes, edges, meta)
}

/// Preferential attachment on sources via stub list (O(1) per edge).
/// Initial softener stubs give every node weight ≈ `pa_softener` (rounded).
fn gen_power_law(cfg: &FamilyConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    let nodes_n = cfg.nodes_n.max(2);
    let mut nodes = Vec::with_capacity(nodes_n);
    for i in 0..nodes_n {
        let r = mix(cfg.seed, i as u64);
        let type_ = NODE_TYPES[(r as usize) % NODE_TYPES.len()];
        nodes.push(make_node(cfg.seed, i, type_, type_));
    }
    let soft = cfg.pa_softener.max(0.01);
    // Small uniform bootstrap so preferential attachment dominates.
    let bootstrap = ((nodes_n as f64) * soft * 0.01).round().max(16.0) as usize;
    let bootstrap = bootstrap.min(nodes_n);
    let mut stubs: Vec<u32> = Vec::with_capacity(bootstrap + cfg.edges_n);
    for i in 0..bootstrap {
        stubs.push(i as u32);
    }
    let mut edges = Vec::with_capacity(cfg.edges_n);
    let mut i = 0usize;
    // 2% uniform exploration; 98% preferential attachment via stub list.
    while edges.len() < cfg.edges_n {
        let r = mix(cfg.seed ^ 0x0A11, i as u64);
        i += 1;
        let src = if (r % 100) < 2 {
            (r as usize) % nodes_n
        } else {
            stubs[(r as usize) % stubs.len()] as usize
        };
        let dst = ((r >> 21) as usize) % nodes_n;
        if src == dst {
            continue;
        }
        let et = EDGE_TYPES[((r >> 7) as usize) % EDGE_TYPES.len()];
        push_edge(&mut edges, &nodes, src, dst, et);
        stubs.push(src as u32);
    }
    let meta = EstateMeta {
        family: "power_law".into(),
        generator_notes: format!(
            "preferential_attachment bootstrap={bootstrap} explore=2%"
        ),
        communities: None,
        intra_edge_target: None,
        hierarchy_levels: None,
        pa_softener: Some(soft),
    };
    (nodes, edges, meta)
}

/// Scale hierarchical skeleton to edge budget: DC→cluster→host→VM→app→service.
fn gen_hierarchical(cfg: &FamilyConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    // Base proportions (counts before scale).
    let base = [1usize, 8, 64, 256, 512, 1024];
    let base_sum: usize = base.iter().sum();
    let target_nodes = cfg.nodes_n.max(base_sum);
    let scale = (target_nodes as f64 / base_sum as f64).max(1.0);
    let mut levels: Vec<usize> = base
        .iter()
        .map(|&c| ((c as f64) * scale).round().max(1.0) as usize)
        .collect();
    // Force first level = 1 DC when scaleable.
    levels[0] = 1;
    let type_names = ["dc", "cluster", "host", "vm", "app", "service"];
    let mut nodes = Vec::new();
    let mut ranges: Vec<(usize, usize)> = Vec::new(); // [start, end)
    for (li, &count) in levels.iter().enumerate() {
        let start = nodes.len();
        for j in 0..count {
            nodes.push(make_node(cfg.seed, start + j, type_names[li], type_names[li]));
        }
        ranges.push((start, nodes.len()));
    }
    let mut edges = Vec::with_capacity(cfg.edges_n);
    // Tree edges: each node links PART_OF / RUNS_ON to parent in previous level.
    for li in 1..levels.len() {
        let (ps, pe) = ranges[li - 1];
        let (cs, ce) = ranges[li];
        let parents = pe - ps;
        for child in cs..ce {
            let parent = ps + ((child - cs) % parents);
            let et = if li <= 3 { "PART_OF" } else { "RUNS_ON" };
            push_edge(&mut edges, &nodes, child, parent, et);
        }
    }
    // Top-up cross-service DEPENDS_ON / COMMUNICATES_WITH to hit edge budget.
    let (ss, se) = ranges[levels.len() - 1];
    let mut i = 0usize;
    while edges.len() < cfg.edges_n {
        let r = mix(cfg.seed ^ 0x013A, i as u64);
        i += 1;
        let src = ss + ((r as usize) % (se - ss).max(1));
        let dst = ss + (((r >> 13) as usize) % (se - ss).max(1));
        if src == dst {
            continue;
        }
        let et = if r % 2 == 0 {
            "DEPENDS_ON"
        } else {
            "COMMUNICATES_WITH"
        };
        push_edge(&mut edges, &nodes, src, dst, et);
    }
    let meta = EstateMeta {
        family: "hierarchical".into(),
        generator_notes: "DC→cluster→host→VM→app→service + service cross-links".into(),
        communities: None,
        intra_edge_target: None,
        hierarchy_levels: Some(levels),
        pa_softener: None,
    };
    (nodes, edges, meta)
}

fn gen_community(cfg: &FamilyConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    let communities = 32usize;
    let nodes_n = cfg.nodes_n.max(communities * 2);
    let mut nodes = Vec::with_capacity(nodes_n);
    let mut membership = Vec::with_capacity(nodes_n);
    for i in 0..nodes_n {
        let r = mix(cfg.seed, i as u64);
        let type_ = NODE_TYPES[(r as usize) % NODE_TYPES.len()];
        nodes.push(make_node(cfg.seed, i, type_, type_));
        membership.push(i % communities);
    }
    let intra_target = 0.90;
    let mut edges = Vec::with_capacity(cfg.edges_n);
    let mut i = 0usize;
    while edges.len() < cfg.edges_n {
        let r = mix(cfg.seed ^ 0xC0A1, i as u64);
        i += 1;
        let src = (r as usize) % nodes_n;
        let want_intra = (r % 10_000) < ((intra_target * 10_000.0) as u64);
        let dst = if want_intra {
            // Sample another node in same community.
            let c = membership[src];
            let mut tries = 0;
            loop {
                let cand = ((r >> (8 + tries)) as usize) % nodes_n;
                tries += 1;
                if membership[cand] == c && cand != src {
                    break cand;
                }
                if tries > 32 {
                    // Fallback: walk community block.
                    let base = c;
                    let step = ((r >> 3) as usize) % (nodes_n / communities).max(1);
                    let cand = (base + step * communities) % nodes_n;
                    if cand != src {
                        break cand;
                    }
                    break (src + 1) % nodes_n;
                }
            }
        } else {
            let mut cand = ((r >> 17) as usize) % nodes_n;
            if cand == src {
                cand = (cand + 1) % nodes_n;
            }
            cand
        };
        let et = EDGE_TYPES[((r >> 5) as usize) % EDGE_TYPES.len()];
        push_edge(&mut edges, &nodes, src, dst, et);
    }
    let meta = EstateMeta {
        family: "community".into(),
        generator_notes: format!("{communities} communities, ~90% intra-edges"),
        communities: Some(communities),
        intra_edge_target: Some(intra_target),
        hierarchy_levels: None,
        pa_softener: None,
    };
    (nodes, edges, meta)
}

fn gen_layered(cfg: &FamilyConfig) -> (Vec<NodeRow>, Vec<EdgeRow>, EstateMeta) {
    let nodes_n = cfg.nodes_n.max(4);
    let infra_n = (nodes_n as f64 * 0.40).round().max(2.0) as usize;
    let app_n = nodes_n - infra_n;
    let mut nodes = Vec::with_capacity(nodes_n);
    for i in 0..infra_n {
        let t = if i % 3 == 0 { "host" } else { "runtime" };
        nodes.push(make_node(cfg.seed, i, t, "infra"));
    }
    for j in 0..app_n {
        let i = infra_n + j;
        let t = if j % 2 == 0 { "service" } else { "database" };
        nodes.push(make_node(cfg.seed, i, t, "app"));
    }
    let mut edges = Vec::with_capacity(cfg.edges_n);
    let mut i = 0usize;
    while edges.len() < cfg.edges_n {
        let r = mix(cfg.seed ^ 0x1A48, i as u64);
        i += 1;
        let kind = r % 100;
        let (src, dst, et) = if kind < 55 {
            // app → infra HOSTED_ON / RUNS_ON
            let src = infra_n + ((r as usize) % app_n.max(1));
            let dst = (r >> 11) as usize % infra_n;
            let et = if r % 2 == 0 { "HOSTED_ON" } else { "RUNS_ON" };
            (src, dst, et)
        } else if kind < 85 {
            // app → app DEPENDS_ON / USES
            let src = infra_n + ((r as usize) % app_n.max(1));
            let dst = infra_n + (((r >> 17) as usize) % app_n.max(1));
            let et = if r % 2 == 0 { "DEPENDS_ON" } else { "USES" };
            (src, dst, et)
        } else {
            // infra → infra CONNECTS_TO (sparse)
            let src = (r as usize) % infra_n;
            let dst = ((r >> 9) as usize) % infra_n;
            (src, dst, "CONNECTS_TO")
        };
        if src == dst {
            continue;
        }
        push_edge(&mut edges, &nodes, src, dst, et);
    }
    let meta = EstateMeta {
        family: "layered".into(),
        generator_notes: "infra→app directed layers; low reciprocity expected".into(),
        communities: None,
        intra_edge_target: None,
        hierarchy_levels: None,
        pa_softener: None,
    };
    (nodes, edges, meta)
}
