//! ObserveOps cold snapshot footer — ``map_snapshot_manifest.v1`` + ``latest.json``.

use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const MANIFEST_SCHEMA: &str = "map_snapshot_manifest.v1";

/// Pointer at ``map/<tenant>/latest.json``.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LatestPointer {
    pub version: String,
}

/// Lists immutable part keys for one snapshot generation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MapSnapshotManifest {
    pub schema_version: String,
    pub tenant: String,
    pub version: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
    pub node_parts: Vec<String>,
    pub edge_parts: Vec<String>,
    pub node_count: u64,
    pub edge_count: u64,
}

impl MapSnapshotManifest {
    pub fn new(
        tenant: impl Into<String>,
        version: impl Into<String>,
        node_parts: Vec<String>,
        edge_parts: Vec<String>,
        node_count: u64,
        edge_count: u64,
    ) -> Self {
        Self {
            schema_version: MANIFEST_SCHEMA.into(),
            tenant: tenant.into(),
            version: version.into(),
            created_at: None,
            node_parts,
            edge_parts,
            node_count,
            edge_count,
        }
    }

    pub fn with_created_at(mut self, created_at: impl Into<String>) -> Self {
        self.created_at = Some(created_at.into());
        self
    }
}

pub fn version_dir(tenant_map_root: &Path, version: &str) -> PathBuf {
    tenant_map_root.join("snapshots").join(version)
}

pub fn write_manifest(manifest: &MapSnapshotManifest, version_dir: &Path) -> Result<PathBuf> {
    std::fs::create_dir_all(version_dir)?;
    let path = version_dir.join("manifest.json");
    let json = serde_json::to_vec_pretty(manifest)?;
    std::fs::write(&path, json)?;
    Ok(path)
}

pub fn read_manifest(version_dir: &Path) -> Result<MapSnapshotManifest> {
    let path = version_dir.join("manifest.json");
    let bytes = std::fs::read(&path).map_err(|e| {
        if e.kind() == std::io::ErrorKind::NotFound {
            Error::IncompleteSnapshot(format!("missing {}", path.display()))
        } else {
            Error::Io(e)
        }
    })?;
    let manifest: MapSnapshotManifest = serde_json::from_slice(&bytes)?;
    if manifest.schema_version != MANIFEST_SCHEMA {
        return Err(Error::Manifest(format!(
            "expected {}, got {}",
            MANIFEST_SCHEMA, manifest.schema_version
        )));
    }
    Ok(manifest)
}

pub fn write_latest(pointer: &LatestPointer, tenant_map_root: &Path) -> Result<PathBuf> {
    std::fs::create_dir_all(tenant_map_root)?;
    let path = tenant_map_root.join("latest.json");
    let json = serde_json::to_vec_pretty(pointer)?;
    std::fs::write(&path, json)?;
    Ok(path)
}

pub fn read_latest(tenant_map_root: &Path) -> Result<LatestPointer> {
    let path = tenant_map_root.join("latest.json");
    let bytes = std::fs::read(&path)?;
    Ok(serde_json::from_slice(&bytes)?)
}
