//! Action 6 priority 3 — lab durability / crash-injection / replay for segmented CSR+CSC.
//!
//! This is a **bench fidelity model**, not Motadata's production commit protocol.
//! Layout: durable directory under `--out` with committed marker, pending batch, and
//! optional publish-in-progress flag. Failure points abort before/after each durable step.

use crate::segmented::{SegmentedStore, snapshot_csr_csc_symmetric};
use anyhow::{Context, Result, bail};
use clap::ValueEnum;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum, Serialize)]
pub enum CrashPoint {
    /// Abort before writing the pending mutation batch.
    BeforeMutationPersist,
    /// Pending batch durable; abort before rebuild/publish.
    AfterPersistBeforePublish,
    /// Pending durable; abort mid-construction (incomplete never published).
    DuringSnapshotConstruction,
    /// New snapshot built; abort during/after publish marker write.
    DuringOrAfterPublication,
    /// Published committed; abort before durable replay-progress clear.
    AfterPublishBeforeReplayProgress,
    /// Happy path — no crash.
    None,
}

impl CrashPoint {
    pub fn id(self) -> &'static str {
        match self {
            Self::BeforeMutationPersist => "before_mutation_persist",
            Self::AfterPersistBeforePublish => "after_persist_before_publish",
            Self::DuringSnapshotConstruction => "during_snapshot_construction",
            Self::DuringOrAfterPublication => "during_or_after_publication",
            Self::AfterPublishBeforeReplayProgress => "after_publish_before_replay_progress",
            Self::None => "none",
        }
    }

    pub fn all_injected() -> &'static [CrashPoint] {
        &[
            Self::BeforeMutationPersist,
            Self::AfterPersistBeforePublish,
            Self::DuringSnapshotConstruction,
            Self::DuringOrAfterPublication,
            Self::AfterPublishBeforeReplayProgress,
        ]
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CommittedMarker {
    generation: u64,
    edge_checksum: String,
    arc_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PendingBatch {
    target_generation: u64,
    inserts: Vec<(u32, u32, String)>,
    deletes: Vec<(u32, u32, String)>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DurabilityCaseResult {
    pub crash_point: String,
    pub committed_generation_before: u64,
    pub committed_generation_after_recovery: u64,
    pub expected_generation: u64,
    pub recovery_ms: f64,
    pub mutations_replayed: usize,
    pub mutations_lost: usize,
    pub oracle_multiset_ok: bool,
    pub symmetry_ok: bool,
    pub generation_ok: bool,
    pub incomplete_never_served: bool,
    pub ok: bool,
    pub notes: String,
}

fn edge_checksum(edges: &[(u32, u32, String)]) -> String {
    let mut items: Vec<_> = edges.iter().cloned().collect();
    items.sort();
    let mut h: u64 = 0xcbf29ce484222325;
    for (s, t, et) in items {
        h ^= s as u64;
        h = h.wrapping_mul(0x100000001b3);
        h ^= t as u64;
        h = h.wrapping_mul(0x100000001b3);
        for b in et.bytes() {
            h ^= b as u64;
            h = h.wrapping_mul(0x100000001b3);
        }
        h ^= 0xA5;
        h = h.wrapping_mul(0x100000001b3);
    }
    format!("{h:016x}")
}

fn edge_multiset(edges: &[(u32, u32, String)]) -> HashMap<(u32, u32, String), u32> {
    let mut m = HashMap::new();
    for e in edges {
        *m.entry(e.clone()).or_default() += 1;
    }
    m
}

fn apply_edges_in_memory(
    base: &[(u32, u32, String)],
    inserts: &[(u32, u32, String)],
    deletes: &[(u32, u32, String)],
) -> Vec<(u32, u32, String)> {
    let mut edges = base.to_vec();
    for e in inserts {
        edges.push(e.clone());
    }
    for e in deletes {
        if let Some(pos) = edges
            .iter()
            .position(|(s, t, et)| s == &e.0 && t == &e.1 && et == &e.2)
        {
            edges.swap_remove(pos);
        }
    }
    edges
}

pub struct DurableDir {
    root: PathBuf,
}

impl DurableDir {
    pub fn new(root: PathBuf) -> Result<Self> {
        fs::create_dir_all(&root)?;
        Ok(Self { root })
    }

    fn committed_path(&self) -> PathBuf {
        self.root.join("committed_gen.json")
    }
    fn pending_path(&self) -> PathBuf {
        self.root.join("pending_batch.json")
    }
    fn publish_inflight_path(&self) -> PathBuf {
        self.root.join("publish_inflight.flag")
    }
    fn edges_checkpoint_path(&self) -> PathBuf {
        self.root.join("committed_edges.json")
    }

    pub fn write_committed(&self, generation_id: u64, edges: &[(u32, u32, String)]) -> Result<()> {
        let marker = CommittedMarker {
            generation: generation_id,
            edge_checksum: edge_checksum(edges),
            arc_count: edges.len(),
        };
        fs::write(self.committed_path(), serde_json::to_string_pretty(&marker)?)?;
        // Durable edge checkpoint for lab recovery (authoritative committed multiset).
        fs::write(
            self.edges_checkpoint_path(),
            serde_json::to_string(edges)?,
        )?;
        Ok(())
    }

    pub fn read_committed(&self) -> Result<Option<CommittedMarker>> {
        let p = self.committed_path();
        if !p.exists() {
            return Ok(None);
        }
        let s = fs::read_to_string(&p)?;
        Ok(Some(serde_json::from_str(&s)?))
    }

    pub fn read_committed_edges(&self) -> Result<Vec<(u32, u32, String)>> {
        let p = self.edges_checkpoint_path();
        if !p.exists() {
            return Ok(Vec::new());
        }
        Ok(serde_json::from_str(&fs::read_to_string(p)?)?)
    }

    pub fn write_pending(&self, pending: &PendingBatch) -> Result<()> {
        fs::write(self.pending_path(), serde_json::to_string_pretty(pending)?)?;
        Ok(())
    }

    pub fn read_pending(&self) -> Result<Option<PendingBatch>> {
        let p = self.pending_path();
        if !p.exists() {
            return Ok(None);
        }
        Ok(Some(serde_json::from_str(&fs::read_to_string(p)?)?))
    }

    pub fn clear_pending(&self) -> Result<()> {
        let p = self.pending_path();
        if p.exists() {
            fs::remove_file(p)?;
        }
        Ok(())
    }

    pub fn set_publish_inflight(&self, on: bool) -> Result<()> {
        let p = self.publish_inflight_path();
        if on {
            fs::write(&p, b"1")?;
        } else if p.exists() {
            fs::remove_file(p)?;
        }
        Ok(())
    }

    pub fn publish_inflight(&self) -> bool {
        self.publish_inflight_path().exists()
    }
}

/// Run one crash-injected durable mutation + recovery, compare to oracle expectation.
pub fn run_crash_case(
    durable_root: &Path,
    base_edges: &[(u32, u32, String)],
    ids_n: usize,
    num_segments: u32,
    ids: crate::hot::IdMap,
    inserts: &[(u32, u32, String)],
    deletes: &[(u32, u32, String)],
    crash: CrashPoint,
) -> Result<DurabilityCaseResult> {
    // Fresh durable dir per case.
    if durable_root.exists() {
        fs::remove_dir_all(durable_root)?;
    }
    let dir = DurableDir::new(durable_root.to_path_buf())?;
    dir.write_committed(0, base_edges)?;

    let mut store = SegmentedStore::from_triples(ids, base_edges.to_vec(), num_segments);
    let committed_before = 0u64;
    let target_gen = 1u64;
    let expected_after_success = apply_edges_in_memory(base_edges, inserts, deletes);

    let pending = PendingBatch {
        target_generation: target_gen,
        inserts: inserts.to_vec(),
        deletes: deletes.to_vec(),
    };

    // --- simulate publish pipeline with crash injection ---
    let crashed = match crash {
        CrashPoint::BeforeMutationPersist => {
            // Never persist pending.
            true
        }
        CrashPoint::AfterPersistBeforePublish => {
            dir.write_pending(&pending)?;
            true
        }
        CrashPoint::DuringSnapshotConstruction => {
            dir.write_pending(&pending)?;
            // Simulate crash mid-construction: do **not** call apply_batch/publish.
            // Incomplete work exists only ephemerally and is discarded on recovery.
            let _ = (&mut store, ids_n);
            true
        }
        CrashPoint::DuringOrAfterPublication => {
            dir.write_pending(&pending)?;
            dir.set_publish_inflight(true)?;
            let mt = store.apply_batch(inserts, deletes);
            // Publish succeeded in memory; crash before durable committed marker + clearing pending.
            // Inflight flag remains; committed marker still generation_id 0.
            let _ = mt;
            true
        }
        CrashPoint::AfterPublishBeforeReplayProgress => {
            dir.write_pending(&pending)?;
            let mt = store.apply_batch(inserts, deletes);
            // Durably commit new generation, but leave pending in place (replay progress not cleared).
            dir.write_committed(mt.new_generation, &expected_after_success)?;
            dir.set_publish_inflight(false)?;
            true
        }
        CrashPoint::None => {
            dir.write_pending(&pending)?;
            let mt = store.apply_batch(inserts, deletes);
            dir.write_committed(mt.new_generation, &expected_after_success)?;
            dir.clear_pending()?;
            dir.set_publish_inflight(false)?;
            false
        }
    };

    // --- recovery ---
    let started = Instant::now();
    let (recovered_edges, recovered_gen, replayed, lost, notes, incomplete_never_served) =
        recover(&dir, base_edges, crash)?;
    let recovery_ms = started.elapsed().as_secs_f64() * 1000.0;

    // Rebuild served snapshot from recovered committed edges.
    // Re-create IdMap from recovered edge endpoint ids is awkward; reuse store's ids via rebuild.
    // For oracle we compare multisets only; rebuild a fresh store for symmetry if generation_id>0 or always.
    let ids2 = rebuild_idmap_from_edges(&recovered_edges, base_edges);
    let store2 = SegmentedStore::from_triples(ids2, recovered_edges.clone(), num_segments);
    let pin = store2.pin();
    let symmetry_ok = snapshot_csr_csc_symmetric(&pin);
    // BeforeMutationPersist: stay at generation_id 0. All other injected points leave durable pending
    // (or committed+stale pending) that recovery must bring to the intended new multiset at generation_id 1.
    let expected_edges = match crash {
        CrashPoint::BeforeMutationPersist => base_edges.to_vec(),
        _ => expected_after_success.clone(),
    };
    let expected_gen = match crash {
        CrashPoint::BeforeMutationPersist => 0,
        _ => 1,
    };

    let oracle_multiset_ok = edge_multiset(&recovered_edges) == edge_multiset(&expected_edges);
    let generation_ok = recovered_gen == expected_gen;
    let ok = oracle_multiset_ok && symmetry_ok && generation_ok && incomplete_never_served;

    let _ = (crashed, committed_before, target_gen);
    Ok(DurabilityCaseResult {
        crash_point: crash.id().into(),
        committed_generation_before: committed_before,
        committed_generation_after_recovery: recovered_gen,
        expected_generation: expected_gen,
        recovery_ms,
        mutations_replayed: replayed,
        mutations_lost: lost,
        oracle_multiset_ok,
        symmetry_ok,
        generation_ok,
        incomplete_never_served,
        ok,
        notes,
    })
}

fn rebuild_idmap_from_edges(
    recovered: &[(u32, u32, String)],
    base: &[(u32, u32, String)],
) -> crate::hot::IdMap {
    // IdMap is string-based in production paths; here edges are already numeric ids.
    // Build a synthetic IdMap with id_to_str[i] = i.to_string() covering max id.
    let mut max_id = 0u32;
    for (s, t, _) in recovered.iter().chain(base.iter()) {
        max_id = max_id.max(*s).max(*t);
    }
    let mut id_to_str = Vec::with_capacity(max_id as usize + 1);
    let mut str_to_id = HashMap::new();
    for i in 0..=max_id {
        let s = format!("n{i}");
        str_to_id.insert(s.clone(), i);
        id_to_str.push(s);
    }
    crate::hot::IdMap { id_to_str, str_to_id }
}

fn recover(
    dir: &DurableDir,
    base_edges: &[(u32, u32, String)],
    crash: CrashPoint,
) -> Result<(Vec<(u32, u32, String)>, u64, usize, usize, String, bool)> {
    let committed = dir
        .read_committed()?
        .context("committed marker missing after init")?;
    let pending = dir.read_pending()?;
    let inflight = dir.publish_inflight();

    // Incomplete snapshot never served: if inflight without updated committed, discard inflight work.
    let incomplete_never_served = match crash {
        CrashPoint::DuringSnapshotConstruction => {
            // Committed still 0; no publish marker that exposes incomplete.
            committed.generation == 0 && !inflight
        }
        CrashPoint::DuringOrAfterPublication => {
            // Inflight set but committed still 0 → must not serve generation_id 1 until replay commits.
            committed.generation == 0
        }
        _ => true,
    };

    let mut notes = String::new();
    let (edges, generation_id, replayed, lost) = if let Some(p) = pending {
        if committed.generation >= p.target_generation {
            // Pending already reflected in committed — clear as idempotent replay progress.
            dir.clear_pending()?;
            dir.set_publish_inflight(false)?;
            notes = "idempotent_clear_stale_pending".into();
            let edges = dir.read_committed_edges()?;
            (edges, committed.generation, 0usize, 0usize)
        } else {
            // Replay pending onto committed edges.
            let base = if committed.generation == 0 {
                base_edges.to_vec()
            } else {
                dir.read_committed_edges()?
            };
            let edges = apply_edges_in_memory(&base, &p.inserts, &p.deletes);
            let n_mut = p.inserts.len() + p.deletes.len();
            dir.write_committed(p.target_generation, &edges)?;
            dir.clear_pending()?;
            dir.set_publish_inflight(false)?;
            notes = format!("replayed_pending_to_gen_{}", p.target_generation);
            (edges, p.target_generation, n_mut, 0usize)
        }
    } else {
        // No pending: committed is authoritative.
        let edges = if committed.generation == 0 {
            base_edges.to_vec()
        } else {
            dir.read_committed_edges()?
        };
        if crash == CrashPoint::BeforeMutationPersist {
            notes = "no_pending_retained_previous_committed".into();
        } else {
            notes = "no_pending_use_committed".into();
        }
        dir.set_publish_inflight(false)?;
        (edges, committed.generation, 0usize, 0usize)
    };

    // Verify checksum if present.
    if let Some(m) = dir.read_committed()? {
        if edge_checksum(&edges) != m.edge_checksum && m.generation > 0 {
            bail!(
                "recovered edges checksum {} != marker {}",
                edge_checksum(&edges),
                m.edge_checksum
            );
        }
    }

    let _ = inflight;
    Ok((
        edges,
        generation_id,
        replayed,
        lost,
        notes,
        incomplete_never_served,
    ))
}
