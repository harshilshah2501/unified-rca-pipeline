//! Design v3 run manifest writer.

use serde::Serialize;
use std::path::Path;

#[derive(Debug, Serialize)]
pub struct RunManifest {
    pub run_id: String,
    pub timestamp_rfc3339: String,
    pub git_sha: String,
    pub host: String,
    pub dataset_id: String,
    pub estate_shape: String,
    pub edges: usize,
    pub nodes: usize,
    pub mean_out_degree_target: f64,
    pub seed: u64,
    pub edge_sort: String,
    pub adj_builder: String,
    pub layout: String,
    pub load_mode: String,
    pub coldness: String,
    pub workload_id: String,
    pub warmup: usize,
    pub repeats: usize,
    pub phases_ms: PhasesMs,
    pub peak_rss_bytes: Option<u64>,
    pub profile: serde_json::Value,
    pub parts_bytes: PartsBytes,
    pub result_checksum: String,
    pub correctness_ok: bool,
    pub query_events_path: Option<String>,
    pub errors: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct PhasesMs {
    pub decode_nodes: f64,
    pub decode_edges: f64,
    pub build: f64,
    pub first_bfs: f64,
    pub total_cold_to_walk: f64,
}

#[derive(Debug, Serialize)]
pub struct PartsBytes {
    pub nodes: u64,
    pub edges: u64,
}

pub fn host_name() -> String {
    std::process::Command::new("uname")
        .arg("-n")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "unknown".into())
}

pub fn git_sha(override_sha: &Option<String>) -> String {
    if let Some(s) = override_sha {
        return s.clone();
    }
    if let Ok(s) = std::env::var("GIT_SHA") {
        if !s.is_empty() {
            return s;
        }
    }
    "unknown".into()
}

pub fn now_rfc3339() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}

pub fn write_manifest(out_dir: &Path, m: &RunManifest) -> std::io::Result<()> {
    let path = out_dir.join("run_manifest.json");
    std::fs::write(path, serde_json::to_string_pretty(m).unwrap())
}
