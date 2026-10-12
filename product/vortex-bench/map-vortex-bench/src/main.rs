//! Map Vortex cold-load + hot adjacency bench (Design v3 Stages 1–4.2).

mod adj;
mod estate;
mod hot;
mod index_mem;
mod load;
mod manifest;
mod properties;
mod query;
mod rss;
mod synth;
mod workload;
mod write;

use crate::adj::AdjBuilder;
use crate::estate::{EstateFamily, FamilyConfig, generate_family};
use crate::hot::{
    HotLayoutKind, apply_hybrid_churn, bfs, build_hot, checksum_names,
};
use crate::index_mem::estimate_index_memory;
use crate::load::{LoadMode, load_parts};
use crate::manifest::{
    PartsBytes, PhasesMs, RunManifest, git_sha, host_name, now_rfc3339, write_manifest,
};
use crate::properties::{compute_properties, estate_checksum};
use crate::query::{QueryClassBreakdown, class_breakdown, percentile, run_query_mix, write_query_jsonl};
use crate::rss::peak_rss_bytes;
use crate::synth::{DegreeStats, EdgeSort, EstateShape, nodes_for_density, sort_edges};
use crate::workload::{
    WorkloadProfile, emit_trace_from_edges, read_trace_jsonl, replay_trace, trace_checksum,
    write_trace_jsonl,
};
use crate::write::write_parts;
use anyhow::{Result, bail};
use clap::{Parser, ValueEnum};
use serde::Serialize;
use std::path::PathBuf;

const MAX_EDGES_DEFAULT: usize = 5_000_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
enum Coldness {
    ProcessCold,
    PageCacheWarm,
}

impl Coldness {
    fn id(self) -> &'static str {
        match self {
            Self::ProcessCold => "process_cold",
            Self::PageCacheWarm => "page_cache_warm",
        }
    }
}

#[derive(Debug, Parser)]
#[command(
    name = "map_vortex_bench",
    about = "Measure Motadata map Vortex cold load + hot adjacency (Design v3)"
)]
struct Args {
    #[arg(long, default_value_t = 10_000)]
    nodes: usize,
    #[arg(long, default_value_t = 50_000)]
    edges: usize,
    #[arg(long, default_value_t = 5.0)]
    mean_out_degree: f64,
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
    /// Stage 4 family (overrides --estate-shape when set).
    #[arg(long, value_enum)]
    estate_family: Option<EstateFamily>,
    #[arg(long, default_value_t = 0.01)]
    hub_fraction: f64,
    #[arg(long, default_value_t = 0.50)]
    hub_edge_share: f64,
    #[arg(long, value_enum, default_values_t = vec![AdjBuilder::Naive, AdjBuilder::SortAware])]
    adj_builder: Vec<AdjBuilder>,
    #[arg(long, value_enum, default_values_t = vec![LoadMode::Full, LoadMode::Spine, LoadMode::NodesFullEdgesSpine])]
    load_mode: Vec<LoadMode>,
    #[arg(long, value_enum, default_values_t = vec![HotLayoutKind::Hash])]
    layout: Vec<HotLayoutKind>,
    #[arg(long, value_enum, default_value_t = Coldness::ProcessCold)]
    coldness: Coldness,
    #[arg(long)]
    seed_ci: Option<String>,
    #[arg(long, default_value_t = 2)]
    walk_hops: usize,
    #[arg(long, default_value_t = 1)]
    warmup: usize,
    #[arg(long, default_value_t = 3)]
    repeats: usize,
    #[arg(long, default_value = "adhoc")]
    workload_id: String,
    #[arg(long)]
    git_sha: Option<String>,
    /// Emit Stage 2/3 equal-mix query JSONL after build.
    #[arg(long, default_value_t = false)]
    emit_queries: bool,
    #[arg(long, default_value_t = 1)]
    query_replicate: usize,
    #[arg(long, default_value_t = 0)]
    hybrid_inserts: usize,
    #[arg(long, default_value_t = 0)]
    hybrid_deletes: usize,
    // —— Stage 4 ——
    #[arg(long, value_enum)]
    workload_profile: Option<WorkloadProfile>,
    /// Write deterministic query-trace JSONL (from edge degrees; no layout needed).
    #[arg(long)]
    emit_query_trace: Option<PathBuf>,
    /// Emit all three Stage-4 workload traces into this directory.
    #[arg(long)]
    emit_all_workload_traces: Option<PathBuf>,
    /// Replay this query-trace JSONL instead of Stage 2/3 equal mix.
    #[arg(long)]
    query_trace: Option<PathBuf>,
    #[arg(long, default_value_t = 200)]
    trace_len: usize,
    #[arg(long, default_value_t = false)]
    validate_properties: bool,
    /// Generate + validate properties only (Phase 4.1); no layout timing.
    #[arg(long, default_value_t = false)]
    characterize_only: bool,
    /// Skip Vortex write; reuse existing parts under DIR/{edge_sort}/.
    #[arg(long)]
    reuse_parts: Option<PathBuf>,
    /// Skip estate generation (requires --reuse-parts and --seed-ci).
    #[arg(long, default_value_t = false)]
    skip_estate_generate: bool,
    /// Prepare estate + traces only (write parts, no layout timing).
    #[arg(long, default_value_t = false)]
    prepare_only: bool,
    #[arg(long, default_value_t = MAX_EDGES_DEFAULT)]
    max_edges: usize,
}

#[derive(Debug, Clone, Serialize)]
struct SampleTiming {
    decode_nodes_ms: f64,
    decode_edges_ms: f64,
    build_ms: f64,
    bfs_ms: f64,
    total_ms: f64,
    reachable: usize,
    checksum: String,
    profile: crate::adj::BuildProfile,
}

#[derive(Debug, Clone, Serialize)]
struct ScenarioResult {
    edge_sort: String,
    estate_shape: String,
    layout: String,
    adj_builder: String,
    load_mode: String,
    coldness: String,
    median: SampleTiming,
    p95_total_ms: f64,
    p50_total_ms: f64,
    samples: usize,
    correctness_ok: bool,
    peak_rss_bytes: Option<u64>,
    steady_index_bytes: Option<u64>,
    query_events: usize,
    query_p50_ms: Option<f64>,
    query_p95_ms: Option<f64>,
    query_by_class: Option<QueryClassBreakdown>,
    reverse_algorithm: String,
    workload_profile: Option<String>,
    trace_checksum: Option<String>,
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
    coldness: String,
    workload_id: String,
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

fn resolve_family(args: &Args) -> EstateFamily {
    if let Some(f) = args.estate_family {
        return f;
    }
    match args.estate_shape {
        EstateShape::Uniform => EstateFamily::Uniform,
        EstateShape::Hubby => EstateFamily::Hubby,
        EstateShape::PowerLaw => EstateFamily::PowerLaw,
        EstateShape::Hierarchical => EstateFamily::Hierarchical,
        EstateShape::Community => EstateFamily::Community,
        EstateShape::Layered => EstateFamily::Layered,
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();
    std::fs::create_dir_all(&args.out)?;

    if args.edges > args.max_edges {
        bail!(
            "edges={} exceeds --max-edges={} (Stage 4 screening ceiling)",
            args.edges,
            args.max_edges
        );
    }

    let family = resolve_family(&args);
    let sort_name = format!("{:?}", args.edge_sort).to_lowercase();

    let (nodes_len, edges_len, degree_stats, seed_ci, written) = if args.skip_estate_generate {
        let reuse = args
            .reuse_parts
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("--skip-estate-generate requires --reuse-parts"))?;
        let seed_ci = args
            .seed_ci
            .clone()
            .ok_or_else(|| anyhow::anyhow!("--skip-estate-generate requires --seed-ci"))?;
        let parts_dir = reuse.join(&sort_name);
        let nodes_path = parts_dir.join("nodes.vortex");
        let edges_path = parts_dir.join("edges.vortex");
        if !nodes_path.exists() || !edges_path.exists() {
            bail!("reuse_parts missing vortex under {}", parts_dir.display());
        }
        let nodes_bytes = std::fs::metadata(&nodes_path)?.len();
        let edges_bytes = std::fs::metadata(&edges_path)?.len();
        println!(
            "skip_estate_generate reuse_parts={} seed_ci={}",
            parts_dir.display(),
            seed_ci
        );
        let degree_stats = DegreeStats {
            mean_out_degree: args.mean_out_degree,
            sources_with_edges: 0,
            max_out_degree: 0,
            p50_out_degree: 0,
            p95_out_degree: 0,
            p99_out_degree: 0,
            top1pct_sources_edge_share: 0.0,
        };
        let written = crate::write::WrittenParts {
            nodes_path,
            edges_path,
            nodes_bytes,
            edges_bytes,
            write_ms: 0,
        };
        // Approximate counts from CLI (actual encoded in parts).
        let nodes_n = if args.fix_nodes_from_density {
            nodes_for_density(args.edges, args.mean_out_degree)
        } else {
            args.nodes
        };
        (nodes_n, args.edges, degree_stats, seed_ci, written)
    } else {
        let nodes_n = if args.fix_nodes_from_density {
            nodes_for_density(args.edges, args.mean_out_degree)
        } else {
            args.nodes
        };

        println!(
            "generating nodes={} edges={} family={} edge_sort={:?} mean_out_degree_target={:.2} seed={}",
            nodes_n,
            args.edges,
            family.id(),
            args.edge_sort,
            args.mean_out_degree,
            args.seed
        );
        let gen_t = std::time::Instant::now();
        let fcfg = FamilyConfig {
            family,
            nodes_n,
            edges_n: args.edges,
            seed: args.seed,
            hub_fraction: args.hub_fraction,
            hub_edge_share: args.hub_edge_share,
            pa_softener: 1.0,
        };
        let (nodes, mut edges, meta) = generate_family(&fcfg);
        sort_edges(&mut edges, args.edge_sort);
        let degree_stats = crate::synth::degree_stats(&edges, nodes.len());
        println!(
            "generate+sort_ms={} actual_nodes={} actual_edges={} max_out={} p99_out={} top1pct_edge_share={:.3} notes={}",
            gen_t.elapsed().as_millis(),
            nodes.len(),
            edges.len(),
            degree_stats.max_out_degree,
            degree_stats.p99_out_degree,
            degree_stats.top1pct_sources_edge_share,
            meta.generator_notes
        );

        let communities = meta.communities;
        let props = compute_properties(family, &nodes, &edges, communities);
        let checksum = estate_checksum(&nodes, &edges);
        if args.validate_properties || args.characterize_only || args.prepare_only {
            let ppath = args.out.join("properties.json");
            std::fs::write(&ppath, serde_json::to_string_pretty(&props)?)?;
            std::fs::write(args.out.join("estate_checksum.txt"), format!("{checksum}\n"))?;
            std::fs::write(
                args.out.join("estate_meta.json"),
                serde_json::to_string_pretty(&meta)?,
            )?;
            println!(
                "properties validation_ok={} notes={:?} checksum={checksum} wrote {}",
                props.validation_ok,
                props.validation_notes,
                ppath.display()
            );
            if !props.validation_ok {
                bail!(
                    "family {} property validation failed: {:?}",
                    family.id(),
                    props.validation_notes
                );
            }
        }
        if args.characterize_only {
            println!("characterize_only: done");
            return Ok(());
        }

        if let Some(tdir) = &args.emit_all_workload_traces {
            std::fs::create_dir_all(tdir)?;
            for profile in WorkloadProfile::all() {
                let ops = emit_trace_from_edges(&edges, *profile, args.seed, args.trace_len);
                let tpath = tdir.join(format!("{}.jsonl", profile.id()));
                write_trace_jsonl(&tpath, &ops)?;
                println!(
                    "wrote query_trace {} ops={} checksum={} profile={}",
                    tpath.display(),
                    ops.len(),
                    trace_checksum(&ops),
                    profile.id()
                );
            }
        }
        if let Some(tpath) = &args.emit_query_trace {
            let profile = args
                .workload_profile
                .unwrap_or(WorkloadProfile::Balanced);
            let ops = emit_trace_from_edges(&edges, profile, args.seed, args.trace_len);
            write_trace_jsonl(tpath, &ops)?;
            println!(
                "wrote query_trace {} ops={} checksum={} profile={}",
                tpath.display(),
                ops.len(),
                trace_checksum(&ops),
                profile.id()
            );
        }

        let seed_ci = args
            .seed_ci
            .clone()
            .unwrap_or_else(|| nodes[0].entity_id.clone());
        std::fs::write(args.out.join("seed_ci.txt"), format!("{seed_ci}\n"))?;
        println!("bfs_seed_ci={seed_ci}");

        let written = if let Some(reuse) = &args.reuse_parts {
            let parts_dir = reuse.join(&sort_name);
            let nodes_path = parts_dir.join("nodes.vortex");
            let edges_path = parts_dir.join("edges.vortex");
            if !nodes_path.exists() || !edges_path.exists() {
                bail!("reuse_parts missing vortex under {}", parts_dir.display());
            }
            let nodes_bytes = std::fs::metadata(&nodes_path)?.len();
            let edges_bytes = std::fs::metadata(&edges_path)?.len();
            println!(
                "reuse_parts nodes_bytes={} edges_bytes={} dir={}",
                nodes_bytes,
                edges_bytes,
                parts_dir.display()
            );
            crate::write::WrittenParts {
                nodes_path,
                edges_path,
                nodes_bytes,
                edges_bytes,
                write_ms: 0,
            }
        } else {
            let parts_dir = args.out.join(&sort_name);
            let w = write_parts(&nodes, &edges, &parts_dir).await?;
            println!(
                "wrote nodes_bytes={} edges_bytes={} write_ms={}",
                w.nodes_bytes, w.edges_bytes, w.write_ms
            );
            w
        };

        if args.prepare_only {
            println!("prepare_only: done");
            return Ok(());
        }

        (nodes.len(), edges.len(), degree_stats, seed_ci, written)
    };

    let builders = if args.adj_builder.is_empty() {
        vec![AdjBuilder::SortAware]
    } else {
        args.adj_builder.clone()
    };
    let modes = if args.load_mode.is_empty() {
        vec![LoadMode::Spine]
    } else {
        args.load_mode.clone()
    };
    let layouts = if args.layout.is_empty() {
        vec![HotLayoutKind::Hash]
    } else {
        args.layout.clone()
    };

    let preloaded_trace = if let Some(tp) = &args.query_trace {
        Some(read_trace_jsonl(tp)?)
    } else {
        None
    };
    let trace_cs = preloaded_trace.as_ref().map(|o| trace_checksum(o));

    let dataset_id = format!(
        "synth-{}-e{}-n{}-s{}",
        family.id(),
        edges_len,
        nodes_len,
        args.seed
    );
    let sha = git_sha(&args.git_sha);
    let host = host_name();
    let shape_id = family.id();

    let mut scenarios = Vec::new();
    let mut last_manifest: Option<RunManifest> = None;

    for mode in &modes {
        if args.coldness == Coldness::PageCacheWarm {
            let (_n, _e, _) =
                load_parts(&written.nodes_path, &written.edges_path, *mode).await?;
        }

        for layout in &layouts {
            for builder in &builders {
                let effective_builder = if *layout == HotLayoutKind::Hash
                    || *layout == HotLayoutKind::HashBi
                {
                    *builder
                } else {
                    AdjBuilder::SortAware
                };
                if !matches!(layout, HotLayoutKind::Hash | HotLayoutKind::HashBi)
                    && *builder != builders[0]
                {
                    continue;
                }

                for _ in 0..args.warmup {
                    let (_n, e, _) =
                        load_parts(&written.nodes_path, &written.edges_path, *mode).await?;
                    let (mut g, _) = build_hot(&e, *layout, effective_builder)?;
                    if *layout == HotLayoutKind::Hybrid {
                        apply_hybrid_churn(
                            &mut g,
                            args.hybrid_inserts,
                            args.hybrid_deletes,
                            args.seed,
                        );
                    }
                    let _ = bfs(&g, &seed_ci, args.walk_hops, false);
                }

                let mut samples = Vec::with_capacity(args.repeats);
                let mut ref_checksum: Option<String> = None;
                let mut correctness_ok = true;
                let mut query_events_count = 0usize;
                let mut query_p50 = None;
                let mut query_p95 = None;
                let mut query_by_class: Option<QueryClassBreakdown> = None;
                let mut query_path: Option<String> = None;
                let mut steady_bytes: Option<u64> = None;
                let rev_algo = layout.reverse_algorithm();

                for rep in 0..args.repeats {
                    let (_nodes_b, edges_b, load_t) =
                        load_parts(&written.nodes_path, &written.edges_path, *mode).await?;
                    let (mut g, build_t) = build_hot(&edges_b, *layout, effective_builder)?;
                    if *layout == HotLayoutKind::Hybrid {
                        apply_hybrid_churn(
                            &mut g,
                            args.hybrid_inserts,
                            args.hybrid_deletes,
                            args.seed,
                        );
                    }
                    let (reach, bfs_ms, names) = bfs(&g, &seed_ci, args.walk_hops, false);
                    let checksum = checksum_names(&names);
                    if let Some(r) = &ref_checksum {
                        if r != &checksum {
                            correctness_ok = false;
                        }
                    } else {
                        ref_checksum = Some(checksum.clone());
                    }
                    let total = load_t.nodes_decode_ms
                        + load_t.edges_decode_ms
                        + build_t.build_ms
                        + bfs_ms;
                    samples.push(SampleTiming {
                        decode_nodes_ms: load_t.nodes_decode_ms,
                        decode_edges_ms: load_t.edges_decode_ms,
                        build_ms: build_t.build_ms,
                        bfs_ms,
                        total_ms: total,
                        reachable: reach,
                        checksum,
                        profile: build_t.profile.clone(),
                    });

                    if rep + 1 == args.repeats {
                        // Steady-state estimate after last build (decode buffers already dropped).
                        let est = estimate_index_memory(&g);
                        steady_bytes = Some(est.steady_index_bytes);
                        std::fs::write(
                            args.out.join(format!(
                                "{}-{}-index_mem.json",
                                shape_id,
                                layout.id()
                            )),
                            serde_json::to_string_pretty(&est)?,
                        )?;

                        if let Some(ops) = &preloaded_trace {
                            let run_id = format!(
                                "{}-{}-{}-{}",
                                args.workload_id,
                                shape_id,
                                layout.id(),
                                args.workload_profile
                                    .map(|p| p.id())
                                    .unwrap_or("trace")
                            );
                            let (events, br) =
                                replay_trace(&g, ops, &run_id, layout.id(), rev_algo);
                            let qpath = args.out.join(format!("{run_id}-queries.jsonl"));
                            write_query_jsonl(&qpath, &events)?;
                            query_path = Some(qpath.display().to_string());
                            query_events_count = events.len();
                            query_p50 = Some(br.aggregate.p50_ms);
                            query_p95 = Some(br.aggregate.p95_ms);
                            query_by_class = Some(br);
                        } else if args.emit_queries {
                            let run_id = format!(
                                "{}-{}-{}-{}-{}",
                                args.workload_id,
                                shape_id,
                                format!("{:?}", args.edge_sort).to_lowercase(),
                                layout.id(),
                                effective_builder.id()
                            );
                            let events = run_query_mix(
                                &g,
                                &run_id,
                                layout.id(),
                                rev_algo,
                                &[1, 2, 3],
                                args.query_replicate,
                            );
                            let qpath = args.out.join(format!("{run_id}-queries.jsonl"));
                            write_query_jsonl(&qpath, &events)?;
                            query_path = Some(qpath.display().to_string());
                            query_events_count = events.len();
                            let br = class_breakdown(&events);
                            query_p50 = Some(br.aggregate.p50_ms);
                            query_p95 = Some(br.aggregate.p95_ms);
                            query_by_class = Some(br);
                        }
                    }
                }

                if !matches!(layout, HotLayoutKind::Hash | HotLayoutKind::HashBi) {
                    let (_n, e, _) =
                        load_parts(&written.nodes_path, &written.edges_path, *mode).await?;
                    let (href, _) = build_hot(&e, HotLayoutKind::Hash, AdjBuilder::SortAware)?;
                    let (_r, _ms, ref_names) = bfs(&href, &seed_ci, args.walk_hops, false);
                    let ref_cs = checksum_names(&ref_names);
                    if samples.last().map(|s| s.checksum.as_str()) != Some(ref_cs.as_str()) {
                        if args.hybrid_inserts == 0 && args.hybrid_deletes == 0 {
                            correctness_ok = false;
                        }
                    }
                }

                samples.sort_by(|a, b| a.total_ms.partial_cmp(&b.total_ms).unwrap());
                let median = samples[samples.len() / 2].clone();
                let mut totals: Vec<f64> = samples.iter().map(|s| s.total_ms).collect();
                totals.sort_by(|a, b| a.partial_cmp(b).unwrap());
                let p50 = percentile(&totals, 50.0);
                let p95 = percentile(&totals, 95.0);
                let peak = peak_rss_bytes();

                let (fwd95, rev95) = query_by_class
                    .as_ref()
                    .map(|c| (c.forward_bfs.p95_ms, c.reverse_blast.p95_ms))
                    .unwrap_or((0.0, 0.0));
                println!(
                    "mode={:<24} layout={:<8} builder={:<11} adj_ms={:>7.2} total_p50={:>7.2} fwd_p95={:>8.3} rev_p95={:>8.3} rss={:?} idx={:?} ok={} q_events={}",
                    mode.id(),
                    layout.id(),
                    effective_builder.id(),
                    median.build_ms,
                    p50,
                    fwd95,
                    rev95,
                    peak,
                    steady_bytes,
                    correctness_ok,
                    query_events_count,
                );

                let run_id = format!(
                    "{}-{}-e{}-{}-{}-{}-{}",
                    args.workload_id,
                    shape_id,
                    args.edges,
                    format!("{:?}", args.edge_sort).to_lowercase(),
                    layout.id(),
                    effective_builder.id(),
                    mode.id()
                );

                let manifest = RunManifest {
                    run_id: run_id.clone(),
                    timestamp_rfc3339: now_rfc3339(),
                    git_sha: sha.clone(),
                    host: host.clone(),
                    dataset_id: dataset_id.clone(),
                    estate_shape: shape_id.into(),
                    edges: edges_len,
                    nodes: nodes_len,
                    mean_out_degree_target: args.mean_out_degree,
                    seed: args.seed,
                    edge_sort: format!("{:?}", args.edge_sort),
                    adj_builder: effective_builder.id().into(),
                    layout: layout.id().into(),
                    load_mode: mode.id().into(),
                    coldness: args.coldness.id().into(),
                    workload_id: args.workload_id.clone(),
                    warmup: args.warmup,
                    repeats: args.repeats,
                    phases_ms: PhasesMs {
                        decode_nodes: median.decode_nodes_ms,
                        decode_edges: median.decode_edges_ms,
                        build: median.build_ms,
                        first_bfs: median.bfs_ms,
                        total_cold_to_walk: median.total_ms,
                    },
                    peak_rss_bytes: peak,
                    profile: serde_json::to_value(&median.profile).unwrap_or_default(),
                    parts_bytes: PartsBytes {
                        nodes: written.nodes_bytes,
                        edges: written.edges_bytes,
                    },
                    result_checksum: median.checksum.clone(),
                    correctness_ok,
                    query_events_path: query_path.clone(),
                    errors: Vec::new(),
                };
                let mpath = args.out.join(format!("{run_id}-manifest.json"));
                std::fs::write(&mpath, serde_json::to_string_pretty(&manifest)?)?;
                last_manifest = Some(manifest);

                scenarios.push(ScenarioResult {
                    edge_sort: format!("{:?}", args.edge_sort),
                    estate_shape: shape_id.into(),
                    layout: layout.id().into(),
                    adj_builder: effective_builder.id().into(),
                    load_mode: mode.id().into(),
                    coldness: args.coldness.id().into(),
                    median,
                    p95_total_ms: p95,
                    p50_total_ms: p50,
                    samples: samples.len(),
                    correctness_ok,
                    peak_rss_bytes: peak,
                    steady_index_bytes: steady_bytes,
                    query_events: query_events_count,
                    query_p50_ms: query_p50,
                    query_p95_ms: query_p95,
                    query_by_class,
                    reverse_algorithm: rev_algo.into(),
                    workload_profile: args.workload_profile.map(|p| p.id().into()),
                    trace_checksum: trace_cs.clone(),
                });
            }
        }
    }

    if let Some(m) = last_manifest {
        write_manifest(&args.out, &m)?;
    }

    let report = BenchReport {
        nodes: nodes_len,
        edges: edges_len,
        seed: args.seed,
        mean_out_degree_target: args.mean_out_degree,
        fix_nodes_from_density: args.fix_nodes_from_density,
        edge_sort: format!("{:?}", args.edge_sort),
        estate_shape: shape_id.into(),
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        degree_stats,
        coldness: args.coldness.id().into(),
        workload_id: args.workload_id.clone(),
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
    Ok(())
}
