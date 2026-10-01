//! Logical row types for Motadata map Vortex physical columns (2026-09-30 lock).

use crate::edge_type::EdgeType;
use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};

/// Configuration-item vertex — cold columns (no ``tenant``, no JSON ``metadata`` bag).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GraphNode {
    pub schema_version: String,
    pub entity_id: String,
    #[serde(rename = "type")]
    pub type_: String,
    pub name: String,
    /// Promoted tag ``attr_catalog.v1`` (nullable).
    #[serde(default)]
    pub env: Option<String>,
    #[serde(default)]
    pub region: Option<String>,
    #[serde(default)]
    pub owner: Option<String>,
    #[serde(default)]
    pub namespace: Option<String>,
    /// Unix epoch milliseconds UTC.
    pub last_seen: u64,
    #[serde(default)]
    pub valid_from: Option<u64>,
    #[serde(default)]
    pub valid_to: Option<u64>,
    pub version: u32,
}

/// Typed relationship — cold columns (no ``tenant``, no tag bag).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GraphEdge {
    pub schema_version: String,
    pub edge_id: u64,
    pub source_id: String,
    pub target_id: String,
    pub edge_type: EdgeType,
    #[serde(default)]
    pub valid_from: Option<u64>,
    #[serde(default)]
    pub valid_to: Option<u64>,
    pub evidence_event_id: u64,
}

impl GraphEdge {
    /// Parse ``edge_type`` from a raw JSON string (SCREAMING Motadata name).
    pub fn parse_edge_type(raw: &str) -> Result<EdgeType> {
        raw.parse()
            .map_err(|_| Error::UnknownEdgeType(raw.to_string()))
    }
}
