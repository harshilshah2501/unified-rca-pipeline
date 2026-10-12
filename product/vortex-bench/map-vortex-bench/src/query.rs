//! Multi-seed query harness + JSONL emission (Design v3 / Stage 3.5).

use crate::hot::{HotGraph, bfs, checksum_names, out_degrees_hash};
use serde::Serialize;
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

#[derive(Debug, Clone, Copy)]
pub enum QueryType {
    ForwardBfs,
    ReverseBlast,
    DependencyChain,
}

impl QueryType {
    pub fn id(self) -> &'static str {
        match self {
            Self::ForwardBfs => "forward_bfs",
            Self::ReverseBlast => "reverse_blast",
            Self::DependencyChain => "dependency_chain",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct QueryEvent {
    pub query_id: String,
    pub run_id: String,
    pub r#type: String,
    pub seed_id: String,
    pub seed_degree_bin: String,
    pub hops: usize,
    pub edge_type_filter: Option<Vec<String>>,
    pub concurrency: u32,
    pub layout: String,
    pub reverse_algorithm: String,
    pub latency_ms: f64,
    pub reachable: usize,
    pub result_checksum: String,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct QueryClassStats {
    pub n: usize,
    pub p50_ms: f64,
    pub p95_ms: f64,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct QueryClassBreakdown {
    pub forward_bfs: QueryClassStats,
    pub reverse_blast: QueryClassStats,
    pub dependency_chain: QueryClassStats,
    /// Equal-mix aggregate (all classes concatenated) — do not use alone for architecture choice.
    pub aggregate: QueryClassStats,
}

pub struct SeedPick {
    pub id: String,
    pub bin: &'static str,
    pub degree: usize,
}

pub fn pick_seeds_by_degree(adj: &HashMap<String, Vec<(String, String)>>) -> Vec<SeedPick> {
    let ranked = out_degrees_hash(adj);
    if ranked.is_empty() {
        return Vec::new();
    }
    let pick = |p: f64, label: &'static str| -> SeedPick {
        let idx = ((p / 100.0) * (ranked.len() as f64 - 1.0)).round() as usize;
        let idx = idx.min(ranked.len() - 1);
        SeedPick {
            id: ranked[idx].0.clone(),
            bin: label,
            degree: ranked[idx].1,
        }
    };
    vec![pick(10.0, "p10"), pick(50.0, "p50"), pick(90.0, "p90")]
}

fn seeds_from_csr(ids: &crate::hot::IdMap, csr: &crate::hot::Csr) -> Vec<SeedPick> {
    let mut ranked: Vec<(String, usize)> = (0..csr.n)
        .map(|i| {
            let deg = (csr.offsets[i + 1] - csr.offsets[i]) as usize;
            (ids.id_to_str[i].clone(), deg)
        })
        .filter(|(_, d)| *d > 0)
        .collect();
    ranked.sort_by_key(|(_, d)| *d);
    if ranked.is_empty() {
        return Vec::new();
    }
    let pick = |p: f64, label: &'static str| -> SeedPick {
        let idx = ((p / 100.0) * (ranked.len() as f64 - 1.0)).round() as usize;
        let idx = idx.min(ranked.len() - 1);
        SeedPick {
            id: ranked[idx].0.clone(),
            bin: label,
            degree: ranked[idx].1,
        }
    };
    vec![pick(10.0, "p10"), pick(50.0, "p50"), pick(90.0, "p90")]
}

pub fn seeds_from_graph(graph: &HotGraph) -> Vec<SeedPick> {
    match graph {
        HotGraph::Hash { adj, .. } => pick_seeds_by_degree(adj),
        HotGraph::HashBi { out, .. } => pick_seeds_by_degree(out),
        HotGraph::Csr { ids, csr }
        | HotGraph::CsrCsc { ids, csr, .. }
        | HotGraph::Hybrid { ids, csr, .. } => seeds_from_csr(ids, csr),
    }
}

/// Stage 3.5: **always** emit forward, dependency_chain, and reverse for every layout.
pub fn run_query_mix(
    graph: &HotGraph,
    run_id: &str,
    layout: &str,
    reverse_algorithm: &str,
    hops_list: &[usize],
    replicate: usize,
) -> Vec<QueryEvent> {
    let seeds = seeds_from_graph(graph);
    let mut events = Vec::new();
    let mut qn = 0u64;
    for _rep in 0..replicate.max(1) {
        for seed in &seeds {
            for &hops in hops_list {
                for (qtype, rev, h) in [
                    (QueryType::ForwardBfs, false, hops),
                    (QueryType::DependencyChain, false, hops + 1),
                    (QueryType::ReverseBlast, true, hops),
                ] {
                    qn += 1;
                    let (reach, ms, names) = bfs(graph, &seed.id, h, rev);
                    events.push(QueryEvent {
                        query_id: format!("{run_id}-q{qn}"),
                        run_id: run_id.into(),
                        r#type: qtype.id().into(),
                        seed_id: seed.id.clone(),
                        seed_degree_bin: seed.bin.into(),
                        hops: h,
                        edge_type_filter: None,
                        concurrency: 1,
                        layout: layout.into(),
                        reverse_algorithm: reverse_algorithm.into(),
                        latency_ms: ms,
                        reachable: reach,
                        result_checksum: checksum_names(&names),
                    });
                }
            }
        }
    }
    events
}

pub fn class_breakdown(events: &[QueryEvent]) -> QueryClassBreakdown {
    let mut fwd = Vec::new();
    let mut rev = Vec::new();
    let mut dep = Vec::new();
    let mut all = Vec::new();
    for e in events {
        all.push(e.latency_ms);
        match e.r#type.as_str() {
            "forward_bfs" => fwd.push(e.latency_ms),
            "reverse_blast" => rev.push(e.latency_ms),
            "dependency_chain" => dep.push(e.latency_ms),
            _ => {}
        }
    }
    let stats = |mut v: Vec<f64>| -> QueryClassStats {
        v.sort_by(|a, b| a.partial_cmp(b).unwrap());
        QueryClassStats {
            n: v.len(),
            p50_ms: percentile(&v, 50.0),
            p95_ms: percentile(&v, 95.0),
        }
    };
    QueryClassBreakdown {
        forward_bfs: stats(fwd),
        reverse_blast: stats(rev),
        dependency_chain: stats(dep),
        aggregate: stats(all),
    }
}

pub fn write_query_jsonl(path: &Path, events: &[QueryEvent]) -> std::io::Result<()> {
    let f = File::create(path)?;
    let mut w = BufWriter::new(f);
    for e in events {
        serde_json::to_writer(&mut w, e)?;
        w.write_all(b"\n")?;
    }
    w.flush()
}

pub fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let idx = ((p / 100.0) * (sorted.len() as f64 - 1.0)).round() as usize;
    sorted[idx.min(sorted.len() - 1)]
}
