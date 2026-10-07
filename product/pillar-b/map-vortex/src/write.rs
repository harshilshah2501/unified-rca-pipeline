//! Persist ``map_nodes`` / ``map_edges`` as Arrow IPC and Vortex files.

use crate::error::{Error, Result};
use crate::tables::{edges_record_batch, nodes_record_batch};
use crate::types::{GraphEdge, GraphNode};
use arrow::array::RecordBatch;
use arrow::ipc::writer::FileWriter;
use std::fs::File;
use std::path::{Path, PathBuf};
use vortex::VortexSessionDefault;
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBufferMut;
use vortex::file::WriteOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

#[derive(Debug, Clone)]
pub struct MaterializedParts {
    pub nodes_arrow: PathBuf,
    pub edges_arrow: PathBuf,
    pub nodes_vortex: PathBuf,
    pub edges_vortex: PathBuf,
}

/// Write an Arrow IPC file for a RecordBatch.
pub fn write_arrow_ipc(batch: &RecordBatch, path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let file = File::create(path)?;
    let mut writer = FileWriter::try_new(file, &batch.schema())?;
    writer.write(batch)?;
    writer.finish()?;
    Ok(path.to_path_buf())
}

/// Convert a RecordBatch to a Vortex struct array and write a ``.vortex`` file.
pub async fn write_vortex(batch: &RecordBatch, path: impl AsRef<Path>) -> Result<PathBuf> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    let session = VortexSession::default().with_tokio();
    let array = session
        .arrow()
        .from_arrow_record_batch(batch.clone(), batch.schema().as_ref())
        .map_err(|e| Error::Vortex(e.to_string()))?;

    let mut buf = ByteBufferMut::empty();
    session
        .write_options()
        .write(&mut buf, array.to_array_stream())
        .await
        .map_err(|e| Error::Vortex(e.to_string()))?;

    std::fs::write(path, buf.as_ref())?;
    Ok(path.to_path_buf())
}

/// Write ``nodes/part-00000`` + ``edges/part-00000`` as Arrow IPC and Vortex under ``out_dir``.
pub async fn materialize_snapshot_parts(
    nodes: &[GraphNode],
    edges: &[GraphEdge],
    out_dir: impl AsRef<Path>,
) -> Result<MaterializedParts> {
    let out_dir = out_dir.as_ref();
    let nodes_batch = nodes_record_batch(nodes)?;
    let edges_batch = edges_record_batch(edges)?;

    let nodes_arrow = write_arrow_ipc(&nodes_batch, out_dir.join("nodes/part-00000.arrow"))?;
    let edges_arrow = write_arrow_ipc(&edges_batch, out_dir.join("edges/part-00000.arrow"))?;
    let nodes_vortex = write_vortex(&nodes_batch, out_dir.join("nodes/part-00000.vortex")).await?;
    let edges_vortex = write_vortex(&edges_batch, out_dir.join("edges/part-00000.vortex")).await?;

    Ok(MaterializedParts {
        nodes_arrow,
        edges_arrow,
        nodes_vortex,
        edges_vortex,
    })
}
