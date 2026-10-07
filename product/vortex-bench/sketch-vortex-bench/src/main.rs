//! Sketch Vortex physical layout bench — layouts A–E × queries Q1–Q8.

mod synth;
mod layouts;
mod queries;

use crate::synth::{SortOrder, generate_rows, sort_rows};
use crate::layouts::{Layout, write_layout};
use crate::queries::{QUERIES, QueryResult, run_query};
use anyhow::Result;
use clap::Parser;
use serde::Serialize;
use std::path::PathBuf;

#[derive(Debug, Parser)]
#[command(
    name = "sketch_vortex_bench",
    about = "Compare Vortex physical layouts for Motadata sketch.v2 staged RCA reads"
)]
struct Args {
    /// Number of synthetic sketch rows
    #[arg(long, default_value_t = 50_000)]
    rows: usize,
    /// Distinct entities in the synthetic estate
    #[arg(long, default_value_t = 256)]
    entities: usize,
    /// Distinct metrics (capped by generator catalog)
    #[arg(long, default_value_t = 4)]
    metrics: usize,
    /// RNG seed
    #[arg(long, default_value_t = 42)]
    seed: u64,
    /// Output directory for .vortex parts + results.json
    #[arg(long, default_value = "out/sketch-vortex-bench")]
    out: PathBuf,
    /// Row clustering for zone locality experiments
    #[arg(long, value_enum, default_value_t = SortOrder::Clustered)]
    sort: SortOrder,
    /// Layouts to build (default: all)
    #[arg(long, value_enum)]
    layout: Vec<Layout>,
    /// Target entity for post-decode filter stats
    #[arg(long, default_value = "svc-0001")]
    entity: String,
    /// Warm-up passes per query (not reported)
    #[arg(long, default_value_t = 1)]
    warmup: usize,
    /// Timed repeats per query (median reported)
    #[arg(long, default_value_t = 3)]
    repeats: usize,
}

#[derive(Debug, Serialize)]
struct BenchReport {
    rows: usize,
    entities: usize,
    metrics: usize,
    seed: u64,
    sort: String,
    target_entity: String,
    layouts: Vec<LayoutSummary>,
    queries: Vec<QueryResult>,
}

#[derive(Debug, Serialize)]
struct LayoutSummary {
    layout: String,
    files: Vec<String>,
    total_bytes: u64,
    write_ms: u128,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();
    std::fs::create_dir_all(&args.out)?;

    println!(
        "generating rows={} entities={} metrics={} sort={:?} seed={}",
        args.rows, args.entities, args.metrics, args.sort, args.seed
    );
    let gen_started = std::time::Instant::now();
    let mut rows = generate_rows(args.rows, args.seed, args.entities, args.metrics);
    sort_rows(&mut rows, args.sort);
    println!("generate+sort_ms={}", gen_started.elapsed().as_millis());

    let layouts = if args.layout.is_empty() {
        vec![
            Layout::Nested,
            Layout::FlatWide,
            Layout::SpineNestedCold,
            Layout::SpineFlatEvidence,
            Layout::SplitTables,
        ]
    } else {
        args.layout.clone()
    };

    let mut layout_summaries = Vec::new();
    let mut written = Vec::new();
    for layout in layouts {
        println!("writing {} …", layout.id());
        let w = write_layout(&rows, layout, &args.out).await?;
        println!(
            "  files={} total_bytes={} write_ms={}",
            w.paths.len(),
            w.total_bytes,
            w.write_ms
        );
        layout_summaries.push(LayoutSummary {
            layout: w.layout.id().into(),
            files: w
                .paths
                .iter()
                .map(|p| p.display().to_string())
                .collect(),
            total_bytes: w.total_bytes,
            write_ms: w.write_ms,
        });
        written.push(w);
    }

    let mut all_queries = Vec::new();
    for w in &written {
        for q in QUERIES {
            for _ in 0..args.warmup {
                let _ = run_query(w, q, &args.entity).await?;
            }
            let mut samples = Vec::with_capacity(args.repeats);
            for _ in 0..args.repeats {
                samples.push(run_query(w, q, &args.entity).await?);
            }
            samples.sort_by(|a, b| a.decode_ms.partial_cmp(&b.decode_ms).unwrap());
            let median = samples[samples.len() / 2].clone();
            println!(
                "{:<22} {:<4} decode_ms={:>8.2} rows={} matched={} cols={}",
                median.layout,
                median.query,
                median.decode_ms,
                median.rows_decoded,
                median.rows_matched_filter,
                median.projected_columns.join(",")
            );
            all_queries.push(median);
        }
    }

    let report = BenchReport {
        rows: args.rows,
        entities: args.entities,
        metrics: args.metrics,
        seed: args.seed,
        sort: format!("{:?}", args.sort),
        target_entity: args.entity,
        layouts: layout_summaries,
        queries: all_queries,
    };
    let report_path = args.out.join("results.json");
    std::fs::write(&report_path, serde_json::to_string_pretty(&report)?)?;
    println!("wrote {}", report_path.display());
    print_stage1_summary(&report);
    Ok(())
}

fn print_stage1_summary(report: &BenchReport) {
    println!("\n=== Stage-1 decode_ms (Q1,Q2,Q7) by layout ===");
    for layout in report.layouts.iter().map(|l| l.layout.as_str()) {
        let mut ms = Vec::new();
        for qid in ["Q1", "Q2", "Q7"] {
            if let Some(r) = report
                .queries
                .iter()
                .find(|r| r.layout == layout && r.query == qid)
            {
                ms.push(format!("{qid}={:.1}", r.decode_ms));
            }
        }
        let bytes = report
            .layouts
            .iter()
            .find(|l| l.layout == layout)
            .map(|l| l.total_bytes)
            .unwrap_or(0);
        println!("{layout:<22} bytes={bytes:<12} {}", ms.join("  "));
    }
}
