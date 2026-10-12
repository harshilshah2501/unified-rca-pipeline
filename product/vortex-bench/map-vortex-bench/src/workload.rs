//! Deterministic query-trace emit + replay (identical across layouts).

use crate::hot::{HotGraph, bfs, checksum_names, out_degrees_hash};
use crate::query::{QueryClassBreakdown, QueryEvent, class_breakdown, percentile};
use crate::synth::mix;
use clap::ValueEnum;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum WorkloadProfile {
    ForwardDominant,
    Balanced,
    ReverseHeavy,
}

impl WorkloadProfile {
    pub fn id(self) -> &'static str {
        match self {
            Self::ForwardDominant => "forward_dominant",
            Self::Balanced => "balanced",
            Self::ReverseHeavy => "reverse_heavy",
        }
    }

    /// (forward%, reverse%, dependency%) — experimental scenarios.
    pub fn mix_pct(self) -> (u32, u32, u32) {
        match self {
            Self::ForwardDominant => (90, 5, 5),
            Self::Balanced => (45, 45, 10),
            Self::ReverseHeavy => (20, 70, 10),
        }
    }

    pub fn all() -> &'static [WorkloadProfile] {
        &[
            Self::ForwardDominant,
            Self::Balanced,
            Self::ReverseHeavy,
        ]
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceOp {
    pub op_id: u64,
    pub r#type: String,
    pub seed_id: String,
    pub seed_degree_bin: String,
    pub hops: usize,
}

#[derive(Debug, Clone)]
struct SeedPick {
    id: String,
    bin: &'static str,
}

fn pick_degree_bins(graph: &HotGraph, include_max_hub: bool) -> Vec<SeedPick> {
    let ranked: Vec<(String, usize)> = match graph {
        HotGraph::Hash { adj, .. } => out_degrees_hash(adj),
        HotGraph::HashBi { out, .. } => out_degrees_hash(out),
        HotGraph::Csr { ids, csr }
        | HotGraph::CsrCsc { ids, csr, .. }
        | HotGraph::Hybrid { ids, csr, .. } => {
            let mut v: Vec<(String, usize)> = (0..csr.n)
                .map(|i| {
                    let deg = (csr.offsets[i + 1] - csr.offsets[i]) as usize;
                    (ids.id_to_str[i].clone(), deg)
                })
                .filter(|(_, d)| *d > 0)
                .collect();
            v.sort_by_key(|(_, d)| *d);
            v
        }
    };
    if ranked.is_empty() {
        return Vec::new();
    }
    let pick = |p: f64, label: &'static str| -> SeedPick {
        let idx = ((p / 100.0) * (ranked.len() as f64 - 1.0)).round() as usize;
        let idx = idx.min(ranked.len() - 1);
        SeedPick {
            id: ranked[idx].0.clone(),
            bin: label,
        }
    };
    let mut seeds = vec![pick(10.0, "p10"), pick(50.0, "p50"), pick(90.0, "p90")];
    if include_max_hub {
        seeds.push(SeedPick {
            id: ranked.last().unwrap().0.clone(),
            bin: "max_hub",
        });
    }
    seeds
}

/// Emit a deterministic trace from an already-built graph (seed bins from that graph).
pub fn emit_query_trace(
    graph: &HotGraph,
    profile: WorkloadProfile,
    estate_seed: u64,
    trace_len: usize,
) -> Vec<TraceOp> {
    let include_hub = matches!(profile, WorkloadProfile::ReverseHeavy);
    let seeds = pick_degree_bins(graph, include_hub);
    if seeds.is_empty() {
        return Vec::new();
    }
    let (pf, pr, pd) = profile.mix_pct();
    let hops_cycle = [1usize, 2, 3];
    let mut ops = Vec::with_capacity(trace_len);
    for i in 0..trace_len {
        let r = mix(estate_seed ^ 0x72CE, mix(i as u64, profile.id().len() as u64));
        let slot = (r % 100) as u32;
        let qtype = if slot < pf {
            "forward_bfs"
        } else if slot < pf + pr {
            "reverse_blast"
        } else {
            let _ = pd;
            "dependency_chain"
        };
        let seed = &seeds[(r as usize >> 8) % seeds.len()];
        let hops = hops_cycle[(i + (r as usize >> 16)) % hops_cycle.len()];
        let hops = if qtype == "dependency_chain" {
            hops + 1
        } else {
            hops
        };
        ops.push(TraceOp {
            op_id: i as u64 + 1,
            r#type: qtype.into(),
            seed_id: seed.id.clone(),
            seed_degree_bin: seed.bin.into(),
            hops,
        });
    }
    ops
}

pub fn write_trace_jsonl(path: &Path, ops: &[TraceOp]) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let f = File::create(path)?;
    let mut w = BufWriter::new(f);
    for op in ops {
        serde_json::to_writer(&mut w, op)?;
        w.write_all(b"\n")?;
    }
    w.flush()
}

pub fn read_trace_jsonl(path: &Path) -> std::io::Result<Vec<TraceOp>> {
    let f = File::open(path)?;
    let reader = BufReader::new(f);
    let mut ops = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        ops.push(serde_json::from_str(&line)?);
    }
    Ok(ops)
}

pub fn trace_checksum(ops: &[TraceOp]) -> String {
    let mut h = 0u64;
    for op in ops {
        h = mix(h, op.op_id);
        h = mix(h, op.seed_id.len() as u64);
        h = mix(h, op.hops as u64);
        h = mix(h, op.r#type.len() as u64);
    }
    format!("{h:016x}")
}

/// Replay a pre-generated trace against a layout; return events + class breakdown.
pub fn replay_trace(
    graph: &HotGraph,
    ops: &[TraceOp],
    run_id: &str,
    layout: &str,
    reverse_algorithm: &str,
) -> (Vec<QueryEvent>, QueryClassBreakdown) {
    let mut events = Vec::with_capacity(ops.len());
    for op in ops {
        let reverse = op.r#type == "reverse_blast";
        let (reach, ms, names) = bfs(graph, &op.seed_id, op.hops, reverse);
        events.push(QueryEvent {
            query_id: format!("{run_id}-op{}", op.op_id),
            run_id: run_id.into(),
            r#type: op.r#type.clone(),
            seed_id: op.seed_id.clone(),
            seed_degree_bin: op.seed_degree_bin.clone(),
            hops: op.hops,
            edge_type_filter: None,
            concurrency: 1,
            layout: layout.into(),
            reverse_algorithm: reverse_algorithm.into(),
            latency_ms: ms,
            reachable: reach,
            result_checksum: checksum_names(&names),
        });
    }
    let br = class_breakdown(&events);
    (events, br)
}

pub fn mean_class_latency(events: &[QueryEvent], class: &str) -> f64 {
    let v: Vec<f64> = events
        .iter()
        .filter(|e| e.r#type == class)
        .map(|e| e.latency_ms)
        .collect();
    if v.is_empty() {
        return 0.0;
    }
    v.iter().sum::<f64>() / v.len() as f64
}

pub fn class_p50_p95(events: &[QueryEvent], class: &str) -> (f64, f64) {
    let mut v: Vec<f64> = events
        .iter()
        .filter(|e| e.r#type == class)
        .map(|e| e.latency_ms)
        .collect();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    (percentile(&v, 50.0), percentile(&v, 95.0))
}

/// Optional: build lightweight seed list from edge out-degrees without hot layout
/// (used when emitting traces before multi-layout screen — build hash once).
pub fn seeds_from_edge_rows(
    edges: &[crate::synth::EdgeRow],
    include_max_hub: bool,
) -> Vec<(String, &'static str)> {
    let mut counts: HashMap<String, usize> = HashMap::new();
    for e in edges {
        *counts.entry(e.source_id.clone()).or_default() += 1;
    }
    let mut ranked: Vec<(String, usize)> = counts.into_iter().collect();
    ranked.sort_by_key(|(_, d)| *d);
    if ranked.is_empty() {
        return Vec::new();
    }
    let pick = |p: f64, label: &'static str| -> (String, &'static str) {
        let idx = ((p / 100.0) * (ranked.len() as f64 - 1.0)).round() as usize;
        let idx = idx.min(ranked.len() - 1);
        (ranked[idx].0.clone(), label)
    };
    let mut seeds = vec![pick(10.0, "p10"), pick(50.0, "p50"), pick(90.0, "p90")];
    if include_max_hub {
        seeds.push((ranked.last().unwrap().0.clone(), "max_hub"));
    }
    seeds
}

pub fn emit_trace_from_edges(
    edges: &[crate::synth::EdgeRow],
    profile: WorkloadProfile,
    estate_seed: u64,
    trace_len: usize,
) -> Vec<TraceOp> {
    let include_hub = matches!(profile, WorkloadProfile::ReverseHeavy);
    let seeds = seeds_from_edge_rows(edges, include_hub);
    if seeds.is_empty() {
        return Vec::new();
    }
    let (pf, pr, pd) = profile.mix_pct();
    let hops_cycle = [1usize, 2, 3];
    let mut ops = Vec::with_capacity(trace_len);
    for i in 0..trace_len {
        let r = mix(estate_seed ^ 0x72CE, mix(i as u64, profile.id().len() as u64));
        let slot = (r % 100) as u32;
        let qtype = if slot < pf {
            "forward_bfs"
        } else if slot < pf + pr {
            "reverse_blast"
        } else {
            let _ = pd;
            "dependency_chain"
        };
        let seed = &seeds[(r as usize >> 8) % seeds.len()];
        let hops = hops_cycle[(i + (r as usize >> 16)) % hops_cycle.len()];
        let hops = if qtype == "dependency_chain" {
            hops + 1
        } else {
            hops
        };
        ops.push(TraceOp {
            op_id: i as u64 + 1,
            r#type: qtype.into(),
            seed_id: seed.0.clone(),
            seed_degree_bin: seed.1.into(),
            hops,
        });
    }
    ops
}
