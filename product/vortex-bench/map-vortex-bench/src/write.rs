//! Build locked map_nodes / map_edges Arrow batches and write Vortex parts.

use crate::synth::{EdgeRow, NodeRow};
use anyhow::{Context, Result};
use arrow::array::{ArrayRef, RecordBatch, StringArray, UInt32Array, UInt64Array};
use arrow::datatypes::{DataType, Field, Schema};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use vortex::VortexSessionDefault;
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBufferMut;
use vortex::file::WriteOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

#[derive(Debug, Clone)]
pub struct WrittenParts {
    pub nodes_path: PathBuf,
    pub edges_path: PathBuf,
    pub nodes_bytes: u64,
    pub edges_bytes: u64,
    pub write_ms: u128,
}

pub async fn write_parts(
    nodes: &[NodeRow],
    edges: &[EdgeRow],
    out_dir: &Path,
) -> Result<WrittenParts> {
    std::fs::create_dir_all(out_dir)?;
    let started = std::time::Instant::now();
    let nodes_batch = nodes_batch(nodes)?;
    let edges_batch = edges_batch(edges)?;
    let nodes_path = write_vortex(&nodes_batch, out_dir.join("nodes.vortex")).await?;
    let edges_path = write_vortex(&edges_batch, out_dir.join("edges.vortex")).await?;
    let write_ms = started.elapsed().as_millis();
    Ok(WrittenParts {
        nodes_bytes: std::fs::metadata(&nodes_path)?.len(),
        edges_bytes: std::fs::metadata(&edges_path)?.len(),
        nodes_path,
        edges_path,
        write_ms,
    })
}

async fn write_vortex(batch: &RecordBatch, path: PathBuf) -> Result<PathBuf> {
    let session = VortexSession::default().with_tokio();
    let array = session
        .arrow()
        .from_arrow_record_batch(batch.clone(), batch.schema().as_ref())
        .map_err(|e| anyhow::anyhow!("arrow→vortex: {e}"))?;
    let mut buf = ByteBufferMut::empty();
    session
        .write_options()
        .write(&mut buf, array.to_array_stream())
        .await
        .map_err(|e| anyhow::anyhow!("vortex write: {e}"))?;
    std::fs::write(&path, buf.as_ref()).with_context(|| format!("write {}", path.display()))?;
    Ok(path)
}

fn opt_str(values: Vec<Option<String>>) -> ArrayRef {
    Arc::new(StringArray::from(values))
}

fn opt_u64(values: Vec<Option<u64>>) -> ArrayRef {
    Arc::new(UInt64Array::from(values))
}

pub fn nodes_batch(nodes: &[NodeRow]) -> Result<RecordBatch> {
    let schema = Arc::new(Schema::new(vec![
        Field::new("entity_id", DataType::Utf8, false),
        Field::new("type", DataType::Utf8, false),
        Field::new("name", DataType::Utf8, false),
        Field::new("env", DataType::Utf8, true),
        Field::new("region", DataType::Utf8, true),
        Field::new("owner", DataType::Utf8, true),
        Field::new("namespace", DataType::Utf8, true),
        Field::new("last_seen", DataType::UInt64, false),
        Field::new("valid_from", DataType::UInt64, true),
        Field::new("valid_to", DataType::UInt64, true),
        Field::new("version", DataType::UInt32, false),
    ]));
    Ok(RecordBatch::try_new(
        schema,
        vec![
            Arc::new(StringArray::from_iter_values(nodes.iter().map(|n| n.entity_id.as_str()))),
            Arc::new(StringArray::from_iter_values(nodes.iter().map(|n| n.type_.as_str()))),
            Arc::new(StringArray::from_iter_values(nodes.iter().map(|n| n.name.as_str()))),
            opt_str(nodes.iter().map(|n| n.env.clone()).collect()),
            opt_str(nodes.iter().map(|n| n.region.clone()).collect()),
            opt_str(nodes.iter().map(|n| n.owner.clone()).collect()),
            opt_str(nodes.iter().map(|n| n.namespace.clone()).collect()),
            Arc::new(UInt64Array::from_iter_values(nodes.iter().map(|n| n.last_seen))),
            opt_u64(nodes.iter().map(|n| n.valid_from).collect()),
            opt_u64(nodes.iter().map(|n| n.valid_to).collect()),
            Arc::new(UInt32Array::from_iter_values(nodes.iter().map(|n| n.version))),
        ],
    )?)
}

pub fn edges_batch(edges: &[EdgeRow]) -> Result<RecordBatch> {
    let schema = Arc::new(Schema::new(vec![
        Field::new("edge_id", DataType::UInt64, false),
        Field::new("source_id", DataType::Utf8, false),
        Field::new("target_id", DataType::Utf8, false),
        Field::new("edge_type", DataType::Utf8, false),
        Field::new("valid_from", DataType::UInt64, true),
        Field::new("valid_to", DataType::UInt64, true),
        Field::new("evidence_event_id", DataType::UInt64, false),
    ]));
    Ok(RecordBatch::try_new(
        schema,
        vec![
            Arc::new(UInt64Array::from_iter_values(edges.iter().map(|e| e.edge_id))),
            Arc::new(StringArray::from_iter_values(edges.iter().map(|e| e.source_id.as_str()))),
            Arc::new(StringArray::from_iter_values(edges.iter().map(|e| e.target_id.as_str()))),
            Arc::new(StringArray::from_iter_values(edges.iter().map(|e| e.edge_type.as_str()))),
            opt_u64(edges.iter().map(|e| e.valid_from).collect()),
            opt_u64(edges.iter().map(|e| e.valid_to).collect()),
            Arc::new(UInt64Array::from_iter_values(
                edges.iter().map(|e| e.evidence_event_id),
            )),
        ],
    )?)
}
