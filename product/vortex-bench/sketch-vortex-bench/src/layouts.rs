//! Competing physical Arrow/Vortex shapes for the same logical sketch rows.

use crate::synth::{BUCKET_COUNT, LATENCY_BOUNDS, SketchRow};
use anyhow::{Context, Result};
use arrow::array::{
    ArrayRef, BinaryArray, BooleanArray, Float32Array, Float64Array, ListArray, ListBuilder,
    StringArray, StringBuilder, StructArray, UInt8Array, UInt32Array, UInt64Array,
};
use arrow::buffer::OffsetBuffer;
use arrow::datatypes::{DataType, Field, Fields, Schema};
use arrow::record_batch::RecordBatch;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use vortex::VortexSessionDefault;
use vortex::arrow::ArrowSessionExt;
use vortex::buffer::ByteBufferMut;
use vortex::file::WriteOptionsSessionExt;
use vortex::io::session::RuntimeSessionExt;
use vortex::session::VortexSession;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, clap::ValueEnum)]
pub enum Layout {
    /// Nested structs for digest / buckets / exemplars (logical sketch.v2 shape).
    Nested,
    /// Fully flat wide table; Stage-1 queries may naively project all columns.
    FlatWide,
    /// Flat spine + nested cold evidence struct.
    SpineNestedCold,
    /// Flat spine + flat distribution/exemplar columns (disciplined projections).
    SpineFlatEvidence,
    /// Split Dest objects: spine / distribution / exemplars (join by row_id).
    SplitTables,
}

impl Layout {
    pub fn id(self) -> &'static str {
        match self {
            Self::Nested => "A_nested",
            Self::FlatWide => "B_flat_wide",
            Self::SpineNestedCold => "C_spine_nested_cold",
            Self::SpineFlatEvidence => "D_spine_flat_evidence",
            Self::SplitTables => "E_split_tables",
        }
    }
}

#[derive(Debug, Clone)]
pub struct WrittenLayout {
    pub layout: Layout,
    pub paths: Vec<PathBuf>,
    pub total_bytes: u64,
    pub write_ms: u128,
}

pub async fn write_layout(rows: &[SketchRow], layout: Layout, out_dir: &Path) -> Result<WrittenLayout> {
    let dir = out_dir.join(layout.id());
    std::fs::create_dir_all(&dir)?;
    let started = std::time::Instant::now();
    let paths = match layout {
        Layout::Nested => {
            let batch = batch_nested(rows)?;
            vec![write_vortex(&batch, dir.join("sketches.vortex")).await?]
        }
        Layout::FlatWide => {
            let batch = batch_flat(rows, /*include_bounds*/ true)?;
            vec![write_vortex(&batch, dir.join("sketches.vortex")).await?]
        }
        Layout::SpineNestedCold => {
            let batch = batch_spine_nested_cold(rows)?;
            vec![write_vortex(&batch, dir.join("sketches.vortex")).await?]
        }
        Layout::SpineFlatEvidence => {
            let batch = batch_flat(rows, /*include_bounds*/ false)?;
            vec![write_vortex(&batch, dir.join("sketches.vortex")).await?]
        }
        Layout::SplitTables => {
            let (spine, dist, ex) = batches_split(rows)?;
            vec![
                write_vortex(&spine, dir.join("spine.vortex")).await?,
                write_vortex(&dist, dir.join("distribution.vortex")).await?,
                write_vortex(&ex, dir.join("exemplars.vortex")).await?,
            ]
        }
    };
    let write_ms = started.elapsed().as_millis();
    let total_bytes = paths
        .iter()
        .map(|p| std::fs::metadata(p).map(|m| m.len()).unwrap_or(0))
        .sum();
    Ok(WrittenLayout {
        layout,
        paths,
        total_bytes,
        write_ms,
    })
}

async fn write_vortex(batch: &RecordBatch, path: PathBuf) -> Result<PathBuf> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let session = VortexSession::default().with_tokio();
    let array = session
        .arrow()
        .from_arrow_record_batch(batch.clone(), batch.schema().as_ref())
        .map_err(|e| anyhow::anyhow!("arrow→vortex: {e}"))?;
    let mut buf = ByteBufferMut::empty();
    session
        .write_options()
        .write(&mut buf, array.to_array_stream())
        .await
        .map_err(|e| anyhow::anyhow!("vortex write: {e}"))?;
    std::fs::write(&path, buf.as_ref()).with_context(|| format!("write {}", path.display()))?;
    Ok(path)
}

fn spine_cols(rows: &[SketchRow]) -> Result<(Vec<(&'static str, ArrayRef)>, usize)> {
    let n = rows.len();
    let cols: Vec<(&str, ArrayRef)> = vec![
        ("tenant", Arc::new(StringArray::from_iter_values(rows.iter().map(|r| r.tenant.as_str())))),
        (
            "entity_id",
            Arc::new(StringArray::from_iter_values(rows.iter().map(|r| r.entity_id.as_str()))),
        ),
        (
            "metric_id",
            Arc::new(StringArray::from_iter_values(rows.iter().map(|r| r.metric_id.as_str()))),
        ),
        (
            "window_start_ms",
            Arc::new(UInt64Array::from_iter_values(rows.iter().map(|r| r.window_start_ms))),
        ),
        (
            "window_end_ms",
            Arc::new(UInt64Array::from_iter_values(rows.iter().map(|r| r.window_end_ms))),
        ),
        (
            "season_key",
            Arc::new(StringArray::from_iter_values(rows.iter().map(|r| r.season_key.as_str()))),
        ),
        (
            "sample_count",
            Arc::new(UInt32Array::from_iter_values(rows.iter().map(|r| r.sample_count))),
        ),
        (
            "anomaly",
            Arc::new(BooleanArray::from(rows.iter().map(|r| r.anomaly).collect::<Vec<_>>())),
        ),
        (
            "red_lane",
            Arc::new(StringArray::from_iter_values(rows.iter().map(|r| r.red_lane.as_str()))),
        ),
        (
            "current_p50",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.current_p50))),
        ),
        (
            "current_p95",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.current_p95))),
        ),
        (
            "current_p99",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.current_p99))),
        ),
        (
            "expected_p50",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.expected_p50))),
        ),
        (
            "expected_p95",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.expected_p95))),
        ),
        (
            "expected_p99",
            Arc::new(Float64Array::from_iter_values(rows.iter().map(|r| r.expected_p99))),
        ),
    ];
    Ok((cols, n))
}

fn batch_from_cols(cols: Vec<(&str, ArrayRef)>, n: usize) -> Result<RecordBatch> {
    let fields: Fields = cols
        .iter()
        .map(|(name, arr)| Field::new(*name, arr.data_type().clone(), true))
        .collect();
    let schema = Arc::new(Schema::new(fields));
    let arrays: Vec<ArrayRef> = cols.into_iter().map(|(_, a)| a).collect();
    Ok(RecordBatch::try_new(schema, arrays).with_context(|| format!("batch n={n}"))?)
}

fn u32_list_column(rows: &[SketchRow], values_fn: impl Fn(&SketchRow) -> Vec<u32>) -> ArrayRef {
    let mut offsets = Vec::with_capacity(rows.len() + 1);
    let mut values = Vec::new();
    offsets.push(0i32);
    for r in rows {
        values.extend(values_fn(r));
        offsets.push(values.len() as i32);
    }
    let values = Arc::new(UInt32Array::from(values));
    let field = Arc::new(Field::new("item", DataType::UInt32, true));
    Arc::new(ListArray::new(
        field,
        OffsetBuffer::new(offsets.into()),
        values,
        None,
    ))
}

fn binary_tdigest(rows: &[SketchRow]) -> ArrayRef {
    Arc::new(BinaryArray::from_iter_values(rows.iter().map(|r| r.tdigest.as_slice())))
}

fn exemplar_list_columns(rows: &[SketchRow]) -> Result<Vec<(&str, ArrayRef)>> {
    let mut bi = ListBuilder::new(arrow::array::UInt8Builder::new());
    let mut val = ListBuilder::new(arrow::array::Float64Builder::new());
    let mut ts = ListBuilder::new(arrow::array::UInt64Builder::new());
    let mut trace = ListBuilder::new(StringBuilder::new());
    let mut span = ListBuilder::new(StringBuilder::new());
    let mut reason = ListBuilder::new(StringBuilder::new());
    let mut conf = ListBuilder::new(arrow::array::Float32Builder::new());

    for r in rows {
        for e in &r.exemplars {
            bi.values().append_value(e.bucket_index);
            val.values().append_value(e.value);
            ts.values().append_value(e.timestamp_ms);
            trace.values().append_value(&e.trace_id);
            span.values().append_value(&e.span_id);
            reason.values().append_value(&e.reason);
            conf.values().append_value(e.confidence);
        }
        bi.append(true);
        val.append(true);
        ts.append(true);
        trace.append(true);
        span.append(true);
        reason.append(true);
        conf.append(true);
    }

    Ok(vec![
        ("exemplar_bucket_index", Arc::new(bi.finish())),
        ("exemplar_value", Arc::new(val.finish())),
        ("exemplar_timestamp_ms", Arc::new(ts.finish())),
        ("exemplar_trace_id", Arc::new(trace.finish())),
        ("exemplar_span_id", Arc::new(span.finish())),
        ("exemplar_reason", Arc::new(reason.finish())),
        ("exemplar_confidence", Arc::new(conf.finish())),
    ])
}

fn nested_evidence_struct(rows: &[SketchRow]) -> Result<ArrayRef> {
    let tdigest = binary_tdigest(rows);
    let bucket_schema_id = Arc::new(UInt32Array::from_iter_values(
        rows.iter().map(|r| r.bucket_schema_id),
    )) as ArrayRef;
    let bucket_counts = u32_list_column(rows, |r| r.bucket_counts.to_vec());
    let mut fields = vec![
        (
            Arc::new(Field::new("tdigest", tdigest.data_type().clone(), true)),
            tdigest,
        ),
        (
            Arc::new(Field::new(
                "bucket_schema_id",
                bucket_schema_id.data_type().clone(),
                true,
            )),
            bucket_schema_id,
        ),
        (
            Arc::new(Field::new(
                "bucket_counts",
                bucket_counts.data_type().clone(),
                true,
            )),
            bucket_counts,
        ),
    ];
    for (name, arr) in exemplar_list_columns(rows)? {
        fields.push((
            Arc::new(Field::new(name, arr.data_type().clone(), true)),
            arr,
        ));
    }
    let (flds, arrays): (Vec<_>, Vec<_>) = fields.into_iter().unzip();
    Ok(Arc::new(StructArray::new(flds.into(), arrays, None)))
}

pub fn batch_nested(rows: &[SketchRow]) -> Result<RecordBatch> {
    let (mut cols, n) = spine_cols(rows)?;
    // Nested logical groups as struct columns.
    let tdigest_struct = {
        let data = binary_tdigest(rows);
        let compression = Arc::new(UInt32Array::from(vec![100u32; n])) as ArrayRef;
        let encoding = Arc::new(StringArray::from(vec!["centroids_v1"; n])) as ArrayRef;
        Arc::new(StructArray::new(
            vec![
                Arc::new(Field::new("compression", DataType::UInt32, true)),
                Arc::new(Field::new("encoding", DataType::Utf8, true)),
                Arc::new(Field::new("data", data.data_type().clone(), true)),
            ]
            .into(),
            vec![compression, encoding, data],
            None,
        )) as ArrayRef
    };
    let buckets_struct = {
        let schema_version = Arc::new(StringArray::from(vec!["latency_v1"; n])) as ArrayRef;
        let bounds = u32_list_column(rows, |_| LATENCY_BOUNDS.to_vec());
        let counts = u32_list_column(rows, |r| r.bucket_counts.to_vec());
        Arc::new(StructArray::new(
            vec![
                Arc::new(Field::new("schema_version", DataType::Utf8, true)),
                Arc::new(Field::new("bounds", bounds.data_type().clone(), true)),
                Arc::new(Field::new("counts", counts.data_type().clone(), true)),
            ]
            .into(),
            vec![schema_version, bounds, counts],
            None,
        )) as ArrayRef
    };
    let exemplars = nested_exemplar_list(rows)?;
    cols.push(("tdigest", tdigest_struct));
    cols.push(("buckets", buckets_struct));
    cols.push(("exemplars", exemplars));
    batch_from_cols(cols, n)
}

fn nested_exemplar_list(rows: &[SketchRow]) -> Result<ArrayRef> {
    // List<Struct{...}> — natural nested sketch.v2 exemplars[].
    let struct_fields = Fields::from(vec![
        Field::new("bucket_index", DataType::UInt8, true),
        Field::new("value", DataType::Float64, true),
        Field::new("timestamp_ms", DataType::UInt64, true),
        Field::new("trace_id", DataType::Utf8, true),
        Field::new("span_id", DataType::Utf8, true),
        Field::new("reason", DataType::Utf8, true),
        Field::new("confidence", DataType::Float32, true),
    ]);
    let mut offsets = Vec::with_capacity(rows.len() + 1);
    offsets.push(0i32);
    let mut bi = Vec::new();
    let mut val = Vec::new();
    let mut ts = Vec::new();
    let mut trace = Vec::<Option<&str>>::new();
    let mut span = Vec::<Option<&str>>::new();
    let mut reason = Vec::<Option<&str>>::new();
    let mut conf = Vec::new();
    // Keep owned strings alive
    let owned: Vec<(String, String, String)> = rows
        .iter()
        .flat_map(|r| {
            r.exemplars
                .iter()
                .map(|e| (e.trace_id.clone(), e.span_id.clone(), e.reason.clone()))
        })
        .collect();
    let mut owned_i = 0usize;
    for r in rows {
        for e in &r.exemplars {
            bi.push(Some(e.bucket_index));
            val.push(Some(e.value));
            ts.push(Some(e.timestamp_ms));
            conf.push(Some(e.confidence));
            let (t, s, re) = &owned[owned_i];
            owned_i += 1;
            trace.push(Some(t.as_str()));
            span.push(Some(s.as_str()));
            reason.push(Some(re.as_str()));
        }
        offsets.push(bi.len() as i32);
    }
    let struct_arr = StructArray::new(
        struct_fields.clone(),
        vec![
            Arc::new(UInt8Array::from(bi)),
            Arc::new(Float64Array::from(val)),
            Arc::new(UInt64Array::from(ts)),
            Arc::new(StringArray::from(trace)),
            Arc::new(StringArray::from(span)),
            Arc::new(StringArray::from(reason)),
            Arc::new(Float32Array::from(conf)),
        ],
        None,
    );
    let list_field = Arc::new(Field::new("item", DataType::Struct(struct_fields), true));
    Ok(Arc::new(ListArray::new(
        list_field,
        OffsetBuffer::new(offsets.into()),
        Arc::new(struct_arr),
        None,
    )))
}

pub fn batch_flat(rows: &[SketchRow], include_bounds: bool) -> Result<RecordBatch> {
    let (mut cols, n) = spine_cols(rows)?;
    cols.push(("tdigest", binary_tdigest(rows)));
    cols.push((
        "bucket_schema_id",
        Arc::new(UInt32Array::from_iter_values(rows.iter().map(|r| r.bucket_schema_id))),
    ));
    if include_bounds {
        cols.push(("bucket_bounds", u32_list_column(rows, |_| LATENCY_BOUNDS.to_vec())));
    }
    cols.push((
        "bucket_counts",
        u32_list_column(rows, |r| r.bucket_counts.to_vec()),
    ));
    cols.extend(exemplar_list_columns(rows)?);
    // Pad names so BUCKET_COUNT is referenced (documentation).
    let _ = BUCKET_COUNT;
    batch_from_cols(cols, n)
}

pub fn batch_spine_nested_cold(rows: &[SketchRow]) -> Result<RecordBatch> {
    let (mut cols, n) = spine_cols(rows)?;
    cols.push(("cold_evidence", nested_evidence_struct(rows)?));
    batch_from_cols(cols, n)
}

pub fn batches_split(rows: &[SketchRow]) -> Result<(RecordBatch, RecordBatch, RecordBatch)> {
    let n = rows.len();
    let row_id: ArrayRef = Arc::new(UInt64Array::from_iter_values(0..n as u64));
    let (mut spine_cols, _) = spine_cols(rows)?;
    spine_cols.insert(0, ("row_id", row_id.clone()));
    let spine = batch_from_cols(spine_cols, n)?;

    let dist = batch_from_cols(
        vec![
            ("row_id", row_id.clone()),
            ("tdigest", binary_tdigest(rows)),
            (
                "bucket_schema_id",
                Arc::new(UInt32Array::from_iter_values(rows.iter().map(|r| r.bucket_schema_id))),
            ),
            (
                "bucket_counts",
                u32_list_column(rows, |r| r.bucket_counts.to_vec()),
            ),
        ],
        n,
    )?;

    let mut ex_cols = vec![("row_id", row_id)];
    ex_cols.extend(exemplar_list_columns(rows)?);
    let ex = batch_from_cols(ex_cols, n)?;
    Ok((spine, dist, ex))
}
