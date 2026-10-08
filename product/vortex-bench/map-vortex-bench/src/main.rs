//! Map Vortex cold-load + adjacency rebuild bench.

mod adj;
mod load;
mod synth;
mod write;

use crate::adj::{AdjBuilder, time_adj_and_walk};
use crate::load::{LoadMode, load_parts};
use crate::synth::{
    DegreeStats, EdgeSort, EstateConfig, EstateShape, generate_estate, nodes_for_density,
    sort_edges,
};
use crate::write::write_parts;
use anyhow::Result;
use clap::Parser;
use serde::Serialize;
use std::path::PathBuf;

#[derive(Debug, Parser)]
#[command(
    name = "map_vortex_bench",
    about = "Measure Motadata map Vortex cold load (projection) + hot adjacency rebuild"
)]
struct Args {
    /// Node count. Ignored when `--fix-nodes-from-density` is set.
    #[arg(long, default_value_t = 10_000)]
    nodes: usize,
    #[arg(long, default_value_t = 50_000)]
    edges: usize,
    /// Target average out-degree (`edges / nodes`). Used with `--fix-nodes-from-density`.
    #[arg(long, default_value_t = 5.0)]
    mean_out_degree: f64,
    /// Set `nodes = round(edges / mean_out_degree)` so scale sweeps keep density fixed.
    #[arg(long, default_value_t = false)]
    fix_nodes_from_density: bool,
    #[arg(long, default_value_t = 42)]
    seed: u64,
    #[arg(long, default_value = "out/map-vortex-bench")]
    out: PathBuf,
    #[arg(long, value_enum, default_value_t = EdgeSort::Clustered)]
    edge_sort: EdgeSort,
    #[arg(long, value_enum, default_value_t = EstateShape::Uniform)]
    estate_shape: EstateShape,
    /// Fraction of nodes that are hubs (`hubby` only).
    #[arg(long, default_value_t = 0.01)]
    hub_fraction: f64,
    /// Fraction of edges whose source is a hub (`hubby` only).
    #[arg(long, default_value_t = 0.50)]
    hub_edge_share: f64,
    /// Adjacency builders to time (repeatable). Default: both.
    #[arg(long, value_enum, default_values_t = vec![AdjBuilder::Naive, AdjBuilder::SortAware])]
    adj_builder: Vec<AdjBuilder>,
    /// Load modes to time (repeatable). Default: all three.
    #[arg(long, value_enum, default_values_t = vec![LoadMode::Full, LoadMode::Spine, LoadMode::NodesFullEdgesSpine])]
    load_mode: Vec<LoadMode>,
    /// Seed CI for BFS; default = first generated node entity_id
    #[arg(long)]
    seed_ci: Option<String>,
    #[arg(long, default_value_t = 2)]
    walk_hops: usize,
    #[arg(long, default_value_t = 1)]
    warmup: usize,
    #[arg(long, default_value_t = 3)]
    repeats: usize,
}

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
struct ScenarioResult {
    edge_sort: String,
    estate_shape: String,
    load: crate::load::LoadTiming,
    adj: crate::adj::AdjTiming,
    total_cold_to_walk_ms: f64,
}

#[derive(Debug, Serialize)]
struct BenchReport {
    nodes: usize,
    edges: usize,
    seed: u64,
    mean_out_degree_target: f64,
    fix_nodes_from_density: bool,
    edge_sort: String,
    estate_shape: String,
    hub_fraction: f64,
    hub_edge_share: f64,
    degree_stats: DegreeStats,
    parts: PartSummary,
    scenarios: Vec<ScenarioResult>,
}

#[derive(Debug, Serialize)]
struct PartSummary {
    nodes_path: String,
    edges_path: String,
    nodes_bytes: u64,
    edges_bytes: u64,
    write_ms: u128,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();
    std::fs::create_dir_all(&args.out)?;

    let nodes_n = if args.fix_nodes_from_density {
        nodes_for_density(args.edges, args.mean_out_degree)
    } else {
        args.nodes
    };

    let cfg = EstateConfig {
        nodes_n,
        edges_n: args.edges,
        seed: args.seed,
        shape: args.estate_shape,
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
    };

    println!(
        "generating nodes={} edges={} shape={} edge_sort={:?} mean_out_degree_target={:.2} seed={}",
        cfg.nodes_n,
        cfg.edges_n,
        cfg.shape.id(),
        args.edge_sort,
        args.mean_out_degree,
        args.seed
    );
    let gen_t = std::time::Instant::now();
    let (nodes, mut edges, degree_stats) = generate_estate(&cfg);
    sort_edges(&mut edges, args.edge_sort);
    println!(
        "generate+sort_ms={} actual_nodes={} actual_edges={} max_out={} p99_out={} top1pct_edge_share={:.3}",
        gen_t.elapsed().as_millis(),
        nodes.len(),
        edges.len(),
        degree_stats.max_out_degree,
        degree_stats.p99_out_degree,
        degree_stats.top1pct_sources_edge_share
    );

    let seed_ci = args
        .seed_ci
        .clone()
        .unwrap_or_else(|| nodes[0].entity_id.clone());
    println!("bfs_seed_ci={seed_ci}");

    let parts_dir = args.out.join(format!("{:?}", args.edge_sort).to_lowercase());
    let written = write_parts(&nodes, &edges, &parts_dir).await?;
    println!(
        "wrote nodes_bytes={} edges_bytes={} write_ms={}",
        written.nodes_bytes, written.edges_bytes, written.write_ms
    );

    let builders = if args.adj_builder.is_empty() {
        vec![AdjBuilder::Naive, AdjBuilder::SortAware]
    } else {
        args.adj_builder.clone()
    };
    let modes = if args.load_mode.is_empty() {
        vec![LoadMode::Full, LoadMode::Spine, LoadMode::NodesFullEdgesSpine]
    } else {
        args.load_mode.clone()
    };

    let mut scenarios = Vec::new();

    for mode in modes {
        for builder in &builders {
            for _ in 0..args.warmup {
                let (n, e, _) =
                    load_parts(&written.nodes_path, &written.edges_path, mode).await?;
                let _ = time_adj_and_walk(&e, &seed_ci, args.walk_hops, *builder)?;
                drop(n);
            }

            let mut samples = Vec::with_capacity(args.repeats);
            for _ in 0..args.repeats {
                let (nodes_b, edges_b, load_t) =
                    load_parts(&written.nodes_path, &written.edges_path, mode).await?;
                let adj_t = time_adj_and_walk(&edges_b, &seed_ci, args.walk_hops, *builder)?;
                let total = load_t.nodes_decode_ms
                    + load_t.edges_decode_ms
                    + adj_t.build_ms
                    + adj_t.bfs_ms;
                samples.push(ScenarioResult {
                    edge_sort: format!("{:?}", args.edge_sort),
                    estate_shape: args.estate_shape.id().into(),
                    load: load_t,
                    adj: adj_t,
                    total_cold_to_walk_ms: total,
                });
                drop(nodes_b);
                drop(edges_b);
            }
            samples.sort_by(|a, b| {
                a.total_cold_to_walk_ms
                    .partial_cmp(&b.total_cold_to_walk_ms)
                    .unwrap()
            });
            let median = samples[samples.len() / 2].clone();
            println!(
                "mode={:<24} builder={:<11} nodes_ms={:>7.2} edges_ms={:>7.2} adj_ms={:>7.2} bfs_ms={:>6.2} total={:>7.2} src_key_clones={} hm_ops={} groups={} reachable={}",
                median.load.mode,
                median.adj.builder,
                median.load.nodes_decode_ms,
                median.load.edges_decode_ms,
                median.adj.build_ms,
                median.adj.bfs_ms,
                median.total_cold_to_walk_ms,
                median.adj.profile.source_key_clones,
                median.adj.profile.hashmap_source_ops,
                median.adj.profile.source_groups,
                median.adj.bfs_reachable
            );
            scenarios.push(median);
        }
    }

    let report = BenchReport {
        nodes: nodes.len(),
        edges: edges.len(),
        seed: args.seed,
        mean_out_degree_target: args.mean_out_degree,
        fix_nodes_from_density: args.fix_nodes_from_density,
        edge_sort: format!("{:?}", args.edge_sort),
        estate_shape: args.estate_shape.id().into(),
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        degree_stats,
        parts: PartSummary {
            nodes_path: written.nodes_path.display().to_string(),
            edges_path: written.edges_path.display().to_string(),
            nodes_bytes: written.nodes_bytes,
            edges_bytes: written.edges_bytes,
            write_ms: written.write_ms,
        },
        scenarios,
    };
    let path = args.out.join("results.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    println!("wrote {}", path.display());
    print_summary(&report);
    Ok(())
}

fn print_summary(report: &BenchReport) {
    println!("\n=== Cold load → adjacency → BFS (median) ===");
    println!(
        "estate nodes={} edges={} shape={} sort={} mean_out={:.2} max_out={} top1pct_share={:.3} parts_bytes={}",
        report.nodes,
        report.edges,
        report.estate_shape,
        report.edge_sort,
        report.degree_stats.mean_out_degree,
        report.degree_stats.max_out_degree,
        report.degree_stats.top1pct_sources_edge_share,
        report.parts.nodes_bytes + report.parts.edges_bytes
    );
    for s in &report.scenarios {
        println!(
            "{:<24} {:<11} decode(n+e)={:>7.2}  adj={:>7.2}  bfs={:>6.2}  total={:>7.2}  key_clones={} hm_ops={}",
            s.load.mode,
            s.adj.builder,
            s.load.nodes_decode_ms + s.load.edges_decode_ms,
            s.adj.build_ms,
            s.adj.bfs_ms,
            s.total_cold_to_walk_ms,
            s.adj.profile.source_key_clones,
            s.adj.profile.hashmap_source_ops
        );
    }
}
