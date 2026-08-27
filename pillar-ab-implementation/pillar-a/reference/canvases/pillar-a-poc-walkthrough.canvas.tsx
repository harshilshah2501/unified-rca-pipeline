import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from "cursor/canvas";

type StepId =
  | "map"
  | "inputs"
  | "admit"
  | "process"
  | "artifacts"
  | "detect"
  | "isolate";

const STEPS: { id: StepId; label: string; blurb: string }[] = [
  { id: "map", label: "1 · Map", blurb: "Where Pillar A sits in the PoC" },
  { id: "inputs", label: "2 · Inputs", blurb: "One admit job — examples + field wiring" },
  { id: "admit", label: "3 · Admit tree", blurb: "Junk filtered here (not at E5)" },
  { id: "process", label: "4 · Process", blurb: "Window → digest → buckets → baseline" },
  { id: "artifacts", label: "5 · Artifacts", blurb: "Real flush from unit-tested writer" },
  { id: "detect", label: "6 · Detect + FP", blurb: "Where false positives are stopped" },
  { id: "isolate", label: "7 · Isolate A/B", blurb: "What is already split; what to restructure" },
];

/** Observed 2026-08-26 from SketchWriter on fixtures/lab_checkout/stream.resolved.jsonl */
const FLUSH_ROWS = [
  {
    entity: "checkout-api",
    metric: "request.latency_ms",
    window: "1m",
    start: "03:30:00Z",
    n: 2,
    note: "92.1 + 145.3",
  },
  {
    entity: "checkout-api",
    metric: "request.latency_ms",
    window: "1m",
    start: "03:31:00Z",
    n: 1,
    note: "88.0",
  },
  {
    entity: "checkout-api",
    metric: "request.latency_ms",
    window: "5m",
    start: "03:30:00Z",
    n: 3,
    note: "p95≈145.3 · season Thu-03:00",
  },
  {
    entity: "linux-server-app-01",
    metric: "cpu.utilization_pct",
    window: "1m",
    start: "03:32:00Z",
    n: 2,
    note: "41.0 + 44.5",
  },
  {
    entity: "linux-server-app-01",
    metric: "cpu.utilization_pct",
    window: "5m",
    start: "03:30:00Z",
    n: 2,
    note: "same two CPU points",
  },
];

export default function PillarAPocWalkthrough() {
  const [step, setStep] = useCanvasState<StepId>("step", "map");
  const idx = STEPS.findIndex((s) => s.id === step);
  const meta = STEPS[idx] ?? STEPS[0];

  const go = (id: StepId) => setStep(id);
  const prev = () => {
    if (idx > 0) setStep(STEPS[idx - 1].id);
  };
  const next = () => {
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1].id);
  };

  return (
    <Stack gap={16} style={{ padding: 16, maxWidth: 960 }}>
      <Stack gap={6}>
        <H1>Pillar A PoC — interactive walkthrough</H1>
        <Text tone="secondary" size="small">
          Unit-tested path under pillar-ab-implementation/poc/sketch. Mapped to
          docs/PILLAR_A_PERCENTILES_DEEP_DIVE.md. Lab fixture flush: 10 sketch
          tests passed · 5 sketch.v1 rows · topo lines skipped by admit.
        </Text>
      </Stack>

      <Row gap={8} style={{ flexWrap: "wrap" }}>
        {STEPS.map((s) => (
          <span key={s.id}>
            <Pill
              active={s.id === step}
              tone={s.id === step ? "info" : "neutral"}
              onClick={() => go(s.id)}
            >
              {s.label}
            </Pill>
          </span>
        ))}
      </Row>

      <Row gap={12} style={{ alignItems: "center", justifyContent: "space-between" }}>
        <Stack gap={2}>
          <H2>{meta.label}</H2>
          <Text tone="secondary" size="small">
            {meta.blurb}
          </Text>
        </Stack>
        <Row gap={8}>
          <Button variant="secondary" disabled={idx === 0} onClick={prev}>
            Previous
          </Button>
          <Button
            variant="primary"
            disabled={idx === STEPS.length - 1}
            onClick={next}
          >
            Next
          </Button>
        </Row>
      </Row>

      <Divider />

      {step === "map" && <StepMap />}
      {step === "inputs" && <StepInputs />}
      {step === "admit" && <StepAdmit />}
      {step === "process" && <StepProcess />}
      {step === "artifacts" && <StepArtifacts />}
      {step === "detect" && <StepDetect />}
      {step === "isolate" && <StepIsolate />}
    </Stack>
  );
}

function StepMap() {
  return (
    <Stack gap={14}>
      <Callout tone="info" title="Already import-isolated">
        sketch/ does not import graph/. graph/ does not import sketch/. Both use
        ab_shared/. Only join/ imports both. make test-sketch runs Pillar A alone
        (10 passed).
      </Callout>
      <Grid columns={3} gap={12}>
        <Stat value="sketch/" label="Pillar A package" tone="info" />
        <Stat value="graph/" label="Pillar B package" />
        <Stat value="join/" label="Integration only" tone="warning" />
      </Grid>
      <Table
        headers={["Layer", "Path", "Job"]}
        rows={[
          ["Shared stubs", "poc/ab_shared/", "Identity gate, season, dest, ingest, schema"],
          ["Pillar A", "poc/sketch/", "Admit → window → T-Digest/buckets → baseline → flush"],
          ["Pillar B", "poc/graph/", "CI qualify, edges, GraphSnapshot → map/"],
          ["Join", "poc/join/", "Identity join, WorkingSet embryo, door-C flags"],
          ["Fixture", "poc/fixtures/lab_checkout/", "Mixed metric + topo stream (A ignores topo)"],
        ]}
        rowTone={["neutral", "info", "neutral", "warning", "neutral"]}
      />
      <Text size="small" tone="secondary">
        Entry is Make/pytest — no CLI. Programmatic: SketchWriter.ingest(source)
        then .flush(dest).
      </Text>
      <Card>
        <CardHeader>Code spine (Pillar A)</CardHeader>
        <CardBody>
          <Stack gap={6}>
            <Text size="small">
              <Code>metric_admit.admit_metric</Code> →{" "}
              <Code>windowing.assignments</Code> (+{" "}
              <Code>HourOfWeekSeason</Code>) → <Code>TDigestAdapter</Code> +{" "}
              <Code>Histogram</Code> → <Code>SketchWriter.build_row</Code> →{" "}
              <Code>dest.put("history", "sketches.jsonl")</Code>
            </Text>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}

function StepInputs() {
  return (
    <Stack gap={14}>
      <Callout tone="info" title="One job, two views (not two sub-jobs)">
        Admit metric samples into the sketch writer. The tables below are the same
        step seen two ways: which lab lines, then how each line’s fields are read.
      </Callout>

      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader>View A — which lines (lab)</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                5 metric_sample rows in stream.resolved.jsonl after E2 already stamped
                resolved identity.
              </Text>
              <Table
                headers={["entity", "metric", "values"]}
                rows={[
                  ["checkout-api", "latency", "92.1, 145.3, 88.0"],
                  ["linux-server-app-01", "cpu %", "41.0, 44.5"],
                ]}
              />
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>View B — field wiring (admit)</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text size="small">
                Same admit_metric step: copy/check fields on each line.
              </Text>
              <Table
                headers={["From line", "Into sample"]}
                rows={[
                  ["ci_id", "entity_id"],
                  ["name / metric_id", "metric_id"],
                  ["value", "value"],
                  ["ts", "ts (windows later)"],
                  ["identity.status", "gate: resolved only"],
                ]}
              />
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Callout tone="neutral" title="Topo lines in the same file">
        5 topo_update rows (runs_on, depends_on, …) are for Pillar B. Admit skips
        non-metric_sample with (None, None) — not a reject. Fixture packaging only;
        not a second Pillar A job.
      </Callout>

      <Text size="small" tone="secondary">
        Placement reminder: Pillar A write is post-E2, parallel to E3 — not inside
        Identity or Topology.
      </Text>
    </Stack>
  );
}

function StepAdmit() {
  return (
    <Stack gap={14}>
      <Text>
        Decision tree implemented in <Code>sketch/metric_admit.py</Code> +{" "}
        <Code>ab_shared/identity_gate.ResolvedOnlyGate</Code>.
      </Text>
      <Card>
        <CardHeader>Admission flowchart (PoC)</CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text size="small">
              signal_class == metric_sample? → no → skip (topo/events ignored)
            </Text>
            <Text size="small">
              identity.status == resolved? → no → reject (reason from gate)
            </Text>
            <Text size="small">
              normalize metric ∈ {"{request.latency_ms, cpu.utilization_pct}"}? → no →
              reject unknown_metric_id
            </Text>
            <Text size="small">value present? → no → reject unknown_metric_id</Text>
            <Text size="small" weight="semibold">
              yes → emit sample dict → windowing
            </Text>
          </Stack>
        </CardBody>
      </Card>
      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader trailing={<Pill tone="success">Lab resolved</Pill>}>
            stream.resolved.jsonl
          </CardHeader>
          <CardBody>
            <Text size="small">
              5 metrics admitted · 5 topo skipped · rejects list empty on flush run.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill tone="warning">Rejects</Pill>}>
            stream.reject.jsonl
          </CardHeader>
          <CardBody>
            <Text size="small">
              Covered in test_flush_read: unresolved / synthesized / unknown metric —
              SketchWriter.rejects accumulates (record, reason).
            </Text>
          </CardBody>
        </Card>
      </Grid>
      <Callout tone="neutral" title="Gap vs deep-dive">
        Exemplars need (latency, trace_id). PoC admit does not pass trace_id through
        yet — optional investigation path not implemented in wave-1 writer.
      </Callout>
    </Stack>
  );
}

function StepProcess() {
  return (
    <Stack gap={14}>
      <Text>
        For each admitted sample, <Code>windowing.assignments(ts)</Code> emits{" "}
        <strong>both</strong> 1m and 5m slots (wave-1). Season via{" "}
        <Code>HourOfWeekSeason</Code> → <Code>Thu-03:00</Code> for this lab clock
        (UTC Thursday 03:xx).
      </Text>
      <Table
        headers={["Sample ts", "1m window_start", "5m window_start", "season_key"]}
        rows={[
          ["03:30:12", "03:30:00Z", "03:30:00Z", "Thu-03:00"],
          ["03:30:18", "03:30:00Z", "03:30:00Z", "Thu-03:00"],
          ["03:31:01", "03:31:00Z", "03:30:00Z", "Thu-03:00"],
          ["03:32:00 CPU", "03:32:00Z", "03:30:00Z", "Thu-03:00"],
        ]}
      />
      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader>T-Digest</CardHeader>
          <CardBody>
            <Text size="small">
              <Code>digest.update(value)</Code> per slot. Checkout 5m live p95 ≈
              145.3 ms (n=3).
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Buckets</CardHeader>
          <CardBody>
            <Text size="small">
              latency_v1 bounds [0,50,100,200,…]. Checkout 5m counts [0,2,1,0,0,0]
              → mass in [50,100) and [100,200).
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Baseline</CardHeader>
          <CardBody>
            <Text size="small">
              SeasonalBaseline per (tenant, entity, metric). First windows copy
              self; later windows average priors. PoC quirk: 1m and 5m share one
              accumulator — baseline mixes resolutions.
            </Text>
          </CardBody>
        </Card>
      </Grid>
      <Callout tone="warning" title="PoC honesty on baseline">
        Deep-dive wants baseline from past same-season windows, not this slice alone.
        With one lab hour of data, build_row often seeds expected_* from early
        observations in the same flush. E5 refresh_baselines is a stub. Multi-day
        history is the real season story.
      </Callout>
    </Stack>
  );
}

function StepArtifacts() {
  return (
    <Stack gap={14}>
      <Row gap={12} style={{ flexWrap: "wrap" }}>
        <Stat value="5" label="sketch.v1 rows flushed" tone="info" />
        <Stat value="history/" label="Dest room (cold stand-in)" />
        <Stat value="sketches.jsonl" label="Object / blob name" />
      </Row>
      <Text>
        <Code>SketchWriter.flush</Code> validates each row against{" "}
        <Code>contracts/schemas/sketch_v1.schema.json</Code>, then{" "}
        <Code>dest.put("history", "sketches.jsonl", …)</Code>. MemoryDest in tests;
        FileDest writes poc/out/…/history/ (lab cold stand-in for S3).
      </Text>
      <Table
        headers={["entity_id", "metric_id", "window", "window_start", "n", "notes"]}
        rows={FLUSH_ROWS.map((r) => [
          r.entity,
          r.metric,
          r.window,
          r.start,
          String(r.n),
          r.note,
        ])}
        rowTone={["info", "info", "info", "neutral", "neutral"]}
      />
      <Card>
        <CardHeader>Checkout 5m body (observed)</CardHeader>
        <CardBody>
          <Stack gap={6}>
            <Text size="small">
              season_key Thu-03:00 · buckets counts [0, 2, 1, 0, 0, 0] · digest
              centroids_json (small-n compression collapses means — read live
              quantiles from Digest before centroid round-trip for teaching).
            </Text>
            <Text size="small" tone="secondary">
              Schema requires window + window_start; PoC also stores window_end
              (derived). Matches time-boundary teaching: duration + start.
            </Text>
          </Stack>
        </CardBody>
      </Card>
      <Callout tone="info" title="Hot surface in this PoC">
        There is no Vortex process. sketch_read.load_rows / get_window_percentiles /
        get_metric_baseline play the hot lookup role over the same JSONL. Production
        Motadata shape still wants S3 cold + Vortex hot — see deep-dive §7.3–7.4.
      </Callout>
    </Stack>
  );
}

function StepDetect() {
  return (
    <Stack gap={14}>
      <Callout tone="warning" title="False positives are not all filtered at E5">
        E5 Maintain refreshes seasonal baselines (and graph validity). It does not
        sit after Detect deleting bad alerts. Different junk is stopped at different
        stages.
      </Callout>

      <Table
        headers={["Kind of “false” / junk", "Where it is stopped", "Stage"]}
        rows={[
          [
            "Unresolved / synthesized identity",
            "ResolvedOnlyGate — never enters a sketch",
            "Admit (Pillar A write)",
          ],
          [
            "Unknown metric / missing value",
            "admit_metric reject → SketchWriter.rejects",
            "Admit (Pillar A write)",
          ],
          [
            "Topo / non-metric lines",
            "Silent skip (None, None) — not a sketch",
            "Admit (Pillar A write)",
          ],
          [
            "Busy hour looks like an outage",
            "Digest p95 vs seasonal expected_p95 (baseline E5 keeps fresh)",
            "E6 Detect uses baseline; E5 prepares it",
          ],
          [
            "Duplicate / related signals after fire",
            "Case merge / Curate — not sketch store",
            "E7 Curate (after Detect)",
          ],
        ]}
        rowTone={["info", "info", "neutral", "warning", "neutral"]}
      />

      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader trailing={<Pill tone="info">E6 door C</Pill>}>
            Detect (fire)
          </CardHeader>
          <CardBody>
            <Text size="small">
              Compare digest p95 to baseline expected_p95. Season-aware compare is
              the main FP control for “Monday 9am ≠ incident.” E5’s job is to keep
              that baseline honest over days — not to filter Signals after they fire.
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill tone="neutral">After fire</Pill>}>
            Investigate
          </CardHeader>
          <CardBody>
            <Text size="small">
              Hot-bin from buckets; exemplars optional later. That improves triage
              speed, not the fire/no-fire decision.
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Text size="small" tone="secondary">
        Short answer to “is FP filtering E5?”: only the season half — E5 maintains
        baselines; E6 Detect applies them. Admit already filtered identity/metric
        junk before any sketch existed.
      </Text>
    </Stack>
  );
}

function StepIsolate() {
  return (
    <Stack gap={14}>
      <Callout tone="success" title="Good news">
        Runtime import isolation already holds (AST test). You can teach and unit-test
        Pillar A without loading graph code. Restructuring is about fixtures, dest
        rooms, contracts layout, and mental packaging — not untangling a spaghetti
        import graph.
      </Callout>
      <H3>What still couples A and B</H3>
      <Table
        headers={["Coupling", "Why it hurts a Pillar-A-only walk"]}
        rows={[
          [
            "Mixed lab stream",
            "Metrics and topo_update share one JSONL; A skips topo but readers trip over it",
          ],
          [
            "FileDest always map/ + history/",
            "One Gate B tree implies both rooms even for sketch-only tests",
          ],
          [
            "Shared reject_codes",
            "unknown_metric_id sits next to never_ci_vertex / unknown_relation",
          ],
          [
            "join/ harness",
            "identity_join asserts every sketch entity exists as a graph node",
          ],
          [
            "Single contracts/schemas/",
            "Fine technically; harder to hand a teammate “only A schemas”",
          ],
        ]}
      />
      <H3>Proposed restructure (folders only — not applied yet)</H3>
      <Table
        headers={["Today", "Proposed", "Why"]}
        rows={[
          ["poc/sketch/", "poc/pillar_a_sketch/", "Name matches ownership"],
          ["poc/graph/", "poc/pillar_b_graph/", "Same"],
          ["poc/ab_shared/", "poc/shared/", "Identity, season, dest protocol"],
          ["poc/join/", "poc/integration/", "Only place both pillars meet"],
          [
            "fixtures/lab_checkout/ (mixed)",
            "fixtures/sketch/ + fixtures/graph/ + optional lab_checkout/",
            "A tests never open topo lines",
          ],
          [
            "contracts/schemas/*",
            "contracts/sketch/ + contracts/graph/ + contracts/shared/",
            "Hand A owner only sketch_v1 + ingest slice",
          ],
        ]}
      />
      <Text>
        Suggested make targets after move: <Code>make test-a</Code> ·{" "}
        <Code>make test-b</Code> · <Code>make test-integration</Code> (today:{" "}
        test-sketch / test-graph / test-join).
      </Text>
      <Callout tone="info" title="What to do next together">
        Pick one: (1) keep chatting through a single sample in the debugger, (2)
        apply the folder restructure + fixture split, or (3) add metric-only fixture
        + exemplar field without renaming packages yet.
      </Callout>
    </Stack>
  );
}
