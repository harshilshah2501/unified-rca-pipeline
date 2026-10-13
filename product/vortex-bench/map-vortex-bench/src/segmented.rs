//! Segmented CSR+CSC with atomic snapshot publish (Action 6 / Milestone B).
//!
//! Partition: node `u` → segment `u % num_segments`.
//! Each segment stores:
//! - CSR for arcs with `src` in the segment
//! - CSC for arcs with `tgt` in the segment
//!
//! Mutation batch: rebuild only segments touched by inserted/deleted endpoints,
//! then publish a new `Arc<SegmentedSnapshot>` (atomic pointer swap analogue).

use crate::hot::{Csc, Csr, IdMap};
use crate::synth::mix;
use anyhow::Result;
use serde::Serialize;
use std::collections::HashSet;
use std::sync::{Arc, RwLock};
use std::time::Instant;

#[derive(Clone)]
pub struct Segment {
    pub csr: Csr,
    pub csc: Csc,
}

#[derive(Clone)]
pub struct SegmentedSnapshot {
    pub ids: Arc<IdMap>,
    pub num_segments: u32,
    pub segments: Arc<Vec<Segment>>,
    pub generation: u64,
    pub arc_count: usize,
}

impl SegmentedSnapshot {
    fn seg_of(&self, u: u32) -> usize {
        (u % self.num_segments) as usize
    }

    pub fn forward_expand(&self, cur: u32) -> Vec<(u32, String)> {
        let seg = &self.segments[self.seg_of(cur)];
        seg.csr
            .neighbors(cur)
            .map(|(t, et)| (t, et.to_string()))
            .collect()
    }

    pub fn reverse_expand(&self, cur: u32) -> Vec<(u32, String)> {
        let seg = &self.segments[self.seg_of(cur)];
        seg.csc
            .predecessors(cur)
            .map(|(s, et)| (s, et.to_string()))
            .collect()
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct MutationTiming {
    pub batch_id: u64,
    pub inserts: usize,
    pub deletes: usize,
    pub segments_rebuilt: usize,
    pub rebuild_ms: f64,
    pub publish_ms: f64,
    /// T_mutation_visible = rebuild + publish (accepted batch → published snapshot).
    pub t_mutation_visible_ms: f64,
    pub generation: u64,
    pub peak_rss_bytes: Option<u64>,
    /// Peak RSS while at least one old pin and the new snapshot both exist.
    pub dual_hold_peak_rss_bytes: Option<u64>,
    /// Old pin still consistent (CSR⇔CSC) after publish.
    pub old_pin_symmetric_ok: bool,
    /// New pin consistent (CSR⇔CSC) after publish.
    pub new_pin_symmetric_ok: bool,
    pub old_generation: u64,
    pub new_generation: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct OverlapReaderReport {
    pub readers: u32,
    pub ops: usize,
    pub generation_mismatches: u64,
    pub symmetry_failures: u64,
    pub ok: bool,
}

pub struct SegmentedStore {
    ids: Arc<IdMap>,
    /// Authoritative typed multigraph (src, tgt, edge_type).
    edges: Vec<(u32, u32, String)>,
    num_segments: u32,
    /// Shared published pointer so readers can pin without `&mut` on the store.
    published: Arc<RwLock<Arc<SegmentedSnapshot>>>,
    next_gen: u64,
}

impl SegmentedStore {
    pub fn from_triples(
        ids: IdMap,
        triples: Vec<(u32, u32, String)>,
        num_segments: u32,
    ) -> Self {
        let num_segments = num_segments.max(1);
        let ids = Arc::new(ids);
        let n = ids.len();
        let segments = rebuild_all_segments(n, num_segments, &triples);
        let arc_count = triples.len();
        let snap = Arc::new(SegmentedSnapshot {
            ids: Arc::clone(&ids),
            num_segments,
            segments: Arc::new(segments),
            generation: 0,
            arc_count,
        });
        Self {
            ids,
            edges: triples,
            num_segments,
            published: Arc::new(RwLock::new(snap)),
            next_gen: 1,
        }
    }

    pub fn pin(&self) -> Arc<SegmentedSnapshot> {
        Arc::clone(&self.published.read().expect("published rwlock"))
    }

    /// Cloneable handle for concurrent readers (Action 6 overlap residual).
    pub fn published_handle(&self) -> Arc<RwLock<Arc<SegmentedSnapshot>>> {
        Arc::clone(&self.published)
    }

    pub fn num_segments(&self) -> u32 {
        self.num_segments
    }

    pub fn arc_count(&self) -> usize {
        self.edges.len()
    }

    /// Apply inserts then deletes; rebuild touched segments; publish new snapshot.
    /// Holds the pre-publish pin through rebuild so dual-snapshot RSS is observable.
    pub fn apply_batch(
        &mut self,
        inserts: &[(u32, u32, String)],
        deletes: &[(u32, u32, String)],
    ) -> MutationTiming {
        let old_pin = self.pin();
        let old_generation = old_pin.generation;
        let started = Instant::now();
        let mut touched: HashSet<u32> = HashSet::new();
        for (s, t, _) in inserts.iter().chain(deletes.iter()) {
            touched.insert(s % self.num_segments);
            touched.insert(t % self.num_segments);
        }

        for (s, t, et) in inserts {
            self.edges.push((*s, *t, et.clone()));
        }
        for (s, t, et) in deletes {
            if let Some(pos) = self
                .edges
                .iter()
                .position(|(a, b, e)| a == s && b == t && e == et)
            {
                self.edges.swap_remove(pos);
            }
        }

        let n = self.ids.len();
        let mut segs = (*old_pin.segments).clone();
        for seg_id in &touched {
            let (csr, csc) = build_one_segment(n, self.num_segments, *seg_id, &self.edges);
            segs[*seg_id as usize] = Segment { csr, csc };
        }
        let rebuild_ms = started.elapsed().as_secs_f64() * 1000.0;

        let pub_started = Instant::now();
        let generation_id = self.next_gen;
        self.next_gen += 1;
        let new_snap = Arc::new(SegmentedSnapshot {
            ids: Arc::clone(&self.ids),
            num_segments: self.num_segments,
            segments: Arc::new(segs),
            generation: generation_id,
            arc_count: self.edges.len(),
        });
        // Dual-hold window: old pin + new snapshot both live before publish swap settles.
        let dual_hold_peak = crate::rss::peak_rss_bytes();
        // Atomic publish: swap published pointer; old Arc drops when last pin releases.
        *self.published.write().expect("published rwlock") = Arc::clone(&new_snap);
        let publish_ms = pub_started.elapsed().as_secs_f64() * 1000.0;
        let peak = crate::rss::peak_rss_bytes();

        let old_pin_symmetric_ok = snapshot_csr_csc_symmetric(&old_pin);
        let new_pin_symmetric_ok = snapshot_csr_csc_symmetric(&new_snap);
        // Old pin must still observe its generation after publish (immutability).
        let old_gen_stable = old_pin.generation == old_generation;

        MutationTiming {
            batch_id: generation_id,
            inserts: inserts.len(),
            deletes: deletes.len(),
            segments_rebuilt: touched.len(),
            rebuild_ms,
            publish_ms,
            t_mutation_visible_ms: rebuild_ms + publish_ms,
            generation: generation_id,
            peak_rss_bytes: peak,
            dual_hold_peak_rss_bytes: dual_hold_peak,
            old_pin_symmetric_ok: old_pin_symmetric_ok && old_gen_stable,
            new_pin_symmetric_ok,
            old_generation,
            new_generation: generation_id,
        }
    }
}

/// CSR arc multiset must equal CSC arc multiset for a single pinned generation.
/// Iterates only nodes owned by each segment (not full n × segments).
pub fn snapshot_csr_csc_symmetric(snap: &SegmentedSnapshot) -> bool {
    use std::collections::HashMap;
    let mut from_csr: HashMap<(u32, u32, String), u32> = HashMap::new();
    let mut from_csc: HashMap<(u32, u32, String), u32> = HashMap::new();
    let n = snap.ids.len() as u32;
    let k = snap.num_segments;
    for seg_id in 0..k {
        let seg = &snap.segments[seg_id as usize];
        let mut u = seg_id;
        while u < n {
            for (tgt, et) in seg.csr.neighbors(u) {
                *from_csr.entry((u, tgt, et.to_string())).or_default() += 1;
            }
            for (src, et) in seg.csc.predecessors(u) {
                *from_csc.entry((src, u, et.to_string())).or_default() += 1;
            }
            u += k;
        }
    }
    from_csr == from_csc
}

/// Background pinned readers that run until `stop` is set (true publish overlap).
pub struct OverlapReaders {
    stop: Arc<std::sync::atomic::AtomicBool>,
    mismatches: Arc<std::sync::atomic::AtomicU64>,
    sym_fail: Arc<std::sync::atomic::AtomicU64>,
    ops: Arc<std::sync::atomic::AtomicU64>,
    handles: Vec<std::thread::JoinHandle<()>>,
    readers: u32,
}

impl OverlapReaders {
    pub fn spawn(
        published: Arc<RwLock<Arc<SegmentedSnapshot>>>,
        seed: &str,
        readers: u32,
    ) -> Self {
        use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
        use std::thread;

        let readers = readers.max(1);
        let stop = Arc::new(AtomicBool::new(false));
        let mismatches = Arc::new(AtomicU64::new(0));
        let sym_fail = Arc::new(AtomicU64::new(0));
        let ops = Arc::new(AtomicU64::new(0));
        let mut handles = Vec::new();
        for _ in 0..readers {
            let published = Arc::clone(&published);
            let stop = Arc::clone(&stop);
            let mismatches = Arc::clone(&mismatches);
            let sym_fail = Arc::clone(&sym_fail);
            let ops = Arc::clone(&ops);
            let seed = seed.to_string();
            handles.push(thread::spawn(move || {
                while !stop.load(Ordering::Relaxed) {
                    let pin = Arc::clone(&published.read().expect("published rwlock"));
                    let g0 = pin.generation;
                    let (_n, _ms, _) = bfs_segmented(&pin, &seed, 2, false);
                    let g1 = pin.generation;
                    let (_n2, _ms2, _) = bfs_segmented(&pin, &seed, 2, true);
                    let g2 = pin.generation;
                    if g0 != g1 || g1 != g2 || g0 != pin.generation {
                        mismatches.fetch_add(1, Ordering::Relaxed);
                    }
                    if let Some(&sid) = pin.ids.str_to_id.get(&seed) {
                        let fw = pin.forward_expand(sid);
                        if let Some((nbr, _)) = fw.first() {
                            let _ = pin.reverse_expand(*nbr);
                        }
                    }
                    ops.fetch_add(1, Ordering::Relaxed);
                }
                let pin = Arc::clone(&published.read().expect("published rwlock"));
                if !snapshot_csr_csc_symmetric(&pin) {
                    sym_fail.fetch_add(1, Ordering::Relaxed);
                }
            }));
        }
        Self {
            stop,
            mismatches,
            sym_fail,
            ops,
            handles,
            readers,
        }
    }

    pub fn finish(self) -> OverlapReaderReport {
        use std::sync::atomic::Ordering;
        self.stop.store(true, Ordering::Relaxed);
        for h in self.handles {
            let _ = h.join();
        }
        let generation_mismatches = self.mismatches.load(Ordering::Relaxed);
        let symmetry_failures = self.sym_fail.load(Ordering::Relaxed);
        OverlapReaderReport {
            readers: self.readers,
            ops: self.ops.load(Ordering::Relaxed) as usize,
            generation_mismatches,
            symmetry_failures,
            ok: generation_mismatches == 0 && symmetry_failures == 0,
        }
    }
}

fn rebuild_all_segments(
    n: usize,
    num_segments: u32,
    triples: &[(u32, u32, String)],
) -> Vec<Segment> {
    (0..num_segments)
        .map(|seg_id| {
            let (csr, csc) = build_one_segment(n, num_segments, seg_id, triples);
            Segment { csr, csc }
        })
        .collect()
}

fn build_one_segment(
    n: usize,
    num_segments: u32,
    seg_id: u32,
    triples: &[(u32, u32, String)],
) -> (Csr, Csc) {
    let out_triples: Vec<(u32, u32, String)> = triples
        .iter()
        .filter(|(s, _, _)| s % num_segments == seg_id)
        .cloned()
        .collect();
    let in_triples: Vec<(u32, u32, String)> = triples
        .iter()
        .filter(|(_, t, _)| t % num_segments == seg_id)
        .cloned()
        .collect();
    // CSR/CSC builders expect full node space `n` with empty lists for non-members.
    let csr = Csr::from_sorted_triples(n, out_triples);
    let csc = Csc::from_triples(n, &in_triples);
    (csr, csc)
}

/// BFS on a pinned segmented snapshot (Action 6 T_query).
pub fn bfs_segmented(
    snap: &SegmentedSnapshot,
    seed: &str,
    hops: usize,
    reverse: bool,
) -> (usize, f64, Vec<String>) {
    // Reuse string-id space via a thin HotGraph-like walk without converting layouts.
    let started = Instant::now();
    let Some(&seed_u) = snap.ids.str_to_id.get(seed) else {
        return (0, 0.0, Vec::new());
    };
    use std::collections::{HashSet, VecDeque};
    let mut seen = HashSet::new();
    let mut q = VecDeque::new();
    seen.insert(seed_u);
    q.push_back((seed_u, 0usize));
    while let Some((cur, d)) = q.pop_front() {
        if d >= hops {
            continue;
        }
        let nbrs = if reverse {
            snap.reverse_expand(cur)
        } else {
            snap.forward_expand(cur)
        };
        for (nxt, _) in nbrs {
            if seen.insert(nxt) {
                q.push_back((nxt, d + 1));
            }
        }
    }
    let mut names: Vec<String> = seen
        .iter()
        .map(|&u| snap.ids.id_to_str[u as usize].clone())
        .collect();
    names.sort();
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    (names.len(), ms, names)
}

/// Synthetic mutation batch drawn from existing edge endpoints (lab only).
pub fn synth_mutation_batch(
    edges: &[(u32, u32, String)],
    seed: u64,
    batch_id: u64,
    inserts: usize,
    deletes: usize,
) -> (Vec<(u32, u32, String)>, Vec<(u32, u32, String)>) {
    if edges.is_empty() {
        return (Vec::new(), Vec::new());
    }
    let mut ins = Vec::with_capacity(inserts);
    let mut del = Vec::with_capacity(deletes);
    for i in 0..inserts {
        let r = mix(seed ^ 0xA6A6, mix(batch_id, i as u64));
        let a = &edges[(r as usize) % edges.len()];
        let b = &edges[((r >> 8) as usize) % edges.len()];
        // Re-wire: src from a, tgt from b, type from a — creates a new typed arc.
        ins.push((a.0, b.1, a.2.clone()));
    }
    for i in 0..deletes {
        let r = mix(seed ^ 0xB7B7, mix(batch_id, i as u64 + 1));
        let e = &edges[(r as usize) % edges.len()];
        del.push(e.clone());
    }
    (ins, del)
}

/// Build conventional CSR+CSC from the same triples (full rebuild baseline).
pub fn build_conventional_csr_csc(
    n: usize,
    triples: &[(u32, u32, String)],
) -> Result<(Csr, Csc, f64)> {
    let started = Instant::now();
    let csr = Csr::from_sorted_triples(n, triples.to_vec());
    let csc = Csc::from_triples(n, triples);
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    Ok((csr, csc, ms))
}
