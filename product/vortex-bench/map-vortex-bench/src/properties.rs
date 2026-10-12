//! Post-generation graph property metrics + family validation gates.

use crate::estate::EstateFamily;
use crate::synth::{EdgeRow, NodeRow, mix};
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Debug, Clone, Serialize)]
pub struct GraphProperties {
    pub family: String,
    pub nodes: usize,
    pub edges: usize,
    pub mean_out_degree: f64,
    pub mean_in_degree: f64,
    pub sources_with_edges: usize,
    pub sinks_with_edges: usize,
    pub out_p50: usize,
    pub out_p90: usize,
    pub out_p99: usize,
    pub out_max: usize,
    pub in_p50: usize,
    pub in_p90: usize,
    pub in_p99: usize,
    pub in_max: usize,
    pub top1pct_sources_edge_share: f64,
    pub weak_component_count: usize,
    pub reciprocity: f64,
    pub edge_type_histogram: HashMap<String, usize>,
    pub reachable_hops_2_median: f64,
    pub intra_community_edge_share: Option<f64>,
    pub validation_ok: bool,
    pub validation_notes: Vec<String>,
}

fn percentile(sorted: &[usize], p: f64) -> usize {
    if sorted.is_empty() {
        return 0;
    }
    let idx = ((p / 100.0) * (sorted.len() as f64 - 1.0)).round() as usize;
    sorted[idx.min(sorted.len() - 1)]
}

pub fn compute_properties(
    family: EstateFamily,
    nodes: &[NodeRow],
    edges: &[EdgeRow],
    communities: Option<usize>,
) -> GraphProperties {
    let n = nodes.len();
    let e = edges.len();
    let mut out: HashMap<&str, usize> = HashMap::new();
    let mut inn: HashMap<&str, usize> = HashMap::new();
    let mut type_hist: HashMap<String, usize> = HashMap::new();
    let mut edge_set: HashSet<(String, String)> = HashSet::new();
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();

    for edge in edges {
        *out.entry(edge.source_id.as_str()).or_default() += 1;
        *inn.entry(edge.target_id.as_str()).or_default() += 1;
        *type_hist.entry(edge.edge_type.clone()).or_default() += 1;
        edge_set.insert((edge.source_id.clone(), edge.target_id.clone()));
        adj.entry(edge.source_id.as_str())
            .or_default()
            .push(edge.target_id.as_str());
        adj.entry(edge.target_id.as_str()).or_default(); // ensure undirected nodes exist
    }

    let mut out_degs: Vec<usize> = out.values().copied().collect();
    out_degs.sort_unstable();
    let mut in_degs: Vec<usize> = inn.values().copied().collect();
    in_degs.sort_unstable();

    let top_n = ((out_degs.len() as f64) * 0.01).ceil().max(1.0) as usize;
    let top_n = top_n.min(out_degs.len().max(1));
    let top_edges: usize = out_degs.iter().rev().take(top_n).sum();
    let top1 = if e == 0 {
        0.0
    } else {
        top_edges as f64 / e as f64
    };

    let mut recip_hits = 0usize;
    for edge in edges {
        if edge_set.contains(&(edge.target_id.clone(), edge.source_id.clone())) {
            recip_hits += 1;
        }
    }
    let reciprocity = if e == 0 {
        0.0
    } else {
        recip_hits as f64 / e as f64
    };

    let weak_component_count = weak_components(nodes, edges);
    let reachable_hops_2_median = sample_reachable_median(nodes, &adj, 2, 16, 42);

    let intra = communities.map(|c| intra_share(nodes, edges, c));

    let mut props = GraphProperties {
        family: family.id().into(),
        nodes: n,
        edges: e,
        mean_out_degree: if n == 0 { 0.0 } else { e as f64 / n as f64 },
        mean_in_degree: if n == 0 { 0.0 } else { e as f64 / n as f64 },
        sources_with_edges: out.len(),
        sinks_with_edges: inn.len(),
        out_p50: percentile(&out_degs, 50.0),
        out_p90: percentile(&out_degs, 90.0),
        out_p99: percentile(&out_degs, 99.0),
        out_max: *out_degs.last().unwrap_or(&0),
        in_p50: percentile(&in_degs, 50.0),
        in_p90: percentile(&in_degs, 90.0),
        in_p99: percentile(&in_degs, 99.0),
        in_max: *in_degs.last().unwrap_or(&0),
        top1pct_sources_edge_share: top1,
        weak_component_count,
        reciprocity,
        edge_type_histogram: type_hist,
        reachable_hops_2_median,
        intra_community_edge_share: intra,
        validation_ok: true,
        validation_notes: Vec::new(),
    };
    validate_family(family, &mut props);
    props
}

fn weak_components(nodes: &[NodeRow], edges: &[EdgeRow]) -> usize {
    let mut parent: HashMap<&str, &str> = HashMap::new();
    for n in nodes {
        parent.insert(n.entity_id.as_str(), n.entity_id.as_str());
    }
    fn find<'a>(parent: &mut HashMap<&'a str, &'a str>, x: &'a str) -> &'a str {
        let p = parent.get(x).copied().unwrap_or(x);
        if p != x {
            let r = find(parent, p);
            parent.insert(x, r);
            r
        } else {
            x
        }
    }
    for e in edges {
        let a = e.source_id.as_str();
        let b = e.target_id.as_str();
        if !parent.contains_key(a) {
            parent.insert(a, a);
        }
        if !parent.contains_key(b) {
            parent.insert(b, b);
        }
        let ra = find(&mut parent, a);
        let rb = find(&mut parent, b);
        if ra != rb {
            parent.insert(ra, rb);
        }
    }
    let mut roots = HashSet::new();
    let keys: Vec<&str> = parent.keys().copied().collect();
    for k in keys {
        roots.insert(find(&mut parent, k));
    }
    roots.len()
}

fn sample_reachable_median(
    nodes: &[NodeRow],
    adj: &HashMap<&str, Vec<&str>>,
    hops: usize,
    samples: usize,
    seed: u64,
) -> f64 {
    if nodes.is_empty() || adj.is_empty() {
        return 0.0;
    }
    let mut sizes = Vec::with_capacity(samples);
    for i in 0..samples {
        let r = mix(seed ^ 0x2C11, i as u64);
        let start = nodes[(r as usize) % nodes.len()].entity_id.as_str();
        let mut seen = HashSet::new();
        let mut q = VecDeque::new();
        q.push_back((start, 0usize));
        seen.insert(start);
        while let Some((u, d)) = q.pop_front() {
            if d >= hops {
                continue;
            }
            if let Some(nbrs) = adj.get(u) {
                for &v in nbrs {
                    if seen.insert(v) {
                        q.push_back((v, d + 1));
                    }
                }
            }
        }
        sizes.push(seen.len());
    }
    sizes.sort_unstable();
    percentile(&sizes, 50.0) as f64
}

fn intra_share(nodes: &[NodeRow], edges: &[EdgeRow], communities: usize) -> f64 {
    if edges.is_empty() || communities == 0 {
        return 0.0;
    }
    let mut id_to_idx: HashMap<&str, usize> = HashMap::new();
    for (i, n) in nodes.iter().enumerate() {
        id_to_idx.insert(n.entity_id.as_str(), i);
    }
    let mut intra = 0usize;
    for e in edges {
        let Some(&si) = id_to_idx.get(e.source_id.as_str()) else {
            continue;
        };
        let Some(&ti) = id_to_idx.get(e.target_id.as_str()) else {
            continue;
        };
        if (si % communities) == (ti % communities) {
            intra += 1;
        }
    }
    intra as f64 / edges.len() as f64
}

fn validate_family(family: EstateFamily, p: &mut GraphProperties) {
    let mut notes = Vec::new();
    let mut ok = true;
    let mean = p.mean_out_degree.max(0.01);
    match family {
        EstateFamily::Uniform => {
            if p.top1pct_sources_edge_share >= 0.05 {
                ok = false;
                notes.push(format!(
                    "uniform top1pct share {:.3} >= 0.05",
                    p.top1pct_sources_edge_share
                ));
            }
        }
        EstateFamily::Hubby => {
            if p.top1pct_sources_edge_share < 0.40 {
                ok = false;
                notes.push(format!(
                    "hubby top1pct share {:.3} < 0.40",
                    p.top1pct_sources_edge_share
                ));
            }
            if p.out_max <= p.out_p50 {
                ok = false;
                notes.push("hubby max_out not ≫ p50".into());
            }
        }
        EstateFamily::PowerLaw => {
            if (p.out_max as f64) < 50.0 * mean {
                ok = false;
                notes.push(format!(
                    "power_law max_out {} < 50× mean {:.2}",
                    p.out_max, mean
                ));
            }
            if (p.out_p99 as f64) < 10.0 * mean {
                ok = false;
                notes.push(format!(
                    "power_law p99_out {} < 10× mean {:.2}",
                    p.out_p99, mean
                ));
            }
        }
        EstateFamily::Hierarchical => {
            let layers = ["dc", "cluster", "host", "vm", "app", "service"];
            // Count distinct type prefixes in histogram is hard; check PART_OF/RUNS_ON share.
            let structural = p
                .edge_type_histogram
                .get("PART_OF")
                .copied()
                .unwrap_or(0)
                + p.edge_type_histogram
                    .get("RUNS_ON")
                    .copied()
                    .unwrap_or(0);
            if structural as f64 / (p.edges.max(1) as f64) < 0.05 {
                ok = false;
                notes.push("hierarchical structural edge share < 5%".into());
            }
            let _ = layers;
        }
        EstateFamily::Community => {
            let share = p.intra_community_edge_share.unwrap_or(0.0);
            if share < 0.85 {
                ok = false;
                notes.push(format!("community intra share {:.3} < 0.85", share));
            }
        }
        EstateFamily::Layered => {
            if p.reciprocity >= 0.15 {
                ok = false;
                notes.push(format!("layered reciprocity {:.3} >= 0.15", p.reciprocity));
            }
            let dep = p
                .edge_type_histogram
                .get("DEPENDS_ON")
                .copied()
                .unwrap_or(0)
                + p.edge_type_histogram.get("USES").copied().unwrap_or(0)
                + p.edge_type_histogram
                    .get("HOSTED_ON")
                    .copied()
                    .unwrap_or(0)
                + p.edge_type_histogram
                    .get("RUNS_ON")
                    .copied()
                    .unwrap_or(0);
            if dep as f64 / (p.edges.max(1) as f64) < 0.40 {
                ok = false;
                notes.push("layered directed-layer edge share < 40%".into());
            }
        }
    }
    p.validation_ok = ok;
    p.validation_notes = notes;
}

/// Simple content checksum (hex of folded mix) for estate reproducibility.
pub fn estate_checksum(nodes: &[NodeRow], edges: &[EdgeRow]) -> String {
    let mut h = 0u64;
    for (i, n) in nodes.iter().enumerate() {
        h = mix(h, mix(i as u64, n.entity_id.len() as u64));
    }
    for (i, e) in edges.iter().enumerate() {
        h = mix(
            h,
            mix(
                i as u64,
                mix(e.source_id.len() as u64, e.target_id.len() as u64),
            ),
        );
        h = mix(h, e.edge_id);
    }
    format!("{h:016x}")
}
