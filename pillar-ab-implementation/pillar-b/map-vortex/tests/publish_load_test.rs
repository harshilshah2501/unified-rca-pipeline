//! Cold publish → ``load_map`` round-trip.

use map_vortex::{EdgeType, GraphEdge, GraphNode, load_map, publish_map};

const LAST_SEEN_MS: u64 = 1_787_196_600_000;
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

fn temp_tenant_root() -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "map-vortex-pub-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[tokio::test]
async fn publish_then_load_map_round_trip() {
    let tenant_root = temp_tenant_root();
    let nodes = vec![sample_node()];
    let edges = vec![sample_edge()];

    let published = publish_map(&tenant_root, "default", "lab-1", &nodes, &edges)
        .await
        .unwrap();
    assert!(published.manifest_path.is_file());
    assert!(published.latest_path.is_file());

    let loaded = load_map(&tenant_root).await.unwrap();
    assert_eq!(loaded.manifest.node_count, 1);
    assert_eq!(loaded.manifest.edge_count, 1);
    assert_eq!(loaded.nodes.num_rows(), 1);
    assert_eq!(loaded.edges.num_rows(), 1);
}
