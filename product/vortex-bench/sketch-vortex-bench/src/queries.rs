//! Staged RCA queries — which columns each stage must decode.

use crate::layouts::{Layout, WrittenLayout};
use anyhow::{Context, Result};
use arrow::array::{Array, ArrayRef, BooleanArray, RecordBatch, StringArray, StructArray};
use arrow::compute;
use arrow::compute::cast;
use arrow::datatypes::DataType;
use serde::Serialize;
use std::path::Path;
use std::time::Instant;
use vortex::VortexSessionDefault;
use vortex::array::stream::ArrayStreamExt;
use vortex::array::VortexSessionExecute;
use vortex::array::expr::{root, select};
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBuffer;
use vortex::file::OpenOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

#[derive(Debug, Clone, Copy)]
pub struct QuerySpec {
    pub id: &'static str,
    pub stage: u8,
    pub description: &'static str,
    /// Columns projected from a single-file layout (A–D).
    pub columns: &'static [&'static str],
    /// For layout E: which file to open (`spine`, `distribution`, `exemplars`).
    pub split_file: &'static str,
    /// Naive flat-wide Stage-1 projects everything (layout B stress).
    pub naive_all: bool,
}

/// Q1–Q8 from Vortex-unit-check.md, mapped to column projections.
pub const QUERIES: &[QuerySpec] = &[
    QuerySpec {
        id: "Q1",
        stage: 1,
        description: "Find anomalous metrics for entity/time (spine)",
        columns: &[
            "tenant",
            "entity_id",
            "metric_id",
            "window_start_ms",
            "anomaly",
            "current_p95",
            "expected_p95",
        ],
        split_file: "spine",
        naive_all: true,
    },
    QuerySpec {
        id: "Q2",
        stage: 1,
        description: "RED Duration drill-down (spine + red_lane)",
        columns: &[
            "entity_id",
            "metric_id",
            "red_lane",
            "anomaly",
            "current_p95",
            "expected_p95",
            "window_start_ms",
        ],
        split_file: "spine",
        naive_all: true,
    },
    QuerySpec {
        id: "Q3",
        stage: 1,
        description: "Read p95/p99 + baseline",
        columns: &[
            "entity_id",
            "metric_id",
            "current_p50",
            "current_p95",
            "current_p99",
            "expected_p50",
            "expected_p95",
            "expected_p99",
        ],
        split_file: "spine",
        naive_all: false,
    },
    QuerySpec {
        id: "Q4",
        stage: 2,
        description: "Open bucket distribution",
        columns: &[
            "entity_id",
            "metric_id",
            "window_start_ms",
            "bucket_schema_id",
            "bucket_counts",
        ],
        split_file: "distribution",
        naive_all: false,
    },
    QuerySpec {
        id: "Q5",
        stage: 3,
        description: "Retrieve exemplar for suspicious bucket",
        columns: &[
            "entity_id",
            "exemplar_bucket_index",
            "exemplar_value",
            "exemplar_trace_id",
            "exemplar_span_id",
        ],
        split_file: "exemplars",
        naive_all: false,
    },
    QuerySpec {
        id: "Q6",
        stage: 3,
        description: "Read trace_id/span_id only",
        columns: &["exemplar_trace_id", "exemplar_span_id"],
        split_file: "exemplars",
        naive_all: false,
    },
    QuerySpec {
        id: "Q7",
        stage: 1,
        description: "Scan anomalies across many entities",
        columns: &["entity_id", "metric_id", "window_start_ms", "anomaly", "current_p95"],
        split_file: "spine",
        naive_all: true,
    },
    QuerySpec {
        id: "Q8",
        stage: 1,
        description: "Historical baseline comparison",
        columns: &[
            "entity_id",
            "metric_id",
            "window_start_ms",
            "season_key",
            "current_p95",
            "expected_p95",
        ],
        split_file: "spine",
        naive_all: false,
    },
];

#[derive(Debug, Clone, Serialize)]
#[allow(dead_code)]
pub struct QueryResult {
    pub layout: String,
    pub query: String,
    pub stage: u8,
    pub description: String,
    pub file_bytes: u64,
    pub projected_columns: Vec<String>,
    pub decode_ms: f64,
    pub rows_decoded: usize,
    pub rows_matched_filter: usize,
    pub target_entity: String,
}

pub async fn run_query(
    written: &WrittenLayout,
    q: &QuerySpec,
    target_entity: &str,
) -> Result<QueryResult> {
    let path = resolve_path(written, q)?;
    let file_bytes = std::fs::metadata(&path)?.len();
    let columns = resolve_columns(written.layout, q)?;

    let started = Instant::now();
    let batch = read_projected(&path, &columns).await?;
    let decode_ms = started.elapsed().as_secs_f64() * 1000.0;
    let rows_decoded = batch.num_rows();
    let rows_matched_filter = count_entity_anomaly(&batch, target_entity, q.id)?;

    Ok(QueryResult {
        layout: written.layout.id().into(),
        query: q.id.into(),
        stage: q.stage,
        description: q.description.into(),
        file_bytes,
        projected_columns: columns,
        decode_ms,
        rows_decoded,
        rows_matched_filter,
        target_entity: target_entity.into(),
    })
}

fn resolve_path(written: &WrittenLayout, q: &QuerySpec) -> Result<std::path::PathBuf> {
    match written.layout {
        Layout::SplitTables => {
            let name = match q.split_file {
                "spine" => "spine.vortex",
                "distribution" => "distribution.vortex",
                "exemplars" => "exemplars.vortex",
                other => anyhow::bail!("unknown split file {other}"),
            };
            written
                .paths
                .iter()
                .find(|p| p.file_name().and_then(|s| s.to_str()) == Some(name))
                .cloned()
                .with_context(|| format!("missing {name}"))
        }
        _ => written
            .paths
            .first()
            .cloned()
            .context("layout has no vortex path"),
    }
}

fn resolve_columns(layout: Layout, q: &QuerySpec) -> Result<Vec<String>> {
    match layout {
        Layout::FlatWide if q.naive_all && q.stage == 1 => {
            // Stress: Stage-1 pulls the whole wide row (decode locality anti-pattern).
            Ok(vec!["*".into()])
        }
        Layout::Nested => Ok(map_nested_projection(q.columns)),
        Layout::SpineNestedCold => Ok(map_spine_nested_projection(q.columns)),
        Layout::SplitTables => Ok(map_split_projection(q)),
        Layout::FlatWide | Layout::SpineFlatEvidence => {
            Ok(q.columns.iter().map(|s| (*s).to_string()).collect())
        }
    }
}

fn map_nested_projection(cols: &[&str]) -> Vec<String> {
    // Nested layout groups cold fields under structs; Stage-2/3 pull whole groups.
    let mut out = Vec::new();
    for c in cols {
        match *c {
            "bucket_schema_id" | "bucket_counts" => {
                if !out.iter().any(|x| x == "buckets") {
                    out.push("buckets".into());
                }
            }
            "exemplar_bucket_index"
            | "exemplar_value"
            | "exemplar_trace_id"
            | "exemplar_span_id" => {
                if !out.iter().any(|x| x == "exemplars") {
                    out.push("exemplars".into());
                }
            }
            "tdigest" => out.push("tdigest".into()),
            other => out.push(other.into()),
        }
    }
    out
}

fn map_spine_nested_projection(cols: &[&str]) -> Vec<String> {
    let mut out = Vec::new();
    let mut need_cold = false;
    for c in cols {
        match *c {
            "bucket_schema_id"
            | "bucket_counts"
            | "tdigest"
            | "exemplar_bucket_index"
            | "exemplar_value"
            | "exemplar_trace_id"
            | "exemplar_span_id" => need_cold = true,
            other => out.push(other.into()),
        }
    }
    if need_cold {
        out.push("cold_evidence".into());
    }
    out
}

fn map_split_projection(q: &QuerySpec) -> Vec<String> {
    match q.split_file {
        "spine" => q
            .columns
            .iter()
            .filter(|c| {
                !c.starts_with("bucket_")
                    && !c.starts_with("exemplar_")
                    && **c != "tdigest"
            })
            .map(|s| (*s).to_string())
            .chain(std::iter::once("row_id".into()))
            .collect(),
        "distribution" => vec![
            "row_id".into(),
            "tdigest".into(),
            "bucket_schema_id".into(),
            "bucket_counts".into(),
        ],
        "exemplars" => vec![
            "row_id".into(),
            "exemplar_bucket_index".into(),
            "exemplar_value".into(),
            "exemplar_trace_id".into(),
            "exemplar_span_id".into(),
            "exemplar_reason".into(),
            "exemplar_confidence".into(),
        ],
        _ => q.columns.iter().map(|s| (*s).to_string()).collect(),
    }
}

async fn read_projected(path: &Path, columns: &[String]) -> Result<RecordBatch> {
    let bytes = std::fs::read(path)?;
    let session = VortexSession::default().with_tokio();
    let file = session
        .open_options()
        .open_buffer(ByteBuffer::from(bytes))
        .map_err(|e| anyhow::anyhow!("open vortex: {e}"))?;

    let scan = file.scan().map_err(|e| anyhow::anyhow!("scan: {e}"))?;
    let array = if columns.len() == 1 && columns[0] == "*" {
        scan.into_array_stream()
            .map_err(|e| anyhow::anyhow!("stream: {e}"))?
            .read_all()
            .await
            .map_err(|e| anyhow::anyhow!("read_all: {e}"))?
    } else {
        let names: Vec<&str> = columns.iter().map(|s| s.as_str()).collect();
        let projection = select(names, root())
            .optimize_recursive(file.dtype())
            .map_err(|e| anyhow::anyhow!("optimize projection: {e}"))?
            .bind(file.dtype())
            .map_err(|e| anyhow::anyhow!("bind projection: {e}"))?;
        scan.with_projection(projection)
            .into_array_stream()
            .map_err(|e| anyhow::anyhow!("stream: {e}"))?
            .read_all()
            .await
            .map_err(|e| anyhow::anyhow!("read_all: {e}"))?
    };

    let mut ctx = session.create_execution_ctx();
    let arr = session
        .arrow()
        .execute_arrow(array, None, &mut ctx)
        .map_err(|e| anyhow::anyhow!("to arrow: {e}"))?;
    let struct_arr = arr
        .as_any()
        .downcast_ref::<StructArray>()
        .context("projected vortex array is not a struct")?;
    Ok(RecordBatch::from(struct_arr.clone()))
}

fn as_utf8(arr: &dyn Array) -> Result<StringArray> {
    if let Some(a) = arr.as_any().downcast_ref::<StringArray>() {
        return Ok(a.clone());
    }
    let casted: ArrayRef = cast(arr, &DataType::Utf8)
        .with_context(|| format!("cast {:?} to utf8", arr.data_type()))?;
    casted
        .as_any()
        .downcast_ref::<StringArray>()
        .cloned()
        .context("utf8 cast did not yield StringArray")
}

fn count_entity_anomaly(batch: &RecordBatch, entity: &str, query_id: &str) -> Result<usize> {
    // Post-decode filter — measures result cardinality, not Vortex zone prune (yet).
    let Some(ent_idx) = batch.schema().index_of("entity_id").ok() else {
        return Ok(batch.num_rows());
    };
    let ent = as_utf8(batch.column(ent_idx).as_ref())?;
    let mut mask = BooleanArray::from(
        (0..batch.num_rows())
            .map(|i| !ent.is_null(i) && ent.value(i) == entity)
            .collect::<Vec<_>>(),
    );
    if matches!(query_id, "Q1" | "Q2" | "Q7") {
        if let Ok(ai) = batch.schema().index_of("anomaly") {
            if let Some(an) = batch.column(ai).as_any().downcast_ref::<BooleanArray>() {
                mask = compute::and(&mask, an)?;
            }
        }
    }
    Ok(mask.true_count())
}
