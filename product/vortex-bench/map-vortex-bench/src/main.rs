//! Map Vortex cold-load + adjacency rebuild bench.

mod adj;
mod load;
mod synth;
mod write;

use crate::adj::time_adj_and_walk;
use crate::load::{LoadMode, load_parts};
use crate::synth::{EdgeSort, generate_estate, sort_edges};
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
    #[arg(long, default_value_t = 10_000)]
    nodes: usize,
    #[arg(long, default_value_t = 50_000)]
    edges: usize,
    #[arg(long, default_value_t = 42)]
    seed: u64,
    #[arg(long, default_value = "out/map-vortex-bench")]
    out: PathBuf,
    #[arg(long, value_enum, default_value_t = EdgeSort::Clustered)]
    edge_sort: EdgeSort,
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
    load: crate::load::LoadTiming,
    adj: crate::adj::AdjTiming,
    total_cold_to_walk_ms: f64,
}

#[derive(Debug, Serialize)]
struct BenchReport {
    nodes: usize,
    edges: usize,
    seed: u64,
    edge_sort: String,
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

    println!(
        "generating nodes={} edges={} edge_sort={:?} seed={}",
        args.nodes, args.edges, args.edge_sort, args.seed
    );
    let gen_t = std::time::Instant::now();
    let (nodes, mut edges) = generate_estate(args.nodes, args.edges, args.seed);
    sort_edges(&mut edges, args.edge_sort);
    println!(
        "generate+sort_ms={} actual_nodes={} actual_edges={}",
        gen_t.elapsed().as_millis(),
        nodes.len(),
        edges.len()
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

    let modes = [LoadMode::Full, LoadMode::Spine, LoadMode::NodesFullEdgesSpine];
    let mut scenarios = Vec::new();

    for mode in modes {
        for _ in 0..args.warmup {
            let (n, e, _) =
                load_parts(&written.nodes_path, &written.edges_path, mode).await?;
            let _ = time_adj_and_walk(&e, &seed_ci, args.walk_hops)?;
            drop(n);
        }

        let mut samples = Vec::with_capacity(args.repeats);
        for _ in 0..args.repeats {
            let (nodes_b, edges_b, load_t) =
                load_parts(&written.nodes_path, &written.edges_path, mode).await?;
            let adj_t = time_adj_and_walk(&edges_b, &seed_ci, args.walk_hops)?;
            let total = load_t.nodes_decode_ms + load_t.edges_decode_ms + adj_t.build_ms + adj_t.bfs_ms;
            samples.push(ScenarioResult {
                edge_sort: format!("{:?}", args.edge_sort),
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
            "mode={:<24} nodes_ms={:>7.2} edges_ms={:>7.2} adj_ms={:>7.2} bfs_ms={:>6.2} total={:>7.2} reachable={}",
            median.load.mode,
            median.load.nodes_decode_ms,
            median.load.edges_decode_ms,
            median.adj.build_ms,
            median.adj.bfs_ms,
            median.total_cold_to_walk_ms,
            median.adj.bfs_reachable
        );
        scenarios.push(median);
    }

    let report = BenchReport {
        nodes: nodes.len(),
        edges: edges.len(),
        seed: args.seed,
        edge_sort: format!("{:?}", args.edge_sort),
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
        "estate nodes={} edges={} sort={} parts_bytes={}",
        report.nodes,
        report.edges,
        report.edge_sort,
        report.parts.nodes_bytes + report.parts.edges_bytes
    );
    for s in &report.scenarios {
        println!(
            "{:<24} decode(n+e)={:>7.2}  adj={:>7.2}  bfs={:>6.2}  total={:>7.2}",
            s.load.mode,
            s.load.nodes_decode_ms + s.load.edges_decode_ms,
            s.adj.build_ms,
            s.adj.bfs_ms,
            s.total_cold_to_walk_ms
        );
    }
}
