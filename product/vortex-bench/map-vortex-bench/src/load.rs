//! Projected Vortex cold load for map parts.

use anyhow::{Context, Result};
use arrow::array::{Array, ArrayRef, RecordBatch, StringArray, StructArray};
use arrow::compute::cast;
use arrow::datatypes::DataType;
use clap::ValueEnum;
use serde::Serialize;
use std::path::Path;
use std::time::Instant;
use vortex::VortexSessionDefault;
use vortex::array::stream::ArrayStreamExt;
use vortex::array::VortexSessionExecute;
use vortex::array::expr::{root, select};
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBuffer;
use vortex::file::OpenOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum LoadMode {
    /// All columns on nodes and edges (naive full materialize).
    Full,
    /// Walk spine only: nodes `(entity_id,type)` · edges `(source_id,target_id,edge_type)`.
    Spine,
    /// Full nodes + edge spine (tags available; evidence deferred).
    NodesFullEdgesSpine,
}

impl LoadMode {
    pub fn id(self) -> &'static str {
        match self {
            Self::Full => "full",
            Self::Spine => "spine",
            Self::NodesFullEdgesSpine => "nodes_full_edges_spine",
        }
    }

    pub fn node_columns(self) -> Option<&'static [&'static str]> {
        match self {
            Self::Full | Self::NodesFullEdgesSpine => None, // all
            Self::Spine => Some(&["entity_id", "type"]),
        }
    }

    pub fn edge_columns(self) -> Option<&'static [&'static str]> {
        match self {
            Self::Full => None,
            Self::Spine | Self::NodesFullEdgesSpine => {
                Some(&["source_id", "target_id", "edge_type"])
            }
        }
    }
}

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
pub struct LoadTiming {
    pub mode: String,
    pub nodes_decode_ms: f64,
    pub edges_decode_ms: f64,
    pub nodes_rows: usize,
    pub edges_rows: usize,
    pub nodes_cols: Vec<String>,
    pub edges_cols: Vec<String>,
}

pub async fn load_parts(
    nodes_path: &Path,
    edges_path: &Path,
    mode: LoadMode,
) -> Result<(RecordBatch, RecordBatch, LoadTiming)> {
    let (nodes, nodes_ms, nodes_cols) = read_projected(nodes_path, mode.node_columns()).await?;
    let (edges, edges_ms, edges_cols) = read_projected(edges_path, mode.edge_columns()).await?;
    let timing = LoadTiming {
        mode: mode.id().into(),
        nodes_decode_ms: nodes_ms,
        edges_decode_ms: edges_ms,
        nodes_rows: nodes.num_rows(),
        edges_rows: edges.num_rows(),
        nodes_cols,
        edges_cols,
    };
    Ok((nodes, edges, timing))
}

async fn read_projected(
    path: &Path,
    columns: Option<&[&str]>,
) -> Result<(RecordBatch, f64, Vec<String>)> {
    let bytes = std::fs::read(path)?;
    let session = VortexSession::default().with_tokio();
    let file = session
        .open_options()
        .open_buffer(ByteBuffer::from(bytes))
        .map_err(|e| anyhow::anyhow!("open: {e}"))?;

    let started = Instant::now();
    let scan = file.scan().map_err(|e| anyhow::anyhow!("scan: {e}"))?;
    let array = if let Some(cols) = columns {
        let projection = select(cols.to_vec(), root())
            .optimize_recursive(file.dtype())
            .map_err(|e| anyhow::anyhow!("optimize: {e}"))?
            .bind(file.dtype())
            .map_err(|e| anyhow::anyhow!("bind: {e}"))?;
        scan.with_projection(projection)
            .into_array_stream()
            .map_err(|e| anyhow::anyhow!("stream: {e}"))?
            .read_all()
            .await
            .map_err(|e| anyhow::anyhow!("read_all: {e}"))?
    } else {
        scan.into_array_stream()
            .map_err(|e| anyhow::anyhow!("stream: {e}"))?
            .read_all()
            .await
            .map_err(|e| anyhow::anyhow!("read_all: {e}"))?
    };
    let mut ctx = session.create_execution_ctx();
    let arr = session
        .arrow()
        .execute_arrow(array, None, &mut ctx)
        .map_err(|e| anyhow::anyhow!("to arrow: {e}"))?;
    let ms = started.elapsed().as_secs_f64() * 1000.0;
    let struct_arr = arr
        .as_any()
        .downcast_ref::<StructArray>()
        .context("not a struct batch")?;
    let batch = RecordBatch::from(struct_arr.clone());
    let cols = batch
        .schema()
        .fields()
        .iter()
        .map(|f| f.name().clone())
        .collect();
    Ok((batch, ms, cols))
}

pub fn utf8_col(batch: &RecordBatch, name: &str) -> Result<StringArray> {
    let idx = batch
        .schema()
        .index_of(name)
        .with_context(|| format!("missing {name}"))?;
    let arr = batch.column(idx).as_ref();
    if let Some(a) = arr.as_any().downcast_ref::<StringArray>() {
        return Ok(a.clone());
    }
    let casted: ArrayRef = cast(arr, &DataType::Utf8)?;
    casted
        .as_any()
        .downcast_ref::<StringArray>()
        .cloned()
        .context("utf8 cast failed")
}
