//! Steady-state index memory estimates (retained after decode buffers discarded).

use crate::hot::HotGraph;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct IndexMemoryEstimate {
    pub layout: String,
    /// Estimated retained bytes of the hot index (not peak RSS).
    pub steady_index_bytes: u64,
    pub accounting_notes: String,
}

fn str_bytes(s: &str) -> u64 {
    s.len() as u64
}

fn hashmap_adj_bytes(adj: &std::collections::HashMap<String, Vec<(String, String)>>) -> u64 {
    let mut n = 0u64;
    for (k, v) in adj {
        n += str_bytes(k);
        // HashMap overhead rough: 24 bytes/entry + key capacity
        n += 32;
        n += (v.capacity() as u64) * 48; // approx (String,String) slot
        for (t, et) in v {
            n += str_bytes(t) + str_bytes(et);
        }
    }
    n
}

fn csr_bytes(csr: &crate::hot::Csr) -> u64 {
    let mut n = (csr.offsets.capacity() as u64) * 4;
    n += (csr.targets.capacity() as u64) * 4;
    n += (csr.edge_types.capacity() as u64) * 24;
    for et in &csr.edge_types {
        n += str_bytes(et);
    }
    n
}

fn csc_bytes(csc: &crate::hot::Csc) -> u64 {
    let mut n = (csc.offsets.capacity() as u64) * 4;
    n += (csc.sources.capacity() as u64) * 4;
    n += (csc.edge_types.capacity() as u64) * 24;
    for et in &csc.edge_types {
        n += str_bytes(et);
    }
    n
}

fn idmap_bytes(ids: &crate::hot::IdMap) -> u64 {
    let mut n = 0u64;
    for s in &ids.id_to_str {
        n += str_bytes(s) + 32;
    }
    n += (ids.str_to_id.capacity() as u64) * 40;
    n
}

pub fn estimate_index_memory(graph: &HotGraph) -> IndexMemoryEstimate {
    match graph {
        HotGraph::Hash { adj, ids } => {
            let b = hashmap_adj_bytes(adj) + idmap_bytes(ids);
            IndexMemoryEstimate {
                layout: "hash".into(),
                steady_index_bytes: b,
                accounting_notes: "sum key/value string bytes + vec capacity + IdMap".into(),
            }
        }
        HotGraph::HashBi { out, inn, ids } => {
            let b = hashmap_adj_bytes(out) + hashmap_adj_bytes(inn) + idmap_bytes(ids);
            IndexMemoryEstimate {
                layout: "hash_bi".into(),
                steady_index_bytes: b,
                accounting_notes: "forward+reverse hash maps + IdMap".into(),
            }
        }
        HotGraph::Csr { ids, csr } => {
            let b = csr_bytes(csr) + idmap_bytes(ids);
            IndexMemoryEstimate {
                layout: "csr".into(),
                steady_index_bytes: b,
                accounting_notes: "CSR offsets+targets+types + IdMap".into(),
            }
        }
        HotGraph::CsrCsc { ids, csr, csc } => {
            let b = csr_bytes(csr) + csc_bytes(csc) + idmap_bytes(ids);
            IndexMemoryEstimate {
                layout: "csr_csc".into(),
                steady_index_bytes: b,
                accounting_notes: "CSR+CSC + IdMap".into(),
            }
        }
        HotGraph::Hybrid {
            ids,
            csr,
            csc,
            delta,
        } => {
            let mut b = csr_bytes(csr) + csc_bytes(csc) + idmap_bytes(ids);
            b += (delta.inserts_out.len() as u64) * 64;
            b += (delta.inserts_in.len() as u64) * 64;
            b += (delta.delete_counts.len() as u64) * 64;
            IndexMemoryEstimate {
                layout: "hybrid".into(),
                steady_index_bytes: b,
                accounting_notes: "CSR+CSC base + delta maps (screen runs churn=0)".into(),
            }
        }
    }
}
