//! Motadata ``map/`` columnar tables for ``vortex_s3.v1``.
//!
//! Two tables only: [`map_nodes`](schema::map_nodes_schema) and
//! [`map_edges`](schema::map_edges_schema). Logical SoT remains
//! ``graph_node.v1`` / ``graph_edge.v1``
//! ([`MAP_VORTEX_COLUMNAR_SCHEMA.md`](../../../contracts/MAP_VORTEX_COLUMNAR_SCHEMA.md)).

pub mod admit;
pub mod ci_qualify;
pub mod edge_type;
pub mod error;
pub mod hot;
pub mod load;
pub mod manifest;
pub mod publish;
pub mod schema;
pub mod tables;
pub mod types;
pub mod write;

pub use admit::{
    AdmitOutcome, RejectCode, TopologyClaim, admit_topology_claim, check_edge_triplet,
    classify_relation, normalize_relation, to_edge_type,
};
pub use ci_qualify::{may_emit_vertex, storage_to_ingest, storage_type_or_none, to_storage_type};
pub use edge_type::EdgeType;
pub use error::{Error, Result};
pub use hot::{HotMap, TopoLine, logical_edge_key, next_snowflake};
pub use load::{LoadedMap, load_map, load_map_version, read_vortex_part};
pub use manifest::{
    LatestPointer, MapSnapshotManifest, read_latest, read_manifest, version_dir, write_latest,
    write_manifest,
};
pub use publish::{PublishedMap, publish_map};
pub use schema::{
    ATTR_CATALOG_VERSION, EDGE_COLUMNS, EDGE_WALK_COLUMNS, NODE_COLUMNS, NODE_WALK_COLUMNS,
    map_edges_schema, map_nodes_schema,
};
pub use tables::{edges_record_batch, nodes_record_batch, project_batch};
pub use types::{GraphEdge, GraphNode};
pub use write::{MaterializedParts, materialize_snapshot_parts, write_arrow_ipc, write_vortex};
