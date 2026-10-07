//! Synthetic sketch.v2-like rows for physical layout experiments.

/// Fixed Motadata-style latency bucket bounds (catalog id 7 in product intent).
pub const LATENCY_BOUNDS: [u32; 7] = [0, 50, 100, 200, 500, 1000, 2000];
pub const BUCKET_COUNT: usize = 8;
pub const TDIGEST_BYTES: usize = 512;
pub const MAX_EXEMPLARS: usize = 4;

#[derive(Debug, Clone)]
pub struct Exemplar {
    pub bucket_index: u8,
    pub value: f64,
    pub timestamp_ms: u64,
    pub trace_id: String,
    pub span_id: String,
    pub reason: String,
    pub confidence: f32,
}

#[derive(Debug, Clone)]
pub struct SketchRow {
    pub tenant: String,
    pub entity_id: String,
    pub metric_id: String,
    pub window_start_ms: u64,
    pub window_end_ms: u64,
    pub season_key: String,
    pub sample_count: u32,
    pub anomaly: bool,
    pub red_lane: String,
    pub current_p50: f64,
    pub current_p95: f64,
    pub current_p99: f64,
    pub expected_p50: f64,
    pub expected_p95: f64,
    pub expected_p99: f64,
    pub tdigest: Vec<u8>,
    pub bucket_schema_id: u32,
    pub bucket_counts: [u32; BUCKET_COUNT],
    pub exemplars: Vec<Exemplar>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum SortOrder {
    /// Generation order: entities interleaved across time (poor zone locality).
    Natural,
    /// Cluster for Stage-1 predicates: tenant → entity → metric → window.
    Clustered,
}

pub fn generate_rows(n: usize, seed: u64, entities: usize, metrics: usize) -> Vec<SketchRow> {
    let entities = entities.max(1);
    let metrics = metrics.max(1);
    let metric_names = [
        "request.latency_ms",
        "http.server.duration",
        "db.query.latency_ms",
        "queue.wait_ms",
    ];
    let red_lanes = ["Duration", "Errors", "Rate"];

    let mut rows = Vec::with_capacity(n);
    for i in 0..n {
        let r = mix(seed, i as u64);
        let ent_i = (r as usize) % entities;
        let met_i = ((r >> 8) as usize) % metrics.min(metric_names.len());
        let window_idx = (r >> 16) % 10_000;
        let window_start = 1_700_000_000_000u64 + window_idx * 300_000;
        let anomaly = (r % 100) < 8; // ~8% anomalous
        let p95 = if anomaly {
            800.0 + (r % 400) as f64
        } else {
            40.0 + (r % 80) as f64
        };
        let expected = 60.0 + ((r >> 3) % 40) as f64;
        let mut counts = [0u32; BUCKET_COUNT];
        let mut remaining = 100u32 + (r % 500) as u32;
        for c in counts.iter_mut().take(BUCKET_COUNT - 1) {
            let take = remaining / 3;
            *c = take;
            remaining = remaining.saturating_sub(take);
        }
        counts[BUCKET_COUNT - 1] = remaining;
        if anomaly {
            counts[5] = counts[5].saturating_add(40);
        }

        let mut exemplars = Vec::new();
        if anomaly || (r % 17) == 0 {
            let k = 1 + ((r as usize) % MAX_EXEMPLARS);
            for e in 0..k {
                let bi = if anomaly { 5u8 } else { (e as u8) % 6 };
                exemplars.push(Exemplar {
                    bucket_index: bi,
                    value: p95 - (e as f64) * 10.0,
                    timestamp_ms: window_start + 60_000 + e as u64 * 1_000,
                    trace_id: format!("T{:016x}", mix(r, e as u64 + 1)),
                    span_id: format!("S{:08x}", mix(r, e as u64 + 99) as u32),
                    reason: if anomaly {
                        "SLOWDOWN_SEVERE_LATENCY".into()
                    } else {
                        "TRACE_BASED".into()
                    },
                    confidence: if anomaly { 0.85 } else { 0.55 },
                });
            }
        }

        let mut tdigest = vec![0u8; TDIGEST_BYTES];
        for (j, b) in tdigest.iter_mut().enumerate() {
            *b = ((r.wrapping_mul(31) + j as u64) % 251) as u8;
        }

        rows.push(SketchRow {
            tenant: "default".into(),
            entity_id: format!("svc-{:04}", ent_i),
            metric_id: metric_names[met_i].into(),
            window_start_ms: window_start,
            window_end_ms: window_start + 300_000,
            season_key: format!("slot-{}", window_idx % 168),
            sample_count: counts.iter().sum(),
            anomaly,
            red_lane: red_lanes[(r as usize) % red_lanes.len()].into(),
            current_p50: p95 * 0.4,
            current_p95: p95,
            current_p99: p95 * 1.2,
            expected_p50: expected * 0.5,
            expected_p95: expected,
            expected_p99: expected * 1.3,
            tdigest,
            bucket_schema_id: 7,
            bucket_counts: counts,
            exemplars,
        });
    }
    rows
}

pub fn sort_rows(rows: &mut [SketchRow], order: SortOrder) {
    match order {
        SortOrder::Natural => {}
        SortOrder::Clustered => {
            rows.sort_by(|a, b| {
                a.tenant
                    .cmp(&b.tenant)
                    .then_with(|| a.entity_id.cmp(&b.entity_id))
                    .then_with(|| a.metric_id.cmp(&b.metric_id))
                    .then_with(|| a.window_start_ms.cmp(&b.window_start_ms))
            });
        }
    }
}

/// Stable mix — not cryptographic; good enough for synthetic diversity.
fn mix(a: u64, b: u64) -> u64 {
    let mut x = a ^ b.wrapping_mul(0x9E37_79B9_7F4A_7C15);
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x.wrapping_mul(0x94D0_49BB_1331_11EB)
}
