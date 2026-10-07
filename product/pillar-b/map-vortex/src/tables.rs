//! Build Arrow ``RecordBatch`` tables for ``map_nodes`` / ``map_edges``.

use crate::error::{Error, Result};
use crate::schema::{map_edges_schema_plain, map_nodes_schema_plain};
use crate::types::{GraphEdge, GraphNode};
use arrow::array::{ArrayRef, RecordBatch, StringArray, UInt32Array, UInt64Array};
use arrow::datatypes::Schema;
use std::sync::Arc;

fn opt_str_array(values: Vec<Option<String>>) -> ArrayRef {
    Arc::new(StringArray::from(values)) as ArrayRef
}

fn opt_u64_array(values: Vec<Option<u64>>) -> ArrayRef {
    Arc::new(UInt64Array::from(values)) as ArrayRef
}

/// Build ``map_nodes`` from physical Motadata rows.
pub fn nodes_record_batch(nodes: &[GraphNode]) -> Result<RecordBatch> {
    let schema = Arc::new(map_nodes_schema_plain());
    let entity_id: ArrayRef = Arc::new(StringArray::from_iter_values(
        nodes.iter().map(|n| n.entity_id.as_str()),
    ));
    let type_: ArrayRef = Arc::new(StringArray::from_iter_values(
        nodes.iter().map(|n| n.type_.as_str()),
    ));
    let name: ArrayRef = Arc::new(StringArray::from_iter_values(
        nodes.iter().map(|n| n.name.as_str()),
    ));
    let env = opt_str_array(nodes.iter().map(|n| n.env.clone()).collect());
    let region = opt_str_array(nodes.iter().map(|n| n.region.clone()).collect());
    let owner = opt_str_array(nodes.iter().map(|n| n.owner.clone()).collect());
    let namespace = opt_str_array(nodes.iter().map(|n| n.namespace.clone()).collect());
    let last_seen: ArrayRef = Arc::new(UInt64Array::from_iter_values(
        nodes.iter().map(|n| n.last_seen),
    ));
    let valid_from = opt_u64_array(nodes.iter().map(|n| n.valid_from).collect());
    let valid_to = opt_u64_array(nodes.iter().map(|n| n.valid_to).collect());
    let version: ArrayRef = Arc::new(UInt32Array::from_iter_values(
        nodes.iter().map(|n| n.version),
    ));

    Ok(RecordBatch::try_new(
        schema,
        vec![
            entity_id, type_, name, env, region, owner, namespace, last_seen, valid_from, valid_to,
            version,
        ],
    )?)
}

/// Build ``map_edges`` from physical Motadata rows.
pub fn edges_record_batch(edges: &[GraphEdge]) -> Result<RecordBatch> {
    let schema = Arc::new(map_edges_schema_plain());
    let edge_id: ArrayRef = Arc::new(UInt64Array::from_iter_values(
        edges.iter().map(|e| e.edge_id),
    ));
    let source_id: ArrayRef = Arc::new(StringArray::from_iter_values(
        edges.iter().map(|e| e.source_id.as_str()),
    ));
    let target_id: ArrayRef = Arc::new(StringArray::from_iter_values(
        edges.iter().map(|e| e.target_id.as_str()),
    ));
    let edge_type: ArrayRef = Arc::new(StringArray::from_iter_values(
        edges.iter().map(|e| e.edge_type.as_str()),
    ));
    let valid_from = opt_u64_array(edges.iter().map(|e| e.valid_from).collect());
    let valid_to = opt_u64_array(edges.iter().map(|e| e.valid_to).collect());
    let evidence_event_id: ArrayRef = Arc::new(UInt64Array::from_iter_values(
        edges.iter().map(|e| e.evidence_event_id),
    ));

    Ok(RecordBatch::try_new(
        schema,
        vec![
            edge_id,
            source_id,
            target_id,
            edge_type,
            valid_from,
            valid_to,
            evidence_event_id,
        ],
    )?)
}

/// Column projection helper (walk path: spine only).
pub fn project_batch(batch: &RecordBatch, columns: &[&str]) -> Result<RecordBatch> {
    let mut fields = Vec::with_capacity(columns.len());
    let mut arrays = Vec::with_capacity(columns.len());
    for name in columns {
        let idx = batch
            .schema()
            .index_of(name)
            .map_err(|_| Error::MissingColumn((*name).to_string()))?;
        fields.push(batch.schema().field(idx).clone());
        arrays.push(batch.column(idx).clone());
    }
    let schema = Arc::new(Schema::new_with_metadata(
        fields,
        batch.schema().metadata().clone(),
    ));
    Ok(RecordBatch::try_new(schema, arrays)?)
}
