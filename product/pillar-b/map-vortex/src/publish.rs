//! ``publish_map`` — cold checkpoint: parts → manifest → ``latest.json``.

use crate::error::Result;
use crate::manifest::{
    LatestPointer, MapSnapshotManifest, version_dir, write_latest, write_manifest,
};
use crate::types::{GraphEdge, GraphNode};
use crate::write::{MaterializedParts, materialize_snapshot_parts};
use std::path::{Path, PathBuf};

/// Relative keys stored in ``map_snapshot_manifest.v1`` (under the version prefix).
pub const DEFAULT_NODE_PART: &str = "nodes/part-00000.vortex";
pub const DEFAULT_EDGE_PART: &str = "edges/part-00000.vortex";

#[derive(Debug, Clone)]
pub struct PublishedMap {
    pub tenant_map_root: PathBuf,
    pub version: String,
    pub version_dir: PathBuf,
    pub manifest_path: PathBuf,
    pub latest_path: PathBuf,
    pub parts: MaterializedParts,
    pub manifest: MapSnapshotManifest,
}

/// Immutable cold publish for one tenant generation.
///
/// Order: write ``.vortex`` (and debug ``.arrow``) parts → ``manifest.json`` → ``latest.json``.
pub async fn publish_map(
    tenant_map_root: impl AsRef<Path>,
    tenant: &str,
    version: &str,
    nodes: &[GraphNode],
    edges: &[GraphEdge],
) -> Result<PublishedMap> {
    let tenant_map_root = tenant_map_root.as_ref();
    let version_dir = version_dir(tenant_map_root, version);

    let parts = materialize_snapshot_parts(nodes, edges, &version_dir).await?;

    let manifest = MapSnapshotManifest::new(
        tenant,
        version,
        vec![DEFAULT_NODE_PART.into()],
        vec![DEFAULT_EDGE_PART.into()],
        nodes.len() as u64,
        edges.len() as u64,
    );
    let manifest_path = write_manifest(&manifest, &version_dir)?;
    let latest_path = write_latest(&LatestPointer { version: version.into() }, tenant_map_root)?;

    Ok(PublishedMap {
        tenant_map_root: tenant_map_root.to_path_buf(),
        version: version.into(),
        version_dir,
        manifest_path,
        latest_path,
        parts,
        manifest,
    })
}
