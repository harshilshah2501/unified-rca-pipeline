//! Cold interface: ``graph_snapshot.v1`` JSON ↔ publish/load for GraphWriter cohesion.

use crate::edge_type::EdgeType;
use crate::error::{Error, Result};
use crate::load::LoadedMap;
use crate::types::{GraphEdge, GraphNode};
use arrow::array::{Array, ArrayRef, StringArray, UInt32Array, UInt64Array};
use arrow::compute::cast;
use arrow::datatypes::DataType;
use arrow::record_batch::RecordBatch;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

/// Packaged snapshot envelope (same logical shape as Python ``build_snapshot``).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphSnapshotJson {
    pub schema_version: String,
    pub tenant: String,
    pub version: String,
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
}

impl GraphSnapshotJson {
    pub fn from_parts(
        tenant: impl Into<String>,
        version: impl Into<String>,
        nodes: Vec<GraphNode>,
        edges: Vec<GraphEdge>,
    ) -> Self {
        Self {
            schema_version: "graph_snapshot.v1".into(),
            tenant: tenant.into(),
            version: version.into(),
            nodes,
            edges,
        }
    }
}

/// Convert a loaded Vortex map into walkable ``graph_snapshot.v1`` JSON rows.
pub fn loaded_map_to_snapshot(loaded: &LoadedMap) -> Result<GraphSnapshotJson> {
    let nodes = nodes_from_batch(&loaded.nodes)?;
    let edges = edges_from_batch(&loaded.edges)?;
    Ok(GraphSnapshotJson::from_parts(
        loaded.manifest.tenant.clone(),
        loaded.manifest.version.clone(),
        nodes,
        edges,
    ))
}

fn col<'a>(batch: &'a RecordBatch, name: &str) -> Result<&'a dyn Array> {
    let idx = batch
        .schema()
        .index_of(name)
        .map_err(|_| Error::Vortex(format!("missing column {name}")))?;
    Ok(batch.column(idx).as_ref())
}

/// Vortex→Arrow often materializes strings as ``Utf8View``; normalize to plain ``Utf8``.
fn as_utf8(arr: &dyn Array) -> Result<StringArray> {
    if let Some(a) = arr.as_any().downcast_ref::<StringArray>() {
        return Ok(a.clone());
    }
    let casted: ArrayRef = cast(arr, &DataType::Utf8)
        .map_err(|e| Error::Vortex(format!("cast to utf8: {e}")))?;
    casted
        .as_any()
        .downcast_ref::<StringArray>()
        .cloned()
        .ok_or_else(|| Error::Vortex("expected utf8 column after cast".into()))
}

fn as_u64(arr: &dyn Array) -> Result<UInt64Array> {
    if let Some(a) = arr.as_any().downcast_ref::<UInt64Array>() {
        return Ok(a.clone());
    }
    let casted: ArrayRef = cast(arr, &DataType::UInt64)
        .map_err(|e| Error::Vortex(format!("cast to u64: {e}")))?;
    casted
        .as_any()
        .downcast_ref::<UInt64Array>()
        .cloned()
        .ok_or_else(|| Error::Vortex("expected u64 column after cast".into()))
}

fn as_u32(arr: &dyn Array) -> Result<UInt32Array> {
    if let Some(a) = arr.as_any().downcast_ref::<UInt32Array>() {
        return Ok(a.clone());
    }
    let casted: ArrayRef = cast(arr, &DataType::UInt32)
        .map_err(|e| Error::Vortex(format!("cast to u32: {e}")))?;
    casted
        .as_any()
        .downcast_ref::<UInt32Array>()
        .cloned()
        .ok_or_else(|| Error::Vortex("expected u32 column after cast".into()))
}

fn str_at(arr: &StringArray, i: usize) -> Result<String> {
    if arr.is_null(i) {
        return Err(Error::Vortex("unexpected null in required utf8".into()));
    }
    Ok(arr.value(i).to_string())
}

fn opt_str_at(arr: &StringArray, i: usize) -> Option<String> {
    if arr.is_null(i) {
        None
    } else {
        Some(arr.value(i).to_string())
    }
}

fn u64_at(arr: &UInt64Array, i: usize) -> Result<u64> {
    if arr.is_null(i) {
        return Err(Error::Vortex("unexpected null in required u64".into()));
    }
    Ok(arr.value(i))
}

fn opt_u64_at(arr: &UInt64Array, i: usize) -> Option<u64> {
    if arr.is_null(i) {
        None
    } else {
        Some(arr.value(i))
    }
}

fn u32_at(arr: &UInt32Array, i: usize) -> Result<u32> {
    if arr.is_null(i) {
        return Err(Error::Vortex("unexpected null in required u32".into()));
    }
    Ok(arr.value(i))
}

pub fn nodes_from_batch(batch: &RecordBatch) -> Result<Vec<GraphNode>> {
    let entity_id = as_utf8(col(batch, "entity_id")?)?;
    let type_ = as_utf8(col(batch, "type")?)?;
    let name = as_utf8(col(batch, "name")?)?;
    let env = as_utf8(col(batch, "env")?)?;
    let region = as_utf8(col(batch, "region")?)?;
    let owner = as_utf8(col(batch, "owner")?)?;
    let namespace = as_utf8(col(batch, "namespace")?)?;
    let last_seen = as_u64(col(batch, "last_seen")?)?;
    let valid_from = as_u64(col(batch, "valid_from")?)?;
    let valid_to = as_u64(col(batch, "valid_to")?)?;
    let version = as_u32(col(batch, "version")?)?;
    let mut out = Vec::with_capacity(batch.num_rows());
    for i in 0..batch.num_rows() {
        out.push(GraphNode {
            schema_version: "graph_node.v1".into(),
            entity_id: str_at(&entity_id, i)?,
            type_: str_at(&type_, i)?,
            name: str_at(&name, i)?,
            env: opt_str_at(&env, i),
            region: opt_str_at(&region, i),
            owner: opt_str_at(&owner, i),
            namespace: opt_str_at(&namespace, i),
            last_seen: u64_at(&last_seen, i)?,
            valid_from: opt_u64_at(&valid_from, i),
            valid_to: opt_u64_at(&valid_to, i),
            version: u32_at(&version, i)?,
        });
    }
    Ok(out)
}

pub fn edges_from_batch(batch: &RecordBatch) -> Result<Vec<GraphEdge>> {
    let edge_id = as_u64(col(batch, "edge_id")?)?;
    let source_id = as_utf8(col(batch, "source_id")?)?;
    let target_id = as_utf8(col(batch, "target_id")?)?;
    let edge_type = as_utf8(col(batch, "edge_type")?)?;
    let valid_from = as_u64(col(batch, "valid_from")?)?;
    let valid_to = as_u64(col(batch, "valid_to")?)?;
    let evidence_event_id = as_u64(col(batch, "evidence_event_id")?)?;
    let mut out = Vec::with_capacity(batch.num_rows());
    for i in 0..batch.num_rows() {
        let et_raw = str_at(&edge_type, i)?;
        let et = EdgeType::from_str(&et_raw).map_err(|_| Error::UnknownEdgeType(et_raw))?;
        out.push(GraphEdge {
            schema_version: "graph_edge.v1".into(),
            edge_id: u64_at(&edge_id, i)?,
            source_id: str_at(&source_id, i)?,
            target_id: str_at(&target_id, i)?,
            edge_type: et,
            valid_from: opt_u64_at(&valid_from, i),
            valid_to: opt_u64_at(&valid_to, i),
            evidence_event_id: u64_at(&evidence_event_id, i)?,
        });
    }
    Ok(out)
}
