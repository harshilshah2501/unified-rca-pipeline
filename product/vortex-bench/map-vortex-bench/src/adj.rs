//! Build walk adjacency from an edge spine batch + optional BFS microbench.

use crate::load::utf8_col;
use anyhow::Result;
use arrow::array::Array;
use arrow::record_batch::RecordBatch;
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};
use std::time::Instant;

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct AdjTiming {
    pub build_ms: f64,
    pub nodes_indexed: usize,
    pub directed_arcs: usize,
    pub bfs_seed: String,
    pub bfs_hops: usize,
    pub bfs_reachable: usize,
    pub bfs_ms: f64,
}

/// Out-adjacency: source → list of (target, edge_type).
pub fn build_out_adjacency(edges: &RecordBatch) -> Result<(HashMap<String, Vec<(String, String)>>, f64)> {
    let src = utf8_col(edges, "source_id")?;
    let tgt = utf8_col(edges, "target_id")?;
    let et = utf8_col(edges, "edge_type")?;
    let started = Instant::now();
    let mut adj: HashMap<String, Vec<(String, String)>> = HashMap::new();
    for i in 0..edges.num_rows() {
        if src.is_null(i) || tgt.is_null(i) || et.is_null(i) {
            continue;
        }
        adj.entry(src.value(i).to_string())
            .or_default()
            .push((tgt.value(i).to_string(), et.value(i).to_string()));
    }
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    Ok((adj, ms))
}

pub fn bfs_reachable(
    adj: &HashMap<String, Vec<(String, String)>>,
    seed: &str,
    hops: usize,
    relation_allow: Option<&HashSet<String>>,
) -> (usize, f64) {
    let started = Instant::now();
    let mut seen = HashSet::new();
    let mut q = VecDeque::new();
    seen.insert(seed.to_string());
    q.push_back((seed.to_string(), 0usize));
    while let Some((cur, d)) = q.pop_front() {
        if d >= hops {
            continue;
        }
        if let Some(neis) = adj.get(&cur) {
            for (t, et) in neis {
                if let Some(allow) = relation_allow {
                    if !allow.contains(et) {
                        continue;
                    }
                }
                if seen.insert(t.clone()) {
                    q.push_back((t.clone(), d + 1));
                }
            }
        }
    }
    (seen.len(), started.elapsed().as_secs_f64() * 1000.0)
}

pub fn time_adj_and_walk(
    edges: &RecordBatch,
    seed: &str,
    hops: usize,
) -> Result<AdjTiming> {
    let (adj, build_ms) = build_out_adjacency(edges)?;
    let arcs: usize = adj.values().map(|v| v.len()).sum();
    let (reachable, bfs_ms) = bfs_reachable(&adj, seed, hops, None);
    Ok(AdjTiming {
        build_ms,
        nodes_indexed: adj.len(),
        directed_arcs: arcs,
        bfs_seed: seed.into(),
        bfs_hops: hops,
        bfs_reachable: reachable,
        bfs_ms,
    })
}
