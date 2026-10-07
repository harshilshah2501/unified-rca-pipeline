//! Admit gates + HotMap apply_topo_line (Phase B).

use map_vortex::{
    AdmitOutcome, HotMap, RejectCode, TopoLine, check_edge_triplet, load_map,
};

fn line(
    src: &str,
    dst: &str,
    relation: &str,
    src_ty: Option<&str>,
    dst_ty: Option<&str>,
    resolved: bool,
) -> TopoLine {
    TopoLine {
        src_ci_id: src.into(),
        dst_ci_id: dst.into(),
        relation: relation.into(),
        identity_resolved: resolved,
        src_ci_type: src_ty.map(str::to_string),
        dst_ci_type: dst_ty.map(str::to_string),
        subject_ci_type: src_ty.map(str::to_string),
        ts: Some(1_787_196_600_000), // 2026-08-20T03:30:00Z
    }
}

#[test]
fn gate1_incomplete_is_noop() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line("a", "", "depends_on", Some("Service"), Some("Database"), true));
    assert_eq!(out, AdmitOutcome::Noop);
    assert!(hot.edges.is_empty());
}

#[test]
fn gate2_unresolved_drops_identity() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "checkout-api",
        "db-1",
        "depends_on",
        Some("Service"),
        Some("Database"),
        false,
    ));
    assert_eq!(out, AdmitOutcome::Drop(RejectCode::Identity));
    assert!(hot.edges.is_empty());
}

#[test]
fn gate3_alert_never_ci() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "checkout-api",
        "alert-1",
        "depends_on",
        Some("Service"),
        Some("Alert"),
        true,
    ));
    assert_eq!(out, AdmitOutcome::Drop(RejectCode::NeverCiVertex));
}

#[test]
fn gate4_unknown_relation() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "checkout-api",
        "db-1",
        "owns",
        Some("Service"),
        Some("Database"),
        true,
    ));
    assert_eq!(out, AdmitOutcome::Drop(RejectCode::UnknownRelation));
}

#[test]
fn gate4_illegal_triplet_host_runs_on_service() {
    assert!(check_edge_triplet("runs_on", Some("host"), Some("service")).is_err());
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "linux-server-app-01",
        "checkout-api",
        "runs_on",
        Some("Host"),
        Some("Service"),
        true,
    ));
    assert_eq!(out, AdmitOutcome::Drop(RejectCode::IllegalEdgeTriplet));
    assert!(hot.edges.is_empty());
}

#[test]
fn gate4_missing_dst_type_drops() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "checkout-api",
        "mystery",
        "depends_on",
        Some("Service"),
        None,
        true,
    ));
    assert_eq!(out, AdmitOutcome::Drop(RejectCode::MissingEndpointType));
}

#[test]
fn write_service_depends_on_db() {
    let mut hot = HotMap::new("default");
    let out = hot.apply_topo_line(&line(
        "checkout-api",
        "db-checkout-primary",
        "depends_on",
        Some("Service"),
        Some("Database"),
        true,
    ));
    assert!(matches!(out, AdmitOutcome::Write { .. }));
    assert_eq!(hot.nodes.len(), 2);
    assert_eq!(hot.edges.len(), 1);
    let edge = hot.edges.values().next().unwrap();
    assert_eq!(edge.edge_type.as_str(), "DEPENDS_ON");
    assert_eq!(hot.nodes["checkout-api"].type_, "service");
    assert_eq!(hot.nodes["db-checkout-primary"].type_, "db");
}

#[test]
fn upsert_same_triple_reuses_edge_id() {
    let mut hot = HotMap::new("default");
    hot.apply_topo_line(&line(
        "checkout-api",
        "db-1",
        "depends_on",
        Some("Service"),
        Some("Database"),
        true,
    ));
    let first_id = hot.edges.values().next().unwrap().edge_id;
    hot.apply_topo_line(&line(
        "checkout-api",
        "db-1",
        "depends_on",
        Some("Service"),
        Some("Database"),
        true,
    ));
    assert_eq!(hot.edges.len(), 1);
    assert_eq!(hot.edges.values().next().unwrap().edge_id, first_id);
}

#[test]
fn multi_edge_different_types_allowed() {
    let mut hot = HotMap::new("default");
    hot.apply_topo_line(&line(
        "checkout-api",
        "inventory-api",
        "depends_on",
        Some("Service"),
        Some("Service"),
        true,
    ));
    hot.apply_topo_line(&line(
        "checkout-api",
        "inventory-api",
        "communicates_with",
        Some("Service"),
        Some("Service"),
        true,
    ));
    assert_eq!(hot.edges.len(), 2);
}

#[tokio::test]
async fn hot_write_then_publish_load() {
    let mut hot = HotMap::new("default");
    hot.apply_topo_line(&line(
        "checkout-api",
        "linux-server-app-01",
        "hosted_on",
        Some("Service"),
        Some("Host"),
        true,
    ));
    let dir = std::env::temp_dir().join(format!(
        "map-vortex-hot-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    hot.publish(&dir, "v1").await.unwrap();
    let loaded = load_map(&dir).await.unwrap();
    assert_eq!(loaded.nodes.num_rows(), 2);
    assert_eq!(loaded.edges.num_rows(), 1);
}
