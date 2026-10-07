//! Cold map publish/load CLI — GraphWriter ↔ ``vortex_s3.v1`` bridge.
//!
//! ```text
//! map_vortex_cold publish --tenant-root DIR --tenant T --version V --snapshot FILE.json
//! map_vortex_cold load    --tenant-root DIR [--out FILE.json]
//! ```

use anyhow::{Context, bail};
use clap::{Parser, Subcommand};
use map_vortex::{
    GraphSnapshotJson, load_map, loaded_map_to_snapshot, publish_map,
};
use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "map_vortex_cold",
    about = "Cold publish/load for Motadata map/ vortex_s3.v1 (GraphWriter cohesion)"
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand, Debug)]
enum Cmd {
    /// Checkpoint a graph_snapshot.v1 JSON into parts + manifest + latest
    Publish {
        #[arg(long)]
        tenant_root: PathBuf,
        #[arg(long)]
        snapshot: PathBuf,
        /// Override tenant from snapshot envelope when set
        #[arg(long)]
        tenant: Option<String>,
        /// Override version from snapshot envelope when set
        #[arg(long)]
        version: Option<String>,
    },
    /// Load latest cold generation and emit graph_snapshot.v1 JSON (stdout or --out)
    Load {
        #[arg(long)]
        tenant_root: PathBuf,
        #[arg(long)]
        out: Option<PathBuf>,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Publish {
            tenant_root,
            snapshot,
            tenant,
            version,
        } => {
            let raw = fs::read_to_string(&snapshot)
                .with_context(|| format!("read snapshot {}", snapshot.display()))?;
            let snap: GraphSnapshotJson =
                serde_json::from_str(&raw).context("parse graph_snapshot.v1")?;
            if snap.schema_version != "graph_snapshot.v1" {
                bail!("unsupported schema_version {}", snap.schema_version);
            }
            let tenant = tenant.unwrap_or(snap.tenant);
            let version = version.unwrap_or(snap.version);
            let published =
                publish_map(&tenant_root, &tenant, &version, &snap.nodes, &snap.edges).await?;
            println!("ok profile=vortex_s3.v1");
            println!("tenant_root={}", published.tenant_map_root.display());
            println!("version={}", published.version);
            println!("manifest={}", published.manifest_path.display());
            println!("latest={}", published.latest_path.display());
            println!("nodes_vortex={}", published.parts.nodes_vortex.display());
            println!("edges_vortex={}", published.parts.edges_vortex.display());
            println!(
                "counts nodes={} edges={}",
                published.manifest.node_count, published.manifest.edge_count
            );
        }
        Cmd::Load { tenant_root, out } => {
            let loaded = load_map(&tenant_root).await?;
            let snap = loaded_map_to_snapshot(&loaded)?;
            let body = serde_json::to_string_pretty(&snap)?;
            if let Some(path) = out {
                fs::write(&path, &body)
                    .with_context(|| format!("write {}", path.display()))?;
                println!("ok wrote {}", path.display());
            } else {
                let mut stdout = io::stdout().lock();
                stdout.write_all(body.as_bytes())?;
                stdout.write_all(b"\n")?;
            }
        }
    }
    Ok(())
}
