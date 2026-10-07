//! Demo: materialize sample ``map_nodes`` / ``map_edges`` columnar parts.

use clap::Parser;
use map_vortex::{EdgeType, GraphEdge, GraphNode, load_map, materialize_snapshot_parts, publish_map};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "map-vortex-demo",
    about = "Demo cold map publish (parts only or full tenant tree with manifest + latest)"
)]
struct Args {
    /// Output directory (snapshot version folder) — parts only, no manifest
    #[arg(long, conflicts_with = "tenant_root")]
    demo: Option<PathBuf>,

    /// ``map/<tenant>/`` root — writes snapshots/<version>/ + latest.json
    #[arg(long, requires = "version")]
    tenant_root: Option<PathBuf>,

    #[arg(long, default_value = "default")]
    tenant: String,

    #[arg(long)]
    version: Option<String>,

    /// After publish, load via latest.json and print row counts
    #[arg(long, default_value_t = false)]
    verify_load: bool,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    let nodes = vec![
        GraphNode {
            schema_version: "graph_node.v1".into(),
            entity_id: "checkout-api".into(),
            type_: "service".into(),
            name: "checkout-api".into(),
            env: Some("rca-lab".into()),
            region: None,
            owner: None,
            namespace: None,
            last_seen: 1_787_196_600_000, // 2026-08-20T03:30:00Z
            valid_from: Some(1_787_184_000_000), // 2026-08-20T00:00:00Z
            valid_to: None,
            version: 1,
        },
        GraphNode {
            schema_version: "graph_node.v1".into(),
            entity_id: "linux-server-app-01".into(),
            type_: "host".into(),
            name: "linux-server-app-01".into(),
            env: Some("rca-lab".into()),
            region: None,
            owner: None,
            namespace: None,
            last_seen: 1_787_196_600_000,
            valid_from: Some(1_787_184_000_000),
            valid_to: None,
            version: 1,
        },
    ];

    let edges = vec![GraphEdge {
        schema_version: "graph_edge.v1".into(),
        edge_id: 7146828800000001,
        source_id: "checkout-api".into(),
        target_id: "linux-server-app-01".into(),
        edge_type: EdgeType::RunsOn,
        valid_from: Some(1_787_184_000_000),
        valid_to: None,
        evidence_event_id: 7146828800000002,
    }];

    if let Some(tenant_root) = args.tenant_root {
        let version = args
            .version
            .expect("--version required with --tenant-root");
        let published = publish_map(&tenant_root, &args.tenant, &version, &nodes, &edges).await?;
        println!("manifest: {}", published.manifest_path.display());
        println!("latest:   {}", published.latest_path.display());
        println!("nodes_vortex: {}", published.parts.nodes_vortex.display());
        println!("edges_vortex: {}", published.parts.edges_vortex.display());
        if args.verify_load {
            let loaded = load_map(&tenant_root).await?;
            println!(
                "load_map: nodes={} edges={} version={}",
                loaded.nodes.num_rows(),
                loaded.edges.num_rows(),
                loaded.manifest.version
            );
        }
    } else {
        let demo = args.demo.expect("pass --demo <dir> or --tenant-root + --version");
        let parts = materialize_snapshot_parts(&nodes, &edges, &demo).await?;
        println!("nodes_arrow:  {}", parts.nodes_arrow.display());
        println!("edges_arrow:  {}", parts.edges_arrow.display());
        println!("nodes_vortex: {}", parts.nodes_vortex.display());
        println!("edges_vortex: {}", parts.edges_vortex.display());
        println!("map_nodes rows={} cols=8", nodes.len());
        println!("map_edges rows={} cols=7", edges.len());
    }
    Ok(())
}
