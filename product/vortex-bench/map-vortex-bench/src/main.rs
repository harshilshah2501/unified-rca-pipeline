//! Map Vortex cold-load + hot adjacency bench (Design v3 Stages 1–4.2).

mod adj;
mod cold;
mod durable;
mod estate;
mod hot;
mod index_mem;
mod load;
mod manifest;
mod oracle;
mod properties;
mod query;
mod rss;
mod segmented;
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
use crate::oracle::{
    Action1Report, degree_bin_definition_note, validate_layout,
};
use crate::properties::{compute_properties, estate_checksum};
use crate::query::{QueryClassBreakdown, class_breakdown, percentile, run_query_mix, write_query_jsonl};
use crate::rss::peak_rss_bytes;
use crate::synth::{DegreeStats, EdgeSort, EstateShape, nodes_for_density, sort_edges};
use crate::write::edges_batch;
use crate::workload::{
    ConcurrentReplayStats, WorkloadProfile, emit_trace_from_edges, read_trace_jsonl, replay_trace,
    replay_trace_concurrent, trace_checksum, write_trace_jsonl,
};
use crate::write::write_parts;
use anyhow::{Result, bail};
use clap::{Parser, ValueEnum};
use serde::Serialize;
use std::path::PathBuf;

const MAX_EDGES_DEFAULT: usize = 5_000_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
enum Coldness {
    /// Fresh process timings; OS page cache may already hold Vortex parts.
    ProcessCold,
    /// Explicitly warm page cache before timed loads.
    PageCacheWarm,
    /// Best-effort drop page cache on part files before each timed load (Action 4).
    DiskCold,
    /// Copy parts to a staging dir then disk-cold load — **lab proxy** for remote Dest fetch (not Motadata S3).
    RemoteProxy,
}

impl Coldness {
    fn id(self) -> &'static str {
        match self {
            Self::ProcessCold => "process_cold",
            Self::PageCacheWarm => "page_cache_warm",
            Self::DiskCold => "disk_cold",
            Self::RemoteProxy => "remote_proxy",
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
    /// Action 5: concurrent shared-graph query readers after final build (1 = serial replay only).
    #[arg(long, default_value_t = 1)]
    concurrent_readers: u32,
    /// Action 5: after build, construct a second index and hold both briefly to observe RSS amplification.
    #[arg(long, default_value_t = false)]
    dual_index_hold: bool,
    /// Action 6 / Milestone B: mutation lifecycle — conventional csr_csc vs segmented_csr_csc.
    #[arg(long, default_value_t = false)]
    action6_mutation: bool,
    /// Action 6 residual: atomic publish under overlapping pinned readers + dual-hold RSS.
    #[arg(long, default_value_t = false)]
    action6_overlap: bool,
    /// Action 6 priority 3: durable mutation log + crash injection / replay.
    #[arg(long, default_value_t = false)]
    action6_durability: bool,
    #[arg(long, default_value_t = 64)]
    segments: u32,
    #[arg(long, default_value_t = 1000)]
    mutation_batch_inserts: usize,
    #[arg(long, default_value_t = 200)]
    mutation_batch_deletes: usize,
    #[arg(long, default_value_t = 20)]
    mutation_batches: u64,
    #[arg(long, default_value_t = 8)]
    overlap_readers: u32,
    /// Skip Vortex write; reuse existing parts under DIR/{edge_sort}/.
    #[arg(long)]
    reuse_parts: Option<PathBuf>,
    /// Skip estate generation (requires --reuse-parts and --seed-ci).
    #[arg(long, default_value_t = false)]
    skip_estate_generate: bool,
    /// Prepare estate + traces only (write parts, no layout timing).
    #[arg(long, default_value_t = false)]
    prepare_only: bool,
    /// Action 1: independent typed-multigraph oracle for hash / hash_bi / csr_csc
    /// across clustered + natural (no performance timing).
    #[arg(long, default_value_t = false)]
    action1_oracle: bool,
    #[arg(long, default_value_t = MAX_EDGES_DEFAULT)]
    max_edges: usize,
}

#[derive(Debug, Clone, Serialize)]
struct SampleTiming {
    decode_nodes_ms: f64,
    decode_edges_ms: f64,
    /// Remote-proxy copy cost (0 unless coldness=remote_proxy).
    remote_fetch_ms: f64,
    build_ms: f64,
    /// Lab publish stub: write ready marker (Action 4 T_publish).
    publish_ms: f64,
    bfs_ms: f64,
    /// T_ready = remote_fetch + decode_nodes + decode_edges + build + publish.
    t_ready_ms: f64,
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
    /// Build-time distribution across repeats (Action 3 credibility).
    build_p50_ms: f64,
    build_p95_ms: f64,
    t_ready_p50_ms: f64,
    t_ready_p95_ms: f64,
    samples: usize,
    correctness_ok: bool,
    peak_rss_bytes: Option<u64>,
    steady_index_bytes: Option<u64>,
    dual_hold_peak_rss_bytes: Option<u64>,
    query_events: usize,
    query_p50_ms: Option<f64>,
    query_p95_ms: Option<f64>,
    query_by_class: Option<QueryClassBreakdown>,
    concurrent: Option<ConcurrentReplayStats>,
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

/// Action 1 — independent oracle for frozen candidates × clustered/natural.
fn run_action1_oracle(args: &Args, family: EstateFamily) -> Result<()> {
    let nodes_n = if args.fix_nodes_from_density {
        nodes_for_density(args.edges, args.mean_out_degree)
    } else {
        args.nodes
    };
    let fcfg = FamilyConfig {
        family,
        nodes_n,
        edges_n: args.edges,
        seed: args.seed,
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        pa_softener: 1.0,
    };
    println!(
        "action1_oracle family={} nodes={} edges={} seed={}",
        family.id(),
        nodes_n,
        args.edges,
        args.seed
    );
    let (nodes, edges_base, _meta) = generate_family(&fcfg);
    let degree_note = degree_bin_definition_note(&edges_base, nodes.len());
    println!("degree_bins: {degree_note}");

    let layouts = [
        HotLayoutKind::Hash,
        HotLayoutKind::HashBi,
        HotLayoutKind::CsrCsc,
    ];
    let sorts = [EdgeSort::Clustered, EdgeSort::Natural];
    let mut reports = Vec::new();

    for sort in sorts {
        let mut edges = edges_base.clone();
        sort_edges(&mut edges, sort);
        let sort_name = format!("{sort:?}").to_lowercase();
        let batch = edges_batch(&edges)?;
        // Reachable reference uses hash_bi (indexed reverse), not forward-only hash.
        let (href, _) = build_hot(&batch, HotLayoutKind::HashBi, AdjBuilder::SortAware)?;
        for layout in layouts {
            let (g, _) = build_hot(&batch, layout, AdjBuilder::SortAware)?;
            let rep = validate_layout(
                &nodes,
                &edges,
                &g,
                layout,
                &sort_name,
                family.id(),
                &href,
            );
            let status = if rep.all_ok { "PASS" } else { "FAIL" };
            println!(
                "oracle {} {} {} → {}",
                family.id(),
                sort_name,
                layout.id(),
                status
            );
            for c in &rep.checks {
                let mark = if c.ok { "ok" } else { "FAIL" };
                println!("  [{mark}] {}: {}", c.name, c.detail);
            }
            reports.push(rep);
        }
    }

    let all_ok = reports.iter().all(|r| r.all_ok);
    let out = Action1Report {
        degree_bin_definition: degree_note,
        layouts: reports,
        all_ok,
    };
    std::fs::create_dir_all(&args.out)?;
    let path = args.out.join("action1_oracle.json");
    std::fs::write(&path, serde_json::to_string_pretty(&out)?)?;
    println!("wrote {} all_ok={all_ok}", path.display());
    if !all_ok {
        bail!("Action 1 oracle failed — see {}", path.display());
    }
    Ok(())
}

/// Action 6 priority 3 — crash injection at publication boundaries + recovery oracle.
fn run_action6_durability(args: &Args, family: EstateFamily) -> Result<()> {
    use crate::durable::{CrashPoint, run_crash_case};
    use crate::hot::triples_from_batch;
    use crate::segmented::synth_mutation_batch;
    use crate::write::edges_batch;

    let nodes_n = if args.fix_nodes_from_density {
        nodes_for_density(args.edges, args.mean_out_degree)
    } else {
        args.nodes
    };
    let fcfg = FamilyConfig {
        family,
        nodes_n,
        edges_n: args.edges,
        seed: args.seed,
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        pa_softener: 1.0,
    };
    println!(
        "action6_durability family={} edges={} segments={}",
        family.id(),
        args.edges,
        args.segments
    );
    let (_nodes, mut edges_rows, _meta) = generate_family(&fcfg);
    sort_edges(&mut edges_rows, EdgeSort::Clustered);
    let batch = edges_batch(&edges_rows)?;
    let (ids, triples, _prof) = triples_from_batch(&batch)?;
    let n = ids.len();
    let (ins, del) = synth_mutation_batch(
        &triples,
        args.seed,
        7,
        args.mutation_batch_inserts,
        args.mutation_batch_deletes,
    );

    let mut cases = Vec::new();
    let mut all_ok = true;
    for crash in CrashPoint::all_injected()
        .iter()
        .copied()
        .chain(std::iter::once(CrashPoint::None))
    {
        // IdMap is moved into store; regenerate mapping each case from same triples.
        let (ids_i, triples_i, _) = triples_from_batch(&batch)?;
        let case_dir = args.out.join(format!("durable-{}", crash.id()));
        let result = run_crash_case(
            &case_dir,
            &triples_i,
            n,
            args.segments,
            ids_i,
            &ins,
            &del,
            crash,
        )?;
        println!(
            "crash={} ok={} gen {}->{} (expect {}) replayed={} lost={} recovery_ms={:.1} notes={}",
            result.crash_point,
            result.ok,
            result.committed_generation_before,
            result.committed_generation_after_recovery,
            result.expected_generation,
            result.mutations_replayed,
            result.mutations_lost,
            result.recovery_ms,
            result.notes
        );
        all_ok = all_ok && result.ok;
        cases.push(result);
    }
    let _ = ids;
    let report = serde_json::json!({
        "action": "action6_durability",
        "milestone_a_frozen": true,
        "lab_model_only": true,
        "family": family.id(),
        "edges": args.edges,
        "segments": args.segments,
        "mutation_batch_inserts": args.mutation_batch_inserts,
        "mutation_batch_deletes": args.mutation_batch_deletes,
        "all_ok": all_ok,
        "cases": cases,
        "note": "Bench durability model with committed marker + pending batch; not Motadata production protocol. Per-segment journals not in scope.",
    });
    let path = args.out.join("action6_durability_results.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    println!("all_ok={} wrote {}", all_ok, path.display());
    Ok(())
}

/// Action 6 residual — atomic publish + dual-hold RSS under overlapping pinned readers.
fn run_action6_overlap(args: &Args, family: EstateFamily) -> Result<()> {
    use crate::hot::triples_from_batch;
    use crate::segmented::{OverlapReaders, SegmentedStore, synth_mutation_batch};
    use crate::write::edges_batch;

    let nodes_n = if args.fix_nodes_from_density {
        nodes_for_density(args.edges, args.mean_out_degree)
    } else {
        args.nodes
    };
    let fcfg = FamilyConfig {
        family,
        nodes_n,
        edges_n: args.edges,
        seed: args.seed,
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        pa_softener: 1.0,
    };
    println!(
        "action6_overlap family={} edges={} segments={} readers={} batches={} ins/del={}/{}",
        family.id(),
        args.edges,
        args.segments,
        args.overlap_readers,
        args.mutation_batches,
        args.mutation_batch_inserts,
        args.mutation_batch_deletes
    );
    let (nodes, mut edges_rows, _meta) = generate_family(&fcfg);
    sort_edges(&mut edges_rows, EdgeSort::Clustered);
    let batch = edges_batch(&edges_rows)?;
    let (ids, triples, _prof) = triples_from_batch(&batch)?;
    let seed_ci = nodes
        .first()
        .map(|r| r.entity_id.clone())
        .unwrap_or_else(|| "middleware-000000".into());

    let baseline_rss = peak_rss_bytes();
    let mut store = SegmentedStore::from_triples(ids, triples.clone(), args.segments);
    let single_hold_rss = peak_rss_bytes();
    let handle = store.published_handle();
    let readers = OverlapReaders::spawn(handle, &seed_ci, args.overlap_readers);

    let mut batch_rows = Vec::new();
    let mut edges_view = triples;
    for b in 0..args.mutation_batches {
        let (ins, del) = synth_mutation_batch(
            &edges_view,
            args.seed,
            b,
            args.mutation_batch_inserts,
            args.mutation_batch_deletes,
        );
        for e in &ins {
            edges_view.push(e.clone());
        }
        for e in &del {
            if let Some(pos) = edges_view
                .iter()
                .position(|(s, t, et)| s == &e.0 && t == &e.1 && et == &e.2)
            {
                edges_view.swap_remove(pos);
            }
        }
        let mt = store.apply_batch(&ins, &del);
        batch_rows.push(mt.clone());
        if (b + 1) % 5 == 0 || b + 1 == args.mutation_batches {
            println!(
                "batch={} gen={}->{} dual_rss={:?} old_sym={} new_sym={} segs={}",
                b + 1,
                mt.old_generation,
                mt.new_generation,
                mt.dual_hold_peak_rss_bytes,
                mt.old_pin_symmetric_ok,
                mt.new_pin_symmetric_ok,
                mt.segments_rebuilt
            );
        }
    }

    let overlap = readers.finish();
    let final_rss = peak_rss_bytes();
    let all_atomic_ok = batch_rows
        .iter()
        .all(|m| m.old_pin_symmetric_ok && m.new_pin_symmetric_ok);
    let report = serde_json::json!({
        "action": "action6_overlap",
        "milestone_a_frozen": true,
        "family": family.id(),
        "edges": args.edges,
        "segments": args.segments,
        "overlap_readers": args.overlap_readers,
        "mutation_batches": args.mutation_batches,
        "mutation_batch_inserts": args.mutation_batch_inserts,
        "mutation_batch_deletes": args.mutation_batch_deletes,
        "baseline_rss_bytes": baseline_rss,
        "single_snapshot_rss_bytes": single_hold_rss,
        "final_rss_bytes": final_rss,
        "batches": batch_rows,
        "overlap_readers_report": overlap,
        "atomic_publish_ok": all_atomic_ok && overlap.ok,
        "implementation_note": "v0 rebuild rescans authoritative edge list per touched segment; per-segment journals are a separate hypothesis",
    });
    let path = args.out.join("action6_overlap_results.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    println!(
        "atomic_publish_ok={} overlap_ok={} gen_mismatch={} sym_fail={} ops={} wrote {}",
        all_atomic_ok && overlap.ok,
        overlap.ok,
        overlap.generation_mismatches,
        overlap.symmetry_failures,
        overlap.ops,
        path.display()
    );
    Ok(())
}

/// Action 6 — conventional full-rebuild CSR+CSC vs segmented incremental publish.
fn run_action6_mutation(args: &Args, family: EstateFamily) -> Result<()> {
    use crate::hot::triples_from_batch;
    use crate::segmented::{
        SegmentedStore, bfs_segmented, build_conventional_csr_csc, synth_mutation_batch,
    };
    use crate::write::edges_batch;
    use std::time::Instant;

    let nodes_n = if args.fix_nodes_from_density {
        nodes_for_density(args.edges, args.mean_out_degree)
    } else {
        args.nodes
    };
    let fcfg = FamilyConfig {
        family,
        nodes_n,
        edges_n: args.edges,
        seed: args.seed,
        hub_fraction: args.hub_fraction,
        hub_edge_share: args.hub_edge_share,
        pa_softener: 1.0,
    };
    println!(
        "action6_mutation family={} nodes={} edges={} segments={} batches={} ins/del={}/{}",
        family.id(),
        nodes_n,
        args.edges,
        args.segments,
        args.mutation_batches,
        args.mutation_batch_inserts,
        args.mutation_batch_deletes
    );
    let (nodes, edges_rows, _meta) = generate_family(&fcfg);
    let mut edges_rows = edges_rows;
    sort_edges(&mut edges_rows, EdgeSort::Clustered);
    let batch = edges_batch(&edges_rows)?;
    let (ids, triples, _prof) = triples_from_batch(&batch)?;
    let n = ids.len();
    let seed_ci = nodes
        .first()
        .map(|r| r.entity_id.clone())
        .unwrap_or_else(|| "middleware-000000".into());

    // --- T_cold-ready: initial build both candidates ---
    let t0 = Instant::now();
    let (_csr0, _csc0, conv_build_ms) = build_conventional_csr_csc(n, &triples)?;
    let t_cold_conv = t0.elapsed().as_secs_f64() * 1000.0;
    let t1 = Instant::now();
    let mut segmented = SegmentedStore::from_triples(ids, triples.clone(), args.segments);
    let t_cold_seg = t1.elapsed().as_secs_f64() * 1000.0;
    println!(
        "T_cold_ready conventional_ms={:.2} (build={:.2}) segmented_ms={:.2} arcs={}",
        t_cold_conv,
        conv_build_ms,
        t_cold_seg,
        triples.len()
    );

    let mut conv_edges = triples.clone();
    let mut seg_timings = Vec::new();
    let mut conv_timings = Vec::new();
    let mut query_rows = Vec::new();

    for b in 0..args.mutation_batches {
        let (ins, del) = synth_mutation_batch(
            &conv_edges,
            args.seed,
            b,
            args.mutation_batch_inserts,
            args.mutation_batch_deletes,
        );

        // Conventional: apply to edge list + full rebuild = T_mutation_visible
        let c_started = Instant::now();
        for e in &ins {
            conv_edges.push(e.clone());
        }
        for e in &del {
            if let Some(pos) = conv_edges
                .iter()
                .position(|(s, t, et)| s == &e.0 && t == &e.1 && et == &e.2)
            {
                conv_edges.swap_remove(pos);
            }
        }
        let (_c, _s, rebuild_ms) = build_conventional_csr_csc(n, &conv_edges)?;
        let conv_vis = c_started.elapsed().as_secs_f64() * 1000.0;
        conv_timings.push(serde_json::json!({
            "batch_id": b + 1,
            "candidate": "csr_csc",
            "t_mutation_visible_ms": conv_vis,
            "rebuild_ms": rebuild_ms,
            "segments_rebuilt": 1,
            "inserts": ins.len(),
            "deletes": del.len(),
            "peak_rss_bytes": peak_rss_bytes(),
        }));

        // Segmented incremental
        let mt = segmented.apply_batch(&ins, &del);
        seg_timings.push(mt.clone());

        // T_query on pinned segmented snapshot (hops=2 forward+reverse sample)
        let pin = segmented.pin();
        let (_rf, fwd_ms, _) = bfs_segmented(&pin, &seed_ci, 2, false);
        let (_rr, rev_ms, _) = bfs_segmented(&pin, &seed_ci, 2, true);
        query_rows.push(serde_json::json!({
            "batch_id": b + 1,
            "generation": pin.generation,
            "t_query_forward_ms": fwd_ms,
            "t_query_reverse_ms": rev_ms,
            "arcs": pin.arc_count,
        }));

        if (b + 1) % 5 == 0 || b + 1 == args.mutation_batches {
            println!(
                "batch={} conv_vis_ms={:.1} seg_vis_ms={:.1} segs_rebuilt={} fwd_ms={:.3} rev_ms={:.3}",
                b + 1,
                conv_vis,
                mt.t_mutation_visible_ms,
                mt.segments_rebuilt,
                fwd_ms,
                rev_ms
            );
        }
    }

    let report = serde_json::json!({
        "action": "action6_mutation",
        "envelope_note": "Milestone B — does not reopen Milestone A layout pick",
        "family": family.id(),
        "nodes": nodes_n,
        "initial_edges": args.edges,
        "segments": args.segments,
        "mutation_batches": args.mutation_batches,
        "mutation_batch_inserts": args.mutation_batch_inserts,
        "mutation_batch_deletes": args.mutation_batch_deletes,
        "t_cold_ready_ms": {
            "csr_csc": t_cold_conv,
            "segmented_csr_csc": t_cold_seg,
        },
        "conventional_batches": conv_timings,
        "segmented_batches": seg_timings,
        "segmented_queries": query_rows,
        "final_arcs_segmented": segmented.arc_count(),
        "peak_rss_bytes": peak_rss_bytes(),
    });
    let path = args.out.join("action6_results.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    println!("wrote {}", path.display());
    Ok(())
}

/// Load Vortex parts under the requested coldness tier.
/// Returns (nodes, edges, load_timing, remote_fetch_ms).
async fn load_with_coldness(
    coldness: Coldness,
    nodes_path: &std::path::Path,
    edges_path: &std::path::Path,
    mode: LoadMode,
    out_dir: &std::path::Path,
) -> Result<(
    arrow::record_batch::RecordBatch,
    arrow::record_batch::RecordBatch,
    crate::load::LoadTiming,
    f64,
)> {
    match coldness {
        Coldness::ProcessCold | Coldness::PageCacheWarm => {
            let (n, e, t) = load_parts(nodes_path, edges_path, mode).await?;
            Ok((n, e, t, 0.0))
        }
        Coldness::DiskCold => {
            crate::cold::drop_parts_page_cache(nodes_path, edges_path)?;
            let (n, e, t) = load_parts(nodes_path, edges_path, mode).await?;
            Ok((n, e, t, 0.0))
        }
        Coldness::RemoteProxy => {
            let staging = out_dir.join("remote_proxy_stage");
            let fetch_started = std::time::Instant::now();
            let (n_path, e_path) =
                crate::cold::stage_remote_proxy_copy(nodes_path, edges_path, &staging)?;
            let remote_fetch_ms = fetch_started.elapsed().as_secs_f64() * 1000.0;
            crate::cold::drop_parts_page_cache(&n_path, &e_path)?;
            let (n, e, t) = load_parts(&n_path, &e_path, mode).await?;
            Ok((n, e, t, remote_fetch_ms))
        }
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

    if args.action1_oracle {
        return run_action1_oracle(&args, family);
    }
    if args.action6_mutation {
        return run_action6_mutation(&args, family);
    }
    if args.action6_overlap {
        return run_action6_overlap(&args, family);
    }
    if args.action6_durability {
        return run_action6_durability(&args, family);
    }
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
            crate::cold::warm_parts_page_cache(&written.nodes_path, &written.edges_path)?;
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
                    let (_n, e, _, _) = load_with_coldness(
                        args.coldness,
                        &written.nodes_path,
                        &written.edges_path,
                        *mode,
                        &args.out,
                    )
                    .await?;
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
                let mut concurrent_stats: Option<ConcurrentReplayStats> = None;
                let mut dual_hold_peak: Option<u64> = None;
                let rev_algo = layout.reverse_algorithm();

                for rep in 0..args.repeats {
                    let (_nodes_b, edges_b, load_t, remote_fetch_ms) = load_with_coldness(
                        args.coldness,
                        &written.nodes_path,
                        &written.edges_path,
                        *mode,
                        &args.out,
                    )
                    .await?;
                    let (mut g, build_t) = build_hot(&edges_b, *layout, effective_builder)?;
                    if *layout == HotLayoutKind::Hybrid {
                        apply_hybrid_churn(
                            &mut g,
                            args.hybrid_inserts,
                            args.hybrid_deletes,
                            args.seed,
                        );
                    }
                    // Lab publish stub: write a ready marker (atomic pointer swap analogue).
                    let pub_started = std::time::Instant::now();
                    let ready_path = args.out.join(format!(
                        "ready-{}-{}.json",
                        shape_id,
                        layout.id()
                    ));
                    std::fs::write(
                        &ready_path,
                        format!(
                            "{{\"layout\":\"{}\",\"ready\":true,\"rep\":{}}}\n",
                            layout.id(),
                            rep
                        ),
                    )?;
                    let publish_ms = pub_started.elapsed().as_secs_f64() * 1000.0;

                    let (reach, bfs_ms, names) = bfs(&g, &seed_ci, args.walk_hops, false);
                    let checksum = checksum_names(&names);
                    if let Some(r) = &ref_checksum {
                        if r != &checksum {
                            correctness_ok = false;
                        }
                    } else {
                        ref_checksum = Some(checksum.clone());
                    }
                    let t_ready = remote_fetch_ms
                        + load_t.nodes_decode_ms
                        + load_t.edges_decode_ms
                        + build_t.build_ms
                        + publish_ms;
                    let total = t_ready + bfs_ms;
                    samples.push(SampleTiming {
                        decode_nodes_ms: load_t.nodes_decode_ms,
                        decode_edges_ms: load_t.edges_decode_ms,
                        remote_fetch_ms,
                        build_ms: build_t.build_ms,
                        publish_ms,
                        bfs_ms,
                        t_ready_ms: t_ready,
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

                        if args.dual_index_hold {
                            let (_n2, e2, _, _) = load_with_coldness(
                                Coldness::ProcessCold,
                                &written.nodes_path,
                                &written.edges_path,
                                *mode,
                                &args.out,
                            )
                            .await?;
                            let (g2, _) = build_hot(&e2, *layout, effective_builder)?;
                            let _keep = (&g, &g2);
                            dual_hold_peak = peak_rss_bytes();
                            drop(g2);
                        }

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
                            let readers = args.concurrent_readers.max(1);
                            let conc = replay_trace_concurrent(
                                &g,
                                ops,
                                &run_id,
                                layout.id(),
                                rev_algo,
                                readers,
                            );
                            // Also keep a JSONL sample for readers=1 debugging.
                            if readers == 1 {
                                let (events, _) =
                                    replay_trace(&g, ops, &run_id, layout.id(), rev_algo);
                                let qpath = args.out.join(format!("{run_id}-queries.jsonl"));
                                write_query_jsonl(&qpath, &events)?;
                                query_path = Some(qpath.display().to_string());
                            }
                            query_events_count = conc.total_ops;
                            query_p50 = Some(conc.latency_p50_ms);
                            query_p95 = Some(conc.latency_p95_ms);
                            query_by_class = Some(conc.by_class.clone());
                            concurrent_stats = Some(conc);
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

                let mut builds: Vec<f64> = samples.iter().map(|s| s.build_ms).collect();
                builds.sort_by(|a, b| a.partial_cmp(b).unwrap());
                let build_p50 = percentile(&builds, 50.0);
                let build_p95 = percentile(&builds, 95.0);
                let mut t_readies: Vec<f64> = samples.iter().map(|s| s.t_ready_ms).collect();
                t_readies.sort_by(|a, b| a.partial_cmp(b).unwrap());
                let t_ready_p50 = percentile(&t_readies, 50.0);
                let t_ready_p95 = percentile(&t_readies, 95.0);
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
                    "mode={:<24} layout={:<8} cold={:<14} adj_ms={:>7.2} t_ready_p50={:>7.2} fwd_p95={:>8.3} rev_p95={:>8.3} rss={:?} idx={:?} ok={} q_events={} conc={}",
                    mode.id(),
                    layout.id(),
                    args.coldness.id(),
                    median.build_ms,
                    t_ready_p50,
                    fwd95,
                    rev95,
                    peak,
                    steady_bytes,
                    correctness_ok,
                    query_events_count,
                    args.concurrent_readers,
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
                    build_p50_ms: build_p50,
                    build_p95_ms: build_p95,
                    t_ready_p50_ms: t_ready_p50,
                    t_ready_p95_ms: t_ready_p95,
                    samples: samples.len(),
                    correctness_ok,
                    peak_rss_bytes: peak,
                    steady_index_bytes: steady_bytes,
                    dual_hold_peak_rss_bytes: dual_hold_peak,
                    query_events: query_events_count,
                    query_p50_ms: query_p50,
                    query_p95_ms: query_p95,
                    query_by_class,
                    concurrent: concurrent_stats,
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
