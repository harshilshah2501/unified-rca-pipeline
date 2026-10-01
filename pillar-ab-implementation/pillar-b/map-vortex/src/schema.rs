//! Arrow schemas for ``map_nodes`` and ``map_edges`` (vortex_s3 physical lock 2026-09-30).

use arrow::datatypes::{DataType, Field, Schema};
use std::sync::Arc;

pub const NODE_COLUMNS: &[&str] = &[
    "entity_id",
    "type",
    "name",
    "env",
    "region",
    "owner",
    "namespace",
    "last_seen",
    "valid_from",
    "valid_to",
    "version",
];

pub const EDGE_COLUMNS: &[&str] = &[
    "edge_id",
    "source_id",
    "target_id",
    "edge_type",
    "valid_from",
    "valid_to",
    "evidence_event_id",
];

/// Walk projection — defer promoted tags and clocks.
pub const NODE_WALK_COLUMNS: &[&str] = &["entity_id", "type"];

/// Walk projection — defer ``evidence_event_id``.
pub const EDGE_WALK_COLUMNS: &[&str] = &["source_id", "target_id", "edge_type"];

/// Promoted tag catalog version stamped on schema metadata.
pub const ATTR_CATALOG_VERSION: &str = "attr_catalog.v1";

fn node_metadata() -> std::collections::HashMap<String, String> {
    [
        ("observeops.table".into(), "map_nodes".into()),
        ("observeops.schema_version".into(), "graph_node.v1".into()),
        ("observeops.attr_catalog".into(), ATTR_CATALOG_VERSION.into()),
    ]
    .into_iter()
    .collect()
}

fn edge_metadata() -> std::collections::HashMap<String, String> {
    [
        ("observeops.table".into(), "map_edges".into()),
        ("observeops.schema_version".into(), "graph_edge.v1".into()),
    ]
    .into_iter()
    .collect()
}

/// Arrow schema for ``map_nodes`` (dictionary on ``type`` + promoted tags).
pub fn map_nodes_schema() -> Schema {
    let fields = vec![
        Field::new("entity_id", DataType::Utf8, false),
        Field::new(
            "type",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            false,
        ),
        Field::new("name", DataType::Utf8, false),
        Field::new(
            "env",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            true,
        ),
        Field::new(
            "region",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            true,
        ),
        Field::new(
            "owner",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            true,
        ),
        Field::new(
            "namespace",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            true,
        ),
        Field::new("last_seen", DataType::UInt64, false),
        Field::new("valid_from", DataType::UInt64, true),
        Field::new("valid_to", DataType::UInt64, true),
        Field::new("version", DataType::UInt32, false),
    ];
    Schema::new_with_metadata(fields, node_metadata())
}

/// Arrow schema for ``map_edges`` (dictionary on ``edge_type``).
pub fn map_edges_schema() -> Schema {
    let fields = vec![
        Field::new("edge_id", DataType::UInt64, false),
        Field::new("source_id", DataType::Utf8, false),
        Field::new("target_id", DataType::Utf8, false),
        Field::new(
            "edge_type",
            DataType::Dictionary(Box::new(DataType::Int32), Box::new(DataType::Utf8)),
            false,
        ),
        Field::new("valid_from", DataType::UInt64, true),
        Field::new("valid_to", DataType::UInt64, true),
        Field::new("evidence_event_id", DataType::UInt64, false),
    ];
    Schema::new_with_metadata(fields, edge_metadata())
}

/// Plain Utf8 schemas (no dictionary) — Vortex write path today.
pub fn map_nodes_schema_plain() -> Schema {
    let fields = vec![
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
    ];
    Schema::new_with_metadata(fields, node_metadata())
}

pub fn map_edges_schema_plain() -> Schema {
    let fields = vec![
        Field::new("edge_id", DataType::UInt64, false),
        Field::new("source_id", DataType::Utf8, false),
        Field::new("target_id", DataType::Utf8, false),
        Field::new("edge_type", DataType::Utf8, false),
        Field::new("valid_from", DataType::UInt64, true),
        Field::new("valid_to", DataType::UInt64, true),
        Field::new("evidence_event_id", DataType::UInt64, false),
    ];
    Schema::new_with_metadata(fields, edge_metadata())
}

pub fn map_nodes_schema_arc() -> Arc<Schema> {
    Arc::new(map_nodes_schema())
}

pub fn map_edges_schema_arc() -> Arc<Schema> {
    Arc::new(map_edges_schema())
}
