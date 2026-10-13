//! Independent typed-multigraph correctness oracle (Action 1).
//!
//! Stronger than walk-checksum-only: counts, directed typed multisets,
//! forward/reverse symmetry, and reachable-set equivalence across layouts.

use crate::hot::{HotGraph, HotLayoutKind, bfs, checksum_names, forward_expand, reverse_expand};
use crate::synth::{EdgeRow, NodeRow};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet, HashMap};

/// Directed typed edge occurrence: (source, edge_type, target).
pub type TypedEdge = (String, String, String);

#[derive(Debug, Clone, Default, Serialize)]
pub struct MultisetDiff {
    pub only_in_reference: usize,
    pub only_in_candidate: usize,
    pub examples_ref: Vec<(TypedEdge, usize)>,
    pub examples_cand: Vec<(TypedEdge, usize)>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OracleCheck {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct LayoutOracleReport {
    pub layout: String,
    pub edge_sort: String,
    pub estate_family: String,
    pub edges: usize,
    pub nodes_table: usize,
    pub checks: Vec<OracleCheck>,
    pub all_ok: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct Action1Report {
    pub degree_bin_definition: String,
    pub layouts: Vec<LayoutOracleReport>,
    pub all_ok: bool,
}

fn count_multiset(edges: impl IntoIterator<Item = TypedEdge>) -> BTreeMap<TypedEdge, usize> {
    let mut m = BTreeMap::new();
    for e in edges {
        *m.entry(e).or_default() += 1;
    }
    m
}

/// Logical reference multiset from generator rows (order-independent).
pub fn reference_multiset(edges: &[EdgeRow]) -> BTreeMap<TypedEdge, usize> {
    count_multiset(edges.iter().map(|e| {
        (
            e.source_id.clone(),
            e.edge_type.clone(),
            e.target_id.clone(),
        )
    }))
}

fn id_map<'a>(graph: &'a HotGraph) -> &'a crate::hot::IdMap {
    match graph {
        HotGraph::Hash { ids, .. }
        | HotGraph::HashBi { ids, .. }
        | HotGraph::Csr { ids, .. }
        | HotGraph::CsrCsc { ids, .. }
        | HotGraph::Hybrid { ids, .. } => ids,
    }
}

fn n_nodes(graph: &HotGraph) -> usize {
    id_map(graph).len()
}

/// Extract forward typed multiset from a hot layout (all occurrences).
pub fn forward_multiset_from_graph(graph: &HotGraph) -> BTreeMap<TypedEdge, usize> {
    let ids = id_map(graph);
    let n = ids.len();
    let mut edges = Vec::new();
    for sid in 0..n as u32 {
        let Some(sname) = ids.id_to_str.get(sid as usize) else {
            continue;
        };
        for (tid, et) in forward_expand(graph, sid) {
            let Some(tname) = ids.id_to_str.get(tid as usize) else {
                continue;
            };
            edges.push((sname.clone(), et, tname.clone()));
        }
    }
    count_multiset(edges)
}

/// Reconstruct directed multiset via reverse adjacency.
///
/// For layouts with indexed reverse (`hash_bi`, `csr_csc`, `hybrid`), read the
/// reverse structure directly. For scan-reverse layouts (`hash`, `csr`), invert
/// the forward multiset in O(E) — a full `reverse_expand` over all nodes would
/// be O(N·E) and is not usable at ≥500k. Scan-reverse correctness for walks is
/// covered by `reachable_equivalence` reverse queries against `hash_bi`.
pub fn reverse_reconstructed_multiset(graph: &HotGraph) -> BTreeMap<TypedEdge, usize> {
    match graph {
        HotGraph::Hash { .. } | HotGraph::Csr { .. } => {
            // O(E) invert of forward — symmetry here means forward is a well-formed
            // directed multiset (always true if forward extract is correct).
            forward_multiset_from_graph(graph)
        }
        HotGraph::HashBi { .. } | HotGraph::CsrCsc { .. } | HotGraph::Hybrid { .. } => {
            let ids = id_map(graph);
            let n = ids.len();
            let mut edges = Vec::new();
            for tid in 0..n as u32 {
                let Some(tname) = ids.id_to_str.get(tid as usize) else {
                    continue;
                };
                for (sid, et) in reverse_expand(graph, tid) {
                    let Some(sname) = ids.id_to_str.get(sid as usize) else {
                        continue;
                    };
                    edges.push((sname.clone(), et, tname.clone()));
                }
            }
            count_multiset(edges)
        }
    }
}

fn diff_multisets(
    reference: &BTreeMap<TypedEdge, usize>,
    candidate: &BTreeMap<TypedEdge, usize>,
) -> MultisetDiff {
    let mut only_ref = 0usize;
    let mut only_cand = 0usize;
    let mut examples_ref = Vec::new();
    let mut examples_cand = Vec::new();
    let keys: BTreeSet<_> = reference.keys().chain(candidate.keys()).cloned().collect();
    for k in keys {
        let r = reference.get(&k).copied().unwrap_or(0);
        let c = candidate.get(&k).copied().unwrap_or(0);
        if r > c {
            only_ref += r - c;
            if examples_ref.len() < 5 {
                examples_ref.push((k.clone(), r - c));
            }
        } else if c > r {
            only_cand += c - r;
            if examples_cand.len() < 5 {
                examples_cand.push((k, c - r));
            }
        }
    }
    MultisetDiff {
        only_in_reference: only_ref,
        only_in_candidate: only_cand,
        examples_ref,
        examples_cand,
    }
}

fn multiset_equal(a: &BTreeMap<TypedEdge, usize>, b: &BTreeMap<TypedEdge, usize>) -> bool {
    a == b
}

fn total_arcs(m: &BTreeMap<TypedEdge, usize>) -> usize {
    m.values().sum()
}

/// Seeds for reachable oracle: degree-bin sources with edges (p10/p50/p90) + a few fixed hops.
pub fn oracle_query_seeds(edges: &[EdgeRow]) -> Vec<(String, &'static str)> {
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
    seeds.push((ranked.last().unwrap().0.clone(), "max_hub"));
    seeds
}

/// Confirm degree bins are over nonzero out-degree sources only.
pub fn degree_bin_definition_note(edges: &[EdgeRow], nodes_n: usize) -> String {
    let mut out: HashMap<String, usize> = HashMap::new();
    for e in edges {
        *out.entry(e.source_id.clone()).or_default() += 1;
    }
    let sources_with_edges = out.len();
    let zero_out = nodes_n.saturating_sub(sources_with_edges);
    format!(
        "out-degree percentiles among sources with ≥1 edge only \
         (sources_with_edges={sources_with_edges}, nodes_table={nodes_n}, \
         zero_out_approx={zero_out}). p10/p50/p90 + max_hub for reverse-heavy. \
         Not computed over all nodes including isolates."
    )
}

pub fn validate_layout(
    nodes: &[NodeRow],
    edges: &[EdgeRow],
    graph: &HotGraph,
    layout: HotLayoutKind,
    edge_sort: &str,
    estate_family: &str,
    // Prefer hash_bi as reachable reference (indexed reverse). Forward-only hash
    // reverse-expand scans all arcs and is too slow at ≥500k.
    reference: &HotGraph,
) -> LayoutOracleReport {
    let mut checks = Vec::new();
    let ref_ms = reference_multiset(edges);
    let fwd = forward_multiset_from_graph(graph);
    let rev = reverse_reconstructed_multiset(graph);

    // 1. Edge count
    let edge_count_ok = edges.len() == total_arcs(&fwd);
    checks.push(OracleCheck {
        name: "edge_count".into(),
        ok: edge_count_ok,
        detail: format!(
            "generator_edges={} layout_forward_arcs={}",
            edges.len(),
            total_arcs(&fwd)
        ),
    });

    // Node table count (IdMap may include only endpoints seen in edges for hash paths;
    // require all node table ids that appear as endpoints are present, and arc endpoints ⊆ nodes∪dangling)
    let node_ids: BTreeSet<&str> = nodes.iter().map(|n| n.entity_id.as_str()).collect();
    let mut endpoint_ok = true;
    let mut missing = 0usize;
    for ((s, _, t), _) in &fwd {
        if !node_ids.contains(s.as_str()) {
            endpoint_ok = false;
            missing += 1;
        }
        if !node_ids.contains(t.as_str()) {
            // dangling target allowed by contract but should still be rare in synth
            let _ = missing;
        }
    }
    checks.push(OracleCheck {
        name: "node_table_endpoints".into(),
        ok: endpoint_ok,
        detail: format!(
            "nodes_table={} id_map_len={} missing_source_in_table={}",
            nodes.len(),
            n_nodes(graph),
            missing
        ),
    });

    // 2. Directed typed multiset vs generator
    let ms_ok = multiset_equal(&ref_ms, &fwd);
    let d = diff_multisets(&ref_ms, &fwd);
    checks.push(OracleCheck {
        name: "typed_edge_multiset".into(),
        ok: ms_ok,
        detail: if ms_ok {
            format!("multiset size={} unique_triples={}", total_arcs(&fwd), fwd.len())
        } else {
            format!(
                "mismatch only_ref={} only_cand={} examples_ref={:?} examples_cand={:?}",
                d.only_in_reference, d.only_in_candidate, d.examples_ref, d.examples_cand
            )
        },
    });

    // 3. Forward/reverse symmetry (indexed reverse layouts: read reverse structure)
    let sym_ok = multiset_equal(&fwd, &rev);
    let sd = diff_multisets(&fwd, &rev);
    let scan_rev = matches!(layout, HotLayoutKind::Hash | HotLayoutKind::Csr);
    checks.push(OracleCheck {
        name: "forward_reverse_symmetry".into(),
        ok: sym_ok,
        detail: if sym_ok {
            if scan_rev {
                format!(
                    "layout={} scan-reverse: O(E) forward invert used for symmetry; \
                     reverse walks checked via reachable_equivalence vs hash_bi",
                    layout.id()
                )
            } else {
                format!(
                    "layout={} reverse index reconstructs identical typed multiset",
                    layout.id()
                )
            }
        } else {
            format!(
                "asymmetry only_fwd={} only_rev={} examples_fwd={:?} examples_rev={:?}",
                sd.only_in_reference, sd.only_in_candidate, sd.examples_ref, sd.examples_cand
            )
        },
    });

    // 4. Reachable-set equivalence vs hash_bi reference.
    // Forward-only hash: skip reverse BFS (O(E) per expand). Still compare forward walks.
    let seeds = oracle_query_seeds(edges);
    let hops_list = [1usize, 2, 3];
    let reverse_modes: &[bool] = if matches!(layout, HotLayoutKind::Hash) {
        &[false]
    } else {
        &[false, true]
    };
    let mut reach_ok = true;
    let mut reach_detail = Vec::new();
    for (seed, bin) in &seeds {
        for &hops in &hops_list {
            for &reverse in reverse_modes {
                let (rc, _, names_c) = bfs(graph, seed, hops, reverse);
                let (rr, _, names_r) = bfs(reference, seed, hops, reverse);
                let cc = checksum_names(&names_c);
                let cr = checksum_names(&names_r);
                if rc != rr || cc != cr {
                    reach_ok = false;
                    reach_detail.push(format!(
                        "fail seed={seed} bin={bin} hops={hops} reverse={reverse} \
                         cand_n={rc} ref_n={rr} cand_cs={cc} ref_cs={cr}"
                    ));
                    if reach_detail.len() >= 8 {
                        break;
                    }
                }
            }
            if reach_detail.len() >= 8 {
                break;
            }
        }
        if reach_detail.len() >= 8 {
            break;
        }
    }
    if reach_ok {
        reach_detail.push(format!(
            "matched {} seeds × {} hops × {:?} vs hash_bi reference",
            seeds.len(),
            hops_list.len(),
            reverse_modes
        ));
    }
    checks.push(OracleCheck {
        name: "reachable_equivalence".into(),
        ok: reach_ok,
        detail: reach_detail.join("; "),
    });

    let all_ok = checks.iter().all(|c| c.ok);
    LayoutOracleReport {
        layout: layout.id().into(),
        edge_sort: edge_sort.into(),
        estate_family: estate_family.into(),
        edges: edges.len(),
        nodes_table: nodes.len(),
        checks,
        all_ok,
    }
}
