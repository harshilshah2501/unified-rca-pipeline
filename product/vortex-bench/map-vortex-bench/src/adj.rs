//! Build walk adjacency from an edge spine batch + optional BFS microbench.

use crate::load::utf8_col;
use anyhow::Result;
use arrow::array::{Array, StringArray};
use arrow::record_batch::RecordBatch;
use clap::ValueEnum;
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};
use std::time::Instant;

/// How to turn edge rows into an out-adjacency map.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum AdjBuilder {
    /// One `HashMap::entry` per edge (clone source key every time).
    Naive,
    /// Walk contiguous `source_id` runs: one key clone + one insert per source group.
    /// Correct for any order; fastest when edges are clustered by source.
    SortAware,
}

impl AdjBuilder {
    pub fn id(self) -> &'static str {
        match self {
            Self::Naive => "naive",
            Self::SortAware => "sort_aware",
        }
    }
}

/// Light counters for adjacency rebuild (not a full allocator profile).
#[derive(Debug, Clone, Default, Serialize, serde::Deserialize)]
pub struct BuildProfile {
    /// Contiguous runs of equal `source_id` (≈ unique sources when clustered).
    pub source_groups: usize,
    /// Times a new `String` was allocated for a HashMap source key.
    pub source_key_clones: usize,
    /// Times target or edge_type strings were cloned into neighbor lists.
    pub neighbor_string_clones: usize,
    /// HashMap insert / entry operations that create or look up a source bucket.
    pub hashmap_source_ops: usize,
    /// Max out-degree observed while building.
    pub max_out_degree: usize,
}

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct AdjTiming {
    pub builder: String,
    pub build_ms: f64,
    pub nodes_indexed: usize,
    pub directed_arcs: usize,
    pub bfs_seed: String,
    pub bfs_hops: usize,
    pub bfs_reachable: usize,
    pub bfs_ms: f64,
    pub profile: BuildProfile,
}

/// Out-adjacency: source → list of (target, edge_type).
pub fn build_out_adjacency(
    edges: &RecordBatch,
    builder: AdjBuilder,
) -> Result<(HashMap<String, Vec<(String, String)>>, f64, BuildProfile)> {
    let src = utf8_col(edges, "source_id")?;
    let tgt = utf8_col(edges, "target_id")?;
    let et = utf8_col(edges, "edge_type")?;
    let started = Instant::now();
    let (adj, profile) = match builder {
        AdjBuilder::Naive => build_naive(&src, &tgt, &et),
        AdjBuilder::SortAware => build_sort_aware(&src, &tgt, &et),
    };
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    Ok((adj, ms, profile))
}

fn build_naive(
    src: &StringArray,
    tgt: &StringArray,
    et: &StringArray,
) -> (HashMap<String, Vec<(String, String)>>, BuildProfile) {
    let n = src.len();
    let mut adj: HashMap<String, Vec<(String, String)>> = HashMap::new();
    let mut profile = BuildProfile::default();
    let mut prev: Option<&str> = None;
    for i in 0..n {
        if src.is_null(i) || tgt.is_null(i) || et.is_null(i) {
            continue;
        }
        let s = src.value(i);
        if prev != Some(s) {
            profile.source_groups += 1;
            prev = Some(s);
        }
        profile.source_key_clones += 1;
        profile.hashmap_source_ops += 1;
        profile.neighbor_string_clones += 2;
        let list = adj.entry(s.to_string()).or_default();
        list.push((tgt.value(i).to_string(), et.value(i).to_string()));
        profile.max_out_degree = profile.max_out_degree.max(list.len());
    }
    (adj, profile)
}

fn build_sort_aware(
    src: &StringArray,
    tgt: &StringArray,
    et: &StringArray,
) -> (HashMap<String, Vec<(String, String)>>, BuildProfile) {
    let n = src.len();
    let mut adj: HashMap<String, Vec<(String, String)>> = HashMap::new();
    let mut profile = BuildProfile::default();
    let mut i = 0usize;
    while i < n {
        if src.is_null(i) || tgt.is_null(i) || et.is_null(i) {
            i += 1;
            continue;
        }
        let source = src.value(i);
        profile.source_groups += 1;
        profile.source_key_clones += 1;
        profile.hashmap_source_ops += 1;
        let key = source.to_string();
        let mut list = Vec::new();
        while i < n {
            if src.is_null(i) || tgt.is_null(i) || et.is_null(i) {
                i += 1;
                continue;
            }
            if src.value(i) != source {
                break;
            }
            profile.neighbor_string_clones += 2;
            list.push((tgt.value(i).to_string(), et.value(i).to_string()));
            i += 1;
        }
        profile.max_out_degree = profile.max_out_degree.max(list.len());
        adj.insert(key, list);
    }
    (adj, profile)
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
    builder: AdjBuilder,
) -> Result<AdjTiming> {
    let (adj, build_ms, profile) = build_out_adjacency(edges, builder)?;
    let arcs: usize = adj.values().map(|v| v.len()).sum();
    let (reachable, bfs_ms) = bfs_reachable(&adj, seed, hops, None);
    Ok(AdjTiming {
        builder: builder.id().into(),
        build_ms,
        nodes_indexed: adj.len(),
        directed_arcs: arcs,
        bfs_seed: seed.into(),
        bfs_hops: hops,
        bfs_reachable: reachable,
        bfs_ms,
        profile,
    })
}
