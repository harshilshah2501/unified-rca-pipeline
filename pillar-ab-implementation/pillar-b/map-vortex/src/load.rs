//! ``load_map`` — manifest-driven cold read into Arrow ``RecordBatch``es.

use crate::error::{Error, Result};
use crate::manifest::{MapSnapshotManifest, read_latest, read_manifest, version_dir};
use arrow::array::{Array, RecordBatch, StructArray};
use std::path::{Path, PathBuf};
use vortex::VortexSessionDefault;
use vortex::array::stream::ArrayStreamExt;
use vortex::array::VortexSessionExecute;
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBuffer;
use vortex::file::OpenOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

/// Rebuilt cold tables for one snapshot generation.
#[derive(Debug, Clone)]
pub struct LoadedMap {
    pub manifest: MapSnapshotManifest,
    pub version_dir: PathBuf,
    pub nodes: RecordBatch,
    pub edges: RecordBatch,
}

/// Read one ``.vortex`` part into an Arrow ``RecordBatch`` (full column materialization).
pub async fn read_vortex_part(path: impl AsRef<Path>) -> Result<RecordBatch> {
    let path = path.as_ref();
    let bytes = std::fs::read(path)?;
    let session = VortexSession::default().with_tokio();
    let file = session
        .open_options()
        .open_buffer(ByteBuffer::from(bytes))
        .map_err(|e| Error::Vortex(e.to_string()))?;

    let array = file
        .scan()
        .map_err(|e| Error::Vortex(e.to_string()))?
        .into_array_stream()
        .map_err(|e| Error::Vortex(e.to_string()))?
        .read_all()
        .await
        .map_err(|e| Error::Vortex(e.to_string()))?;

    let mut ctx = session.create_execution_ctx();
    let arr = session
        .arrow()
        .execute_arrow(array, None, &mut ctx)
        .map_err(|e| Error::Vortex(e.to_string()))?;

    struct_array_to_record_batch(arr.as_ref())
}

fn struct_array_to_record_batch(arr: &dyn Array) -> Result<RecordBatch> {
    let struct_arr = arr
        .as_any()
        .downcast_ref::<StructArray>()
        .ok_or_else(|| Error::Vortex("vortex part is not a struct column batch".into()))?;
    Ok(RecordBatch::from(struct_arr.clone()))
}

async fn read_single_part(version_dir: &Path, relative: &str) -> Result<RecordBatch> {
    read_vortex_part(version_dir.join(relative)).await
}

/// Load a snapshot when the version directory is known. Fails if ``manifest.json`` is missing.
pub async fn load_map_version(version_dir: &Path) -> Result<LoadedMap> {
    let manifest = read_manifest(version_dir)?;
    if manifest.node_parts.is_empty() || manifest.edge_parts.is_empty() {
        return Err(Error::IncompleteSnapshot(
            "manifest lists no node or edge parts".into(),
        ));
    }
    let nodes = read_single_part(version_dir, &manifest.node_parts[0]).await?;
    let edges = read_single_part(version_dir, &manifest.edge_parts[0]).await?;
    Ok(LoadedMap {
        manifest,
        version_dir: version_dir.to_path_buf(),
        nodes,
        edges,
    })
}

/// Resolve ``latest.json`` under ``tenant_map_root`` then load that generation.
pub async fn load_map(tenant_map_root: &Path) -> Result<LoadedMap> {
    let latest = read_latest(tenant_map_root)?;
    let dir = version_dir(tenant_map_root, &latest.version);
    load_map_version(&dir).await
}
