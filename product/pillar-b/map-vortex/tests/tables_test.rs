//! Unit tests for map_nodes / map_edges columnar construction.

use arrow::array::{StringArray, UInt64Array};
use arrow::datatypes::DataType;
use map_vortex::{
    ATTR_CATALOG_VERSION, EDGE_COLUMNS, EDGE_WALK_COLUMNS, EdgeType, GraphEdge, GraphNode,
    NODE_COLUMNS, NODE_WALK_COLUMNS, edges_record_batch, map_edges_schema, map_nodes_schema,
    nodes_record_batch, project_batch,
};

/// 2026-08-20T03:30:00Z
const LAST_SEEN_MS: u64 = 1_787_196_600_000;
/// 2026-08-20T00:00:00Z
const VALID_FROM_MS: u64 = 1_787_184_000_000;

fn sample_node() -> GraphNode {
    GraphNode {
        schema_version: "graph_node.v1".into(),
        entity_id: "checkout-api".into(),
        type_: "service".into(),
        name: "checkout-api".into(),
        env: Some("rca-lab".into()),
        region: None,
        owner: None,
        namespace: None,
        last_seen: LAST_SEEN_MS,
        valid_from: Some(VALID_FROM_MS),
        valid_to: None,
        version: 1,
    }
}

fn sample_edge() -> GraphEdge {
    GraphEdge {
        schema_version: "graph_edge.v1".into(),
        edge_id: 7146828800000001,
        source_id: "checkout-api".into(),
        target_id: "linux-server-app-01".into(),
        edge_type: EdgeType::RunsOn,
        valid_from: Some(VALID_FROM_MS),
        valid_to: None,
        evidence_event_id: 7146828800000002,
    }
}

#[test]
fn schemas_match_locked_column_order() {
    assert_eq!(
        NODE_COLUMNS,
        &[
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
        ]
    );
    assert_eq!(
        EDGE_COLUMNS,
        &[
            "edge_id",
            "source_id",
            "target_id",
            "edge_type",
            "valid_from",
            "valid_to",
            "evidence_event_id",
        ]
    );
    assert_eq!(
        map_nodes_schema()
            .metadata()
            .get("observeops.table")
            .map(String::as_str),
        Some("map_nodes")
    );
    assert_eq!(
        map_nodes_schema()
            .metadata()
            .get("observeops.attr_catalog")
            .map(String::as_str),
        Some(ATTR_CATALOG_VERSION)
    );
    assert_eq!(
        map_edges_schema()
            .metadata()
            .get("observeops.table")
            .map(String::as_str),
        Some("map_edges")
    );
}

#[test]
fn round_trip_from_lab_examples() {
    let n = nodes_record_batch(&[sample_node()]).unwrap();
    let e = edges_record_batch(&[sample_edge()]).unwrap();
    assert_eq!(n.num_rows(), 1);
    assert_eq!(e.num_rows(), 1);
    assert_eq!(n.schema().fields().len(), NODE_COLUMNS.len());
    assert_eq!(e.schema().fields().len(), EDGE_COLUMNS.len());

    let entity = n
        .column_by_name("entity_id")
        .unwrap()
        .as_any()
        .downcast_ref::<StringArray>()
        .unwrap();
    assert_eq!(entity.value(0), "checkout-api");
    let last_seen = n
        .column_by_name("last_seen")
        .unwrap()
        .as_any()
        .downcast_ref::<UInt64Array>()
        .unwrap();
    assert_eq!(last_seen.value(0), LAST_SEEN_MS);
    assert_eq!(
        n.schema().field_with_name("last_seen").unwrap().data_type(),
        &DataType::UInt64
    );
    assert_eq!(
        n.schema().field_with_name("version").unwrap().data_type(),
        &DataType::UInt32
    );
    assert_eq!(
        e.schema().field_with_name("edge_id").unwrap().data_type(),
        &DataType::UInt64
    );
    assert!(n.schema().field_with_name("metadata").is_err());
    assert!(n.schema().field_with_name("schema_version").is_err());
    assert!(n.schema().field_with_name("tenant").is_err());
}

#[test]
fn walk_projection_defers_promoted_tags() {
    let n = project_batch(
        &nodes_record_batch(&[sample_node()]).unwrap(),
        NODE_WALK_COLUMNS,
    )
    .unwrap();
    let e = project_batch(
        &edges_record_batch(&[sample_edge()]).unwrap(),
        EDGE_WALK_COLUMNS,
    )
    .unwrap();
    assert_eq!(n.schema().fields().len(), 2);
    assert!(n.schema().field_with_name("env").is_err());
    assert!(n.schema().field_with_name("last_seen").is_err());
    assert_eq!(e.schema().fields().len(), 3);
    assert!(e.schema().field_with_name("evidence_event_id").is_err());
}

#[test]
fn rejects_unknown_edge_type() {
    let err = "OWNS".parse::<EdgeType>().unwrap_err();
    assert!(err.to_string().contains("edge_type"));
}

#[test]
fn empty_tables_preserve_schema() {
    let n = nodes_record_batch(&[]).unwrap();
    let e = edges_record_batch(&[]).unwrap();
    assert_eq!(n.num_rows(), 0);
    assert_eq!(e.num_rows(), 0);
    assert_eq!(n.num_columns(), NODE_COLUMNS.len());
    assert_eq!(e.num_columns(), EDGE_COLUMNS.len());
}

#[test]
fn edge_type_serde_round_trip() {
    let json = serde_json::to_string(&EdgeType::RunsOn).unwrap();
    assert_eq!(json, "\"RUNS_ON\"");
    let back: EdgeType = serde_json::from_str(&json).unwrap();
    assert_eq!(back, EdgeType::RunsOn);
}

#[tokio::test]
async fn materialize_writes_arrow_and_vortex() {
    use map_vortex::materialize_snapshot_parts;
    let dir = tempfile_dir();
    let parts = materialize_snapshot_parts(&[sample_node()], &[sample_edge()], &dir)
        .await
        .unwrap();
    assert!(parts.nodes_arrow.is_file());
    assert!(parts.edges_arrow.is_file());
    assert!(parts.nodes_vortex.is_file());
    assert!(parts.edges_vortex.is_file());
    assert!(parts.nodes_vortex.metadata().unwrap().len() > 0);
}

fn tempfile_dir() -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "map-vortex-test-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}
