//! Publish → Vortex load → ``graph_snapshot.v1`` JSON round-trip (Utf8View cast path).

use map_vortex::{
    EdgeType, GraphEdge, GraphNode, load_map, loaded_map_to_snapshot, publish_map,
};

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
        "map-vortex-snap-{}-{}",
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
async fn publish_load_to_snapshot_json_round_trip() {
    let tenant_root = temp_tenant_root();
    let nodes = vec![sample_node()];
    let edges = vec![sample_edge()];

    publish_map(&tenant_root, "default", "lab-1", &nodes, &edges)
        .await
        .unwrap();
    let loaded = load_map(&tenant_root).await.unwrap();
    let snap = loaded_map_to_snapshot(&loaded).unwrap();

    assert_eq!(snap.schema_version, "graph_snapshot.v1");
    assert_eq!(snap.tenant, "default");
    assert_eq!(snap.version, "lab-1");
    assert_eq!(snap.nodes.len(), 1);
    assert_eq!(snap.edges.len(), 1);
    assert_eq!(snap.nodes[0].entity_id, "checkout-api");
    assert_eq!(snap.nodes[0].env.as_deref(), Some("rca-lab"));
    assert!(snap.nodes[0].region.is_none());
    assert_eq!(snap.nodes[0].last_seen, LAST_SEEN_MS);
    assert_eq!(snap.edges[0].source_id, "checkout-api");
    assert_eq!(snap.edges[0].target_id, "linux-server-app-01");
    assert_eq!(snap.edges[0].edge_type, EdgeType::RunsOn);
}
