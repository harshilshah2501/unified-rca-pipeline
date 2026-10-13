//! Hot graph layouts: hash, hash_bi, CSR, CSR+CSC, hybrid (CSR/CSC + occurrence delta).

use crate::adj::{AdjBuilder, BuildProfile, build_out_adjacency};
use crate::load::utf8_col;
use anyhow::Result;
use arrow::array::Array;
use arrow::record_batch::RecordBatch;
use clap::ValueEnum;
use serde::Serialize;
use std::collections::{HashMap, HashSet, VecDeque};
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum HotLayoutKind {
    /// Forward HashMap only; reverse = full scan of out-adjacency.
    Hash,
    /// Forward + reverse HashMaps (bidirectional hash).
    HashBi,
    /// Forward CSR; reverse = scan all CSR arcs.
    Csr,
    /// Forward CSR + reverse CSC.
    CsrCsc,
    /// CSR+CSC base + mutable occurrence-count delta.
    Hybrid,
}

impl HotLayoutKind {
    pub fn id(self) -> &'static str {
        match self {
            Self::Hash => "hash",
            Self::HashBi => "hash_bi",
            Self::Csr => "csr",
            Self::CsrCsc => "csr_csc",
            Self::Hybrid => "hybrid",
        }
    }

    /// Documented reverse algorithm for Stage 3.5 fairness notes.
    pub fn reverse_algorithm(self) -> &'static str {
        match self {
            Self::Hash => "scan_all_out_lists",
            Self::HashBi => "in_hashmap_lookup",
            Self::Csr => "scan_all_csr_arcs",
            Self::CsrCsc => "csc_predecessor_lookup",
            Self::Hybrid => "csc_lookup_plus_delta",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct LayoutBuildTiming {
    pub layout: String,
    pub build_ms: f64,
    pub nodes: usize,
    pub arcs: usize,
    pub profile: BuildProfile,
    pub reverse_algorithm: String,
}

pub struct IdMap {
    pub id_to_str: Vec<String>,
    pub str_to_id: HashMap<String, u32>,
}

impl IdMap {
    pub fn from_strings<'a>(ids: impl IntoIterator<Item = &'a str>) -> Self {
        let mut str_to_id = HashMap::new();
        let mut id_to_str = Vec::new();
        for s in ids {
            if str_to_id.contains_key(s) {
                continue;
            }
            let id = id_to_str.len() as u32;
            str_to_id.insert(s.to_string(), id);
            id_to_str.push(s.to_string());
        }
        Self { id_to_str, str_to_id }
    }

    pub fn get(&self, s: &str) -> Option<u32> {
        self.str_to_id.get(s).copied()
    }

    pub fn len(&self) -> usize {
        self.id_to_str.len()
    }
}

#[derive(Clone)]
pub struct Csr {
    pub n: usize,
    pub offsets: Vec<u32>,
    pub targets: Vec<u32>,
    pub edge_types: Vec<String>,
}

impl Csr {
    pub fn from_sorted_triples(n: usize, mut triples: Vec<(u32, u32, String)>) -> Self {
        triples.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)).then(a.2.cmp(&b.2)));
        let mut offsets = vec![0u32; n + 1];
        let mut targets = Vec::with_capacity(triples.len());
        let mut edge_types = Vec::with_capacity(triples.len());
        let mut cursor = 0usize;
        for src in 0..n as u32 {
            offsets[src as usize] = targets.len() as u32;
            while cursor < triples.len() && triples[cursor].0 == src {
                targets.push(triples[cursor].1);
                edge_types.push(std::mem::take(&mut triples[cursor].2));
                cursor += 1;
            }
        }
        offsets[n] = targets.len() as u32;
        Self {
            n,
            offsets,
            targets,
            edge_types,
        }
    }

    pub fn neighbors(&self, src: u32) -> impl Iterator<Item = (u32, &str)> + '_ {
        let s = src as usize;
        let a = self.offsets[s] as usize;
        let b = self.offsets[s + 1] as usize;
        (a..b).map(move |i| (self.targets[i], self.edge_types[i].as_str()))
    }

    pub fn arc_count(&self) -> usize {
        self.targets.len()
    }
}

#[derive(Clone)]
pub struct Csc {
    pub n: usize,
    pub offsets: Vec<u32>,
    pub sources: Vec<u32>,
    pub edge_types: Vec<String>,
}

impl Csc {
    pub fn from_triples(n: usize, triples: &[(u32, u32, String)]) -> Self {
        let mut by_tgt: Vec<(u32, u32, String)> = triples
            .iter()
            .map(|(s, t, et)| (*t, *s, et.clone()))
            .collect();
        by_tgt.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)).then(a.2.cmp(&b.2)));
        let mut offsets = vec![0u32; n + 1];
        let mut sources = Vec::with_capacity(by_tgt.len());
        let mut edge_types = Vec::with_capacity(by_tgt.len());
        let mut cursor = 0usize;
        for tgt in 0..n as u32 {
            offsets[tgt as usize] = sources.len() as u32;
            while cursor < by_tgt.len() && by_tgt[cursor].0 == tgt {
                sources.push(by_tgt[cursor].1);
                edge_types.push(std::mem::take(&mut by_tgt[cursor].2));
                cursor += 1;
            }
        }
        offsets[n] = sources.len() as u32;
        Self {
            n,
            offsets,
            sources,
            edge_types,
        }
    }

    pub fn predecessors(&self, tgt: u32) -> impl Iterator<Item = (u32, &str)> + '_ {
        let t = tgt as usize;
        let a = self.offsets[t] as usize;
        let b = self.offsets[t + 1] as usize;
        (a..b).map(move |i| (self.sources[i], self.edge_types[i].as_str()))
    }
}

/// Mutable delta over a packed base. Deletes are **occurrence counts** of typed triples
/// `(src, tgt, edge_type)` — each delete removes one matching occurrence from the
/// effective multigraph (base ∪ inserts), not all matching edges.
#[derive(Default)]
pub struct Delta {
    pub inserts_out: HashMap<u32, Vec<(u32, String)>>,
    pub inserts_in: HashMap<u32, Vec<(u32, String)>>,
    /// How many occurrences of (src,tgt,et) to hide from the effective graph.
    pub delete_counts: HashMap<(u32, u32, String), u32>,
}

impl Delta {
    pub fn insert_edge(&mut self, src: u32, tgt: u32, et: String) {
        let key = (src, tgt, et.clone());
        if let Some(c) = self.delete_counts.get_mut(&key) {
            if *c > 0 {
                *c -= 1;
                if *c == 0 {
                    self.delete_counts.remove(&key);
                }
                return; // cancel one pending delete
            }
        }
        self.inserts_out.entry(src).or_default().push((tgt, et.clone()));
        self.inserts_in.entry(tgt).or_default().push((src, et));
    }

    /// Remove one occurrence: prefer popping a matching insert; else bump delete count.
    pub fn delete_one_occurrence(&mut self, src: u32, tgt: u32, et: String) {
        if let Some(list) = self.inserts_out.get_mut(&src) {
            if let Some(pos) = list.iter().position(|(t, e)| *t == tgt && *e == et) {
                list.swap_remove(pos);
                if let Some(ilist) = self.inserts_in.get_mut(&tgt) {
                    if let Some(ip) = ilist.iter().position(|(s, e)| *s == src && *e == et) {
                        ilist.swap_remove(ip);
                    }
                }
                return;
            }
        }
        *self.delete_counts.entry((src, tgt, et)).or_default() += 1;
    }

    fn remaining_deletes(&self, src: u32, tgt: u32, et: &str) -> u32 {
        self.delete_counts
            .get(&(src, tgt, et.to_string()))
            .copied()
            .unwrap_or(0)
    }
}

/// Filter a neighbor stream, consuming occurrence deletes for each typed triple.
fn apply_occurrence_filter(
    src: u32,
    edges: impl Iterator<Item = (u32, String)>,
    delta: &Delta,
) -> Vec<(u32, String)> {
    let mut used: HashMap<(u32, String), u32> = HashMap::new();
    let mut out = Vec::new();
    for (t, et) in edges {
        let key = (t, et.clone());
        let allowed = delta.remaining_deletes(src, t, &et);
        let seen = used.entry(key).or_default();
        if *seen < allowed {
            *seen += 1;
            continue; // hide this occurrence
        }
        out.push((t, et));
    }
    out
}

pub enum HotGraph {
    Hash {
        adj: HashMap<String, Vec<(String, String)>>,
        ids: IdMap,
    },
    HashBi {
        out: HashMap<String, Vec<(String, String)>>,
        inn: HashMap<String, Vec<(String, String)>>,
        ids: IdMap,
    },
    Csr {
        ids: IdMap,
        csr: Csr,
    },
    CsrCsc {
        ids: IdMap,
        csr: Csr,
        csc: Csc,
    },
    Hybrid {
        ids: IdMap,
        csr: Csr,
        csc: Csc,
        delta: Delta,
    },
}

pub fn build_hot(
    edges: &RecordBatch,
    kind: HotLayoutKind,
    hash_builder: AdjBuilder,
) -> Result<(HotGraph, LayoutBuildTiming)> {
    let started = Instant::now();
    let (graph, profile, nodes, arcs) = match kind {
        HotLayoutKind::Hash => {
            let (adj, _, profile) = build_out_adjacency(edges, hash_builder)?;
            let mut names = Vec::new();
            for (s, list) in &adj {
                names.push(s.as_str());
                for (t, _) in list {
                    names.push(t.as_str());
                }
            }
            let ids = IdMap::from_strings(names);
            let nodes = adj.len();
            let arcs = adj.values().map(|v| v.len()).sum();
            (HotGraph::Hash { adj, ids }, profile, nodes, arcs)
        }
        HotLayoutKind::HashBi => {
            let (out, _, profile) = build_out_adjacency(edges, hash_builder)?;
            let mut inn: HashMap<String, Vec<(String, String)>> = HashMap::new();
            let mut names = Vec::new();
            for (s, list) in &out {
                names.push(s.as_str());
                for (t, et) in list {
                    names.push(t.as_str());
                    inn.entry(t.clone())
                        .or_default()
                        .push((s.clone(), et.clone()));
                }
            }
            let ids = IdMap::from_strings(names);
            let nodes = out.len();
            let arcs = out.values().map(|v| v.len()).sum();
            (HotGraph::HashBi { out, inn, ids }, profile, nodes, arcs)
        }
        HotLayoutKind::Csr | HotLayoutKind::CsrCsc | HotLayoutKind::Hybrid => {
            let (ids, triples, profile) = triples_from_batch(edges)?;
            let n = ids.len();
            let arcs = triples.len();
            let csr = Csr::from_sorted_triples(n, triples.clone());
            let graph = match kind {
                HotLayoutKind::Csr => HotGraph::Csr { ids, csr },
                HotLayoutKind::CsrCsc => {
                    let csc = Csc::from_triples(n, &triples);
                    HotGraph::CsrCsc { ids, csr, csc }
                }
                HotLayoutKind::Hybrid => {
                    let csc = Csc::from_triples(n, &triples);
                    HotGraph::Hybrid {
                        ids,
                        csr,
                        csc,
                        delta: Delta::default(),
                    }
                }
                _ => unreachable!(),
            };
            (graph, profile, n, arcs)
        }
    };
    let build_ms = started.elapsed().as_secs_f64() * 1000.0;
    Ok((
        graph,
        LayoutBuildTiming {
            layout: kind.id().into(),
            build_ms,
            nodes,
            arcs,
            profile,
            reverse_algorithm: kind.reverse_algorithm().into(),
        },
    ))
}

pub(crate) fn triples_from_batch(
    edges: &RecordBatch,
) -> Result<(IdMap, Vec<(u32, u32, String)>, BuildProfile)> {
    let src = utf8_col(edges, "source_id")?;
    let tgt = utf8_col(edges, "target_id")?;
    let et = utf8_col(edges, "edge_type")?;
    let mut names = Vec::with_capacity(src.len() * 2);
    for i in 0..src.len() {
        if src.is_null(i) || tgt.is_null(i) {
            continue;
        }
        names.push(src.value(i));
        names.push(tgt.value(i));
    }
    let ids = IdMap::from_strings(names);
    let mut triples = Vec::with_capacity(src.len());
    let mut profile = BuildProfile::default();
    let mut prev: Option<&str> = None;
    for i in 0..src.len() {
        if src.is_null(i) || tgt.is_null(i) || et.is_null(i) {
            continue;
        }
        let s = src.value(i);
        if prev != Some(s) {
            profile.source_groups += 1;
            prev = Some(s);
        }
        profile.neighbor_string_clones += 1;
        let sid = ids.get(s).unwrap();
        let tid = ids.get(tgt.value(i)).unwrap();
        triples.push((sid, tid, et.value(i).to_string()));
    }
    Ok((ids, triples, profile))
}

pub(crate) fn forward_expand(graph: &HotGraph, cur: u32) -> Vec<(u32, String)> {
    match graph {
        HotGraph::Hash { adj, ids } | HotGraph::HashBi { out: adj, ids, .. } => {
            let Some(name) = ids.id_to_str.get(cur as usize) else {
                return Vec::new();
            };
            adj.get(name)
                .map(|list| {
                    list.iter()
                        .filter_map(|(t, et)| ids.get(t).map(|id| (id, et.clone())))
                        .collect()
                })
                .unwrap_or_default()
        }
        HotGraph::Csr { csr, .. } | HotGraph::CsrCsc { csr, .. } => csr
            .neighbors(cur)
            .map(|(t, et)| (t, et.to_string()))
            .collect(),
        HotGraph::Hybrid { csr, delta, .. } => {
            // Occurrence deletes apply to base arcs; inserts are already trimmed by delete_one.
            let base = csr.neighbors(cur).map(|(t, et)| (t, et.to_string()));
            let mut out = apply_occurrence_filter(cur, base, delta);
            if let Some(extra) = delta.inserts_out.get(&cur) {
                out.extend(extra.iter().cloned());
            }
            out
        }
    }
}

pub(crate) fn reverse_expand(graph: &HotGraph, cur: u32) -> Vec<(u32, String)> {
    match graph {
        HotGraph::Hash { adj, ids } => {
            let mut preds = Vec::new();
            let Some(cur_name) = ids.id_to_str.get(cur as usize) else {
                return preds;
            };
            for (s, list) in adj {
                for (t, et) in list {
                    if t == cur_name {
                        if let Some(sid) = ids.get(s) {
                            preds.push((sid, et.clone()));
                        }
                    }
                }
            }
            preds
        }
        HotGraph::HashBi { inn, ids, .. } => {
            let Some(name) = ids.id_to_str.get(cur as usize) else {
                return Vec::new();
            };
            inn.get(name)
                .map(|list| {
                    list.iter()
                        .filter_map(|(s, et)| ids.get(s).map(|id| (id, et.clone())))
                        .collect()
                })
                .unwrap_or_default()
        }
        HotGraph::Csr { csr, .. } => {
            let mut preds = Vec::new();
            for s in 0..csr.n as u32 {
                for (t, et) in csr.neighbors(s) {
                    if t == cur {
                        preds.push((s, et.to_string()));
                    }
                }
            }
            preds
        }
        HotGraph::CsrCsc { csc, .. } => csc
            .predecessors(cur)
            .map(|(s, et)| (s, et.to_string()))
            .collect(),
        HotGraph::Hybrid { csc, delta, .. } => {
            let base = csc.predecessors(cur).map(|(s, et)| (s, et.to_string()));
            // Map (src,tgt=cur,et) deletes onto predecessor stream by treating src as "neighbor id".
            let mut used: HashMap<(u32, String), u32> = HashMap::new();
            let mut preds = Vec::new();
            for (s, et) in base {
                let allowed = delta.remaining_deletes(s, cur, &et);
                let seen = used.entry((s, et.clone())).or_default();
                if *seen < allowed {
                    *seen += 1;
                    continue;
                }
                preds.push((s, et));
            }
            if let Some(extra) = delta.inserts_in.get(&cur) {
                preds.extend(extra.iter().cloned());
            }
            preds
        }
    }
}

pub fn bfs(
    graph: &HotGraph,
    seed_str: &str,
    hops: usize,
    reverse: bool,
) -> (usize, f64, Vec<String>) {
    let started = Instant::now();
    let ids = match graph {
        HotGraph::Hash { ids, .. }
        | HotGraph::HashBi { ids, .. }
        | HotGraph::Csr { ids, .. }
        | HotGraph::CsrCsc { ids, .. }
        | HotGraph::Hybrid { ids, .. } => ids,
    };
    let Some(seed) = ids.get(seed_str) else {
        return (0, started.elapsed().as_secs_f64() * 1000.0, Vec::new());
    };
    let mut seen = HashSet::new();
    let mut q = VecDeque::new();
    seen.insert(seed);
    q.push_back((seed, 0usize));
    while let Some((cur, d)) = q.pop_front() {
        if d >= hops {
            continue;
        }
        let nexts = if reverse {
            reverse_expand(graph, cur)
        } else {
            forward_expand(graph, cur)
        };
        for (n, _) in nexts {
            if seen.insert(n) {
                q.push_back((n, d + 1));
            }
        }
    }
    let mut names: Vec<String> = seen
        .into_iter()
        .filter_map(|id| ids.id_to_str.get(id as usize).cloned())
        .collect();
    names.sort();
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    (names.len(), ms, names)
}

pub fn checksum_names(names: &[String]) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut h = DefaultHasher::new();
    for n in names {
        n.hash(&mut h);
        "\n".hash(&mut h);
    }
    format!("{:016x}", h.finish())
}

pub fn apply_hybrid_churn(graph: &mut HotGraph, inserts: usize, deletes: usize, seed: u64) {
    let HotGraph::Hybrid {
        ids,
        csr,
        delta,
        ..
    } = graph
    else {
        return;
    };
    let n = ids.len().max(2) as u64;
    let mut x = seed ^ 0xA5A5_A5A5_A5A5_A5A5;
    let mut next = || {
        x = x.wrapping_mul(0x9E37_79B9_7F4A_7C15).wrapping_add(1);
        x
    };
    for _ in 0..inserts {
        let s = (next() % n) as u32;
        let t = (next() % n) as u32;
        if s != t {
            delta.insert_edge(s, t, "USES".into());
        }
    }
    for _ in 0..deletes {
        if csr.arc_count() == 0 {
            break;
        }
        let s = (next() % n) as u32;
        let neis: Vec<_> = csr.neighbors(s).map(|(t, et)| (t, et.to_string())).collect();
        if neis.is_empty() {
            continue;
        }
        let (t, et) = &neis[(next() as usize) % neis.len()];
        delta.delete_one_occurrence(s, *t, et.clone());
    }
}

pub fn out_degrees_hash(adj: &HashMap<String, Vec<(String, String)>>) -> Vec<(String, usize)> {
    let mut v: Vec<_> = adj
        .iter()
        .map(|(k, list)| (k.clone(), list.len()))
        .collect();
    v.sort_by_key(|(_, d)| *d);
    v
}
