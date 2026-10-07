//! In-process hot map — upsert before ``publish_map``.
//!
//! Port of Python ``GraphState`` + ``apply_topo_stream`` WRITE path
//! (``poc/graph/graph_builder.py``).

use crate::admit::{AdmitOutcome, RejectCode, TopologyClaim, admit_topology_claim};
use crate::ci_qualify::{may_emit_vertex, storage_to_ingest, to_storage_type};
use crate::edge_type::EdgeType;
use crate::error::Result;
use crate::publish::{PublishedMap, publish_map};
use crate::types::{GraphEdge, GraphNode};
use std::collections::HashMap;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// Lab snowflake counter (monotonic for PoC; not Motadata production allocator).
static NEXT_ID: AtomicU64 = AtomicU64::new(7_146_828_800_000_100);

pub fn next_snowflake() -> u64 {
    NEXT_ID.fetch_add(1, Ordering::Relaxed)
}

/// Stable upsert key — same as Python ``logical_edge_key``.
pub fn logical_edge_key(source_id: &str, edge_type: &str, target_id: &str) -> String {
    format!("{source_id}|{edge_type}|{target_id}")
}

fn now_epoch_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

/// One stream / topo line after fact_kind filtering (caller skips non-topo).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TopoLine {
    pub src_ci_id: String,
    pub dst_ci_id: String,
    pub relation: String,
    pub identity_resolved: bool,
    pub src_ci_type: Option<String>,
    pub dst_ci_type: Option<String>,
    pub subject_ci_type: Option<String>,
    /// Event time as Unix epoch milliseconds UTC.
    pub ts: Option<u64>,
}

impl TopoLine {
    pub fn into_claim(&self, hot: &HotMap) -> TopologyClaim {
        let src_map = hot.nodes.get(&self.src_ci_id).map(|n| n.type_.clone());
        let dst_map = hot.nodes.get(&self.dst_ci_id).map(|n| n.type_.clone());
        let src_declared = self
            .src_ci_type
            .clone()
            .or_else(|| self.subject_ci_type.clone());
        TopologyClaim {
            src_ci_id: self.src_ci_id.clone(),
            dst_ci_id: self.dst_ci_id.clone(),
            relation: self.relation.clone(),
            identity_resolved: self.identity_resolved,
            src_ci_type: src_declared,
            dst_ci_type: self.dst_ci_type.clone(),
            src_map_type: src_map,
            dst_map_type: dst_map,
        }
    }
}

/// Working estate before / between Dest publishes.
#[derive(Debug, Clone, Default)]
pub struct HotMap {
    pub tenant: String,
    pub nodes: HashMap<String, GraphNode>,
    pub edges: HashMap<String, GraphEdge>,
    pub rejects: Vec<(String, RejectCode)>,
}

impl HotMap {
    pub fn new(tenant: impl Into<String>) -> Self {
        Self {
            tenant: tenant.into(),
            ..Default::default()
        }
    }

    pub fn upsert_node(&mut self, node: GraphNode) {
        let eid = node.entity_id.clone();
        if let Some(prev) = self.nodes.get_mut(&eid) {
            prev.last_seen = node.last_seen;
            prev.version = prev.version.saturating_add(1);
            if node.name != eid {
                prev.name = node.name;
            }
            // Keep Motadata type from first write.
            return;
        }
        self.nodes.insert(eid, node);
    }

    pub fn upsert_edge(&mut self, edge: GraphEdge) {
        let key = logical_edge_key(
            &edge.source_id,
            edge.edge_type.as_str(),
            &edge.target_id,
        );
        if let Some(prev) = self.edges.get_mut(&key) {
            prev.valid_from = edge.valid_from;
            prev.evidence_event_id = edge.evidence_event_id;
            return;
        }
        self.edges.insert(key, edge);
    }

    pub fn nodes_vec(&self) -> Vec<GraphNode> {
        self.nodes.values().cloned().collect()
    }

    pub fn edges_vec(&self) -> Vec<GraphEdge> {
        self.edges.values().cloned().collect()
    }

    fn ensure_node(&mut self, entity_id: &str, emit_type: &str, last_seen: u64) {
        if !may_emit_vertex(emit_type) {
            return;
        }
        let storage = match to_storage_type(emit_type) {
            Some(s) => s,
            None => return,
        };
        self.upsert_node(GraphNode {
            schema_version: "graph_node.v1".into(),
            entity_id: entity_id.into(),
            type_: storage,
            name: entity_id.into(),
            env: None,
            region: None,
            owner: None,
            namespace: None,
            last_seen,
            valid_from: Some(last_seen),
            valid_to: None,
            version: 1,
        });
    }

    /// Admit + mutate for one topology line. Returns the outcome.
    pub fn apply_topo_line(&mut self, line: &TopoLine) -> AdmitOutcome {
        let claim = line.into_claim(self);
        let outcome = admit_topology_claim(&claim);
        match &outcome {
            AdmitOutcome::Noop => {}
            AdmitOutcome::Drop(code) => {
                self.rejects
                    .push((format!("{}-{}-{}", line.src_ci_id, line.relation, line.dst_ci_id), code.clone()));
            }
            AdmitOutcome::Write {
                src_storage,
                dst_storage,
                edge_type,
            } => {
                let ts = line.ts.unwrap_or_else(now_epoch_ms);
                let src_emit = claim
                    .src_ci_type
                    .as_deref()
                    .filter(|s| !s.is_empty())
                    .map(str::to_string)
                    .or_else(|| storage_to_ingest(src_storage).map(str::to_string));
                let dst_emit = claim
                    .dst_ci_type
                    .as_deref()
                    .filter(|s| !s.is_empty())
                    .map(str::to_string)
                    .or_else(|| storage_to_ingest(dst_storage).map(str::to_string));
                if let Some(ref t) = src_emit {
                    self.ensure_node(&line.src_ci_id, t, ts);
                }
                if let Some(ref t) = dst_emit {
                    self.ensure_node(&line.dst_ci_id, t, ts);
                }
                let edge_id = next_snowflake();
                let evidence = next_snowflake();
                self.upsert_edge(GraphEdge {
                    schema_version: "graph_edge.v1".into(),
                    edge_id,
                    source_id: line.src_ci_id.clone(),
                    target_id: line.dst_ci_id.clone(),
                    edge_type: *edge_type,
                    valid_from: Some(ts),
                    valid_to: None,
                    evidence_event_id: evidence,
                });
                let _ = EdgeType::as_str(*edge_type);
            }
        }
        outcome
    }

    /// Apply many lines; returns counts of NOOP / WRITE / DROP.
    pub fn apply_topo_stream(&mut self, lines: &[TopoLine]) -> (usize, usize, usize) {
        let mut noop = 0;
        let mut write = 0;
        let mut drop = 0;
        for line in lines {
            match self.apply_topo_line(line) {
                AdmitOutcome::Noop => noop += 1,
                AdmitOutcome::Write { .. } => write += 1,
                AdmitOutcome::Drop(_) => drop += 1,
            }
        }
        (noop, write, drop)
    }

    /// Cold checkpoint of current hot estate.
    pub async fn publish(
        &self,
        tenant_map_root: impl AsRef<Path>,
        version: &str,
    ) -> Result<PublishedMap> {
        publish_map(
            tenant_map_root,
            &self.tenant,
            version,
            &self.nodes_vec(),
            &self.edges_vec(),
        )
        .await
    }
}
